CLIPROXY_BIN="${SYNOPKG_PKGDEST}/bin/cliproxy"
CONFIG_FILE="${SYNOPKG_PKGVAR}/config.yaml"
AUTH_DIR="${SYNOPKG_PKGVAR}/auth"

service_prestart() {
    [ -f "${CONFIG_FILE}" ] || cp -f "${SYNOPKG_PKGDEST}/var/config.yaml" "${CONFIG_FILE}"

    # Ensure auth directory exists in DSM service environment (no $HOME)
    mkdir -p "${AUTH_DIR}"

    # Auto-fix user config that still contains home shorthand (~/ or $HOME)
    if grep -Eq '^[[:space:]]*auth-dir:[[:space:]]*"?~/' "${CONFIG_FILE}"; then
        sed -i 's#^[[:space:]]*auth-dir:[[:space:]]*"\?~/.*#auth-dir: "'"${AUTH_DIR}"'"#' "${CONFIG_FILE}"
    fi
    if grep -Eq '^[[:space:]]*auth-dir:[[:space:]]*"?\$HOME/' "${CONFIG_FILE}"; then
        sed -i 's#^[[:space:]]*auth-dir:[[:space:]]*"\?\$HOME/.*#auth-dir: "'"${AUTH_DIR}"'"#' "${CONFIG_FILE}"
    fi
}

SERVICE_COMMAND="${CLIPROXY_BIN} -config ${CONFIG_FILE}"
SVC_BACKGROUND=yes
SVC_WRITE_PID=yes
