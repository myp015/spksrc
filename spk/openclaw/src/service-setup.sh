#!/bin/sh
# OpenClaw (container mode) — DSM package lifecycle + shared helpers.
#
# This package runs OpenClaw as a Docker container managed by the DSM
# "Container Manager" (docker-project resource). The image is FIXED and
# bundled in the SPK as an offline Docker build context (target/app/openclaw:
# Dockerfile + rootfs.tar.gz, FROM scratch). Container Manager BUILDS the image
# from that context at install time (postreplace, runs as root) — so these
# package scripts never need docker or root. The OpenClaw app payload lives in
# a persistent volume and self-updates in place via npm.
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
# HOME 基目录：所有 OpenClaw 文件位于 ${CONTAINER_OPENCLAW_HOME}/.openclaw
CONTAINER_OPENCLAW_HOME="/volume1/openclaw"
CONTAINER_USER="root"

# Wizard-provided overrides (exported by the DSM installer at install/upgrade).
# 兼容旧字段 wizard_data_dir（旧版安装向导的数据目录即现在的 HOME 基目录）。
WIZARD_OPENCLAW_HOME="${wizard_openclaw_home:-${wizard_data_dir:-${WIZARD_OPENCLAW_HOME:-${WIZARD_DATA_DIR:-}}}}"
WIZARD_GATEWAY_PORT="${wizard_gateway_port:-${WIZARD_GATEWAY_PORT:-}}"
[ -n "${WIZARD_OPENCLAW_HOME}" ] && CONTAINER_OPENCLAW_HOME="${WIZARD_OPENCLAW_HOME}"
[ -n "${WIZARD_GATEWAY_PORT}" ] && CONTAINER_GATEWAY_PORT="${WIZARD_GATEWAY_PORT}"

# Persist wizard choices for postinst/postupgrade (spksrc loads INST_VARIABLES).
save_wizard_variables() {
    [ -n "${INST_VARIABLES}" ] || return 0
    mkdir -p "$(dirname "${INST_VARIABLES}")" 2>/dev/null || true
    [ -n "${WIZARD_OPENCLAW_HOME}" ] && printf 'wizard_openclaw_home=%s\n' "${WIZARD_OPENCLAW_HOME}" >> "${INST_VARIABLES}"
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
        echo "CONTAINER_OPENCLAW_HOME=\"${CONTAINER_OPENCLAW_HOME}\""
    } > "${SYNOPKG_PKGVAR}/container.env"
    chmod 600 "${SYNOPKG_PKGVAR}/container.env"
    # Persist the HOME 基目录 for the non-root web CGI (index.cgi reads this).
    printf '%s\n' "${CONTAINER_OPENCLAW_HOME}" > "${SYNOPKG_PKGVAR}/home-dir" 2>/dev/null || true
    # 兼容旧消费者（旧面板/终端入口读 data-dir）：同步写一份，指向同一 HOME 基目录。
    printf '%s\n' "${CONTAINER_OPENCLAW_HOME}" > "${SYNOPKG_PKGVAR}/data-dir" 2>/dev/null || true
}

