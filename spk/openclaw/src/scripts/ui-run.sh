#!/bin/sh
# OpenClaw (container mode) — root-privileged helper for the DSM UI.
# The DSM web CGI runs as the http user; it invokes this script via
# `sudo -n /var/packages/openclaw/target/scripts/ui-run.sh <action>`.
#
# Actions operate on the persistent container volume (config) and the fixed
# Docker container. JSON in on stdin for set operations, JSON out on stdout.
set -u

SYNOPKG_PKGNAME="${SYNOPKG_PKGNAME:-openclaw}"
SYNOPKG_PKGDEST="${SYNOPKG_PKGDEST:-/var/packages/${SYNOPKG_PKGNAME}/target}"
SYNOPKG_PKGVAR="${SYNOPKG_PKGVAR:-/var/packages/${SYNOPKG_PKGNAME}/var}"

CONTAINER_NAME="openclaw"
# HOME 基目录：所有 OpenClaw 文件位于 ${CONTAINER_OPENCLAW_HOME}/.openclaw。
# 实际值由 postinst 写入 container.env（向导确定），此处仅为 fallback。
CONTAINER_OPENCLAW_HOME="${SYNOPKG_PKGVAR}/data"
CONTAINER_GATEWAY_PORT="58789"
CONTAINER_IMAGE="openclaw/openclaw"
CONTAINER_IMAGE_TAG="latest"

if [ -r "${SYNOPKG_PKGVAR}/container.env" ]; then
    . "${SYNOPKG_PKGVAR}/container.env"
fi

CONFIG_FILE="${CONTAINER_OPENCLAW_HOME}/.openclaw/openclaw.json"

find_docker() {
    for c in docker /usr/local/bin/docker /usr/bin/docker; do
        [ -x "$c" ] && { echo "$c"; return; }
    done
    echo ""
}
DOCKER="$(find_docker)"

container_running() {
    [ -n "${DOCKER}" ] && \
        "${DOCKER}" inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null | grep -q '^true$'
}

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

config_get() {
    python3 - "$CONFIG_FILE" <<'PY'
import json, os, sys
cfg = sys.argv[1]
data = {}
if cfg and os.path.exists(cfg):
    try:
        data = json.load(open(cfg, 'r', encoding='utf-8'))
    except Exception as e:
        data = {'_readError': f'{type(e).__name__}: {e}'}
print(json.dumps(data, ensure_ascii=False, indent=2))
PY
}

config_set() {
    python3 - "$CONFIG_FILE" <<'PY'
import json, os, sys
cfg = sys.argv[1]
try:
    payload = json.load(sys.stdin)
except Exception as e:
    print(json.dumps({'ok': False, 'error': f'invalid json: {e}'}, ensure_ascii=False))
    sys.exit(0)
try:
    with open(cfg, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'ok': True, 'configPath': cfg}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({'ok': False, 'error': f'{type(e).__name__}: {e}'}, ensure_ascii=False))
PY
}

do_status() {
    local running="false" ver="unknown" image="unknown"
    if container_running; then
        running="true"
        ver="$("${DOCKER}" exec "${CONTAINER_NAME}" sh -c 'grep -m1 "\"version\"" /data/runtime/package.json 2>/dev/null | sed -E "s/.*\"version\"[[:space:]]*:[[:space:]]*\"([^\"]+)\".*/\1/"' 2>/dev/null || echo unknown)"
    fi
    image="$("${DOCKER}" inspect -f '{{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || echo "${CONTAINER_IMAGE}:${CONTAINER_IMAGE_TAG}")"
    python3 -c 'import json,sys; print(json.dumps({"running": %s, "version": %r, "image": %r, "container": %r, "homeDir": %r, "configPath": %r, "port": %r}, ensure_ascii=False))' \
        "$running" "$ver" "$image" "$CONTAINER_NAME" "$CONTAINER_OPENCLAW_HOME" "$CONFIG_FILE" "$CONTAINER_GATEWAY_PORT"
}

do_check_update() {
    local installed="unknown" latest="unknown" updatable="false"
    if container_running; then
        installed="$("${DOCKER}" exec "${CONTAINER_NAME}" sh -c 'grep -m1 "\"version\"" /data/runtime/package.json 2>/dev/null | sed -E "s/.*\"version\"[[:space:]]*:[[:space:]]*\"([^\"]+)\".*/\1/"' 2>/dev/null || echo unknown)"
        latest="$("${DOCKER}" exec "${CONTAINER_NAME}" sh -c 'npm view openclaw version 2>/dev/null || echo unknown' 2>/dev/null || echo unknown)"
    fi
    if [ "$installed" != "unknown" ] && [ "$latest" != "unknown" ] && [ "$installed" != "$latest" ]; then
        updatable="true"
    fi
    python3 -c 'import json,sys; print(json.dumps({"installed": %r, "latest": %r, "updatable": %s}, ensure_ascii=False))' \
        "$installed" "$latest" "$updatable"
}

do_update() {
    local ver="${1:-latest}"
    if ! container_running; then
        echo '{"ok":false,"error":"container not running"}'
        return
    fi
    local out
    out="$("${DOCKER}" exec -i -u root "${CONTAINER_NAME}" /data/scripts/update-openclaw.sh "$ver" 2>&1)"
    local rc=$?
    # restart container to load the new version
    "${DOCKER}" restart "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    python3 -c 'import json,sys; print(json.dumps({"ok": %s, "output": sys.argv[1]}, ensure_ascii=False))' "$([ $rc -eq 0 ] && echo true || echo false)" "$out"
}

do_restart() {
    if [ -n "${DOCKER}" ] && container_running; then
        "${DOCKER}" restart "${CONTAINER_NAME}" >/dev/null 2>&1 && echo '{"ok":true}' || echo '{"ok":false}'
    else
        echo '{"ok":false,"error":"container not running"}'
    fi
}

do_start() {
    "${SYNOPKG_PKGDEST}/scripts/start-stop-status" start >/dev/null 2>&1 && echo '{"ok":true}' || echo '{"ok":false}'
}

do_stop() {
    "${SYNOPKG_PKGDEST}/scripts/start-stop-status" stop >/dev/null 2>&1 && echo '{"ok":true}' || echo '{"ok":false}'
}

do_logs() {
    local n="${1:-200}"
    if [ -n "${DOCKER}" ] && container_running; then
        "${DOCKER}" logs --tail "$n" "${CONTAINER_NAME}" 2>&1 | python3 -c 'import json,sys; print(json.dumps({"logs": sys.stdin.read()}, ensure_ascii=False))'
    else
        python3 -c 'import json; print(json.dumps({"logs": "container not running"}, ensure_ascii=False))'
    fi
}

ACTION="${1:-}"
case "${ACTION}" in
    config_get) config_get ;;
    config_set) config_set ;;
    status) do_status ;;
    check_update) do_check_update ;;
    update) do_update "${2:-latest}" ;;
    restart) do_restart ;;
    start) do_start ;;
    stop) do_stop ;;
    logs) do_logs "${2:-200}" ;;
    *)
        echo "{\"error\":\"unknown action ${ACTION}\"}"
        ;;
esac
