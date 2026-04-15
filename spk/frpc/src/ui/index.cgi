#!/bin/sh

CFG_FILE="/var/packages/frpc/var/frpc.toml"
LOG_FILE="/var/packages/frpc/var/frpc.log"
TMP_FILE="/tmp/frpc.toml.$$"

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

restart_frpc() {
    if command -v synopkg >/dev/null 2>&1; then
        synopkg stop frpc >/dev/null 2>&1 || true
        synopkg start frpc >/dev/null 2>&1 || true
    else
        /var/packages/frpc/scripts/start-stop-status stop >/dev/null 2>&1 || true
        /var/packages/frpc/scripts/start-stop-status start >/dev/null 2>&1 || true
    fi
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

if [ "$METHOD" = "POST" ]; then
    BODY=$(read_post_body)
    RAW_CONTENT=$(get_param "textcontent" "$BODY")
    NEW_CONTENT=$(urldecode "$RAW_CONTENT")

    if [ -n "$NEW_CONTENT" ]; then
        printf '%s' "$NEW_CONTENT" > "$TMP_FILE"
        sed -i 's/\r$//' "$TMP_FILE" 2>/dev/null || true
        mv "$TMP_FILE" "$CFG_FILE"
        chmod 644 "$CFG_FILE" 2>/dev/null || true

        restart_frpc
        SAVED_MSG="保存成功，已尝试重启 frpc。"
    else
        SAVED_MSG="未检测到可保存内容。"
    fi
fi

[ -f "$CFG_FILE" ] || touch "$CFG_FILE"
CFG_CONTENT=$(cat "$CFG_FILE" 2>/dev/null | html_escape)

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
h2 { margin: 0 0 10px; }
.desc { color: #666; margin-bottom: 12px; }
.msg { margin: 10px 0; color: #0a7a0a; font-weight: 600; min-height: 20px; }
form { display: flex; flex-direction: column; flex: 1; min-height: 0; }
textarea { width: 100%; flex: 1; min-height: 220px; border: 1px solid #d0d7de; border-radius: 8px; padding: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 13px; line-height: 1.4; box-sizing: border-box; resize: none; }
.actions { margin-top: 12px; display: flex; gap: 10px; align-items: center; }
button { border: 0; background: #1677ff; color: white; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
button:hover { background: #4096ff; }
button.secondary { background: #5d6778; }
button.secondary:hover { background: #76839a; }
small { color: #888; display: block; margin-top: 8px; }
#logBox { display:none; margin-top: 12px; border: 1px solid #d0d7de; border-radius: 8px; padding: 10px; background: #fafafa; max-height: 240px; overflow: auto; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12px; }
</style>
</head>
<body>
<div class="wrapper">
  <h2>frpc 配置编辑器</h2>
  <div class="desc">编辑并保存 <code>/var/packages/frpc/var/frpc.toml</code>。保存后会尝试重启 frpc。</div>
  <div class="msg">$SAVED_MSG</div>
  <form method="post" action="index.cgi?$QUERY">
    <textarea name="textcontent">$CFG_CONTENT</textarea>
    <div class="actions">
      <button type="submit">保存并重启</button>
      <button class="secondary" type="button" onclick="loadLog()">查看当前日志</button>
      <button class="secondary" type="button" onclick="toggleLog()">收起/展开日志</button>
    </div>
    <small>提示：若 frps 地址不可达，frpc 可能会退出（日志见 $LOG_FILE）。</small>
    <div id="logBox">点击“查看当前日志”加载。</div>
  </form>
</div>
<script>
function buildLogUrl() {
  var qs = window.location.search || '';
  var sep = qs.indexOf('?') === -1 ? '?' : '&';
  return 'index.cgi' + qs + sep + 'action=log&_=' + Date.now();
}
function loadLog() {
  var box = document.getElementById('logBox');
  box.style.display = 'block';
  box.textContent = '加载日志中...';
  fetch(buildLogUrl(), { cache: 'no-store' })
    .then(function(r){ return r.text(); })
    .then(function(t){ box.textContent = t || '日志为空'; box.scrollTop = box.scrollHeight; })
    .catch(function(e){ box.textContent = '读取日志失败：' + e; });
}
function toggleLog() {
  var box = document.getElementById('logBox');
  box.style.display = (box.style.display === 'none' || !box.style.display) ? 'block' : 'none';
}
</script>
</body>
</html>
HTML
