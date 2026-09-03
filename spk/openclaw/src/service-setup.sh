#!/bin/sh
# OpenClaw (container mode) — DSM package lifecycle + shared helpers.
#
# This package runs OpenClaw as a Docker container. The image is FIXED; the
# OpenClaw app payload lives in a persistent volume and self-updates in place.
#
# Hooks: initialize_variables, service_postinst, service_preupgrade,
#        service_postupgrade, service_preuninst, service_postuninst.

SYNOPKG_PKGNAME="${SYNOPKG_PKGNAME:-openclaw}"
SYNOPKG_PKGDEST="${SYNOPKG_PKGDEST:-/var/packages/${SYNOPKG_PKGNAME}/target}"
SYNOPKG_PKGVAR="${SYNOPKG_PKGVAR:-/var/packages/${SYNOPKG_PKGNAME}/var}"

# ---- container configuration (same values as start-stop-status) ----
CONTAINER_NAME="openclaw"
CONTAINER_IMAGE="openclaw/openclaw"
CONTAINER_IMAGE_TAG="2026.8.2"
CONTAINER_GATEWAY_PORT="58789"
CONTAINER_DATA_DIR="${SYNOPKG_PKGVAR}/data"
CONTAINER_USER="root"
CONTAINER_EXTRA_ARGS=""

# Allow runtime override persisted by write_container_env().
if [ -r "${SYNOPKG_PKGVAR}/container.env" ]; then
    . "${SYNOPKG_PKGVAR}/container.env"
fi

# Wizard-provided overrides (exported by the DSM installer at install/upgrade).
WIZARD_DATA_DIR="${wizard_data_dir:-${WIZARD_DATA_DIR:-}}"
WIZARD_GATEWAY_PORT="${wizard_gateway_port:-${WIZARD_GATEWAY_PORT:-}}"
[ -n "${WIZARD_DATA_DIR}" ] && CONTAINER_DATA_DIR="${WIZARD_DATA_DIR}"
[ -n "${WIZARD_GATEWAY_PORT}" ] && CONTAINER_GATEWAY_PORT="${WIZARD_GATEWAY_PORT}"

CONTAINER_LOG="${SYNOPKG_PKGVAR}/openclaw.log"

find_docker() {
    for c in docker /usr/local/bin/docker /usr/bin/docker; do
        [ -x "$c" ] && { echo "$c"; return; }
    done
    echo ""
}
DOCKER_BIN="$(find_docker)"

container_exists() { [ -n "${DOCKER_BIN}" ] && "${DOCKER_BIN}" inspect "${CONTAINER_NAME}" >/dev/null 2>&1; }
container_running() {
    [ -n "${DOCKER_BIN}" ] && \
        "${DOCKER_BIN}" inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null | grep -q '^true$'
}

# Persist wizard choices for postinst/postupgrade (spksrc loads INST_VARIABLES).
save_wizard_variables() {
    [ -n "${INST_VARIABLES}" ] || return 0
    mkdir -p "$(dirname "${INST_VARIABLES}")" 2>/dev/null || true
    [ -n "${WIZARD_DATA_DIR}" ] && printf 'wizard_data_dir=%s\n' "${WIZARD_DATA_DIR}" >> "${INST_VARIABLES}"
    [ -n "${WIZARD_GATEWAY_PORT}" ] && printf 'wizard_gateway_port=%s\n' "${WIZARD_GATEWAY_PORT}" >> "${INST_VARIABLES}"
}

# write container.env from wizard variables (called from postinst/postupgrade)
write_container_env() {
    mkdir -p "${SYNOPKG_PKGVAR}"
    {
        echo "CONTAINER_IMAGE=\"${CONTAINER_IMAGE}\""
        echo "CONTAINER_IMAGE_TAG=\"${CONTAINER_IMAGE_TAG}\""
        echo "CONTAINER_GATEWAY_PORT=\"${CONTAINER_GATEWAY_PORT:-58789}\""
        echo "CONTAINER_USER=\"${CONTAINER_USER:-root}\""
        echo "CONTAINER_DATA_DIR=\"${CONTAINER_DATA_DIR}\""
    } > "${SYNOPKG_PKGVAR}/container.env"
    chmod 600 "${SYNOPKG_PKGVAR}/container.env"
}

