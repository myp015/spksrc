#!/bin/sh
# OpenClaw container entrypoint — supervisor for the in-container gateway.
#
# The gateway (openclaw-gateway) runs as a CHILD of this supervisor instead of
# being the container's PID 1, so the panel can stop/start it WITHOUT stopping
# the container (容器保持运行，只有 gateway 停):
#
#   SIGUSR1  stop the gateway gracefully (SIGTERM); keep it stopped.
#   SIGUSR2  start the gateway again (after a stop).
#   SIGKILL to the gateway PID (see .gateway.pid) = force-stop: the loop below
#           treats it as a crash and auto-restarts it (restart: always style).
#   SIGTERM  `docker stop` / Container Manager stop reached the supervisor:
#           forward SIGTERM to the gateway, wait for it to drain, then exit so
#           the container stops cleanly.
#
# The container image is FIXED and serves only as:
#   - the Node.js runtime environment
#   - the initial OpenClaw seed (/app)
# The OpenClaw application itself lives in the persistent volume /data/runtime
# so it can be updated in-place (npm) without changing the image, and updates
# survive container restarts.
set -eu

RUNTIME_DIR="${OPENCLAW_RUNTIME_DIR:-/data/runtime}"
CONF_DIR="${OPENCLAW_CONF_DIR:-/home/node/.openclaw}"
SEED_DIR="/app"
PIDFILE="${RUNTIME_DIR}/.gateway.pid"
# In-container TCP relay: re-dials the gateway on loopback so every connection
# (via docker-proxy) reaches the gateway as a direct-local peer and the WebChat
# device pairing auto-approves instead of prompting (see gateway-relay.cjs).
RELAY_SCRIPT="${OPENCLAW_RELAY_SCRIPT:-/data/scripts/gateway-relay.cjs}"
RELAY_PID=""
# Gateway internal listen: loopback-only on 58788; the relay owns the published
# 58789. Config gateway.port stays 58789 so the panel/URLs keep the public port.
GATEWAY_ARGS="--bind loopback --port 58788"

STOPPED=0
GW_PID=""
STOP_TIMEOUT=8   # seconds to wait for the gateway to drain after SIGTERM

# --- 0. First-start bootstrap (runs as root) ---------------------------------
# On a TRUE first install the package's postinst runs as a NON-root service
# user (sc-openclaw) and cannot create the HOME base (/volume1/openclaw) under
# the root-owned /volume1 root — and this DSM's docker engine does not
# auto-create missing bind-mount source dirs. So instead of binding the
# individual $HOME subdirs, the compose mounts the whole HOME volume at /ocvol
# (always exists), and this bootstrap (as container root):
#   1. creates /ocvol/openclaw/.openclaw/{runtime,scripts} on the host volume
#   2. symlinks the in-container app paths (/home/node/.openclaw,
#      /data/runtime, /data/scripts) into it, so the existing code paths and the
#      config's workspace ($HOME/.openclaw) keep working unchanged
#   3. seeds /data/scripts + the config template from the image (the image also
#      carries its own copies of the container-facing scripts and template, see
#      Makefile ocscripts + gen-dockerfile.py, so we self-heal regardless of
#      what postinst managed to stage on host).
IMAGE_SCRIPTS_DIR="/opt/ocscripts"
IMAGE_TEMPLATE="/opt/openclaw.template.json"
HOST_HOME="${OPENCLAW_HOST_HOME:-/volume1/openclaw}"

if [ -d /ocvol ] && [ -n "${HOST_HOME}" ]; then
    # host_dir = HOST_HOME re-rooted under the mount (e.g.
    # /volume1/openclaw -> /ocvol/openclaw, which IS the host /volume1/openclaw).
    vol_root="$(printf '%s' "${HOST_HOME}" | sed -E 's|^(/[^/]+).*|\1|')"
    host_dir="/ocvol${HOST_HOME#${vol_root}}"
    # Create the HOME base + workspace dirs on the host volume (root-owned).
    mkdir -p "${host_dir}/.openclaw/runtime" "${host_dir}/.openclaw/scripts" 2>/dev/null || true
    chmod 755 "${host_dir}" 2>/dev/null || true
    # Point the in-container app paths at the host HOME via symlinks. Idempotent
    # across restarts; re-done on container recreate from the image. Only
    # replaced when NOT already a symlink (never clobber a real dir that holds
    # live data — with this compose those paths are never binds).
    if [ ! -L "${CONF_DIR}" ]; then
        rm -rf "${CONF_DIR}" 2>/dev/null || true   # image dir: only empty workspace/
        mkdir -p "$(dirname "${CONF_DIR}")" 2>/dev/null || true
        ln -s "${host_dir}/.openclaw" "${CONF_DIR}" 2>/dev/null || true
    fi
    for p in /data/runtime /data/scripts; do
        if [ ! -L "$p" ]; then
            rm -rf "$p" 2>/dev/null || true
            mkdir -p "$(dirname "$p")" 2>/dev/null || true
            ln -s "${host_dir}/.openclaw/$(basename "$p")" "$p" 2>/dev/null || true
        fi
    done
