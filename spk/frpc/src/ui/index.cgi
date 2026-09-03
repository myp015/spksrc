#!/bin/sh

# DSM7 常见实际路径（/var/packages/frpc/* 往往是符号链接）
APP_VAR_DIR="/var/packages/frpc/var"
APP_TARGET_DIR="/var/packages/frpc/target"
if [ -d "/volume1/@appdata/frpc" ]; then
    APP_VAR_DIR="/volume1/@appdata/frpc"
fi
if [ -d "/volume1/@appstore/frpc" ]; then
    APP_TARGET_DIR="/volume1/@appstore/frpc"
fi

CFG_FILE="${APP_VAR_DIR}/frpc.toml"
LOG_FILE="${APP_VAR_DIR}/frpc.log"
PID_FILE="${APP_VAR_DIR}/frpc.pid"
TMP_FILE="/tmp/frpc.toml.$$"

# frp 皮肤：与 .spk 相同的 frp GitHub 官方 logo（base64 data URI）
FRP_LOGO_B64="$(cat "$(dirname "$0")/frp_logo.b64" 2>/dev/null || true)"
[ -n "$FRP_LOGO_B64" ] || FRP_LOGO_B64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC"

html_escape() {
    sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

urldecode() {
    # + -> space, %XX -> byte
    local data
    data=$(printf '%s' "$1" | sed 's/+/ /g;s/%/\\x/g')
    printf '%b' "$data"
}

get_param() {
    # $1: key, $2: query string/form body
    printf '%s' "$2" | tr '&' '\n' | awk -F= -v k="$1" '$1==k{print substr($0, index($0,"=")+1)}' | tail -n1
}

read_post_body() {
    [ -n "$CONTENT_LENGTH" ] || return 0
    [ "$CONTENT_LENGTH" -gt 0 ] 2>/dev/null || return 0
    dd bs=1 count="$CONTENT_LENGTH" 2>/dev/null
}

# 运行状态显示：frpc 是否运行 + PID
frpc_status() {
    # 1) PID 文件优先
    if [ -f "$PID_FILE" ]; then
        pid="$(cat "$PID_FILE" 2>/dev/null | tr -d '[:space:]')"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            printf 'running|%s' "$pid"
            return
        fi
    fi
    # 2) 兜底按进程名匹配
    if command -v pgrep >/dev/null 2>&1; then
        pid="$(pgrep -f "${APP_TARGET_DIR}/bin/frpc" 2>/dev/null | head -n1 | tr -d '[:space:]')"
        if [ -n "$pid" ]; then
            printf 'running|%s' "$pid"
            return
        fi
    else
        # busybox ps：DSM 上 ps 输出格式可能不同，逐列找进程号
        line="$(ps 2>/dev/null | grep -F "${APP_TARGET_DIR}/bin/frpc" | grep -v grep | head -n1)"
        if [ -n "$line" ]; then
            pid="$(printf '%s' "$line" | awk '{print $1}' | tr -d '[:space:]')"
            if [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
                printf 'running|%s' "$pid"
                return
            fi
        fi
    fi
    printf 'stopped|'
}

restart_frpc() {
    # 1) 优先走 synopkg（若 CGI 权限足够）
    if command -v synopkg >/dev/null 2>&1; then
        if synopkg restart frpc >/dev/null 2>&1; then
            return 0
        fi
    fi

    # 2) 走标准脚本
    if [ -x /var/packages/frpc/scripts/start-stop-status ]; then
        /var/packages/frpc/scripts/start-stop-status stop >/dev/null 2>&1 || true
        /var/packages/frpc/scripts/start-stop-status start >/dev/null 2>&1 || true
        sleep 1
        if /var/packages/frpc/scripts/start-stop-status status >/dev/null 2>&1; then
            return 0
        fi
    fi

    # 3) 最后兜底：直接拉起进程（兼容权限/状态异常场景）
    pkill -f "${APP_TARGET_DIR}/bin/frpc -c ${CFG_FILE}" >/dev/null 2>&1 || true
    nohup "${APP_TARGET_DIR}/bin/frpc" -c "${CFG_FILE}" >> "${LOG_FILE}" 2>&1 &
    echo $! > "${PID_FILE}" 2>/dev/null || true
    sleep 1
    kill -0 $! >/dev/null 2>&1
}

METHOD="${REQUEST_METHOD:-GET}"
QUERY="${QUERY_STRING:-}"
SAVED_MSG=""

ACTION_RAW=$(get_param "action" "$QUERY")
ACTION=$(urldecode "$ACTION_RAW")

if [ "$METHOD" = "GET" ] && [ "$ACTION" = "log" ]; then
    printf 'Content-type: text/plain; charset=UTF-8\r\n\r\n'
    if [ -f "$LOG_FILE" ]; then
        tail -n 400 "$LOG_FILE"
    else
        echo "日志文件不存在：$LOG_FILE"
    fi
    exit 0
fi

if [ "$METHOD" = "GET" ] && [ "$ACTION" = "status" ]; then
    printf 'Content-type: text/plain; charset=UTF-8\r\n\r\n'
    frpc_status
    exit 0
fi

if [ "$METHOD" = "POST" ]; then
    BODY=$(read_post_body)
    RAW_CONTENT=$(get_param "textcontent" "$BODY")
    NEW_CONTENT=$(urldecode "$RAW_CONTENT")

    if [ -n "$NEW_CONTENT" ]; then
        printf '%s' "$NEW_CONTENT" > "$TMP_FILE"
        sed -i 's/\r$//' "$TMP_FILE" 2>/dev/null || true
        mv "$TMP_FILE" "$CFG_FILE"
        chmod 644 "$CFG_FILE" 2>/dev/null || true

        if restart_frpc; then
            SAVED_MSG="保存成功，frpc 已重启。"
        else
            SAVED_MSG="保存成功，但重启失败，请手工执行：${APP_TARGET_DIR}/bin/frpc -c ${CFG_FILE}"
        fi
    else
        SAVED_MSG="未检测到可保存内容。"
    fi
fi

[ -f "$CFG_FILE" ] || touch "$CFG_FILE"
CFG_CONTENT=$(cat "$CFG_FILE" 2>/dev/null | html_escape)

# 当前运行状态
STATUS="$(frpc_status)"
STATUS_STATE="${STATUS%%|*}"
STATUS_PID="${STATUS#*|}"
case "$STATUS_STATE" in
    running) STATUS_HTML="<span class=\"status-dot running\"></span>运行中<span class=\"status-pid\">PID: ${STATUS_PID}</span>"; STATUS_CLASS="running" ;;
    *)       STATUS_HTML="<span class=\"status-dot stopped\"></span>未运行<span class=\"status-pid\"></span>"; STATUS_CLASS="stopped" ;;
