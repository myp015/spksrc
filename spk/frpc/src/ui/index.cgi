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

html_escape() {
    sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

urldecode() {
    # + -> space, %XX -> byte
    # 单个 awk 按字节解码（仅用 POSIX index/substr/sprintf/%c，兼容
    # dash/mawk 与 DSM 的 busybox awk）。不用 printf %b 的 \x/\OOO 转义：
    # dash 的 %b 会贪婪多读八进制位（如 \042127 会变成 0x11 + "27"）。
    printf '%s' "$1" | awk '
    { s = s $0 }
    END {
        out = ""
        n = length(s)
        HEX = "0123456789abcdefABCDEF"
        i = 1
        while (i <= n) {
            c = substr(s, i, 1)
            if (c == "%" && i + 2 <= n) {
                hi = substr(s, i + 1, 1)
                lo = substr(s, i + 2, 1)
                hv = index(HEX, hi)
                lv = index(HEX, lo)
                if (hv > 0 && lv > 0) {
                    v = (hv > 16 ? hv - 7 : hv - 1) * 16 + (lv > 16 ? lv - 7 : lv - 1)
                    out = out sprintf("%c", v)
                    i = i + 3
                    continue
                }
                out = out "%"
                i = i + 1
                continue
            }
            if (c == "+") { out = out " "; i = i + 1; continue }
            out = out c
            i = i + 1
        }
        printf "%s", out
    }'
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
# 判断 frpc 是否真正连上 frps（依据 frpc.log 中最后一次连接标志）
frpc_connected() {
    # 优先用 netstat 检测 frpc 是否有 ESTABLISHED TCP 连接（实时、准确）。
    # 连接失败/重连中 frpc 处于 SYN_SENT（不是 ESTABLISHED）→ 判定未连接。
    # 日志末尾标志有 i/o timeout 写入延迟，刚重启/断线时可能误判为已连接。
    if command -v netstat >/dev/null 2>&1; then
        netstat -anp 2>/dev/null | grep -F "frpc" | grep -q "ESTABLISHED" && return 0
        return 1
    fi
    # netstat 不可用时回退日志检测
    [ -f "$LOG_FILE" ] || return 1
    last="$(grep -E 'login to server (success|failed)|connect to server error|start proxy success' "$LOG_FILE" 2>/dev/null | tail -n1)"
    case "$last" in
        *"login to server success"*|*"start proxy success"*) return 0 ;;
        *) return 1 ;;
    esac
}

