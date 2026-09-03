#!/bin/sh
# OpenClaw (container mode) — DSM settings UI (index.cgi).
#
# Serves the settings page (native_api=0) and JSON API (native_api=1).
# Privileged actions run through the root helper ui-run.sh via sudo.
set -u

PKG_NAME="openclaw"
PKG_VAR="/var/packages/${PKG_NAME}/var"
PKG_DEST="/var/packages/${PKG_NAME}/target"
UI_RUN="${PKG_DEST}/scripts/ui-run.sh"
SUDO="sudo -n ${UI_RUN}"

QUERY="${QUERY_STRING:-}"

get_param() {
    printf '%s' "$2" | tr '&' '\n' | awk -F= -v k="$1" '$1==k{print substr($0,index($0,"=")+1)}' | tail -n1
}
urldecode() {
    data=$(printf '%s' "$1" | sed 's/+/ /g;s/%/\\x/g')
    printf '%b' "$data"
}
read_body() {
    if [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -gt 0 ] 2>/dev/null; then
        python3 -c 'import sys
n=int(sys.argv[1]) if len(sys.argv)>1 else 0
sys.stdout.buffer.write(sys.stdin.buffer.read(n) if n>0 else b"")
' "$CONTENT_LENGTH"
    else
        python3 -c 'import os,sys,select
fd=sys.stdin.fileno(); chunks=[]
while True:
  r,_,_=select.select([fd],[],[],0.15)
  if not r: break
  data=os.read(fd,65536)
  if not data: break
  chunks.append(data)
sys.stdout.buffer.write(b"".join(chunks))
'
    fi
}

action=$(urldecode "$(get_param action "$QUERY")")
native_api=$(urldecode "$(get_param native_api "$QUERY")")
launch_app=$(urldecode "$(get_param launchApp "$QUERY")")
from_app=$(urldecode "$(get_param fromApp "$QUERY")")

# Require a DSM login session (unless it's a native_api JSON call which is
# still served behind the same session in practice).
REQ_COOKIE="${HTTP_COOKIE:-}"
if ! printf '%s' "$REQ_COOKIE" | grep -Eq '(^|;[[:space:]]*)id='; then
    printf "Status: 403 Forbidden\n"
    printf "Content-Type: text/plain; charset=UTF-8\n\n"
    printf "Forbidden: DSM login required\n"
    exit 0
fi
if [ "$native_api" != "1" ] && [ "$launch_app" = "1" ]; then
    if [ "$from_app" != "1" ]; then
        printf "Status: 403 Forbidden\n"
        printf "Content-Type: text/plain; charset=UTF-8\n\n"
        printf "Forbidden: direct launch blocked\n"
        exit 0
    fi
fi

# ---------- JSON API ----------
if [ "$native_api" = "1" ]; then
    printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
    case "$action" in
        status)
            ${SUDO} status
            ;;
        check_update)
            ${SUDO} check_update
            ;;
        update)
            body=$(read_body)
            ver=$(printf '%s' "$body" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("version","latest"))
except: print("latest")' 2>/dev/null)
            [ -z "$ver" ] && ver=latest
            ${SUDO} update "$ver"
            ;;
        restart)
            ${SUDO} restart
            ;;
        start)
            ${SUDO} start
            ;;
        stop)
            ${SUDO} stop
            ;;
        config_get)
            ${SUDO} config_get
            ;;
        config_set)
            body=$(read_body)
            printf '%s' "$body" | ${SUDO} config_set
            ;;
        logs)
            ${SUDO} logs 300
            ;;
        *)
            printf '{"error":"unknown action %s"}\n' "$action"
            ;;
    esac
    exit 0
fi

