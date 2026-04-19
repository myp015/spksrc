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
        models_discover)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body"
import json, sys, urllib.request, urllib.error
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
try:
    payload = json.loads(raw or '{}')
except Exception:
    print('{"error":"invalid payload"}')
    raise SystemExit
base_url = (payload.get('baseUrl') or '').strip().rstrip('/')
api_key = (payload.get('apiKey') or '').strip()
api_type = (payload.get('api') or 'openai-completions').strip()
if not base_url:
    print('{"error":"baseUrl required"}')
    raise SystemExit
headers = {'User-Agent': 'openclaw2-native-ui/1.0'}
if api_key:
    headers['Authorization'] = 'Bearer ' + api_key
try:
    if api_type == 'ollama':
        req = urllib.request.Request(base_url + '/api/tags', headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode('utf-8', 'ignore'))
        models = []
        for item in data.get('models', []):
            name = item.get('name') or item.get('model') or ''
            if name:
                models.append({'id': name, 'modelId': name})
        print(json.dumps({'models': models}, ensure_ascii=False))
    else:
        req = urllib.request.Request(base_url + '/models', headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode('utf-8', 'ignore'))
        models = []
        for item in data.get('data', data.get('models', [])):
            mid = item.get('id') or item.get('name') or item.get('model') or ''
            if mid:
                models.append({'id': mid, 'modelId': mid})
        print(json.dumps({'models': models}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({'error': str(e), 'models': []}, ensure_ascii=False))
PY
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
    .field input, .field select, .field textarea { width:100%; box-sizing:border-box; border:1px solid #d0d5dd; border-radius:8px; padding:8px 10px; }
    .field select[multiple] { min-height: 160px; }
    .list { display:flex; flex-direction:column; gap:10px; margin-bottom:16px; }
    .item { border:1px solid #e5e7eb; border-radius:12px; padding:14px; background:#fff; }
    .item-title { font-size:16px; font-weight:600; margin-bottom:6px; }
    .item-meta { font-size:12px; color:#667085; margin-bottom:8px; }
    .chips { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }
    .chip { background:#eef4ff; color:#175cd3; border:1px solid #c7d7fe; border-radius:999px; padding:2px 8px; font-size:12px; }
    .modal-mask { position:fixed; inset:0; background:rgba(15,23,42,.45); display:none; align-items:center; justify-content:center; z-index:9999; }
    .modal { width:min(760px,92vw); max-height:88vh; overflow:auto; background:#fff; border-radius:16px; padding:18px; box-shadow:0 20px 60px rgba(0,0,0,.25); }
    .modal h3 { margin:0 0 14px; font-size:18px; }
    .modal-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:14px; }
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
    const PROVIDER_PRESETS = {
      anthropic: { label: 'Anthropic', baseUrl: 'https://api.anthropic.com', api: 'anthropic-messages' },
      google: { label: 'Google', baseUrl: 'https://generativelanguage.googleapis.com/v1beta', api: 'openai-completions' },
      'minimax-cn': { label: 'MiniMax CN', baseUrl: 'https://api.minimaxi.com/anthropic', api: 'anthropic-messages' },
      minimax: { label: 'MiniMax', baseUrl: 'https://api.minimax.io/anthropic', api: 'anthropic-messages' },
      'kimi-coding': { label: 'Kimi Coding', baseUrl: 'https://api.kimi.com/coding/', api: 'anthropic-messages' },
      mistral: { label: 'Mistral', baseUrl: 'https://api.mistral.ai/v1', api: 'openai-completions' },
      moonshot: { label: 'Moonshot', baseUrl: 'https://api.moonshot.ai/v1', api: 'openai-completions' },
      openai: { label: 'OpenAI', baseUrl: 'https://api.openai.com/v1', api: 'openai-completions' },
      ollama: { label: 'Ollama', baseUrl: 'http://127.0.0.1:11434', api: 'ollama' },
      openrouter: { label: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1', api: 'openai-completions' },
      together: { label: 'Together', baseUrl: 'https://api.together.xyz/v1', api: 'openai-completions' },
      xai: { label: 'xAI', baseUrl: 'https://api.x.ai/v1', api: 'openai-completions' },
      zai: { label: 'Z.AI', baseUrl: 'https://api.z.ai/api/paas/v4', api: 'openai-completions' }
    };
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
        if (tab === 'models') {
          const providers = data.configuredProviders || [];
          window.__modelsData = data;
          const options = ['<option value="custom-openai">自定义 OpenAI 兼容</option>'].concat(Object.entries(PROVIDER_PRESETS).map(([key, val]) => '<option value="' + esc(key) + '">' + esc(val.label) + '</option>')).join('');
          content.innerHTML = ''
            + '<div style="margin-bottom:12px;"><button class="btn primary" onclick="openModelDialog()">添加模型服务器</button></div>'
            + '<div class="list">'
            + providers.map((p, idx) => {
                const modelIds = (p.models || []).map(m => m.modelId || m.id).filter(Boolean);
                return '<div class="item">'
                  + '<div class="item-title">' + esc(p.displayName || p.id || '未命名服务') + '</div>'
                  + '<div class="item-meta">providerId=' + esc(p.id || '-') + ' / api=' + esc(p.api || '-') + ' / baseUrl=' + esc(p.baseUrl || '-') + '</div>'
                  + '<div class="chips">' + modelIds.map(m => '<span class="chip">' + esc(m) + '</span>').join('') + '</div>'
                  + '<div style="display:flex;gap:8px;">'
                  + '<button class="btn" onclick="openModelDialog(' + idx + ')">编辑</button>'
                  + '<button class="btn" onclick="deleteModelProvider(' + idx + ')">删除</button>'
                  + '</div>'
                  + '</div>';
              }).join('')
            + '</div>'
            + '<textarea id="editor">' + esc(JSON.stringify(data, null, 2)) + '</textarea>'
            + '<div class="modal-mask" id="modelModalMask">'
            + '  <div class="modal">'
            + '    <h3 id="modelModalTitle">添加模型服务器</h3>'
            + '    <div class="field"><label>服务商</label><select id="dlg_provider_preset" onchange="applyProviderPresetDialog()">' + options + '</select></div>'
            + '    <div class="field"><label>Provider ID</label><input id="dlg_provider_id"></div>'
            + '    <div class="field"><label>显示名</label><input id="dlg_display_name"></div>'
            + '    <div class="field"><label>API 类型</label><select id="dlg_api" onchange="invalidateModelDiscoverCache()"><option value="openai-completions">openai-completions</option><option value="openai-responses">openai-responses</option><option value="anthropic-messages">anthropic-messages</option><option value="ollama">ollama</option></select></div>'
            + '    <div class="field"><label>Base URL</label><input id="dlg_base_url" oninput="invalidateModelDiscoverCache()"></div>'
            + '    <div class="field"><label>API Key（留空表示不改）</label><input id="dlg_api_key" type="password" oninput="invalidateModelDiscoverCache()"></div>'
            + '    <div class="field"><label>可选模型（按住 Ctrl / Command 可多选）</label><select id="dlg_model_select" multiple onchange="syncModelTextareaFromSelect()" onclick="triggerDiscoverModelsForDialog()" onfocus="triggerDiscoverModelsForDialog()"></select></div>'
            + '    <div class="field"><label>模型列表（每行一个 modelId，可手工补充）</label><textarea id="dlg_model_ids" style="min-height:140px;" oninput="syncModelSelectFromTextarea()"></textarea></div>'
            + '    <div class="modal-actions">'
            + '      <button class="btn" onclick="closeModelDialog()">取消</button>'
            + '      <button class="btn primary" onclick="saveModelDialog()">保存</button>'
            + '    </div>'
            + '  </div>'
            + '</div>';
          setMsg('模型配置已加载；可添加模型服务器，或编辑当前已配置的服务', 'ok');
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
    function applyProviderPresetDialog() {
      const presetId = document.getElementById('dlg_provider_preset').value;
      if (presetId === 'custom-openai') {
        document.getElementById('dlg_provider_id').value = 'custom-openai';
        document.getElementById('dlg_display_name').value = '自定义 OpenAI 兼容';
        document.getElementById('dlg_api').value = 'openai-completions';
        document.getElementById('dlg_base_url').value = '';
        setMsg('已切换到自定义 OpenAI 兼容，请手动填写服务器地址', 'ok');
        return;
      }
      const preset = PROVIDER_PRESETS[presetId];
      if (!preset) return;
      document.getElementById('dlg_provider_id').value = presetId;
      document.getElementById('dlg_display_name').value = preset.label;
      document.getElementById('dlg_base_url').value = preset.baseUrl || '';
      document.getElementById('dlg_api').value = preset.api || 'openai-completions';
      setMsg('已按服务商自动填充服务器地址与 API 类型', 'ok');
    }
    function setModelSelectOptions(ids, selectedIds) {
      const select = document.getElementById('dlg_model_select');
      if (!select) return;
      const all = Array.from(new Set((ids || []).concat(selectedIds || []))).filter(Boolean);
      select.innerHTML = all.map(id => '<option value="' + esc(id) + '"' + ((selectedIds || []).includes(id) ? ' selected' : '') + '>' + esc(id) + '</option>').join('');
    }
    function syncModelTextareaFromSelect() {
      const select = document.getElementById('dlg_model_select');
      const ids = Array.from(select.selectedOptions).map(o => o.value);
      document.getElementById('dlg_model_ids').value = ids.join('\n');
    }
    function syncModelSelectFromTextarea() {
      const ids = (document.getElementById('dlg_model_ids').value || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
      setModelSelectOptions(ids, ids);
    }
    function getDiscoverCacheKey() {
      return JSON.stringify({
        baseUrl: (document.getElementById('dlg_base_url').value || '').trim(),
        api: (document.getElementById('dlg_api').value || '').trim(),
        apiKey: (document.getElementById('dlg_api_key').value || '').trim()
      });
    }
    function invalidateModelDiscoverCache() {
      window.__modelsDiscovering = false;
      window.__modelsDiscoveredKey = '';
    }
    async function triggerDiscoverModelsForDialog() {
      const key = getDiscoverCacheKey();
      if (window.__modelsDiscovering) return;
      if (window.__modelsDiscoveredKey === key && key !== JSON.stringify({ baseUrl: '', api: '', apiKey: '' })) return;
      await discoverModelsForDialog();
    }
    function openModelDialog(index) {
      const data = window.__modelsData || {};
      const providers = data.configuredProviders || [];
      const editing = typeof index === 'number';
      const p = editing ? (providers[index] || {}) : {};
      const currentIds = (p.models || []).map(m => m.modelId || m.id).filter(Boolean);
      document.getElementById('modelModalTitle').textContent = editing ? '编辑模型服务器' : '添加模型服务器';
      document.getElementById('dlg_provider_preset').value = p.id && PROVIDER_PRESETS[p.id] ? p.id : (p.id === 'custom-openai' ? 'custom-openai' : 'openai');
      document.getElementById('dlg_provider_id').value = p.id || '';
      document.getElementById('dlg_display_name').value = p.displayName || '';
      document.getElementById('dlg_api').value = p.api || 'openai-completions';
      document.getElementById('dlg_base_url').value = p.baseUrl || '';
      document.getElementById('dlg_api_key').value = '';
      document.getElementById('dlg_model_ids').value = currentIds.join('\n');
      setModelSelectOptions(currentIds, currentIds);
      window.__modelsDiscovering = false;
      window.__modelsDiscoveredKey = '';
      document.getElementById('modelModalMask').style.display = 'flex';
      document.getElementById('modelModalMask').dataset.editIndex = editing ? String(index) : '';
    }
    function closeModelDialog() {
      document.getElementById('modelModalMask').style.display = 'none';
      document.getElementById('modelModalMask').dataset.editIndex = '';
    }
    async function discoverModelsForDialog() {
      try {
        window.__modelsDiscovering = true;
        setMsg('正在获取模型列表...');
        const payload = {
          baseUrl: document.getElementById('dlg_base_url').value,
          apiKey: document.getElementById('dlg_api_key').value,
          api: document.getElementById('dlg_api').value
        };
        const key = getDiscoverCacheKey();
        const data = await api('models_discover', 'POST', payload);
        const ids = (data.models || []).map(m => m.modelId || m.id).filter(Boolean);
        const existing = (document.getElementById('dlg_model_ids').value || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
        const merged = Array.from(new Set(ids.concat(existing)));
        document.getElementById('dlg_model_ids').value = merged.join('\n');
        setModelSelectOptions(merged, existing.length ? existing : ids);
        if (!data.error) {
          window.__modelsDiscoveredKey = key;
        }
        if (ids.length > 0) setMsg('模型列表已更新，共 ' + ids.length + ' 个', 'ok');
        else setMsg(data.error ? ('获取失败：' + data.error) : '未发现模型', data.error ? 'err' : '');
      } catch (e) { setMsg('获取模型失败：' + (e.message || e), 'err'); }
      finally { window.__modelsDiscovering = false; }
    }
    async function saveModelDialog() {
      try {
        const data = window.__modelsData || {};
        const providers = (data.configuredProviders || []).slice();
        const idxRaw = document.getElementById('modelModalMask').dataset.editIndex;
        const idx = idxRaw === '' ? -1 : parseInt(idxRaw, 10);
        const provider = {
          id: document.getElementById('dlg_provider_id').value || 'custom-openai',
          displayName: document.getElementById('dlg_display_name').value,
          api: document.getElementById('dlg_api').value,
          baseUrl: document.getElementById('dlg_base_url').value,
          apiKey: document.getElementById('dlg_api_key').value,
          models: (document.getElementById('dlg_model_ids').value || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean).map(id => ({ modelId: id, id: id }))
        };
        if (idx >= 0) providers[idx] = provider; else providers.push(provider);
        const payload = { providers };
        const saved = await api('models_save', 'POST', payload);
        closeModelDialog();
        await load('models');
        document.getElementById('editor').value = JSON.stringify(saved, null, 2);
        setMsg('模型服务器保存成功', 'ok');
      } catch (e) { setMsg('模型服务器保存失败：' + (e.message || e), 'err'); }
    }
    async function deleteModelProvider(index) {
      try {
        const data = window.__modelsData || {};
        const providers = (data.configuredProviders || []).slice();
        providers.splice(index, 1);
        const saved = await api('models_save', 'POST', { providers });
        await load('models');
        document.getElementById('editor').value = JSON.stringify(saved, null, 2);
        setMsg('模型服务器已删除', 'ok');
      } catch (e) { setMsg('删除失败：' + (e.message || e), 'err'); }
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