frpc_status() {
    # 1) 进程是否存活（PID 文件优先）
    local pid=""
    if [ -f "$PID_FILE" ]; then
        pid="$(cat "$PID_FILE" 2>/dev/null | tr -d '[:space:]')"
        if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
            pid=""
        fi
    fi
    if [ -z "$pid" ] && command -v pgrep >/dev/null 2>&1; then
        pid="$(pgrep -f "${APP_TARGET_DIR}/bin/frpc" 2>/dev/null | head -n1 | tr -d '[:space:]')"
    fi
    if [ -z "$pid" ]; then
        # busybox ps：DSM 上 ps 输出格式可能不同，逐列找进程号
        line="$(ps 2>/dev/null | grep -F "${APP_TARGET_DIR}/bin/frpc" | grep -v grep | head -n1)"
        if [ -n "$line" ]; then
            pid="$(printf '%s' "$line" | awk '{print $1}' | tr -d '[:space:]')"
            [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null || pid=""
        fi
    fi

    # 进程不存在 → 已停止
    if [ -z "$pid" ]; then
        printf 'stopped|'
        return
    fi

    # 进程存活，但需确认真正连上 frps（连接失败也视为已停止）
    if frpc_connected; then
        printf 'running|%s' "$pid"
    else
        printf 'stopped|'
    fi
}

restart_frpc() {
    # 快速路径（与 .spk 的 index.cgi 一致）：SIGKILL 强制终止 + nohup 直接拉起
    # frpc 是 Go 程序，SIGTERM 会触发优雅退出并等待连接清理，可能耗时数秒；
    # 用 -9 强制立即终止即可跳过 wait_for_status 的秒级轮询等待，实现点击保存秒级重启。
    if command -v pkill >/dev/null 2>&1; then
        pkill -9 -f "${APP_TARGET_DIR}/bin/frpc" >/dev/null 2>&1 || true
    else
        killall -9 frpc >/dev/null 2>&1 || true
    fi
    : > "${PID_FILE}" 2>/dev/null || true
    nohup "${APP_TARGET_DIR}/bin/frpc" -c "${CFG_FILE}" >> "${LOG_FILE}" 2>&1 &
    echo $! > "${PID_FILE}" 2>/dev/null || true
    # 短等后确认进程存活（进程起来即算启动成功，不等 frps 连接）
    sleep 0.5
    if kill -0 $! 2>/dev/null; then
        return 0
    fi

    # 兜底：快速路径未能拉起（权限/环境异常）时，回退标准脚本
    if [ -x /var/packages/frpc/scripts/start-stop-status ]; then
        /var/packages/frpc/scripts/start-stop-status stop >/dev/null 2>&1 || true
        /var/packages/frpc/scripts/start-stop-status start >/dev/null 2>&1 || true
        sleep 1
        if /var/packages/frpc/scripts/start-stop-status status >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
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
# 刚保存过（POST 成功）：先显示“检测状态...”，由 JS 异步刷新真实状态
if [ -n "$SAVED_MSG" ]; then
    STATUS_DOT="checking"
    STATUS_TEXT="检测状态..."
    STATUS_CLASS="checking"
    SAVED_FLAG=1
else
    SAVED_FLAG=0
    case "$STATUS_STATE" in
        running) STATUS_DOT="running"; STATUS_TEXT="运行中"; STATUS_CLASS="running" ;;
        *)       STATUS_DOT="stopped"; STATUS_TEXT="已停止"; STATUS_CLASS="stopped" ;;
    esac
fi

# 无保存消息时隐藏 msg，把空间让给编辑框
if [ -n "$SAVED_MSG" ]; then
    MSG_HIDE=""
else
    MSG_HIDE=' style="display:none"'
