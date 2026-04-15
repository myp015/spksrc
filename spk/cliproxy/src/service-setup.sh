CLIPROXY_BIN="${SYNOPKG_PKGDEST}/bin/cliproxy"
CONFIG_FILE="${SYNOPKG_PKGVAR}/config.yaml"

service_prestart() {
    [ -f "${CONFIG_FILE}" ] || cp -f "${SYNOPKG_PKGDEST}/var/config.yaml" "${CONFIG_FILE}"
}

SERVICE_COMMAND="${CLIPROXY_BIN} -config ${CONFIG_FILE}"
SVC_BACKGROUND=yes
SVC_WRITE_PID=yes
