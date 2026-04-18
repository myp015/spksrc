#!/bin/sh

if [ -z "${SYNOPKG_PKGNAME}" ] || [ -z "${SYNOPKG_DSM_VERSION_MAJOR}" ]; then
    echo "Error: Environment variables are not set." 1>&2
    exit 1
fi

if [ "$SYNOPKG_DSM_VERSION_MAJOR" -lt 7 ]; then
    SYNOPKG_PKGVAR="${SYNOPKG_PKGDEST}/var"
fi

SVC_SETUP="$(dirname $0)/service-setup"
if [ -r "${SVC_SETUP}" ]; then
    . "${SVC_SETUP}"
fi

log() {
    mkdir -p "${SYNOPKG_PKGVAR}" >/dev/null 2>&1 || true
    echo "$(date '+%F %T') $*" >> "${LOG_FILE}"
}

docker_cmd() {
    if command -v docker >/dev/null 2>&1; then
        docker "$@"
    elif [ -x /usr/local/bin/docker ]; then
        /usr/local/bin/docker "$@"
    else
        return 127
    fi
}

container_exists() {
    docker_cmd container inspect "${CONTAINER_NAME}" >/dev/null 2>&1
}

container_running() {
    [ "$(docker_cmd inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null)" = "true" ]
}

start_service() {
    service_prestart >/dev/null 2>&1 || true

    if ! docker_cmd info >/dev/null 2>&1; then
        log "docker is not available; cannot start ${CONTAINER_NAME}"
        return 1
    fi

    log "pulling image ${OPENCLAW_IMAGE}"
    docker_cmd pull "${OPENCLAW_IMAGE}" >/dev/null 2>&1 || true

    if container_exists; then
        if container_running; then
            log "container already running"
            return 0
        fi
        log "starting existing container ${CONTAINER_NAME}"
        docker_cmd start "${CONTAINER_NAME}" >/dev/null
        return $?
    fi

    log "creating container ${CONTAINER_NAME}"
    docker_cmd run -d \
      --name "${CONTAINER_NAME}" \
      --restart unless-stopped \
      -e HOME=/home/node \
      -e TERM=xterm-256color \
      -v "${STATE_DIR}:/home/node/.openclaw" \
      -v "${WORKSPACE_DIR}:/home/node/.openclaw/workspace" \
      -p "${HOST_GATEWAY_PORT}:18789" \
      -p "${HOST_BRIDGE_PORT}:18790" \
      "${OPENCLAW_IMAGE}" \
      node dist/index.js gateway --bind lan --port 18789 >/dev/null
}

stop_service() {
    if ! container_exists; then
        return 0
    fi
    if container_running; then
        log "stopping container ${CONTAINER_NAME}"
        docker_cmd stop "${CONTAINER_NAME}" >/dev/null
    fi
}

status_service() {
    if container_running; then
        echo "${SYNOPKG_PKGNAME} is running"
        return 0
    fi
    echo "${SYNOPKG_PKGNAME} is not running"
    return 3
}

case "$1" in
    start)
        start_service
        exit $?
        ;;
    stop)
        stop_service
        exit $?
        ;;
    status)
        status_service
        exit $?
        ;;
    log)
        echo "${LOG_FILE}"
        exit 0
        ;;
    *)
        exit 1
        ;;
esac