ensure_data_dirs() {
    # HOME 布局：所有 OpenClaw 文件在 ${CONTAINER_OPENCLAW_HOME}/.openclaw。
    #   .openclaw/          -> /home/node/.openclaw   （配置 openclaw.json 在此）
    #   .openclaw/runtime   -> /data/runtime          （应用代码，嵌套 bind）
    #   .openclaw/scripts   -> /data/scripts          （entrypoint/update 脚本）
    #
    # DSM 套件脚本以非 root 运行，无法在 /volume1 根（root:root 755）下新建目录，
    # 因此 HOME 基目录必须已存在且对 sc-openclaw 可写（见安装向导说明）。创建失败
    # 时显式失败安装，避免静默装出无法启动的套件。
    if ! mkdir -p "${CONTAINER_OPENCLAW_HOME}/.openclaw/runtime" \
                  "${CONTAINER_OPENCLAW_HOME}/.openclaw/scripts"; then
        echo "[openclaw] FAILED to create HOME directory ${CONTAINER_OPENCLAW_HOME}/.openclaw" >&2
        echo "[openclaw] Please create ${CONTAINER_OPENCLAW_HOME} as root and chown it to sc-openclaw" >&2
        echo "[openclaw] (or pick a HOME under a writable shared folder such as /volume1/docker)" >&2
        exit 1
    fi
    stage_container_scripts
    # Seed an initial OpenClaw config into the volume if none exists yet.
    local conf="${CONTAINER_OPENCLAW_HOME}/.openclaw/openclaw.json"
    if [ ! -f "${conf}" ]; then
        if [ -f "${SYNOPKG_PKGDEST}/app/openclaw/config/openclaw.template.json" ]; then
            cp -f "${SYNOPKG_PKGDEST}/app/openclaw/config/openclaw.template.json" \
                  "${conf}"
        fi
    fi
    # Make the config dir/file readable & writable by the DSM web CGI (http)
    # so the settings panel can load/save it WITHOUT root/docker. The container
    # runs as root and can still read/write it too.
    chmod -R a+rX "${CONTAINER_OPENCLAW_HOME}/.openclaw" 2>/dev/null || true
    chmod a+rw "${conf}" 2>/dev/null || true
    # The panel also shows the installed version from the seeded runtime.
    if [ -f "${CONTAINER_OPENCLAW_HOME}/.openclaw/runtime/package.json" ]; then
        chmod a+r "${CONTAINER_OPENCLAW_HOME}/.openclaw/runtime/package.json" 2>/dev/null || true
    fi
}

stage_container_scripts() {
    if [ -d "${SYNOPKG_PKGDEST}/etc" ]; then
        cp -f "${SYNOPKG_PKGDEST}/etc/entrypoint.sh"       "${CONTAINER_OPENCLAW_HOME}/.openclaw/scripts/entrypoint.sh"
        cp -f "${SYNOPKG_PKGDEST}/etc/update-openclaw.sh"  "${CONTAINER_OPENCLAW_HOME}/.openclaw/scripts/update-openclaw.sh"
        chmod 755 "${CONTAINER_OPENCLAW_HOME}/.openclaw/scripts/entrypoint.sh" "${CONTAINER_OPENCLAW_HOME}/.openclaw/scripts/update-openclaw.sh"
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
    local home_dir port
    home_dir="$(printf '%s' "${CONTAINER_OPENCLAW_HOME}" | sed 's|/$||')"
    port="${CONTAINER_GATEWAY_PORT:-58789}"
    # Replace {{OPENCLAW_HOME}} and {{GATEWAY_PORT}} placeholders.
    sed -e "s|{{OPENCLAW_HOME}}|${home_dir}|g" \
        -e "s|{{GATEWAY_PORT}}|${port}|g" \
        "${tpl_base}" > "${app_dir}/docker-compose.yaml"
    if [ -f "${tpl_admin}" ]; then
        sed -e "s|{{OPENCLAW_HOME}}|${home_dir}|g" \
            -e "s|{{GATEWAY_PORT}}|${port}|g" \
            "${tpl_admin}" > "${app_dir}/docker-compose.admin.yaml"
    fi
    chmod 644 "${app_dir}/docker-compose.yaml" "${app_dir}/docker-compose.admin.yaml" 2>/dev/null || true
}

# NOTE: no static sudoers is written at install time. The panel's 授权面板操作
# flow (root scheduled task, SimplePermissionManager-style) owns
# /etc/sudoers.d/openclaw-ui — writing a docker-less rule here could clobber the
# working one.

# ---- lifecycle hooks ----

initialize_variables() {
    save_wizard_variables
}

service_postinst() {
    mkdir -p "${SYNOPKG_PKGVAR}"
    ensure_data_dirs
    write_container_env
    render_compose
    # The bundled offline image is built by Container Manager's docker-project
    # postreplace from target/app/openclaw (no docker/root needed here).
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
}

service_preuninst() {
    # Container is managed by Container Manager; it stops/removes it on
    # uninstall. Nothing to do here (avoid touching docker directly).
    :
}

service_postuninst() {
    # Container Manager removes the project/container on uninstall; nothing to
    # do here (package scripts have no docker access anyway).
    :
}
