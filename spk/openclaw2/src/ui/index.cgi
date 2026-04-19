#!/bin/sh

APP_VAR_DIR="/var/packages/openclaw2/var"
APP_TARGET_DIR="/var/packages/openclaw2/target"
if [ -d "/volume1/@appdata/openclaw2" ]; then
    APP_VAR_DIR="/volume1/@appdata/openclaw2"
fi
if [ -d "/volume1/@appstore/openclaw2" ]; then
    APP_TARGET_DIR="/volume1/@appstore/openclaw2"
fi

LOG_FILE="${APP_VAR_DIR}/openclaw2.log"
PID_FILE="${APP_VAR_DIR}/openclaw2.pid"
GATEWAY_URL="http://127.0.0.1:18789/"

html_escape() {
    sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

check_gateway() {
    if command -v curl >/dev/null 2>&1; then
        if curl -fsS --max-time 2 "${GATEWAY_URL}" >/dev/null 2>&1; then
            echo "running"
            return 0
        fi
    fi
    echo "down"
    return 1
}

STATUS=$(check_gateway)
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
    Gateway 状态：
    <span class="badge $( [ "$STATUS" = "running" ] && echo ok || echo err )">$STATUS</span>
    （$GATEWAY_URL）
  </p>

  <div class="actions">
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
