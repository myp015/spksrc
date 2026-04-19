#!/bin/sh
APP_VAR_DIR="/var/packages/openclaw2/var"
if [ -d "/volume1/@appdata/openclaw2" ]; then
    APP_VAR_DIR="/volume1/@appdata/openclaw2"
fi

LOG_FILE="${APP_VAR_DIR}/openclaw2.log"
PANEL_URL="http://127.0.0.1:18700"
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
        dd bs=1 count="$CONTENT_LENGTH" 2>/dev/null
    fi
}

action=$(urldecode "$(get_param action "$QUERY")")
native_api=$(urldecode "$(get_param native_api "$QUERY")")

if [ "$native_api" = "1" ]; then
    case "$action" in
        status)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            curl -fsS --max-time 8 "${PANEL_URL}/app/trim-openclaw/api/status" || printf '{"error":"status unavailable"}'
            exit 0
            ;;
        models)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            curl -fsS --max-time 8 "${PANEL_URL}/app/trim-openclaw/api/models/config" || printf '{"error":"models unavailable"}'
            exit 0
            ;;
        models_save)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '%s' "$body" | curl -fsS --max-time 15 -X POST -H "Content-Type: ${CONTENT_TYPE:-application/json}" --data-binary @- "${PANEL_URL}/app/trim-openclaw/api/models/config" || printf '{"error":"models save failed"}'
            exit 0
            ;;
        channels)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            curl -fsS --max-time 8 "${PANEL_URL}/app/trim-openclaw/api/channels/config" || printf '{"error":"channels unavailable"}'
            exit 0
            ;;
        channels_save)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '%s' "$body" | curl -fsS --max-time 15 -X POST -H "Content-Type: ${CONTENT_TYPE:-application/json}" --data-binary @- "${PANEL_URL}/app/trim-openclaw/api/channels/config" || printf '{"error":"channels save failed"}'
            exit 0
            ;;
        plugins)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            curl -fsS --max-time 8 "${PANEL_URL}/app/trim-openclaw/api/channels/plugins" || printf '{"error":"plugins unavailable"}'
            exit 0
            ;;
        plugins_refresh)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{}' | curl -fsS --max-time 15 -X POST -H "Content-Type: application/json" --data-binary @- "${PANEL_URL}/app/trim-openclaw/api/channels/plugins/refresh" || printf '{"error":"plugins refresh failed"}'
            exit 0
            ;;
        plugin_install)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '%s' "$body" | curl -fsS --max-time 60 -X POST -H "Content-Type: ${CONTENT_TYPE:-application/json}" --data-binary @- "${PANEL_URL}/app/trim-openclaw/api/channels/plugins/install" || printf '{"error":"plugin install failed"}'
            exit 0
            ;;
        install)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            curl -fsS --max-time 8 "${PANEL_URL}/app/trim-openclaw/api/status" || printf '{"error":"install unavailable"}'
            exit 0
            ;;
        install_run)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '%s' "$body" | curl -fsS --max-time 120 -X POST -H "Content-Type: ${CONTENT_TYPE:-application/json}" --data-binary @- "${PANEL_URL}/app/trim-openclaw/api/install" || printf '{"error":"install action failed"}'
            exit 0
            ;;
        process_governor)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            curl -fsS --max-time 8 "${PANEL_URL}/app/trim-openclaw/api/process-governor" || printf '{"error":"process governor unavailable"}'
            exit 0
            ;;
        logs)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            [ -f "$LOG_FILE" ] || touch "$LOG_FILE"
            logs_json=$(tail -n 120 "$LOG_FILE" 2>/dev/null | sed ':a;N;$!ba;s/\\/\\\\/g;s/"/\\"/g;s/\r/\\r/g;s/\n/\\n/g')
            printf '{"log":"%s"}' "$logs_json"
            exit 0
            ;;
        *)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"error":"unknown action"}'
            exit 0
            ;;
    esac
fi

