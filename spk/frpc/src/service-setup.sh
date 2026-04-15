FRPC_BIN="${SYNOPKG_PKGDEST}/bin/frpc"
CONFIG_FILE="${SYNOPKG_PKGVAR}/frpc.toml"

# 保证“先能启动、再进设置页修配置”的体验：
# 若配置里未显式设置 loginFailExit，则默认补上 false，避免连接失败时进程秒退。
ensure_login_fail_exit_default() {
    [ -f "${CONFIG_FILE}" ] || touch "${CONFIG_FILE}"
    if ! grep -Eq '^[[:space:]]*loginFailExit[[:space:]]*=' "${CONFIG_FILE}"; then
        printf '\nloginFailExit = false\n' >> "${CONFIG_FILE}"
    fi
}

service_prestart() {
    ensure_login_fail_exit_default
}

SERVICE_COMMAND="${FRPC_BIN} -c ${CONFIG_FILE}"
SVC_BACKGROUND=yes
SVC_WRITE_PID=yes
