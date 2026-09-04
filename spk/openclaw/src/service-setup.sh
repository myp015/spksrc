#!/bin/sh
# OpenClaw (container mode) — DSM package lifecycle + shared helpers.
#
# This package runs OpenClaw as a Docker container managed by the DSM
# "Container Manager" (docker-project resource). The image is FIXED and
# bundled in the SPK (offline install); the OpenClaw app payload lives in a
# persistent volume and self-updates in place via npm.
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
    # Persist the data dir for the non-root web CGI (index.cgi reads this).
    printf '%s\n' "${CONTAINER_DATA_DIR}" > "${SYNOPKG_PKGVAR}/data-dir" 2>/dev/null || true
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
    # Make the config dir/file readable & writable by the DSM web CGI (http)
    # so the settings panel can load/save it WITHOUT root/docker. The container
    # runs as root and can still read/write it too.
    chmod -R a+rX "${CONTAINER_DATA_DIR}/conf" 2>/dev/null || true
    chmod a+rw "${CONTAINER_DATA_DIR}/conf/openclaw.json" 2>/dev/null || true
    # The panel also shows the installed version from the seeded runtime.
    if [ -f "${CONTAINER_DATA_DIR}/runtime/package.json" ]; then
        chmod a+r "${CONTAINER_DATA_DIR}/runtime/package.json" 2>/dev/null || true
    fi
}

stage_container_scripts() {
    if [ -d "${SYNOPKG_PKGDEST}/etc" ]; then
        cp -f "${SYNOPKG_PKGDEST}/etc/entrypoint.sh"       "${CONTAINER_DATA_DIR}/scripts/entrypoint.sh"
        cp -f "${SYNOPKG_PKGDEST}/etc/update-openclaw.sh"  "${CONTAINER_DATA_DIR}/scripts/update-openclaw.sh"
        chmod 755 "${CONTAINER_DATA_DIR}/scripts/entrypoint.sh" "${CONTAINER_DATA_DIR}/scripts/update-openclaw.sh"
    fi
}

# Render the docker-compose files from templates, substituting wizard values.
# Container Manager reads these from target/app/ and manages the container.
render_compose() {
    local app_dir="${SYNOPKG_PKGDEST}/app"
    local tpl_base="${app_dir}/docker-compose.yaml.tpl"
    local tpl_admin="${app_dir}/docker-compose.admin.yaml.tpl"
    [ -f "${tpl_base}" ] || return 0
    mkdir -p "${app_dir}"
    local data_dir port
    data_dir="$(printf '%s' "${CONTAINER_DATA_DIR}" | sed 's|/$||')"
    port="${CONTAINER_GATEWAY_PORT:-58789}"
    # Replace {{DATA_DIR}} and {{GATEWAY_PORT}} placeholders.
    sed -e "s|{{DATA_DIR}}|${data_dir}|g" \
        -e "s|{{GATEWAY_PORT}}|${port}|g" \
        "${tpl_base}" > "${app_dir}/docker-compose.yaml"
    if [ -f "${tpl_admin}" ]; then
        sed -e "s|{{DATA_DIR}}|${data_dir}|g" \
            -e "s|{{GATEWAY_PORT}}|${port}|g" \
            "${tpl_admin}" > "${app_dir}/docker-compose.admin.yaml"
    fi
    chmod 644 "${app_dir}/docker-compose.yaml" "${app_dir}/docker-compose.admin.yaml" 2>/dev/null || true
}

# Allow the DSM web CGI (http user) to invoke the root helper for UI actions
# (status / self-update / logs), which need docker access. postinst runs as
# root (privilege run-as: root) so this write succeeds.
ensure_ui_sudoers() {
    local rule_file="/etc/sudoers.d/openclaw-ui"
    local rule="http ALL=(root) NOPASSWD: ${SYNOPKG_PKGDEST}/scripts/ui-run.sh"
    if [ -d /etc/sudoers.d ]; then
        printf '%s\n' "${rule}" > "${rule_file}"
        chmod 440 "${rule_file}" 2>/dev/null || true
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
    render_compose
    ensure_ui_sudoers
    # Import the FULL bundled container image (offline install, no download).
    # Runs as root (privilege run-as: root) so docker.sock is accessible.
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
    render_compose
    stage_container_scripts
    ensure_ui_sudoers
    load_bundled_image
}

service_preuninst() {
    # Container is managed by Container Manager; it stops/removes it on
    # uninstall. Nothing to do here (avoid touching docker directly).
    :
}

service_postuninst() {
    # best-effort cleanup of any orphaned container name
    if [ -n "${DOCKER_BIN}" ]; then
        "${DOCKER_BIN}" rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    fi
}