printf 'Content-Type: text/html; charset=UTF-8\r\n\r\n'
cat <<'HTML'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OpenClaw2</title>
  <style>
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif; background:#f5f6f8; color:#222; }
    .wrap { padding:18px; }
    .title { font-size:24px; font-weight:700; margin-bottom:6px; }
    .sub { color:#667085; font-size:13px; margin-bottom:14px; }
    .tabs { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
    .tab { border:1px solid #d0d5dd; background:#fff; border-radius:10px; padding:10px 14px; cursor:pointer; }
    .tab.active { background:#1677ff; color:#fff; border-color:#1677ff; }
    .panel { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:16px; min-height:560px; }
    .toolbar { display:flex; gap:8px; margin-bottom:12px; }
    .btn { border:1px solid #d0d5dd; background:#fff; border-radius:10px; padding:8px 12px; cursor:pointer; }
    .btn.primary { background:#1677ff; color:#fff; border-color:#1677ff; }
    .grid { display:grid; grid-template-columns:180px 1fr; border-top:1px solid #eee; }
    .cellk,.cellv { padding:10px 8px; border-bottom:1px solid #eee; }
    .cellk { color:#667085; }
    textarea { width:100%; min-height:520px; resize:vertical; box-sizing:border-box; border:1px solid #d0d5dd; border-radius:10px; padding:12px; font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
    pre { white-space:pre-wrap; word-break:break-word; background:#111827; color:#dbeafe; border-radius:10px; padding:14px; min-height:520px; overflow:auto; font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
    .msg { margin-bottom:12px; font-size:13px; color:#667085; }
    .err { color:#b42318; }
    .ok { color:#067647; }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; margin-bottom:16px; }
    .card { border:1px solid #e5e7eb; border-radius:12px; padding:14px; background:#fff; }
    .card h3 { margin:0 0 10px; font-size:16px; }
    .field { margin-bottom:10px; }
    .field label { display:block; font-size:12px; color:#667085; margin-bottom:4px; }
    .field input { width:100%; box-sizing:border-box; border:1px solid #d0d5dd; border-radius:8px; padding:8px 10px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="title">OpenClaw2</div>
    <div class="sub">DSM 原生可编辑 MVP（本地 API 桥接）</div>
    <div class="tabs">
      <button class="tab active" data-tab="status">概览</button>
      <button class="tab" data-tab="models">模型配置</button>
      <button class="tab" data-tab="channels">消息渠道</button>
      <button class="tab" data-tab="plugins">插件管理</button>
      <button class="tab" data-tab="install">安装 / 控制</button>
      <button class="tab" data-tab="process_governor">进程治理</button>
      <button class="tab" data-tab="logs">运行日志</button>
    </div>
    <div class="panel">
      <div class="toolbar">
        <button class="btn" id="refreshBtn">刷新当前页</button>
        <button class="btn primary" id="saveBtn" style="display:none;">保存当前页</button>
      </div>
      <div id="msg" class="msg"></div>
      <div id="content"></div>
    </div>
  </div>

  <script>
    const API_BASE = '/webman/3rdparty/openclaw2/index.cgi?native_api=1&action=';
    let currentTab = 'status';

    function esc(s) {
      return String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }
    function setMsg(text, cls='') {
      const el = document.getElementById('msg');
      el.className = 'msg ' + cls;
      el.textContent = text || '';
    }
    function setTabs(tab) {
      currentTab = tab;
      document.querySelectorAll('.tab').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));
      document.getElementById('saveBtn').style.display = (tab === 'models' || tab === 'channels' || tab === 'plugins' || tab === 'install') ? '' : 'none';
    }
    async function api(action, method='GET', payload=null) {
      const resp = await fetch(API_BASE + encodeURIComponent(action), {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: payload ? JSON.stringify(payload) : undefined,
        cache: 'no-store'
      });
      const text = await resp.text();
      try { return text ? JSON.parse(text) : {}; } catch (e) { return { error: 'JSON parse failed', raw: text }; }
    }
    async function load(tab) {
      setTabs(tab);
      setMsg('加载中…');
      const content = document.getElementById('content');
      content.innerHTML = '';
      try {
        const data = await api(tab);
        if (tab === 'status') {
          const rows = [
            ['实例 ID', data.instanceId || '-'],
            ['显示名', data.displayName || '-'],
            ['已安装', data.installed ? '是' : '否'],
            ['运行中', data.running ? '是' : '否'],
            ['版本', data.version || '-'],
            ['端口', data.port || '-'],
            ['代理路径', data.proxyBasePath || '-'],
            ['binaryPath', data.binaryPath || '-']
          ];
          content.innerHTML = '<div class="grid">' + rows.map(([k,v]) => '<div class="cellk">'+esc(k)+'</div><div class="cellv">'+esc(v)+'</div>').join('') + '</div>';
          setMsg('概览已加载', 'ok');
          return;
        }
        if (tab === 'logs') {
          content.innerHTML = '<pre>' + esc(data.log || '') + '</pre>';
          setMsg('日志已加载', 'ok');
          return;
        }
        if (tab === 'plugins') {
          const list = (data.plugins || []);
          content.innerHTML = '<div>' + list.map(p => {
            return '<div style="border:1px solid #e5e7eb;border-radius:10px;padding:12px;margin-bottom:10px;background:#fff;">'
              + '<div style="font-weight:600;margin-bottom:4px;">' + esc(p.label || p.channelKey || '-') + '</div>'
              + '<div style="font-size:12px;color:#667085;margin-bottom:8px;">pluginId=' + esc(p.pluginId || '-') + ' / installed=' + esc(String(!!p.installed)) + '</div>'
              + '<div style="font-size:12px;color:#667085;margin-bottom:8px;">' + esc(p.note || '') + '</div>'
              + '<button class="btn primary" onclick="installPlugin(' + JSON.stringify(p.channelKey || '') + ')">安装/修复插件</button>'
              + '</div>';
          }).join('') + '</div>';
          setMsg('插件列表已加载，可直接点击安装/修复插件', 'ok');
          return;
        }
        if (tab === 'install') {
          const running = !!data.running;
          const installed = !!data.installed;
          content.innerHTML = ''
            + '<div style="margin-bottom:16px;">'
            + '<div style="font-size:14px;color:#667085;margin-bottom:8px;">当前状态：installed=' + esc(String(installed)) + ' / running=' + esc(String(running)) + '</div>'
            + '<div style="display:flex;gap:8px;flex-wrap:wrap;">'
            + '<button class="btn primary" onclick="runInstallAction(\'install\')">安装/修复</button>'
            + '<button class="btn" onclick="runInstallAction(\'start\')">启动</button>'
            + '<button class="btn" onclick="runInstallAction(\'stop\')">停止</button>'
            + '<button class="btn" onclick="runInstallAction(\'restart\')">重启</button>'
            + '</div></div>'
            + '<textarea id="editor">' + esc(JSON.stringify(data, null, 2)) + '</textarea>';
          setMsg('安装/控制面板已加载，可直接点按钮执行', 'ok');
          return;
        }
        if (tab === 'channels') {
          const feishu = data.feishu || {};
          const wecom = data.wecom || {};
          const dingtalk = data.dingtalk || {};
          content.innerHTML = ''
            + '<div class="cards">'
            + '  <div class="card">'
            + '    <h3>飞书</h3>'
            + '    <div class="field"><label>App ID</label><input id="feishu_appId" value="' + esc(feishu.appId || '') + '"></div>'
            + '    <div class="field"><label>App Secret（留空表示不改）</label><input id="feishu_appSecret" type="password" value=""></div>'
            + '    <button class="btn primary" onclick="saveFeishuQuick()">保存飞书配置</button>'
            + '  </div>'
            + '  <div class="card">'
            + '    <h3>企业微信</h3>'
            + '    <div class="field"><label>Bot ID</label><input id="wecom_botId" value="' + esc(wecom.botId || '') + '"></div>'
            + '    <div class="field"><label>Secret（留空表示不改）</label><input id="wecom_secret" type="password" value=""></div>'
            + '    <button class="btn primary" onclick="saveWecomQuick()">保存企业微信配置</button>'
            + '  </div>'
            + '  <div class="card">'
            + '    <h3>钉钉</h3>'
            + '    <div class="field"><label>Client ID</label><input id="dingtalk_clientId" value="' + esc(dingtalk.clientId || '') + '"></div>'
            + '    <div class="field"><label>Client Secret（留空表示不改）</label><input id="dingtalk_clientSecret" type="password" value=""></div>'
            + '    <button class="btn primary" onclick="saveDingtalkQuick()">保存钉钉配置</button>'
            + '  </div>'
            + '</div>'
            + '<textarea id="editor">' + esc(JSON.stringify(data, null, 2)) + '</textarea>';
          setMsg('消息渠道已加载；可直接填写上面的表单保存，也可编辑下方 JSON', 'ok');
          return;
        }
        content.innerHTML = '<textarea id="editor">' + esc(JSON.stringify(data, null, 2)) + '</textarea>';
        if (tab === 'process_governor') {
          setMsg('进程治理信息已加载', 'ok');
        } else {
          setMsg('JSON 已加载，可编辑后保存', 'ok');
        }
      } catch (e) {
        setMsg('加载失败：' + (e.message || e), 'err');
      }
    }
    async function saveCurrent() {
      if (!(currentTab === 'models' || currentTab === 'channels' || currentTab === 'plugins' || currentTab === 'install')) return;
      try {
        const raw = document.getElementById('editor').value;
        const payload = JSON.parse(raw);
        let action = 'models_save';
        if (currentTab === 'channels') action = 'channels_save';
        else if (currentTab === 'plugins') action = 'plugin_install';
        else if (currentTab === 'install') action = 'install_run';
        const data = await api(action, 'POST', payload);
        document.getElementById('editor').value = JSON.stringify(data, null, 2);
        setMsg('保存成功', 'ok');
      } catch (e) {
        setMsg('保存失败：' + (e.message || e), 'err');
      }
    }
    async function installPlugin(channelKey) {
      try {
        setMsg('正在安装/修复插件：' + channelKey + ' ...');
        const data = await api('plugin_install', 'POST', { channelKey });
        setMsg('插件操作已提交：' + channelKey, 'ok');
        if (document.getElementById('editor')) {
          document.getElementById('editor').value = JSON.stringify(data, null, 2);
        }
        await load('plugins');
      } catch (e) {
        setMsg('插件安装失败：' + (e.message || e), 'err');
      }
    }
    async function runInstallAction(actionName) {
      try {
        setMsg('正在执行：' + actionName + ' ...');
        const data = await api('install_run', 'POST', { method: 'bun', action: actionName });
        if (document.getElementById('editor')) {
          document.getElementById('editor').value = JSON.stringify(data, null, 2);
        }
        setMsg('操作已提交：' + actionName, 'ok');
      } catch (e) {
        setMsg('操作失败：' + (e.message || e), 'err');
      }
    }
    async function saveFeishuQuick() {
      try {
        const payload = { feishu: { appId: document.getElementById('feishu_appId').value, appSecret: document.getElementById('feishu_appSecret').value } };
        const data = await api('channels_save', 'POST', payload);
        document.getElementById('editor').value = JSON.stringify(data, null, 2);
        setMsg('飞书配置保存成功', 'ok');
      } catch (e) { setMsg('飞书配置保存失败：' + (e.message || e), 'err'); }
    }
    async function saveWecomQuick() {
      try {
        const payload = { wecom: { botId: document.getElementById('wecom_botId').value, secret: document.getElementById('wecom_secret').value } };
        const data = await api('channels_save', 'POST', payload);
        document.getElementById('editor').value = JSON.stringify(data, null, 2);
        setMsg('企业微信配置保存成功', 'ok');
      } catch (e) { setMsg('企业微信配置保存失败：' + (e.message || e), 'err'); }
    }
    async function saveDingtalkQuick() {
      try {
        const payload = { dingtalk: { clientId: document.getElementById('dingtalk_clientId').value, clientSecret: document.getElementById('dingtalk_clientSecret').value } };
        const data = await api('channels_save', 'POST', payload);
        document.getElementById('editor').value = JSON.stringify(data, null, 2);
        setMsg('钉钉配置保存成功', 'ok');
      } catch (e) { setMsg('钉钉配置保存失败：' + (e.message || e), 'err'); }
    }
    document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => load(btn.dataset.tab)));
    document.getElementById('refreshBtn').addEventListener('click', () => load(currentTab));
    document.getElementById('saveBtn').addEventListener('click', saveCurrent);
    load('status');
  </script>
</body>
</html>
HTML