fi

if [ -d "${IMAGE_SCRIPTS_DIR}" ]; then
    # Populate the host-side scripts dir (via the /data/scripts symlink above).
    if [ ! -f "/data/scripts/entrypoint.sh" ]; then
        echo "[openclaw-entry] seeding /data/scripts from image ${IMAGE_SCRIPTS_DIR}"
        mkdir -p /data/scripts 2>/dev/null || true
        cp -a "${IMAGE_SCRIPTS_DIR}/." /data/scripts/ 2>/dev/null || true
        chmod 755 /data/scripts/entrypoint.sh /data/scripts/update-openclaw.sh 2>/dev/null || true
    fi
    # Seed the initial config from the template on first start.
    if [ ! -f "${CONF_DIR}/openclaw.json" ] && [ -f "${IMAGE_TEMPLATE}" ]; then
        echo "[openclaw-entry] seeding config ${CONF_DIR}/openclaw.json from template"
        mkdir -p "${CONF_DIR}" 2>/dev/null || true
        cp -f "${IMAGE_TEMPLATE}" "${CONF_DIR}/openclaw.json" 2>/dev/null || true
        chmod a+rw "${CONF_DIR}/openclaw.json" 2>/dev/null || true
    fi
fi

# --- 1. Seed: copy the fixed image's OpenClaw into the persistent volume ---
if [ ! -f "${RUNTIME_DIR}/openclaw.mjs" ]; then
    echo "[openclaw-entry] seeding runtime from image ${SEED_DIR} -> ${RUNTIME_DIR}"
    mkdir -p "${RUNTIME_DIR}"
    cp -a "${SEED_DIR}/." "${RUNTIME_DIR}/"
    # record the seeded image version so the UI can show base vs. running
    if [ -f "${SEED_DIR}/package.json" ]; then
        seed_ver="$(grep -m1 '"version"' "${SEED_DIR}/package.json" | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
        echo "seeded=${seed_ver:-unknown}" > "${RUNTIME_DIR}/.image-version"
    fi
fi

# --- 2. Optional update marker: if the updater left a request, run it ---
UPDATE_MARKER="${RUNTIME_DIR}/.update-requested"
if [ -f "${UPDATE_MARKER}" ]; then
    echo "[openclaw-entry] update marker present, running updater"
    if [ -x /data/scripts/update-openclaw.sh ]; then
        /data/scripts/update-openclaw.sh || {
            echo "[openclaw-entry] update failed; starting with existing runtime" >&2
        }
    fi
    rm -f "${UPDATE_MARKER}"
fi

# --- 3. Start from the persistent runtime ---
if [ ! -f "${RUNTIME_DIR}/openclaw.mjs" ]; then
    echo "[openclaw-entry] FATAL: no openclaw runtime at ${RUNTIME_DIR}/openclaw.mjs" >&2
    exit 1
fi

rm -f "$PIDFILE"

# --- 3.5 配置可读写性（供 DSM 面板 CGI）---
# 面板 CGI 以非 root（sc-openclaw）运行：models_save 直接以 in-place 写回
# openclaw.json；授权前的终端（pre-auth terminal）也需要在工作区创建文件。
# 容器以 root 运行，gateway 原子保存会重置为 600 并收紧 home 目录权限。
# 这里用容器内的后台轻量循环保持“最小访问面”：.openclaw 目录本身 a+rwx
# （可遍历、面板终端可写）+ openclaw.json a+rw（面板可直接写回），不触碰
# secrets.json / state / agents 等敏感子目录。
(
  while :; do
    chmod a+rwx "${CONF_DIR}" 2>/dev/null || true
    chmod a+rw "${CONF_DIR}/openclaw.json" 2>/dev/null || true
    sleep 20
  done
) &

