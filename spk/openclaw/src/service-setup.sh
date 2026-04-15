OPENCLAW_IMAGE_DEFAULT="ghcr.io/openclaw/openclaw:v2026.4.14"
OPENCLAW_IMAGE_FILE="${SYNOPKG_PKGVAR}/openclaw-image"
OPENCLAW_IMAGE="${OPENCLAW_IMAGE_DEFAULT}"

if [ -f "${OPENCLAW_IMAGE_FILE}" ]; then
    _img=$(sed -n '1p' "${OPENCLAW_IMAGE_FILE}" | tr -d '\r\n')
    [ -n "${_img}" ] && OPENCLAW_IMAGE="${_img}"
fi

CONTAINER_NAME="syno-openclaw"
STATE_DIR="${SYNOPKG_PKGVAR}"
WORKSPACE_DIR="${SYNOPKG_PKGVAR}/workspace"
CONFIG_FILE="${SYNOPKG_PKGVAR}/openclaw.json"
DEFAULT_CONFIG_FILE="${SYNOPKG_PKGDEST}/var/openclaw.json"
LOG_FILE="${SYNOPKG_PKGVAR}/${SYNOPKG_PKGNAME}.log"

HOST_GATEWAY_PORT="18789"
HOST_BRIDGE_PORT="18790"

service_prestart() {
    mkdir -p "${STATE_DIR}" "${WORKSPACE_DIR}"
    [ -f "${CONFIG_FILE}" ] || cp -f "${DEFAULT_CONFIG_FILE}" "${CONFIG_FILE}"
}

service_postuninst() {
    if command -v docker >/dev/null 2>&1; then
        docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    fi
}
