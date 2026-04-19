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
    printf '%s' "$2" | tr '&' '\n' | awk -F= -v k="$1" '$1==k{print substr($0,index($0,"=")+1)}' | tail -n1
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

    # Compatibility shim for current fn-port UI bundle vs packaged backend routes.
    # Return lightweight JSON for routes missing in backend to prevent frontend parse failures.
    case "$proxy_path" in
        /app/trim-openclaw/api/telemetry)
            printf 'Status: 204 No Content\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'
            exit 0
            ;;
        /app/trim-openclaw/api/process-governor)
            printf 'Status: 200 OK\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"enabled":false,"running":false,"message":"process governor compatibility fallback"}'
            exit 0
            ;;
        /app/trim-openclaw/api/cloud-config/bailian-banner)
            printf 'Status: 200 OK\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"visible":false}'
            exit 0
            ;;
        /app/trim-openclaw/api/models/config/fast)
            proxy_path="/app/trim-openclaw/api/models/config"
            ;;
        /app/trim-openclaw/api/models/providers/ollama/discover)
            printf 'Status: 200 OK\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"models":[]}'
            exit 0
            ;;
        /app/trim-openclaw/api/channels/plugins/refresh)
            proxy_path="/app/trim-openclaw/api/channels/plugins"
            ;;
        /app/trim-openclaw/api/channels/weixin/status)
            printf 'Status: 200 OK\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"connected":false,"status":"idle"}'
            exit 0
            ;;
        /app/trim-openclaw/api/channels/weixin/disconnect|/app/trim-openclaw/api/channels/qqbot/disconnect|/app/trim-openclaw/api/channels/weixin/login/start|/app/trim-openclaw/api/channels/weixin/login/wait)
            printf 'Status: 200 OK\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":true}'
            exit 0
            ;;
    esac

    # panel base path is /app/trim-openclaw, but backend API actually lives at /api/*.
    # Map proxied /app/trim-openclaw/api/* -> backend /api/*.
    case "$proxy_path" in
        /app/trim-openclaw/api/gateway/status|/app/trim-openclaw/api/install/status|/app/trim-openclaw/api/system/status|/app/trim-openclaw/api/gateway)
            backend_path="/api/status"
            ;;
        /app/trim-openclaw/api/*)
            backend_path="/api/${proxy_path#/app/trim-openclaw/api/}"
            ;;
        *)
            backend_path="$proxy_path"
            ;;
    esac

    target_url="${PANEL_URL}${backend_path}"

    passthrough_q=$(printf '%s' "$QUERY" | tr '&' '\n' | grep -v '^proxy=' | grep -v '^path=' | paste -sd '&' -)
    [ -n "$passthrough_q" ] && target_url="${target_url}?${passthrough_q}"

    emit_proxy_response "$target_url"
    exit 0
fi

# Always enter panel directly from DSM entry to avoid nested backend shell.
redirect_url="${SCRIPT_NAME_RAW}?proxy=1&path=/app/trim-openclaw/"
printf 'Status: 302 Found\r\nLocation: %s\r\nCache-Control: no-store\r\n\r\n' "$redirect_url"
exit 0