esac

printf 'Content-type: text/html\r\n\r\n'
cat <<HTML
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<title>frpc 配置</title>
<style>
html, body { height: 100%; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; padding: 0; background: #f5f6f7; overflow: hidden; }
.wrapper { max-width: 1080px; height: calc(100vh - 40px); margin: 20px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,.08); padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; }
.header { display: flex; align-items: center; gap: 16px; margin-bottom: 12px; }
.header img { height: 48px; }
.header h2 { margin: 0; font-size: 20px; }
.desc { color: #666; margin-bottom: 12px; }
.status-bar { display: flex; align-items: center; gap: 8px; background: #f7f9fc; border: 1px solid #e3e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 14px; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.status-dot.running { background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,.2); }
.status-dot.stopped { background: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,.2); }
.status-bar.running { color: #15803d; }
.status-bar.stopped { color: #b91c1c; }
.status-pid { margin-left: 8px; color: #6b7280; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.msg { margin: 10px 0; color: #0a7a0a; font-weight: 600; min-height: 20px; }
form { display: flex; flex-direction: column; flex: 1; min-height: 0; }
textarea { width: 100%; flex: 1; min-height: 220px; border: 1px solid #d0d7de; border-radius: 8px; padding: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 13px; line-height: 1.4; box-sizing: border-box; resize: none; }
.actions { margin-top: 12px; display: flex; gap: 10px; align-items: center; }
button { border: 0; background: #1E90FF; color: white; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-family: "Microsoft YaHei", sans-serif; }
button:hover { background: #5599FF; }
button.secondary { background: #5d6778; }
button.secondary:hover { background: #76839a; }
small { color: #888; display: block; margin-top: 8px; }
#logBox { display:none; margin-top: 12px; border: 1px solid #d0d7de; border-radius: 8px; padding: 10px; background: #fafafa; max-height: 240px; overflow: auto; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12px; }
a { text-decoration: none; }
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <a href="https://github.com/fatedier/frp" target="_blank"><img src="data:image/png;base64,${FRP_LOGO_B64}" alt="frp" /></a>
    <div>
      <h2>frpc 配置编辑器</h2>
      <div class="desc">编辑并保存 <code>${CFG_FILE}</code>。保存后会尝试重启 frpc。</div>
    </div>
  </div>
  <div class="status-bar ${STATUS_CLASS}" id="statusBar">
    <span class="status-dot ${STATUS_CLASS}"></span>
    <span id="statusText">$STATUS_HTML</span>
  </div>
  <div class="msg" id="statusMsg">$SAVED_MSG</div>
  <form method="post" action="index.cgi?$QUERY">
    <textarea name="textcontent">$CFG_CONTENT</textarea>
    <div class="actions">
      <button type="submit">保存并重启</button>
      <button class="secondary" type="button" onclick="loadLog()">查看当前日志</button>
      <button class="secondary" type="button" onclick="toggleLog()">收起/展开日志</button>
      <button class="secondary" id="autoBtn" type="button" onclick="toggleAutoRefresh()">开启实时刷新日志(2秒)</button>
      <button class="secondary" type="button" onclick="refreshStatus()">刷新状态</button>
    </div>
    <small>提示：若 frps 地址不可达，frpc 可能会退出（日志见 $LOG_FILE）。</small>
    <div id="logBox">点击“查看当前日志”加载。</div>
  </form>
</div>
<script>
var autoTimer = null;

function buildUrl(action) {
  var qs = window.location.search || '';
  var sep = qs.indexOf('?') === -1 ? '?' : '&';
  return 'index.cgi' + qs + sep + 'action=' + action + '&_=' + Date.now();
}

function loadLog() {
  var box = document.getElementById('logBox');
  box.style.display = 'block';
  if (!box.dataset.loaded) {
    box.textContent = '加载日志中...';
  }
  fetch(buildUrl('log'), { cache: 'no-store' })
    .then(function(r){ return r.text(); })
    .then(function(t){
      box.textContent = t || '日志为空';
      box.dataset.loaded = '1';
      box.scrollTop = box.scrollHeight;
    })
    .catch(function(e){ box.textContent = '读取日志失败：' + e; });
}

function refreshStatus() {
  var bar = document.getElementById('statusBar');
  var txt = document.getElementById('statusText');
  fetch(buildUrl('status'), { cache: 'no-store' })
    .then(function(r){ return r.text(); })
    .then(function(s){
      s = (s || '').trim();
      var state = s.split('|')[0];
      var pid = s.split('|')[1] || '';
      var running = (state === 'running');
      bar.className = 'status-bar ' + (running ? 'running' : 'stopped');
      var dot = bar.querySelector('.status-dot');
      dot.className = 'status-dot ' + (running ? 'running' : 'stopped');
      txt.innerHTML = running
        ? '<span class="status-dot running"></span>运行中<span class="status-pid">PID: ' + pid + '</span>'
        : '<span class="status-dot stopped"></span>未运行<span class="status-pid"></span>';
    })
    .catch(function(){});
}

function toggleLog() {
  var box = document.getElementById('logBox');
  box.style.display = (box.style.display === 'none' || !box.style.display) ? 'block' : 'none';
}

function toggleAutoRefresh() {
  var btn = document.getElementById('autoBtn');
  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = null;
    btn.textContent = '开启实时刷新日志(2秒)';
    return;
  }
  loadLog();
  autoTimer = setInterval(loadLog, 2000);
  btn.textContent = '关闭自动刷新';
}

window.addEventListener('beforeunload', function(){
  if (autoTimer) clearInterval(autoTimer);
});

(function autoClearStatusMsg(){
  var msg = document.getElementById('statusMsg');
  if (!msg) return;
  if ((msg.textContent || '').trim().length === 0) return;
  setTimeout(function(){ msg.textContent = ''; }, 3500);
})();
</script>
</body>
</html>
HTML