ensure_data_dirs() {
    mkdir -p "${CONTAINER_DATA_DIR}/runtime" \
             "${CONTAINER_DATA_DIR}/conf" \
             "${CONTAINER_DATA_DIR}/workspace" \
             "${CONTAINER_DATA_DIR}/scripts"
    stage_container_scripts
    # Seed an initial OpenClaw config into the volume if none exists yet.
    if [ ! -f "${CONTAINER_DATA_DIR}/conf/openclaw.json" ]; then
        if [ -f "${SYNOPKG_PKGDEST}/app/openclaw/config/openclaw.template.json" ]; then
            cp -f "${SYNOPKG_PKGDEST}/app/openclaw/config/openclaw.template.json" \
                  "${CONTAINER_DATA_DIR}/conf/openclaw.json"
        fi
    fi
}

stage_container_scripts() {
    if [ -d "${SYNOPKG_PKGDEST}/etc" ]; then
        cp -f "${SYNOPKG_PKGDEST}/etc/entrypoint.sh"       "${CONTAINER_DATA_DIR}/scripts/entrypoint.sh"
        cp -f "${SYNOPKG_PKGDEST}/etc/update-openclaw.sh"  "${CONTAINER_DATA_DIR}/scripts/update-openclaw.sh"
        chmod 755 "${CONTAINER_DATA_DIR}/scripts/entrypoint.sh" "${CONTAINER_DATA_DIR}/scripts/update-openclaw.sh"
    fi
}

# Allow the DSM web CGI (http user) to invoke the root helper for UI actions.
ensure_ui_sudoers() {
    local rule_file="/etc/sudoers.d/openclaw-ui"
    local rule="http ALL=(root) NOPASSWD: ${SYNOPKG_PKGDEST}/scripts/ui-run.sh"
    if [ -d /etc/sudoers.d ]; then
        printf '%s\n' "${rule}" > "${rule_file}"
        chmod 440 "${rule_file}" 2>/dev/null || true
        # Validate before leaving a broken sudoers in place.
        if command -v visudo >/dev/null 2>&1; then
            if ! visudo -c -f "${rule_file}" >/dev/null 2>&1; then
                rm -f "${rule_file}"
            fi
        fi
    fi
}

# ---- lifecycle hooks ----

initialize_variables() {
    save_wizard_variables
}

service_postinst() {
    mkdir -p "${SYNOPKG_PKGVAR}"
    ensure_data_dirs
    write_container_env
    ensure_ui_sudoers
    # Import the FULL bundled container image (offline install, no download).
    load_bundled_image
}

# Import the image bundled inside the SPK (etc/openclaw-image.tar) if not
# already present locally. Offline install — nothing is downloaded.
load_bundled_image() {
    local image_tar="${SYNOPKG_PKGDEST}/etc/openclaw-image.tar"
    [ -n "${DOCKER_BIN}" ] || return 0
    if [ ! -f "${image_tar}" ]; then
        echo "[openclaw] no bundled image tar at ${image_tar}; skipping load" >> "${CONTAINER_LOG}" 2>&1 || true
        return 0
    fi
    if "${DOCKER_BIN}" image inspect "${CONTAINER_IMAGE}:${CONTAINER_IMAGE_TAG}" >/dev/null 2>&1; then
        return 0
    fi
    echo "[openclaw] loading bundled image ${CONTAINER_IMAGE}:${CONTAINER_IMAGE_TAG}" >> "${CONTAINER_LOG}" 2>&1 || true
    "${DOCKER_BIN}" load -i "${image_tar}" >> "${CONTAINER_LOG}" 2>&1 || true
}

service_preupgrade() {
    # keep container running through the upgrade; nothing to stop.
    :
}

service_postupgrade() {
    mkdir -p "${SYNOPKG_PKGVAR}"
    ensure_data_dirs
    write_container_env
    stage_container_scripts
    ensure_ui_sudoers
}

service_preuninst() {
    # Stop and remove the container. The persistent data under PKGVAR is
    # removed by DSM after uninstall.
    if container_exists; then
        if container_running; then
            "${DOCKER_BIN}" stop -t 15 "${CONTAINER_NAME}" >> "${CONTAINER_LOG}" 2>&1 || true
        fi
        "${DOCKER_BIN}" rm "${CONTAINER_NAME}" >> "${CONTAINER_LOG}" 2>&1 || true
    fi
}

service_postuninst() {
    # cleanup legacy container name if present
    "${DOCKER_BIN}" rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