# ---------- Settings page ----------
printf 'Content-Type: text/html; charset=UTF-8\r\n\r\n'
cat <<'HTML'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenClaw 设置</title>
<style>
:root{--bg:#0f172a;--panel:#1e293b;--line:#334155;--fg:#e2e8f0;--muted:#94a3b8;--accent:#38bdf8;--ok:#22c55e;--warn:#f59e0b;--danger:#ef4444;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--fg)}
header{padding:14px 20px;background:var(--panel);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px}
header h1{font-size:16px;margin:0;font-weight:600}
header .badge{margin-left:auto;font-size:12px;padding:3px 10px;border-radius:999px;background:#0b3a52;color:var(--accent)}
.tabs{display:flex;gap:4px;padding:10px 16px;background:var(--panel);border-bottom:1px solid var(--line);flex-wrap:wrap}
.tab{padding:8px 16px;border-radius:8px;cursor:pointer;font-size:14px;color:var(--muted);border:1px solid transparent;background:none}
.tab:hover{color:var(--fg)}
.tab.active{color:var(--fg);background:#0b3a52;border-color:var(--accent)}
main{padding:20px;max-width:1100px;margin:0 auto}
.pane{display:none}
.pane.active{display:block}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:16px}
.card h3{margin:0 0 12px;font-size:15px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.stat{background:#0f172a;border:1px solid var(--line);border-radius:10px;padding:14px}
.stat .label{font-size:12px;color:var(--muted)}
.stat .value{font-size:18px;font-weight:600;margin-top:4px;word-break:break-all}
.btn{padding:8px 16px;border-radius:8px;border:1px solid var(--line);background:#0b3a52;color:var(--fg);cursor:pointer;font-size:14px}
.btn:hover{border-color:var(--accent)}
.btn.primary{background:var(--accent);color:#082f49;border-color:var(--accent);font-weight:600}
.btn.danger{background:transparent;border-color:var(--danger);color:var(--danger)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:8px 0}
input[type=text],input[type=password],select,textarea{background:#0f172a;border:1px solid var(--line);color:var(--fg);border-radius:8px;padding:8px 10px;font-size:14px;width:100%}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--accent)}
textarea{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;min-height:300px}
label{display:block;font-size:13px;color:var(--muted);margin:10px 0 4px}
.status-line{margin-top:10px;font-size:13px;min-height:18px}
.status-line.ok{color:var(--ok)}
.status-line.err{color:var(--danger)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:500}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.dot.green{background:var(--ok)}.dot.gray{background:var(--muted)}.dot.amber{background:var(--warn)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
a{color:var(--accent)}
</style>
</head>
<body>
<header>
  <h1>🦊 OpenClaw 设置</h1>
  <span class="badge">容器版 · 在线自更新</span>
</header>
<div class="tabs">
  <button class="tab active" data-tab="status">概览</button>
  <button class="tab" data-tab="models">模型配置</button>
  <button class="tab" data-tab="channels">渠道配置</button>
  <button class="tab" data-tab="update">在线升级</button>
  <button class="tab" data-tab="logs">运行日志</button>
</div>
<main>
  <!-- 概览 -->
  <div class="pane active" id="pane-status">
    <div class="card">
      <h3>运行状态</h3>
      <div class="grid">
        <div class="stat"><div class="label">容器</div><div class="value"><span class="dot gray" id="st-dot"></span><span id="st-container">…</span></div></div>
        <div class="stat"><div class="label">OpenClaw 版本</div><div class="value mono" id="st-version">…</div></div>
        <div class="stat"><div class="label">固定镜像</div><div class="value mono" id="st-image">…</div></div>
        <div class="stat"><div class="label">数据目录</div><div class="value mono" id="st-data">…</div></div>
        <div class="stat"><div class="label">端口</div><div class="value mono" id="st-port">…</div></div>
      </div>
      <div class="row" style="margin-top:16px">
        <button class="btn" onclick="refreshStatus()">刷新</button>
        <button class="btn primary" onclick="start()">启动</button>
        <button class="btn" onclick="restart()">重启</button>
        <button class="btn danger" onclick="stop()">停止</button>
      </div>
      <div class="status-line" id="st-msg"></div>
    </div>
    <div class="card">
      <h3>打开 OpenClaw 面板</h3>
      <div class="row">
        <a class="btn" id="open-web" href="#" target="_blank">打开 Control UI</a>
        <span class="status-line" style="margin:0;color:var(--muted)">默认 Token: 123456（在 openclaw.json 中可改）</span>
      </div>
    </div>
  </div>

  <!-- 模型配置 -->
  <div class="pane" id="pane-models">
    <div class="card">
      <h3>模型 Provider（models.providers）</h3>
      <p style="color:var(--muted);font-size:13px">直接编辑 openclaw.json 的 providers。保存后重启容器生效。</p>
      <textarea id="models-json"></textarea>
      <div class="row" style="margin-top:12px">
        <button class="btn" onclick="configGet('models-json')">加载</button>
        <button class="btn primary" onclick="configSave()">保存</button>
        <button class="btn" onclick="restart()">保存并重启</button>
      </div>
      <div class="status-line" id="models-msg"></div>
    </div>
  </div>

  <!-- 渠道配置 -->
  <div class="pane" id="pane-channels">
    <div class="card">
      <h3>渠道配置（channels）</h3>
      <p style="color:var(--muted);font-size:13px">配置 feishu / qqbot / wecom 等渠道。保存后重启容器生效。</p>
      <textarea id="channels-json"></textarea>
      <div class="row" style="margin-top:12px">
        <button class="btn" onclick="configGet('channels-json')">加载</button>
        <button class="btn primary" onclick="configSave()">保存</button>
        <button class="btn" onclick="restart()">保存并重启</button>
      </div>
      <div class="status-line" id="channels-msg"></div>
    </div>
  </div>

  <!-- 在线升级 -->
  <div class="pane" id="pane-update">
    <div class="card">
      <h3>在线升级 OpenClaw</h3>
      <p style="color:var(--muted);font-size:13px">镜像固定不变；OpenClaw 本体在容器内通过 npm 更新到持久卷，重启保留。升级全程无需重新编译本套件。</p>
      <div class="grid">
        <div class="stat"><div class="label">当前已装</div><div class="value mono" id="up-installed">…</div></div>
        <div class="stat"><div class="label">最新可用</div><div class="value mono" id="up-latest">…</div></div>
      </div>
      <div class="row" style="margin-top:16px">
        <button class="btn" onclick="checkUpdate()">检查更新</button>
        <button class="btn primary" id="btn-update" onclick="doUpdate()">立即升级到最新</button>
      </div>
      <div class="status-line" id="up-msg"></div>
    </div>
  </div>

  <!-- 日志 -->
  <div class="pane" id="pane-logs">
    <div class="card">
      <h3>容器日志</h3>
      <pre id="logs-pre" class="mono" style="background:#0f172a;border:1px solid var(--line);border-radius:8px;padding:12px;max-height:480px;overflow:auto;font-size:12px;white-space:pre-wrap"></pre>
      <div class="row" style="margin-top:12px">
        <button class="btn" onclick="loadLogs()">刷新日志</button>
      </div>
    </div>
  </div>
</main>

<script>
var API = '/webman/3rdparty/openclaw/index.cgi?native_api=1&action=';

function api(action, method, payload, cb) {
  var xhr = new XMLHttpRequest();
  xhr.open(method || 'GET', API + action, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function(){
    if (xhr.readyState === 4) {
      var data = {};
      try { data = JSON.parse(xhr.responseText); } catch(e) { data = {error: xhr.responseText}; }
      cb(data);
    }
  };
  xhr.send(payload ? JSON.stringify(payload) : null);
}

function setMsg(id, text, cls) {
  var el = document.getElementById(id);
  el.textContent = text || '';
  el.className = 'status-line ' + (cls || '');
}

document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click', function(){
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active');});
    document.querySelectorAll('.pane').forEach(function(x){x.classList.remove('active');});
    t.classList.add('active');
    document.getElementById('pane-' + t.dataset.tab).classList.add('active');
    if (t.dataset.tab === 'status') refreshStatus();
    if (t.dataset.tab === 'update') checkUpdate();
    if (t.dataset.tab === 'logs') loadLogs();
  });
});

function refreshStatus() {
  api('status', 'GET', null, function(d){
    var running = d.running === true;
    var dot = document.getElementById('st-dot');
    dot.className = 'dot ' + (running ? 'green' : 'gray');
    document.getElementById('st-container').textContent = running ? '运行中' : '已停止';
    document.getElementById('st-version').textContent = d.version || 'unknown';
    document.getElementById('st-image').textContent = d.image || '';
    document.getElementById('st-data').textContent = d.dataDir || '';
    document.getElementById('st-port').textContent = d.port || '';
    document.getElementById('open-web').href = (d.port ? 'http://' + location.hostname + ':' + d.port + '/openclaw-web' : '#');
  });
}

function start() {
  api('start', 'GET', null, function(d){ setMsg('st-msg', d.ok ? '已启动' : '启动失败', d.ok ? 'ok' : 'err'); refreshStatus(); });
}
function stop() {
  api('stop', 'GET', null, function(d){ setMsg('st-msg', d.ok ? '已停止' : '停止失败', d.ok ? 'ok' : 'err'); refreshStatus(); });
}
function restart() {
  setMsg('st-msg', '重启中…');
  api('restart', 'GET', null, function(d){ setMsg('st-msg', d.ok ? '已重启' : '重启失败', d.ok ? 'ok' : 'err'); refreshStatus(); });
}

function configGet(textareaId) {
  api('config_get', 'GET', null, function(d){
    var el = document.getElementById(textareaId);
    el.value = JSON.stringify(d, null, 2);
  });
}
function configSave() {
  var src = document.getElementById('models-json').value;
  var msgId = 'models-msg';
  var id = 'models-json';
  if (!src) { src = document.getElementById('channels-json').value; id = 'channels-json'; msgId = 'channels-msg'; }
  api('config_set', 'POST', JSON.parse(src), function(d){
    setMsg(msgId, d.ok ? '已保存' : ('保存失败: ' + (d.error||'')), d.ok ? 'ok' : 'err');
  });
}

function checkUpdate() {
  api('check_update', 'GET', null, function(d){
    document.getElementById('up-installed').textContent = d.installed || 'unknown';
    document.getElementById('up-latest').textContent = d.latest || 'unknown';
    var btn = document.getElementById('btn-update');
    btn.disabled = d.updatable !== true;
    setMsg('up-msg', d.updatable === true ? '发现新版本，可升级' : '已是最新', d.updatable === true ? 'ok' : '');
  });
}
function doUpdate() {
  var btn = document.getElementById('btn-update');
  btn.disabled = true;
  setMsg('up-msg', '正在升级，请稍候…（下载+替换+重启容器）');
  api('update', 'POST', {version:'latest'}, function(d){
    btn.disabled = false;
    setMsg('up-msg', d.ok ? ('升级完成: ' + (d.output||'')) : ('升级失败: ' + (d.output||'')), d.ok ? 'ok' : 'err');
    checkUpdate();
    refreshStatus();
  });
}

function loadLogs() {
  api('logs', 'GET', null, function(d){
    document.getElementById('logs-pre').textContent = d.logs || '(empty)';
  });
}

refreshStatus();
</script>
</body>
</html>
HTML
