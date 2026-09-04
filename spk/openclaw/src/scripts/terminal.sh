#!/bin/sh
# OpenClaw bundled terminal (ttyd) lifecycle — host-side helper.
#
# The container itself is managed by Container Manager (docker-project); this
# script only manages the host-side ttyd process that serves the web terminal
# at /openclaw-terminal/ (port 17682).
#
# Usage: terminal.sh {start|stop|status|ensure}
set -u

SYNOPKG_PKGNAME="${SYNOPKG_PKGNAME:-openclaw}"
SYNOPKG_PKGDEST="${SYNOPKG_PKGDEST:-/var/packages/${SYNOPKG_PKGNAME}/target}"
SYNOPKG_PKGVAR="${SYNOPKG_PKGVAR:-/var/packages/${SYNOPKG_PKGNAME}/var}"

TTYD_BIN="${SYNOPKG_PKGDEST}/bin/ttyd"
TTYD_PORT="17682"
TTYD_BASE="/openclaw-terminal/"
PID_FILE="${SYNOPKG_PKGVAR}/openclaw-terminal.pid"
LOG_FILE="${SYNOPKG_PKGVAR}/openclaw-terminal.log"
TERM_ENTRY="${SYNOPKG_PKGDEST}/scripts/openclaw-terminal-entry.sh"

find_docker() {
    for c in docker /usr/local/bin/docker /usr/bin/docker; do
        [ -x "$c" ] && { echo "$c"; return; }
    done
    echo ""
}

is_running() {
    [ -f "$PID_FILE" ] || return 1
    local pid; pid="$(cat "$PID_FILE" 2>/dev/null)"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

start() {
    [ -x "$TTYD_BIN" ] || { echo "ttyd binary missing: $TTYD_BIN"; return 1; }
    [ -x "$TERM_ENTRY" ] || { echo "terminal entry missing: $TERM_ENTRY"; return 1; }
    if is_running; then
        echo "terminal already running"
        return 0
    fi
    # TERMINFO: ttyd needs terminfo for the PTY.
    local terminfo_root="${SYNOPKG_PKGDEST}/share/terminfo"
    [ -d "$terminfo_root" ] || terminfo_root="/usr/share/terminfo"
    # Start ttyd as the invoking (service) user. When granted root (after the
    # one-time authorize flow), it restarts as root so docker commands work.
    TERMINFO="$terminfo_root" nohup "${TTYD_BIN}" \
        -p "${TTYD_PORT}" -6 -a -W \
        --base-path "${TTYD_BASE}" \
        -t titleFixed=OpenClaw \
        -t allow-clipboard-read=true -t allow-clipboard-write=true \
        -t rendererType=canvas \
        "${TERM_ENTRY}" >"${LOG_FILE}" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1
    if is_running; then
        echo "terminal started (port ${TTYD_PORT})"
    else
        echo "terminal failed to start; see ${LOG_FILE}"
        return 1
    fi
}

stop() {
    if is_running; then
        local pid; pid="$(cat "$PID_FILE" 2>/dev/null)"
        kill "$pid" 2>/dev/null
        sleep 1
        kill -9 "$pid" 2>/dev/null
        rm -f "$PID_FILE"
        echo "terminal stopped"
    else
        echo "terminal not running"
    fi
    # also stop any stray ttyd
    pkill -f "${TTYD_BASE}" 2>/dev/null || true
}

status() {
    if is_running; then
        echo "terminal is running (port ${TTYD_PORT})"
        return 0
    fi
    echo "terminal is not running"
    return 1
}

case "$1" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    ensure) is_running || start ;;
    *) echo "Usage: $0 {start|stop|status|ensure}" >&2; exit 1 ;;
esac