# --- 3.7 Relay lifecycle -----------------------------------------------------
# The relay only listens while the gateway is meant to be running, so "can I
# connect to the public port" still means "is the gateway up" for the panel's
# socket probes. Start before the gateway; stop with it.
start_relay() {
    [ -f "$RELAY_SCRIPT" ] || { RELAY_PID=""; return 0; }
    if [ -n "$RELAY_PID" ] && kill -0 "$RELAY_PID" 2>/dev/null; then
        return
    fi
    node "$RELAY_SCRIPT" &
    RELAY_PID=$!
    echo "[openclaw-entry] relay started as PID ${RELAY_PID}"
}
stop_relay() {
    if [ -n "$RELAY_PID" ] && kill -0 "$RELAY_PID" 2>/dev/null; then
        kill -TERM "$RELAY_PID" 2>/dev/null || true
        wait "$RELAY_PID" 2>/dev/null || true
    fi
    RELAY_PID=""
}

# --- 4. Signal control ------------------------------------------------------
# SIGUSR1: graceful stop — TERM the gateway (and the relay), keep it stopped.
stop_gateway() {
    STOPPED=1
    stop_relay
    if [ -n "$GW_PID" ] && kill -0 "$GW_PID" 2>/dev/null; then
        kill -TERM "$GW_PID" 2>/dev/null || true
    fi
}
# SIGUSR2: start — clear the stop flag; the main loop launches if not running.
start_gateway() {
    STOPPED=0
}
# SIGTERM (docker stop / Container Manager): forward to the gateway, drain,
# then exit so the container stops cleanly.
forward_term_and_exit() {
    stop_relay
    if [ -n "$GW_PID" ] && kill -0 "$GW_PID" 2>/dev/null; then
        kill -TERM "$GW_PID" 2>/dev/null || true
        i=0
        while [ "$i" -lt "$STOP_TIMEOUT" ] && kill -0 "$GW_PID" 2>/dev/null; do
            sleep 1
            i=$((i+1))
        done
    fi
    rm -f "$PIDFILE"
    exit 0
}
trap stop_gateway USR1
trap start_gateway USR2
trap forward_term_and_exit TERM INT

# --- 5. Main loop: keep the container alive, manage the gateway -------------
cd "${RUNTIME_DIR}"
while :; do
    if [ "$STOPPED" = "1" ]; then
        # Gateway stopped on purpose: hold the container up, wait for SIGUSR2.
        stop_relay
        if [ -n "$GW_PID" ]; then
            wait "$GW_PID" 2>/dev/null || true   # drains the TERM'd gateway
            if kill -0 "$GW_PID" 2>/dev/null; then
                # `wait` was interrupted by a signal and the gateway is still
                # alive (TERM in flight, or a hung gateway ignoring TERM) —
                # keep tracking it, nudge TERM again.
                kill -TERM "$GW_PID" 2>/dev/null || true
            else
                GW_PID=""
                rm -f "$PIDFILE"
            fi
        fi
        sleep 1
        continue
    fi

    start_relay   # relay up first so the public port is ready with the gateway

    if [ -z "$GW_PID" ] || ! kill -0 "$GW_PID" 2>/dev/null; then
        # shellcheck disable=SC2086  # GATEWAY_ARGS is an intentional word split
        node openclaw.mjs gateway --allow-unconfigured $GATEWAY_ARGS "$@" &
        GW_PID=$!
        echo "$GW_PID" > "$PIDFILE"
        echo "[openclaw-entry] gateway started as PID ${GW_PID}"
    fi

    wait "$GW_PID" 2>/dev/null || true
    if [ "$STOPPED" = "1" ]; then
        continue   # stop requested — handled by the stop branch above
    fi
    if kill -0 "$GW_PID" 2>/dev/null; then
        # `wait` was interrupted by a signal (e.g. USR2) but the gateway is
        # still alive — do NOT treat this as a crash, go back to waiting.
        continue
    fi
    # The gateway exited on its own (crash) or was SIGKILL'd by the panel's
    # force-stop: bring it back after a short pause, mirroring restart: always.
    rm -f "$PIDFILE"
    echo "[openclaw-entry] gateway exited; restarting"
    stop_relay
    sleep 2
done
