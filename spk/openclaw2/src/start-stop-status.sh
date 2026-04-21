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

call_func() {
    FUNC="$1"
    if type "${FUNC}" 2>/dev/null | grep -q 'function' 2>/dev/null; then
        echo "Begin ${FUNC}" >> "${LOG_FILE}"
        eval "${FUNC}" >> "${LOG_FILE}" 2>&1
        echo "End ${FUNC}" >> "${LOG_FILE}"
    fi
}

is_running() {
    # 1) PID file check
    if [ -n "${PID_FILE}" ] && [ -f "${PID_FILE}" ]; then
        pid="$(cat "${PID_FILE}" 2>/dev/null)"
        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
            return 0
        fi
    fi

    # 2) fallback process check for monitor entry
    pgrep -f '/var/packages/openclaw2/target/fn-port/server/index.cjs|/volume1/@appstore/openclaw2/fn-port/server/index.cjs' >/dev/null 2>&1
}

start_daemon() {
    if [ -z "${SVC_QUIET}" ]; then
        if [ -z "${SVC_KEEP_LOG}" ]; then
            date > "${LOG_FILE}"
        else
            date >> "${LOG_FILE}"
        fi
    fi

    call_func "service_prestart"

    if is_running; then
        return 0
    fi

    if [ -n "${SVC_CWD}" ]; then
        cd "${SVC_CWD}" || true
    fi

    nohup /bin/sh -c "${SERVICE_COMMAND}" >> "${LOG_FILE}" 2>&1 &
    echo $! > "${PID_FILE}"

    sleep 1
    is_running
}

stop_daemon() {
    if [ -f "${PID_FILE}" ]; then
        pid="$(cat "${PID_FILE}" 2>/dev/null)"
        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
            kill -TERM "${pid}" >> "${LOG_FILE}" 2>&1 || true
            sleep 1
            kill -KILL "${pid}" >> "${LOG_FILE}" 2>&1 || true
        fi
        rm -f "${PID_FILE}" >/dev/null 2>&1 || true
    fi

    pkill -f '/var/packages/openclaw2/target/fn-port/server/index.cjs|/volume1/@appstore/openclaw2/fn-port/server/index.cjs' >/dev/null 2>&1 || true

    call_func "service_poststop"
}

case "$1" in
    start)
        if is_running; then
            echo "${SYNOPKG_PKGNAME} is already running" >> "${LOG_FILE}"
            exit 0
        fi
        echo "Starting ${SYNOPKG_PKGNAME} ..." >> "${LOG_FILE}"
        start_daemon
        exit $?
        ;;
    stop)
        if is_running; then
            echo "Stopping ${SYNOPKG_PKGNAME} ..." >> "${LOG_FILE}"
            stop_daemon
            exit $?
        fi
        echo "${SYNOPKG_PKGNAME} is not running" >> "${LOG_FILE}"
        exit 0
        ;;
    status)
        if is_running; then
            echo "${SYNOPKG_PKGNAME} is running"
            exit 0
        fi
        echo "${SYNOPKG_PKGNAME} is not running"
        exit 3
        ;;
    log)
        if [ -n "${LOG_FILE}" ] && [ -r "${LOG_FILE}" ]; then
            TEMP_LOG_FILE="${SYNOPKG_PKGVAR}/${SYNOPKG_PKGNAME}_temp.log"
            echo "Full log: ${LOG_FILE}" > "${TEMP_LOG_FILE}"
            tail -n100 "${LOG_FILE}" >> "${TEMP_LOG_FILE}"
            echo "${TEMP_LOG_FILE}"
        fi
        exit 0
        ;;
    *)
        exit 1
        ;;
esac
