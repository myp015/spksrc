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

# --- 3.5 配置可读性（供 DSM 面板的 http CGI）---
# 面板 CGI 以非 root（http）运行，而容器以 root 写配置：openclaw.json 原子保存
# 会重置为 600，gateway 启动时还会把 home 目录收紧为 700，导致面板（未授权或
# 授权后）都读不到配置。这里用容器内的后台轻量循环保持“最小可读面”：仅
# .openclaw 目录本身 a+rx（可遍历到配置）+ openclaw.json a+r，不触碰
# secrets.json / state / agents 等敏感子目录。
(
  while :; do
    chmod a+rx "${CONF_DIR}" 2>/dev/null || true
    chmod a+r "${CONF_DIR}/openclaw.json" 2>/dev/null || true
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