fi

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
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.header h2 { margin: 0; font-size: 20px; }
.status-chip { display: flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px; font-size: 14px; background: #f7f9fc; border: 1px solid #e3e8f0; }
.status-chip.running { color: #15803d; background: #f0fdf4; border-color: #bbf7d0; }
.status-chip.stopped { color: #b91c1c; background: #fef2f2; border-color: #fecaca; }
.status-chip.checking { color: #b45309; background: #fffbeb; border-color: #fde68a; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex: 0 0 auto; }
.status-dot.running { background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,.2); }
.status-dot.stopped { background: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,.2); }
.status-dot.checking { background: #f59e0b; box-shadow: 0 0 0 3px rgba(245,158,11,.2); animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: .35; } }
.msg { margin: 0 0 10px; color: #0a7a0a; font-weight: 600; }
form { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.editor { flex: 1; min-height: 0; display: flex; border: 1px solid #d0d7de; border-radius: 8px; overflow: hidden; background: #fff; }
.gutter { width: 48px; flex: 0 0 auto; box-sizing: border-box; padding: 12px 10px 12px 0; text-align: right; white-space: pre; background: #f6f8fa; border-right: 1px solid #e1e4e8; color: #8c959f; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 13px; line-height: 1.4; overflow: hidden; user-select: none; }
textarea { width: 100%; flex: 1; min-height: 220px; border: 0; border-radius: 0; padding: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 13px; line-height: 1.4; box-sizing: border-box; resize: none; outline: none; }
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
    <h2>frpc 配置编辑器</h2>
    <div class="status-chip ${STATUS_CLASS}" id="statusBar">
      <span class="status-dot ${STATUS_DOT}" id="statusDot"></span>
      <span id="statusText">${STATUS_TEXT}</span>
    </div>
  </div>
  <div class="msg" id="statusMsg"${MSG_HIDE}>$SAVED_MSG</div>
  <form method="post" action="index.cgi?$QUERY" id="configForm" target="saveFrame" onsubmit="return saveConfig()">
    <div class="editor">
      <div class="gutter" id="lineGutter"></div>
      <textarea name="textcontent" id="cfgTextarea" spellcheck="false">$CFG_CONTENT</textarea>
    </div>
    <div class="actions">
      <button type="submit">保存并重启</button>
      <button class="secondary" type="button" onclick="loadLog()">查看当前日志</button>
      <button class="secondary" type="button" onclick="toggleLog()">收起/展开日志</button>
      <button class="secondary" id="autoBtn" type="button" onclick="toggleAutoRefresh()">开启实时刷新日志(2秒)</button>
      <button class="secondary" type="button" onclick="refreshStatus()">刷新状态</button>
    </div>
    <div id="logBox">点击“查看当前日志”加载。</div>
  </form>
  <!-- 隐藏 iframe：表单提交到此处，主页面不刷新，日志窗口保持打开，只刷新状态 -->
  <iframe name="saveFrame" style="display:none" aria-hidden="true"></iframe>
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
  var dot = document.getElementById('statusDot');
  var txt = document.getElementById('statusText');
  fetch(buildUrl('status'), { cache: 'no-store' })
    .then(function(r){ return r.text(); })
    .then(function(s){
      s = (s || '').trim();
      var state = s.split('|')[0];
      var running = (state === 'running');
      bar.className = 'status-chip ' + (running ? 'running' : 'stopped');
      dot.className = 'status-dot ' + (running ? 'running' : 'stopped');
      txt.textContent = running ? '运行中' : '已停止';
    })
    .catch(function(){});
}

// 点击保存：立即（同步）显示“检测状态...”，再异步 AJAX 保存，完成后刷新真实状态
function showChecking() {
  var bar = document.getElementById('statusBar');
  var dot = document.getElementById('statusDot');
  var txt = document.getElementById('statusText');
  bar.className = 'status-chip checking';
  dot.className = 'status-dot checking';
  txt.textContent = '检测状态...';
}

function saveConfig() {
  // 1) 点击瞬间立即显示“检测状态...”（同步，无延迟）
  showChecking();
  // 2) 表单提交到隐藏 iframe（target=saveFrame），主页面不刷新，日志窗口保持打开。
  //    采用原生表单 POST（可靠，能正常写入配置），不依赖 fetch。
  // 3) 稍等 frpc 重启并连上 frps 后，只刷新状态（不刷新整个页面）。
  setTimeout(refreshStatus, 1200);
  return true; // 提交到 iframe
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
  setTimeout(function(){ msg.textContent = ''; msg.style.display = 'none'; }, 3500);
})();

// 行号：按 textarea 内容生成，随 textarea 滚动保持对齐
function updateLineNumbers() {
  var ta = document.getElementById('cfgTextarea');
  var count = ta.value.split('\n').length;
  var nums = new Array(count);
  for (var i = 0; i < count; i++) nums[i] = i + 1;
  document.getElementById('lineGutter').textContent = nums.join('\n');
}
(function initEditor(){
  var ta = document.getElementById('cfgTextarea');
  var gutter = document.getElementById('lineGutter');
  updateLineNumbers();
  ta.addEventListener('scroll', function(){ gutter.scrollTop = ta.scrollTop; });
  ta.addEventListener('input', updateLineNumbers);
})();

// 刚保存过：延迟一点等 frpc 起来，再异步刷新真实运行状态（未连接成功则显示已停止）
if (${SAVED_FLAG} === 1) {
  setTimeout(refreshStatus, 1200);
}
</script>
</body>
</html>
HTML