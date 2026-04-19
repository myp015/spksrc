#!/bin/sh

APP_VAR_DIR="/var/packages/openclaw2/var"
if [ -d "/volume1/@appdata/openclaw2" ]; then
    APP_VAR_DIR="/volume1/@appdata/openclaw2"
fi

LOG_FILE="${APP_VAR_DIR}/openclaw2.log"
PID_FILE="${APP_VAR_DIR}/openclaw2.pid"
GATEWAY_URL="http://127.0.0.1:18789/"
PANEL_URL="http://127.0.0.1:18700"

METHOD="${REQUEST_METHOD:-GET}"
QUERY="${QUERY_STRING:-}"
SCRIPT_NAME_RAW="${SCRIPT_NAME:-/webman/3rdparty/openclaw2/index.cgi}"

html_escape() {
    sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

urldecode() {
    local data
    data=$(printf '%s' "$1" | sed 's/+/ /g;s/%/\\x/g')
    printf '%b' "$data"
}

get_param() {
    # $1 key, $2 query/body
    printf '%s' "$2" | tr '&' '\n' | awk -F= -v k="$1" '$1==k{print substr($0, index($0,"=")+1)}' | tail -n1
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

emit_proxy_response() {
    local target_url="$1"

    if ! command -v curl >/dev/null 2>&1; then
        printf 'Status: 500 Internal Server Error\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n'
        echo "curl not found for proxy"
        return 0
    fi

    local resp_headers resp_body rewrite_body
    resp_headers=$(mktemp)
    resp_body=$(mktemp)
    rewrite_body=$(mktemp)

    if [ "$METHOD" = "POST" ] || [ "$METHOD" = "PUT" ] || [ "$METHOD" = "PATCH" ] || [ "$METHOD" = "DELETE" ]; then
        local body=""
        if [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -gt 0 ] 2>/dev/null; then
            body=$(dd bs=1 count="$CONTENT_LENGTH" 2>/dev/null)
        fi
        printf '%s' "$body" | curl -sS -D "$resp_headers" -o "$resp_body" \
            -X "$METHOD" \
            -H "Content-Type: ${CONTENT_TYPE:-application/json}" \
            --data-binary @- \
            "$target_url" || true
    else
        curl -sS -D "$resp_headers" -o "$resp_body" "$target_url" || true
    fi

    local status_line status_code status_text content_type
    status_line=$(head -n 1 "$resp_headers" | tr -d '\r')
    status_code=$(printf '%s' "$status_line" | awk '{print $2}')
    [ -n "$status_code" ] || status_code=200
    status_text=$(printf '%s' "$status_line" | cut -d' ' -f3-)
    [ -n "$status_text" ] || status_text="OK"

    content_type=$(grep -i '^Content-Type:' "$resp_headers" | tail -n1 | cut -d':' -f2- | tr -d '\r' | sed 's/^ *//')
    [ -n "$content_type" ] || content_type='text/plain; charset=UTF-8'

    # Rewrite front-end absolute paths to DSM proxy query paths.
    if printf '%s' "$content_type" | grep -Eiq 'text/|javascript|json|css'; then
        sed \
          -e "s#\(/app/trim-openclaw\)#${SCRIPT_NAME_RAW}?proxy=1\\&path=/app/trim-openclaw#g" \
          -e "s#\"/api/#\"${SCRIPT_NAME_RAW}?proxy=1\\&path=/app/trim-openclaw/api/#g" \
          -e "s#'/api/#'${SCRIPT_NAME_RAW}?proxy=1\\&path=/app/trim-openclaw/api/#g" \
          "$resp_body" > "$rewrite_body" || cp -f "$resp_body" "$rewrite_body"
    else
        cp -f "$resp_body" "$rewrite_body"
    fi

    printf 'Status: %s %s\r\n' "$status_code" "$status_text"
    printf 'Content-Type: %s\r\n' "$content_type"
    grep -i '^Set-Cookie:' "$resp_headers" | tr -d '\r' || true
    grep -i '^Cache-Control:' "$resp_headers" | tail -n1 | tr -d '\r' || true

    local loc_line loc_val
    loc_line=$(grep -i '^Location:' "$resp_headers" | tail -n1 | tr -d '\r')
    if [ -n "$loc_line" ]; then
        loc_val=$(printf '%s' "$loc_line" | cut -d':' -f2- | sed 's/^ *//')
        loc_val=$(printf '%s' "$loc_val" | sed "s#^/app/trim-openclaw#${SCRIPT_NAME_RAW}?proxy=1\\&path=/app/trim-openclaw#")
        printf 'Location: %s\r\n' "$loc_val"
    fi

    echo
    cat "$rewrite_body"

    rm -f "$resp_headers" "$resp_body" "$rewrite_body"
    return 0
}

proxy_flag_raw=$(get_param "proxy" "$QUERY")
proxy_flag=$(urldecode "$proxy_flag_raw")
proxy_path_raw=$(get_param "path" "$QUERY")
proxy_path=$(urldecode "$proxy_path_raw")

if [ "$proxy_flag" = "1" ]; then
    [ -n "$proxy_path" ] || proxy_path="/"
    case "$proxy_path" in
        /*) ;;
        *) proxy_path="/$proxy_path" ;;
    esac

    target_url="${PANEL_URL}${proxy_path}"

    # Pass through non-control query params to backend
    passthrough_q=$(printf '%s' "$QUERY" | tr '&' '\n' | grep -v '^proxy=' | grep -v '^path=' | paste -sd '&' -)
    [ -n "$passthrough_q" ] && target_url="${target_url}?${passthrough_q}"

    emit_proxy_response "$target_url"
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
    <a href="${SCRIPT_NAME_RAW}?proxy=1&path=/app/trim-openclaw/" target="_self">打开完整内嵌面板</a>
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
