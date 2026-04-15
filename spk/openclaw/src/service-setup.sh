OPENCLAW_NODE="${SYNOPKG_PKGDEST}/bin/node"
OPENCLAW_APP_DIR="${SYNOPKG_PKGDEST}/app/openclaw"
OPENCLAW_ENTRY="${OPENCLAW_APP_DIR}/dist/index.js"
OPENCLAW_CONFIG_FILE="${SYNOPKG_PKGVAR}/openclaw.json"
OPENCLAW_DEFAULT_CONFIG="${SYNOPKG_PKGDEST}/var/openclaw.json"
OPENCLAW_WORKSPACE="${SYNOPKG_PKGVAR}/workspace"

service_prestart() {
    mkdir -p "${OPENCLAW_WORKSPACE}"
    [ -f "${OPENCLAW_CONFIG_FILE}" ] || cp -f "${OPENCLAW_DEFAULT_CONFIG}" "${OPENCLAW_CONFIG_FILE}"
}

# Force native SPK paths so gateway reads the package-managed config/state.
export OPENCLAW_STATE_DIR="${SYNOPKG_PKGVAR}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_FILE}"
export HOME="${SYNOPKG_PKGVAR}"

SERVICE_COMMAND="${OPENCLAW_NODE} ${OPENCLAW_ENTRY} gateway run --allow-unconfigured --bind lan --port ${SERVICE_PORT}"
SVC_BACKGROUND=yes
SVC_WRITE_PID=yes
SVC_CWD="${OPENCLAW_APP_DIR}"
