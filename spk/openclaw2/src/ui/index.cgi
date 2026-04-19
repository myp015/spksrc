#!/bin/sh

APP_VAR_DIR="/var/packages/openclaw2/var"
if [ -d "/volume1/@appdata/openclaw2" ]; then
    APP_VAR_DIR="/volume1/@appdata/openclaw2"
fi

LOG_FILE="${APP_VAR_DIR}/openclaw2.log"
PID_FILE="${APP_VAR_DIR}/openclaw2.pid"
GATEWAY_URL="http://127.0.0.1:18789/"
PANEL_URL="http://127.0.0.1:18700"
PROXY_PREFIX="/proxy"

html_escape() {
    sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

check_url() {
    if command -v curl >/dev/null 2>&1; then
        if curl -fsS --max-time 2 "$1" >/dev/null 2>&1; then
            echo "running"
            return 0
        fi
    fi
    echo "down"
    return 1
}

METHOD="${REQUEST_METHOD:-GET}"
QUERY="${QUERY_STRING:-}"
REQUEST_URI_RAW="${REQUEST_URI:-}"
SCRIPT_NAME_RAW="${SCRIPT_NAME:-/webman/3rdparty/openclaw2/index.cgi}"
PATH_INFO_RAW="${PATH_INFO:-}"

# Derive PATH_INFO when DSM doesn't pass it.
if [ -z "$PATH_INFO_RAW" ] && [ -n "$REQUEST_URI_RAW" ] && [ -n "$SCRIPT_NAME_RAW" ]; then
    case "$REQUEST_URI_RAW" in
        "$SCRIPT_NAME_RAW"/*)
            PATH_INFO_RAW="${REQUEST_URI_RAW#${SCRIPT_NAME_RAW}}"
            PATH_INFO_RAW="${PATH_INFO_RAW%%\?*}"
            ;;
    esac
fi

# DSM-internal proxy mode:
# /webman/3rdparty/openclaw2/index.cgi/proxy/... -> http://127.0.0.1:18700/...
if [ "${PATH_INFO_RAW#${PROXY_PREFIX}}" != "$PATH_INFO_RAW" ]; then
    PROXY_PATH="${PATH_INFO_RAW#${PROXY_PREFIX}}"
    [ -n "$PROXY_PATH" ] || PROXY_PATH="/"
    TARGET_URL="${PANEL_URL}${PROXY_PATH}"
    [ -n "$QUERY" ] && TARGET_URL="${TARGET_URL}?${QUERY}"

    if ! command -v curl >/dev/null 2>&1; then
        printf 'Status: 500 Internal Server Error\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n'
        echo "curl not found for proxy"
        exit 0
    fi

    RESP_HEADERS=$(mktemp)
    RESP_BODY=$(mktemp)

    if [ "$METHOD" = "POST" ] || [ "$METHOD" = "PUT" ] || [ "$METHOD" = "PATCH" ] || [ "$METHOD" = "DELETE" ]; then
        BODY=""
        if [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -gt 0 ] 2>/dev/null; then
            BODY=$(dd bs=1 count="$CONTENT_LENGTH" 2>/dev/null)
        fi
        printf '%s' "$BODY" | curl -sS -D "$RESP_HEADERS" -o "$RESP_BODY" \
            -X "$METHOD" \
            -H "Content-Type: ${CONTENT_TYPE:-application/json}" \
            --data-binary @- \
            "$TARGET_URL" || true
    else
        curl -sS -D "$RESP_HEADERS" -o "$RESP_BODY" "$TARGET_URL" || true
    fi

    STATUS_LINE=$(head -n 1 "$RESP_HEADERS" | tr -d '\r')
    STATUS_CODE=$(printf '%s' "$STATUS_LINE" | awk '{print $2}')
    [ -n "$STATUS_CODE" ] || STATUS_CODE=200
    STATUS_TEXT=$(printf '%s' "$STATUS_LINE" | cut -d' ' -f3-)
    [ -n "$STATUS_TEXT" ] || STATUS_TEXT="OK"

    printf 'Status: %s %s\r\n' "$STATUS_CODE" "$STATUS_TEXT"
    (grep -i '^Content-Type:' "$RESP_HEADERS" | tail -n1 | tr -d '\r') || true
    grep -i '^Set-Cookie:' "$RESP_HEADERS" | tr -d '\r' || true
    grep -i '^Cache-Control:' "$RESP_HEADERS" | tail -n1 | tr -d '\r' || true
    grep -i '^Location:' "$RESP_HEADERS" | tail -n1 | tr -d '\r' || true
    echo
    cat "$RESP_BODY"

    rm -f "$RESP_HEADERS" "$RESP_BODY"
    exit 0
fi

GATEWAY_STATUS=$(check_url "${GATEWAY_URL}")
PANEL_STATUS=$(check_url "${PANEL_URL}/")
[ -f "$LOG_FILE" ] || touch "$LOG_FILE"
TAIL_LOG=$(tail -n 80 "$LOG_FILE" 2>/dev/null | html_escape)

printf 'Content-type: text/html\r\n\r\n'
cat <<HTML
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<title>OpenClaw2 配置面板</title>
<style>
html, body { height: 100%; }
body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif; margin:0; background:#f5f6f7; }
.wrapper { max-width:1100px; margin:20px auto; background:#fff; border-radius:10px; box-shadow:0 2px 12px rgba(0,0,0,.08); padding:20px; }
.badge { display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; }
.ok { background:#e8f7ee; color:#0a7a0a; }
.err { background:#fdecec; color:#b42318; }
.actions a { display:inline-block; margin-right:10px; padding:8px 12px; border-radius:6px; text-decoration:none; color:#fff; background:#1677ff; }
pre { background:#fafafa; border:1px solid #d0d7de; border-radius:8px; padding:12px; overflow:auto; max-height:420px; }
code { background:#f1f3f5; padding:2px 6px; border-radius:4px; }
</style>
</head>
<body>
<div class="wrapper">
  <h2>OpenClaw2 配置面板</h2>
  <p>主服务：面板（独立） | Gateway：独立运行状态可单独检查</p>
  <p>
    面板状态：
    <span class="badge $( [ "$PANEL_STATUS" = "running" ] && echo ok || echo err )">$PANEL_STATUS</span>
    （$PANEL_URL/）
  </p>
  <p>
    Gateway 状态：
    <span class="badge $( [ "$GATEWAY_STATUS" = "running" ] && echo ok || echo err )">$GATEWAY_STATUS</span>
    （$GATEWAY_URL）
  </p>

  <div class="actions">
    <a href="${PROXY_PREFIX}/" target="_self">打开内嵌面板（DSM 内部代理）</a>
    <a href="/" target="_blank" rel="noopener">打开 Gateway 页面</a>
  </div>

  <h3>运行信息</h3>
  <ul>
    <li>PID 文件：<code>${PID_FILE}</code></li>
    <li>日志文件：<code>${LOG_FILE}</code></li>
  </ul>

  <h3>最近日志（openclaw2）</h3>
  <pre>${TAIL_LOG}</pre>
</div>
</body>
</html>
HTML
