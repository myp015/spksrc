#!/bin/sh
APP_VAR_DIR="/var/packages/openclaw2/var"
if [ -d "/volume1/@appdata/openclaw2" ]; then
    APP_VAR_DIR="/volume1/@appdata/openclaw2"
fi

LOG_FILE="${APP_VAR_DIR}/openclaw2.log"
GATEWAY_PORT="18789"
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

# 入口访问放宽：避免误伤 DSM 套件中心打开链路。
# 如需公网防护，请在网关/反向代理层做来源限制。

if [ "$native_api" = "1" ]; then
    case "$action" in
        status)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$GATEWAY_PORT" "/volume1/docker/openclaw/.openclaw/openclaw.json"
import json, os, socket, sys, time
port = int(sys.argv[1]) if len(sys.argv) > 1 else 44539
cfg_path = sys.argv[2] if len(sys.argv) > 2 else ''
running = False
# 避免单次探测抖动导致“已停止 -> 运行中”闪烁：做短重试。
for _ in range(3):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        s.connect(('127.0.0.1', port))
        running = True
        s.close()
        break
    except Exception:
        running = False
        try:
            s.close()
        except Exception:
            pass
        time.sleep(0.15)

# 计算 gateway 运行时长（秒）
started_ts = None
uptime_seconds = 0
if running:
    try:
        # 优先按 PID 读取 etimes，避免字符串匹配误差导致一直 0 秒。
        cmdline = "pgrep -af 'openclaw.*gateway|dist/index.js gateway' | grep -v 'fn-port/server' | head -n1"
        p = os.popen(cmdline)
        line = (p.read() or '').strip()
        p.close()
        if line:
            pid = line.split(None, 1)[0]
            p2 = os.popen(f"ps -o etimes= -p {pid} | head -n1")
            et = (p2.read() or '').strip()
            p2.close()
            if et.isdigit():
                uptime_seconds = int(et)
                started_ts = int(time.time()) - uptime_seconds
    except Exception:
        uptime_seconds = 0
        started_ts = None
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
workspace = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/docker/openclaw')
token = ((((cfg.get('gateway') or {}).get('auth') or {}).get('token')) or '123456')
binary_path = '/var/packages/openclaw2/target/bin/openclaw' if os.path.exists('/var/packages/openclaw2/target/bin/openclaw') else ''
out = {
  'instanceId': 'default',
  'displayName': 'Default Gateway',
  'running': running,
  'installed': True,
  'version': 'OpenClaw 2026.4.15 (041266a)',
  'port': port,
  'proxyBasePath': '/default',
  'dashboardUrl': f'http://LAN_HOST:{port}/default/chat?session=main',
  'dashboardTokenizedUrl': f'http://LAN_HOST:{port}/default/chat?session=main&token={token}',
  'workspaceDir': workspace,
  'configPath': cfg_path,
  'binaryPath': binary_path,
  'uptimeSeconds': uptime_seconds,
  'startedAt': started_ts
}
print(json.dumps(out, ensure_ascii=False))
PY
            exit 0
            ;;
        models)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "/volume1/docker/openclaw/.openclaw/openclaw.json"
import json, os, sys
cfg_path = sys.argv[1] if len(sys.argv) > 1 else ''
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
providers_map = ((cfg.get('models') or {}).get('providers') or {})
providers = []
for pid, p in providers_map.items():
    if not isinstance(p, dict):
        continue
    item = {
        'id': pid,
        'displayName': p.get('displayName') or pid,
        'api': p.get('api') or 'openai-completions',
        'baseUrl': p.get('baseUrl') or '',
        'models': []
    }
    if isinstance(p.get('apiKey'), str) and p.get('apiKey'):
        item['apiKeyMasked'] = '*' * min(16, max(8, len(p.get('apiKey'))))
        item['apiKeyRaw'] = p.get('apiKey')
    for m in (p.get('models') or []):
        if isinstance(m, dict):
            mid = m.get('modelId') or m.get('id') or ''
            if mid:
                item['models'].append({'id': mid, 'modelId': mid})
    providers.append(item)
workspace_dir = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/docker/openclaw')
print(json.dumps({'configuredProviders': providers, 'workspaceDir': workspace_dir, 'configPath': cfg_path, 'configExists': bool(cfg)}, ensure_ascii=False))
PY
            exit 0
            ;;
        models_save)
            body=$(read_body)
            cfg_file="/volume1/docker/openclaw/.openclaw/openclaw.json"
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "$cfg_file"
import json, os, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
cfg_path = sys.argv[2] if len(sys.argv) > 2 else ''
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
workspace = (payload.get('workspaceDir') or '').strip()
if workspace:
    cfg.setdefault('agents', {}).setdefault('defaults', {})['workspace'] = workspace
    qmd = cfg.setdefault('memory', {}).setdefault('qmd', {})
    paths = qmd.setdefault('paths', [])
    if not paths:
        paths.append({'path': workspace, 'name': 'workspace', 'pattern': '**/*.md'})
    elif isinstance(paths[0], dict):
        paths[0]['path'] = workspace
providers_payload = payload.get('providers') or []
apply_now = bool(payload.get('applyNow', True))
existing_providers = ((cfg.get('models') or {}).get('providers') or {})
providers_map = {}
for p in providers_payload:
    if not isinstance(p, dict):
        continue
    pid = (p.get('id') or '').strip()
    if not pid:
        continue
    provider = {
        'api': p.get('api') or 'openai-completions',
        'baseUrl': p.get('baseUrl') or '',
        'models': []
    }
    old_key = ''
    if isinstance(existing_providers.get(pid), dict) and isinstance(existing_providers.get(pid).get('apiKey'), str):
        old_key = existing_providers.get(pid).get('apiKey').strip()
    api_key = p.get('apiKey')
    if isinstance(api_key, str):
        key_trim = api_key.strip()
        if key_trim and set(key_trim) == {'*'}:
            if old_key:
                provider['apiKey'] = old_key
        elif key_trim:
            provider['apiKey'] = key_trim
        elif old_key:
            provider['apiKey'] = old_key
    elif old_key:
        provider['apiKey'] = old_key
    for m in (p.get('models') or []):
        if not isinstance(m, dict):
            continue
        mid = (m.get('modelId') or m.get('id') or '').strip()
        if mid:
            provider['models'].append({'id': mid, 'name': f"{pid} / {mid}"})
    providers_map[pid] = provider
cfg.setdefault('models', {})['providers'] = providers_map
os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')
out = {'configuredProviders': providers_payload, 'workspaceDir': ((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/docker/openclaw', 'configPath': cfg_path, 'configExists': True}
# applyNow=true 时立即应用（重启）；false 时仅落配置，重启后生效。
if apply_now:
    try:
        import subprocess
        pr = subprocess.run(['/usr/syno/bin/synopkg', 'restart', 'openclaw2'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        out['restartTriggered'] = True
        out['restartRc'] = pr.returncode
        out['restartOutTail'] = ((pr.stdout or b'').decode('utf-8', 'ignore'))[-180:]
    except Exception as e:
        out['restartTriggered'] = False
        out['restartErr'] = str(e)
else:
    out['restartTriggered'] = False
    out['message'] = '配置已保存，重启后生效'
print(json.dumps(out, ensure_ascii=False))
PY
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


def build_candidates(base, api):
    out = []

    def add(url):
        if url and url not in out:
            out.append(url)

    if api == 'ollama':
        add(base + '/api/tags')
        if base.endswith('/v1'):
            add(base + '/models')
        else:
            add(base + '/v1/models')
    else:
        if base.endswith('/v1'):
            add(base + '/models')
            add(base[:-3] + '/models' if base[:-3] else '/models')
        else:
            add(base + '/models')
            add(base + '/v1/models')
    return out


def fetch_json(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8', 'ignore'))


last_error = None
for endpoint in build_candidates(base_url, api_type):
    try:
        data = fetch_json(endpoint)
        models = []
        if api_type == 'ollama' and endpoint.endswith('/api/tags'):
            for item in data.get('models', []):
                name = item.get('name') or item.get('model') or ''
                if name:
                    models.append({'id': name, 'modelId': name})
        else:
            for item in data.get('data', data.get('models', [])):
                mid = item.get('id') or item.get('name') or item.get('model') or ''
                if mid:
                    models.append({'id': mid, 'modelId': mid})
        print(json.dumps({'models': models, 'resolvedEndpoint': endpoint}, ensure_ascii=False))
        raise SystemExit
    except Exception as e:
        last_error = f"{endpoint}: {e}"

print(json.dumps({'error': last_error or 'discover failed', 'models': []}, ensure_ascii=False))
PY
            exit 0
            ;;
        models_sync_provider)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body"
import json, sys, urllib.request
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
try:
    payload = json.loads(raw or '{}')
except Exception:
    print('{"error":"invalid payload","models":[]}')
    raise SystemExit
base_url = (payload.get('baseUrl') or '').strip().rstrip('/')
api_key = (payload.get('apiKey') or '').strip()
api_type = (payload.get('api') or 'openai-completions').strip()
if not base_url:
    print('{"error":"baseUrl required","models":[]}')
    raise SystemExit
headers = {'User-Agent': 'openclaw2-native-ui/1.0'}
if api_key:
    headers['Authorization'] = 'Bearer ' + api_key

def build_candidates(base, api):
    out = []
    def add(url):
        if url and url not in out:
            out.append(url)
    if api == 'ollama':
        add(base + '/api/tags')
        if base.endswith('/v1'):
            add(base + '/models')
        else:
            add(base + '/v1/models')
    else:
        if base.endswith('/v1'):
            add(base + '/models')
            add(base[:-3] + '/models' if base[:-3] else '/models')
        else:
            add(base + '/models')
            add(base + '/v1/models')
    return out

last_error = None
for endpoint in build_candidates(base_url, api_type):
    try:
        req = urllib.request.Request(endpoint, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode('utf-8', 'ignore'))
        models = []
        if api_type == 'ollama' and endpoint.endswith('/api/tags'):
            seq = data.get('models', [])
        else:
            seq = data.get('data', data.get('models', []))
        for item in seq:
            if not isinstance(item, dict):
                continue
            mid = item.get('id') or item.get('name') or item.get('model') or ''
            if mid:
                models.append({'id': mid, 'modelId': mid})
        print(json.dumps({'models': models, 'resolvedEndpoint': endpoint}, ensure_ascii=False))
        raise SystemExit
    except Exception as e:
        last_error = f"{endpoint}: {e}"
print(json.dumps({'error': last_error or 'sync failed', 'models': []}, ensure_ascii=False))
PY
            exit 0
            ;;
        channels)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "/volume1/docker/openclaw/.openclaw/openclaw.json"
import json, os, sys
cfg_path = sys.argv[1] if len(sys.argv) > 1 else ''
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
ch = cfg.get('channels') or {}

def enabled_ids(channels):
  ids = []
  for cid, cv in (channels or {}).items():
    if isinstance(cv, dict):
      if cv.get('enabled', True):
        ids.append(cid)
    else:
      ids.append(cid)
  return ids

out = {
  'configPath': cfg_path,
  'configExists': bool(cfg),
  'configuredChannelIds': enabled_ids(ch),
  'feishu': ch.get('feishu') or {},
  'wecom': ch.get('wecom') or {},
  'dingtalk': ch.get('dingtalk') or {},
  'qqbot': ch.get('qqbot') or {},
  'weixin': ch.get('weixin') or {}
}
print(json.dumps(out, ensure_ascii=False))
PY
            exit 0
            ;;
        channels_save)
            body=$(read_body)
            cfg_file="/volume1/docker/openclaw/.openclaw/openclaw.json"
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "$cfg_file"
import json, os, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
cfg_path = sys.argv[2] if len(sys.argv) > 2 else ''
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
ch = cfg.setdefault('channels', {})
if isinstance(payload.get('feishu'), dict):
    f = ch.setdefault('feishu', {})
    app_id = (payload['feishu'].get('appId') or '').strip()
    app_secret = (payload['feishu'].get('appSecret') or '').strip()
    if app_id:
        f.setdefault('defaultAccount', 'default')
        ac = f.setdefault('accounts', {}).setdefault(f['defaultAccount'], {})
        ac['appId'] = app_id
    if app_secret:
        f.setdefault('defaultAccount', 'default')
        ac = f.setdefault('accounts', {}).setdefault(f['defaultAccount'], {})
        ac['appSecret'] = app_secret
    f['dmPolicy'] = 'open'; f['groupPolicy'] = 'open'; f['allowFrom'] = ['*']; f['enabled'] = True
if isinstance(payload.get('wecom'), dict):
    w = ch.setdefault('wecom', {})
    bot_id = (payload['wecom'].get('botId') or '').strip()
    sec = (payload['wecom'].get('secret') or '').strip()
    if bot_id: w['botId'] = bot_id
    if sec: w['secret'] = sec
    w['enabled'] = True; w['dmPolicy'] = 'open'; w['groupPolicy'] = 'open'; w['allowFrom'] = ['*']
if isinstance(payload.get('dingtalk'), dict):
    d = ch.setdefault('dingtalk', {})
    cid = (payload['dingtalk'].get('clientId') or '').strip()
    csec = (payload['dingtalk'].get('clientSecret') or '').strip()
    if cid: d['clientId'] = cid
    if csec: d['clientSecret'] = csec
    d['enabled'] = True; d['dmPolicy'] = 'open'; d['groupPolicy'] = 'open'; d['allowFrom'] = ['*']
if isinstance(payload.get('qqbot'), dict):
    q = ch.setdefault('qqbot', {})
    aid = (payload['qqbot'].get('appId') or '').strip()
    sec = (payload['qqbot'].get('clientSecret') or '').strip()
    if aid: q['appId'] = aid
    if sec: q['clientSecret'] = sec
    q['enabled'] = True; q['dmPolicy']='open'; q['groupPolicy']='open'; q['allowFrom']=['*']
if isinstance(payload.get('weixin'), dict):
    w = ch.setdefault('openclaw-weixin', {})
    w['enabled'] = bool(payload['weixin'].get('enabled', True))

# 保存渠道时，自动补齐插件 allow/entries（完整权限），避免插件未加载导致渠道不可用。
plugins = cfg.setdefault('plugins', {})
plugins['enabled'] = True
allow = plugins.get('allow')
if not isinstance(allow, list):
    allow = []
entries = plugins.get('entries')
if not isinstance(entries, dict):
    entries = {}

channel_plugin_map = {
    'feishu': 'feishu',
    'qqbot': 'qqbot',
    'dingtalk': 'dingtalk',
    'wecom': 'wecom',
    'openclaw-weixin': 'openclaw-weixin',
    'weixin': 'openclaw-weixin'
}
for cid, cv in (ch or {}).items():
    enabled = True
    if isinstance(cv, dict):
        enabled = bool(cv.get('enabled', True))
    if not enabled:
        continue
    pid = channel_plugin_map.get(cid)
    if not pid:
        continue
    if pid not in allow:
        allow.append(pid)
    e = entries.get(pid)
    if not isinstance(e, dict):
        e = {}
    e['enabled'] = True
    entries[pid] = e

plugins['allow'] = allow
plugins['entries'] = entries

def enabled_ids(channels):
    ids = []
    for cid, cv in (channels or {}).items():
        if isinstance(cv, dict):
            if cv.get('enabled', True):
                ids.append(cid)
        else:
            ids.append(cid)
    return ids

os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')

# 保存渠道后自动热重载 gateway，尽量做到“保存后直接可用”。
reload_ok = False
reload_out = ''
try:
    import subprocess
    env = os.environ.copy()
    env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
    env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/openclaw2/data'
    env['HOME'] = '/volume1/@appdata/openclaw2/data/home'
    env['OPENCLAW_CONFIG_PATH'] = cfg_path
    env['OPENCLAW_STATE_DIR'] = '/volume1/docker/openclaw/.openclaw'
    cmd = ['/var/packages/openclaw2/target/bin/openclaw', 'gateway', 'restart', '--json']
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    reload_ok = (p.returncode == 0)
    reload_out = (p.stdout or b'').decode('utf-8', 'ignore')[-500:]
except Exception as e:
    reload_ok = False
    reload_out = str(e)

channels_obj = (cfg.get('channels') or {})
out = {
  'configPath': cfg_path, 'configExists': True,
  'configuredChannelIds': enabled_ids(channels_obj),
  'feishu': channels_obj.get('feishu') or {},
  'wecom': channels_obj.get('wecom') or {},
  'dingtalk': channels_obj.get('dingtalk') or {},
  'qqbot': channels_obj.get('qqbot') or {},
  'weixin': channels_obj.get('weixin') or {},
  'reloaded': reload_ok,
  'reloadOutput': reload_out
}
print(json.dumps(out, ensure_ascii=False))
PY
            exit 0
            ;;
        channels_delete)
            body=$(read_body)
            cfg_file="/volume1/docker/openclaw/.openclaw/openclaw.json"
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "$cfg_file"
import json, os, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
cfg_path = sys.argv[2] if len(sys.argv) > 2 else ''
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
cid = (payload.get('id') or '').strip()
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
ch = cfg.setdefault('channels', {})
if cid:
    # 删除语义：从配置中彻底移除该渠道，避免残留账号信息。
    if cid in ch:
        ch.pop(cid, None)

    # 微信别名联动：两个 key 都清理。
    if cid in ('openclaw-weixin', 'weixin'):
        ch.pop('openclaw-weixin', None)
        ch.pop('weixin', None)

    # 删除渠道只改 channels 配置，不做插件 allow/entries 热删。
    # 这样可避免运行中出现短暂“停止->运行”的抖动；插件层按重启后策略生效。


def enabled_ids(channels):
    ids = []
    for k, v in (channels or {}).items():
        if isinstance(v, dict):
            if v.get('enabled', True):
                ids.append(k)
        else:
            ids.append(k)
    return ids

os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')
channels_obj = (cfg.get('channels') or {})
out = {
  'configPath': cfg_path, 'configExists': True,
  'configuredChannelIds': enabled_ids(channels_obj),
  'feishu': channels_obj.get('feishu') or {},
  'wecom': channels_obj.get('wecom') or {},
  'dingtalk': channels_obj.get('dingtalk') or {},
  'qqbot': channels_obj.get('qqbot') or {},
  'weixin': channels_obj.get('weixin') or {},
  'reloaded': False,
  'message': 'deleted in config only, no hot restart'
}

print(json.dumps(out, ensure_ascii=False))
PY
            exit 0
            ;;
        weixin_status)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"connected":false,"status":"idle","message":"weixin status local mode"}'
            exit 0
            ;;
        weixin_login_start)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "${APP_VAR_DIR}/data/home" "/volume1/docker/openclaw/.openclaw/openclaw.json" "${APP_VAR_DIR}/weixin-login-debug.log" "${APP_VAR_DIR}/weixin-login-worker.pid" "$body"
import json, os, re, subprocess, sys, time, select, signal
home_dir = sys.argv[1]
cfg_path = sys.argv[2]
debug_log = sys.argv[3] if len(sys.argv) > 3 else '/tmp/openclaw-weixin-login.log'
worker_pid_file = sys.argv[4] if len(sys.argv) > 4 else '/tmp/openclaw-weixin-login-worker.pid'
raw_body = sys.argv[5] if len(sys.argv) > 5 else '{}'
start_ts = time.time()
round_id = f"r{int(start_ts*1000)}"
try:
    payload = json.loads(raw_body or '{}')
except Exception:
    payload = {}
force_new = bool((payload or {}).get('force', False))

def log(msg):
    try:
        os.makedirs(os.path.dirname(debug_log), exist_ok=True)
        with open(debug_log, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/openclaw2/data'
env['HOME'] = home_dir
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = '/volume1/docker/openclaw/.openclaw'
log(f'weixin_login_start begin round={round_id} force={1 if force_new else 0}')
# 清理历史遗留登录 worker，避免旧流程仍在后台运行干扰当前登录。
try:
    if os.path.exists(worker_pid_file):
        pid_txt = (open(worker_pid_file, 'r', encoding='utf-8').read() or '').strip()
        if pid_txt:
            try:
                os.kill(int(pid_txt), signal.SIGTERM)
                log(f'legacy_login_worker_stopped pid={pid_txt} round={round_id}')
            except Exception:
                pass
        try:
            os.remove(worker_pid_file)
        except Exception:
            pass
except Exception:
    pass

# 关键：openclaw2 内部有并发流程会覆写 openclaw.json，导致 weixin 插件配置丢失。
# 每次开始登录前都做一次强制修正，确保 allowlist/entries/channels 包含 openclaw-weixin。
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
plugins = cfg.setdefault('plugins', {})
plugins['enabled'] = True
allow = plugins.get('allow')
if not isinstance(allow, list):
    allow = []
if 'openclaw-weixin' not in allow:
    allow.append('openclaw-weixin')
plugins['allow'] = allow
entries = plugins.get('entries')
if not isinstance(entries, dict):
    entries = {}
entry = entries.get('openclaw-weixin')
if not isinstance(entry, dict):
    entry = {}
entry['enabled'] = True
entries['openclaw-weixin'] = entry
plugins['entries'] = entries
chs = cfg.setdefault('channels', {})
wx = chs.get('openclaw-weixin')
if not isinstance(wx, dict):
    wx = {}
wx['enabled'] = True
chs['openclaw-weixin'] = wx
if 'weixin' in chs:
    try:
        chs.pop('weixin', None)
    except Exception:
        pass
os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')
log('openclaw_weixin_config_repaired=1')
# 提速：不再每次执行 plugins enable（该操作经常阻塞 15s+），仅在配置层保证可用。
bootstrap_log = 'openclaw-weixin config repaired (fast path)'
log('openclaw_weixin_ensure_enabled=1 fast_path=1')

# 直接调用微信二维码接口（对齐 trim.openclaw_v0.0.10 的“秒出码”路径），避免走 CLI login 阻塞。
import urllib.request, urllib.error
base_url = 'https://ilinkai.weixin.qq.com'
bot_type = '3'
qrcode = None
url = None
err_text = ''
login_begin = time.time()
try:
    req = urllib.request.Request(f"{base_url}/ilink/bot/get_bot_qrcode?bot_type={bot_type}", headers={'iLink-App-ClientVersion': '1'})
    with urllib.request.urlopen(req, timeout=12) as r:
        body = (r.read() or b'').decode('utf-8', 'ignore')
    j = json.loads(body or '{}')
    qrcode = str(j.get('qrcode') or '')
    url = str(j.get('qrcode_img_content') or '')
    if qrcode and url:
        log(f'qr_url_detected_ms={int((time.time()-login_begin)*1000)} round={round_id} url={url}')
    else:
        err_text = body[-500:]
except Exception as e:
    err_text = str(e)
    log(f'weixin_direct_qr_err_ms={int((time.time()-login_begin)*1000)} round={round_id} err={e}')

if url and qrcode:
    try:
        state = {
            'roundId': round_id,
            'sessionKey': 'openclaw-weixin',
            'qrcode': qrcode,
            'qrUrl': url,
            'baseUrl': base_url,
            'startedAt': int(time.time()),
            'force': bool(force_new)
        }
        with open('/tmp/openclaw2-weixin-login-state.json', 'w', encoding='utf-8') as sf:
            json.dump(state, sf, ensure_ascii=False)
        log(f'weixin_state_saved round={round_id} qrcode_len={len(qrcode)}')
    except Exception as e:
        log(f'weixin_state_save_err round={round_id} err={e}')

    log(f'return_ms={int((time.time()-start_ts)*1000)} round={round_id} success=1')
    print(json.dumps({'supported': True, 'qrUrl': url, 'sessionKey': 'openclaw-weixin', 'roundId': round_id, 'message': '请用微信扫码完成登录', 'debugLog': debug_log}, ensure_ascii=False))
else:
    snippet = (bootstrap_log + '\n' + err_text)[-600:].replace('\n', ' | ')
    log(f'return_ms={int((time.time()-start_ts)*1000)} round={round_id} success=0 output_snippet={snippet}')
    print(json.dumps({'supported': False, 'message': '未获取到二维码，请重试', 'raw': snippet, 'debugLog': debug_log}, ensure_ascii=False))
PY
            exit 0
            ;;
        weixin_login_wait)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "/volume1/docker/openclaw/.openclaw/openclaw.json" "${APP_VAR_DIR}/weixin-login-debug.log" "${APP_VAR_DIR}/weixin-login-worker.pid" "$body"
import json, os, subprocess, sys, time
cfg_path = sys.argv[1]
debug_log = sys.argv[2] if len(sys.argv) > 2 else '/tmp/openclaw-weixin-login.log'
worker_pid_file = sys.argv[3] if len(sys.argv) > 3 else '/tmp/openclaw-weixin-login-worker.pid'
raw_body = sys.argv[4] if len(sys.argv) > 4 else '{}'
try:
    payload = json.loads(raw_body or '{}')
except Exception:
    payload = {}
round_id = str((payload or {}).get('roundId') or '').strip()

def log(msg):
    try:
        os.makedirs(os.path.dirname(debug_log), exist_ok=True)
        with open(debug_log, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/openclaw2/data'
env['HOME'] = '/volume1/@appdata/openclaw2/data/home'
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = '/volume1/docker/openclaw/.openclaw'
cmd = ['/var/packages/openclaw2/target/bin/openclaw', 'channels', 'status', '--json']
raw = ''
try:
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
    raw = (p.stdout or b'').decode('utf-8', 'ignore')
except Exception as e:
    raw = str(e)
text = raw
if raw.strip().startswith('202') and '\n{' in raw:
    text = raw[raw.find('\n{')+1:]
connected = False
message = '等待扫码确认'

# 新实现：直接轮询二维码状态接口（对齐 trim.openclaw_v0.0.10），不再依赖日志关键字判定连接。
import urllib.request, urllib.error
state_file = '/tmp/openclaw2-weixin-login-state.json'
state = {}
if os.path.exists(state_file):
    try:
        state = json.load(open(state_file, 'r', encoding='utf-8'))
    except Exception:
        state = {}
state_round = str(state.get('roundId') or '').strip()
if round_id and state_round and round_id != state_round:
    connected = False
    message = '等待扫码确认'
    qr_url = str(state.get('qrUrl') or '')
    print(json.dumps({'supported': True, 'connected': False, 'status': 'pending', 'message': message, 'qrUrl': qr_url, 'raw': raw[-300:]}, ensure_ascii=False))
    raise SystemExit

qrcode = str(state.get('qrcode') or '')
base_url = str(state.get('baseUrl') or 'https://ilinkai.weixin.qq.com')
qr_url = str(state.get('qrUrl') or '')
if not qrcode:
    print(json.dumps({'supported': True, 'connected': False, 'status': 'idle', 'message': '请先点击“开始微信登录”生成二维码', 'qrUrl': qr_url, 'raw': raw[-300:]}, ensure_ascii=False))
    raise SystemExit

connected = False
status = 'pending'
message = '等待扫码确认'
try:
    req = urllib.request.Request(f"{base_url}/ilink/bot/get_qrcode_status?qrcode={qrcode}", headers={'iLink-App-ClientVersion': '1'})
    with urllib.request.urlopen(req, timeout=12) as r:
        body = (r.read() or b'').decode('utf-8', 'ignore')
    st = json.loads(body or '{}')
    s = str(st.get('status') or 'wait')
    if s == 'confirmed' and st.get('bot_token') and st.get('ilink_bot_id'):
        connected = True
        status = 'connected'
        message = '已连接'
        # 落盘账号，供渠道实际收发使用
        try:
            import re
            aid_raw = str(st.get('ilink_bot_id') or '').strip()
            aid = re.sub(r'[^a-zA-Z0-9_-]+', '-', aid_raw).strip('-')
            if not aid:
                aid = aid_raw.replace('@', '-').replace('.', '-')
            acc_dir = '/volume1/docker/openclaw/.openclaw/openclaw-weixin/accounts'
            os.makedirs(acc_dir, exist_ok=True)
            acc_path = os.path.join(acc_dir, f'{aid}.json')
            acc = {
                'token': str(st.get('bot_token') or ''),
                'savedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'baseUrl': str(st.get('baseurl') or base_url),
                'userId': str(st.get('ilink_user_id') or '')
            }
            with open(acc_path, 'w', encoding='utf-8') as af:
                json.dump(acc, af, ensure_ascii=False, indent=2)
                af.write('\n')
            ids_path = '/volume1/docker/openclaw/.openclaw/openclaw-weixin/accounts.json'
            # 关键：仅保留当前新账号，避免网关继续用旧账号（旧账号常被 session-guard 暂停）
            with open(ids_path, 'w', encoding='utf-8') as idf:
                json.dump([aid], idf, ensure_ascii=False, indent=2)
                idf.write('\n')
            # 清理旧账号文件
            try:
                for fn in os.listdir(acc_dir):
                    if not fn.endswith('.json'):
                        continue
                    if fn == f'{aid}.json':
                        continue
                    try:
                        os.remove(os.path.join(acc_dir, fn))
                    except Exception:
                        pass
            except Exception:
                pass
            # 同步重写 openclaw.json 的渠道账号配置，强制只启用当前账号
            try:
                ocfg_path = '/volume1/docker/openclaw/.openclaw/openclaw.json'
                ocfg = json.load(open(ocfg_path, 'r', encoding='utf-8')) if os.path.exists(ocfg_path) else {}
                chs = ocfg.setdefault('channels', {})
                wx = chs.get('openclaw-weixin')
                if not isinstance(wx, dict):
                    wx = {}
                wx['enabled'] = True
                wx['defaultAccount'] = aid
                wx['accounts'] = {aid: {'enabled': True}}
                chs['openclaw-weixin'] = wx

                # 同步强制插件 allow/entries，避免网关重启后只剩 browser。
                plugs = ocfg.setdefault('plugins', {})
                plugs['enabled'] = True
                allow = plugs.get('allow')
                if not isinstance(allow, list):
                    allow = []
                if 'openclaw-weixin' not in allow:
                    allow.append('openclaw-weixin')
                plugs['allow'] = allow
                ents = plugs.get('entries')
                if not isinstance(ents, dict):
                    ents = {}
                pe = ents.get('openclaw-weixin')
                if not isinstance(pe, dict):
                    pe = {}
                pe['enabled'] = True
                ents['openclaw-weixin'] = pe
                plugs['entries'] = ents

                with open(ocfg_path, 'w', encoding='utf-8') as cf:
                    json.dump(ocfg, cf, ensure_ascii=False, indent=2)
                    cf.write('\n')
            except Exception as e2:
                log(f'weixin_openclaw_json_update_err={e2}')

            # 连接成功后重启一次包，使网关立刻切换到新账号
            try:
                pr = subprocess.run(['/usr/syno/bin/synopkg', 'restart', 'openclaw2'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
                rt = (pr.stdout or b'').decode('utf-8', 'ignore')
                log(f'weixin_restart_after_confirm rc={pr.returncode} out={rt[-180:]}')
            except Exception as e3:
                log(f'weixin_restart_after_confirm_err={e3}')

            log(f'weixin_account_saved aid={aid} round={state_round or round_id} single_account=1')
        except Exception as e:
            log(f'weixin_account_save_err={e}')
    elif s == 'scaned':
        connected = False
        status = 'scaned'
        message = '已扫码，请在微信里确认授权'
    elif s == 'expired':
        connected = False
        status = 'expired'
        message = '二维码已过期，请点“重新生成”'
    else:
        connected = False
        status = 'pending'
        message = '等待扫码确认'
except Exception as e:
    connected = False
    status = 'pending'
    message = '等待扫码确认'
    log(f'weixin_qr_status_poll_err={e}')

log(f'weixin_login_wait connected={bool(connected)} status={status} message={message}')
print(json.dumps({'supported': True, 'connected': bool(connected), 'status': status, 'message': message, 'qrUrl': qr_url, 'raw': raw[-300:]}, ensure_ascii=False))
PY
            exit 0
            ;;
        weixin_disconnect)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "/volume1/docker/openclaw/.openclaw/openclaw.json"
import json, os, subprocess, sys
cfg_path = sys.argv[1]
env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/openclaw2/data'
env['HOME'] = '/volume1/@appdata/openclaw2/data/home'
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = '/volume1/docker/openclaw/.openclaw'
cmd = ['/var/packages/openclaw2/target/bin/openclaw', 'channels', 'logout', '--channel', 'openclaw-weixin']
try:
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=12)
    text = (p.stdout or b'').decode('utf-8', 'ignore')
    # 同步禁用配置中的 weixin 渠道（若存在）
    try:
        cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if os.path.exists(cfg_path) else {}
    except Exception:
        cfg = {}
    ch = cfg.setdefault('channels', {})
    for key in ('openclaw-weixin', 'weixin'):
        if key in ch:
            if isinstance(ch[key], dict):
                ch[key]['enabled'] = False
            else:
                ch[key] = {'enabled': False}
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'supported': True, 'ok': p.returncode == 0, 'message': '已断开' if p.returncode == 0 else '断开失败', 'raw': text[-300:]}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({'supported': False, 'ok': False, 'message': str(e)}, ensure_ascii=False))
PY
            exit 0
            ;;
        plugins)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"plugins":[],"source":"local","stale":false,"refreshing":false}'
            exit 0
            ;;
        plugins_refresh)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":true,"source":"local"}'
            exit 0
            ;;
        terminal_session_start)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "${APP_VAR_DIR}"
import json, os, signal, socket, subprocess, sys, time
base = (sys.argv[1] if len(sys.argv) > 1 else '/tmp').rstrip('/')
term_root = os.path.join(base, 'terminal-sessions')
os.makedirs(term_root, exist_ok=True)
sid = f"t{int(time.time()*1000)}-{os.getpid()}"
sdir = os.path.join(term_root, sid)
os.makedirs(sdir, exist_ok=True)
fifo = os.path.join(sdir, 'in.fifo')
log = os.path.join(sdir, 'out.log')
pid_file = os.path.join(sdir, 'shell.pid')
keeper_file = os.path.join(sdir, 'keeper.pid')
open(log, 'ab').close()
os.mkfifo(fifo)

cfg_path = '/volume1/docker/openclaw/.openclaw/openclaw.json'
workspace_dir = '/volume1/docker/openclaw'
try:
    if os.path.exists(cfg_path):
        cfg = json.load(open(cfg_path, 'r', encoding='utf-8'))
        ws = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '').strip()
        if ws:
            workspace_dir = ws
except Exception:
    pass
try:
    os.makedirs(workspace_dir, exist_ok=True)
except Exception:
    workspace_dir = '/volume1/@appdata/openclaw2/data/home'

env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/openclaw2/data'
env['HOME'] = workspace_dir
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = '/volume1/docker/openclaw/.openclaw'
# 提示符直接显示当前目录（由 shell 原生渲染）。
env['PS1'] = '\\w$ '
# 确保 openclaw 原生命令任意目录可用
env['PATH'] = '/var/packages/openclaw2/target/bin:/var/packages/openclaw/target/bin:/usr/local/bin:' + env.get('PATH', '')
try:
    cli = '/var/packages/openclaw2/target/bin/openclaw'
    if not os.path.exists(cli):
        cli = '/var/packages/openclaw/target/bin/openclaw'
    link = '/usr/local/bin/openclaw'
    if os.path.exists(cli):
        if os.path.islink(link) or os.path.exists(link):
            try:
                if os.path.realpath(link) != cli:
                    os.remove(link)
            except Exception:
                pass
        if not os.path.exists(link):
            os.symlink(cli, link)
except Exception:
    pass

import pty, select
cmd_fifo = os.path.join(sdir, 'cmd.fifo')
os.mkfifo(cmd_fifo)

master_fd, slave_fd = pty.openpty()
# 真 PTY 交互 shell（退格/Tab/行编辑由终端驱动处理）
shell = subprocess.Popen(['/bin/bash','--noprofile','--norc','-i'], stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, cwd=workspace_dir, env=env, start_new_session=True)
os.close(slave_fd)

# 初始化到目标目录并固定提示符样式（SSH 风格）
try:
    os.write(master_fd, (f"cd '{workspace_dir}'\nexport PS1='\\u@\\h:\\w$ '\n").encode('utf-8', 'ignore'))
except Exception:
    pass

relay_pid = os.fork()
if relay_pid == 0:
    # 中继进程：cmd_fifo -> pty，pty -> out.log
    # 关闭 CGI stdout/stderr，避免请求被子进程持续占用导致前端卡在“终端连接中...”。
    try:
        devnull = os.open('/dev/null', os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        if devnull > 2:
            os.close(devnull)
    except Exception:
        pass
    try:
        cmd_fd = os.open(cmd_fifo, os.O_RDWR | os.O_NONBLOCK)
        with open(log, 'ab', buffering=0) as lf:
            while True:
                if shell.poll() is not None:
                    # shell 退出后尽量把缓冲读完
                    try:
                        while True:
                            b = os.read(master_fd, 4096)
                            if not b:
                                break
                            lf.write(b)
                    except Exception:
                        pass
                    break
                r, _, _ = select.select([master_fd, cmd_fd], [], [], 0.5)
                if master_fd in r:
                    try:
                        b = os.read(master_fd, 4096)
                    except Exception:
                        b = b''
                    if b:
                        lf.write(b)
                if cmd_fd in r:
                    try:
                        b = os.read(cmd_fd, 4096)
                    except Exception:
                        b = b''
                    if b:
                        try:
                            os.write(master_fd, b)
                        except Exception:
                            pass
    finally:
        try: os.close(master_fd)
        except Exception: pass
        try: os.close(cmd_fd)
        except Exception: pass
        os._exit(0)

with open(pid_file, 'w', encoding='utf-8') as f: f.write(str(shell.pid))
with open(keeper_file, 'w', encoding='utf-8') as f: f.write(str(relay_pid))
try:
    user = subprocess.check_output(['id','-un'], text=True).strip()
except Exception:
    user = ''
try:
    host = socket.gethostname()
except Exception:
    host = ''
print(json.dumps({'ok': True, 'sessionId': sid, 'offset': os.path.getsize(log), 'user': user, 'host': host, 'cwd': workspace_dir, 'backend': 'pty-relay'}, ensure_ascii=False))
PY
            exit 0
            ;;
        terminal_session_write)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "${APP_VAR_DIR}"
import json, os, signal, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
base = (sys.argv[2] if len(sys.argv) > 2 else '/tmp').rstrip('/')
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
sid = str(payload.get('sessionId') or '').strip()
text = str(payload.get('text') or '')
if not sid:
    print(json.dumps({'ok': False, 'error': 'missing sessionId'}, ensure_ascii=False)); raise SystemExit
sdir = os.path.join(base, 'terminal-sessions', sid)
cmd_fifo = os.path.join(sdir, 'cmd.fifo')
pid_file = os.path.join(sdir, 'shell.pid')
if not os.path.exists(cmd_fifo) or not os.path.exists(pid_file):
    print(json.dumps({'ok': False, 'error': 'session not found'}, ensure_ascii=False)); raise SystemExit
try:
    pid = int((open(pid_file, 'r', encoding='utf-8').read() or '0').strip() or '0')
    os.kill(pid, 0)
except Exception:
    print(json.dumps({'ok': False, 'error': 'session not alive'}, ensure_ascii=False)); raise SystemExit
with open(cmd_fifo, 'wb', buffering=0) as f:
    f.write(text.encode('utf-8', 'ignore'))
print(json.dumps({'ok': True}, ensure_ascii=False))
PY
            exit 0
            ;;
        terminal_session_read)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "${APP_VAR_DIR}"
import json, os, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
base = (sys.argv[2] if len(sys.argv) > 2 else '/tmp').rstrip('/')
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
sid = str(payload.get('sessionId') or '').strip()
offset = int(payload.get('offset') or 0)
if not sid:
    print(json.dumps({'ok': False, 'error': 'missing sessionId'}, ensure_ascii=False)); raise SystemExit
sdir = os.path.join(base, 'terminal-sessions', sid)
log = os.path.join(sdir, 'out.log')
pid_file = os.path.join(sdir, 'shell.pid')
if not os.path.exists(log):
    print(json.dumps({'ok': False, 'error': 'session not found'}, ensure_ascii=False)); raise SystemExit
size = os.path.getsize(log)
if offset < 0: offset = 0
if offset > size: offset = size
with open(log, 'rb') as f:
    f.seek(offset)
    data = f.read(32768)
next_offset = offset + len(data)
alive = False
try:
    if os.path.exists(pid_file):
      pid = int((open(pid_file, 'r', encoding='utf-8').read() or '0').strip() or '0')
      os.kill(pid, 0)
      alive = True
except Exception:
    alive = False
cwd = ''
try:
    if os.path.exists(pid_file):
        pid = int((open(pid_file, 'r', encoding='utf-8').read() or '0').strip() or '0')
        cwd = os.path.realpath(f'/proc/{pid}/cwd') if pid > 0 else ''
except Exception:
    cwd = ''
print(json.dumps({'ok': True, 'output': data.decode('utf-8', 'ignore'), 'nextOffset': next_offset, 'alive': alive, 'cwd': cwd}, ensure_ascii=False))
PY
            exit 0
            ;;
        terminal_session_stop)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "${APP_VAR_DIR}"
import json, os, signal, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
base = (sys.argv[2] if len(sys.argv) > 2 else '/tmp').rstrip('/')
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
sid = str(payload.get('sessionId') or '').strip()
if not sid:
    print(json.dumps({'ok': False, 'error': 'missing sessionId'}, ensure_ascii=False)); raise SystemExit
sdir = os.path.join(base, 'terminal-sessions', sid)
for fn in ('shell.pid','keeper.pid'):
    p = os.path.join(sdir, fn)
    if os.path.exists(p):
        try:
            pid = int((open(p, 'r', encoding='utf-8').read() or '0').strip() or '0')
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
print(json.dumps({'ok': True}, ensure_ascii=False))
PY
            exit 0
            ;;
        plugin_install)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":true,"message":"builtin plugins, no install needed"}'
            exit 0
            ;;
        install)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":true,"message":"local mode"}'
            exit 0
            ;;
        install_run)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "/volume1/docker/openclaw/.openclaw/openclaw.json"
import json, os, subprocess, sys, time
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
cfg = sys.argv[2]
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
action = (payload.get('action') or '').strip().lower()
if action not in ('start','stop','restart'):
    print(json.dumps({'ok': False, 'error': 'unsupported action'}, ensure_ascii=False)); raise SystemExit

env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG']='0'
env['OPENCLAW_DATA_DIR']='/volume1/@appdata/openclaw2/data'
env['HOME']='/volume1/@appdata/openclaw2/data/home'
env['OPENCLAW_CONFIG_PATH']=cfg
env['OPENCLAW_STATE_DIR']='/volume1/docker/openclaw/.openclaw'
env['OPENCLAW_TOOLS_PROFILE']='full'
env['OPENCLAW_TOOLS_ELEVATED_ENABLED']='1'
env['OPENCLAW_ELEVATED_DEFAULT']='full'
env['OPENCLAW_EXEC_SECURITY_DEFAULT']='full'

# 强制保持 LAN 可访问（44539）
try:
    c = json.load(open(cfg,'r',encoding='utf-8')) if cfg and os.path.exists(cfg) else {}
except Exception:
    c = {}
gw = c.setdefault('gateway', {})
gw['bind'] = 'lan'
gw['mode'] = 'local'
gw['port'] = 18789
cu = gw.setdefault('controlUi', {})
cu['allowInsecureAuth'] = True
cu['dangerouslyDisableDeviceAuth'] = True
cu['allowedOrigins'] = ['*']
# 兼容清理：移除当前版本不支持的键，避免启动时报 Invalid config
defs = c.setdefault('agents', {}).setdefault('defaults', {})
if isinstance(defs, dict) and 'fallbackModels' in defs:
    defs.pop('fallbackModels', None)
# 外部命令权限：默认开启 full + elevated（用户要求“完整权限”）
if isinstance(defs, dict):
    defs['elevatedDefault'] = 'full'

tools = c.setdefault('tools', {})
if not isinstance(tools, dict):
    tools = {}
    c['tools'] = tools
tools['profile'] = 'full'
elev = tools.setdefault('elevated', {})
if not isinstance(elev, dict):
    elev = {}
    tools['elevated'] = elev
elev['enabled'] = True
allow_from = elev.get('allowFrom')
if not isinstance(allow_from, dict):
    allow_from = {}
for k in ['webchat', 'feishu', 'dingtalk', 'qqbot', 'wecom', 'telegram', 'discord', 'slack']:
    v = allow_from.get(k)
    if not isinstance(v, list) or not v:
        allow_from[k] = ['*']
elev['allowFrom'] = allow_from

os.makedirs(os.path.dirname(cfg), exist_ok=True)
with open(cfg,'w',encoding='utf-8') as f:
    json.dump(c,f,ensure_ascii=False,indent=2); f.write('\n')

# 安装后自动补齐完整默认策略（全新可用配置）
try:
    plugins = c.setdefault('plugins', {})
    plugins['enabled'] = True
    allow = plugins.get('allow')
    if not isinstance(allow, list):
        allow = []
    for pid in ['feishu','qqbot','dingtalk','wecom','openclaw-weixin']:
        if pid not in allow:
            allow.append(pid)
    plugins['allow'] = allow
    entries = plugins.get('entries')
    if not isinstance(entries, dict):
        entries = {}
    for pid in ['feishu','qqbot','dingtalk','wecom','openclaw-weixin']:
        ent = entries.get(pid)
        if not isinstance(ent, dict):
            ent = {}
        ent['enabled'] = True
        entries[pid] = ent
    plugins['entries'] = entries

    # 不在启动流程里强行重建/启用 channels，避免用户删除后的渠道在重启后“复活”。
    with open(cfg,'w',encoding='utf-8') as f2:
        json.dump(c,f2,ensure_ascii=False,indent=2); f2.write('\n')
except Exception:
    pass

def run(cmd, timeout=20):
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.returncode, (p.stdout or b'').decode('utf-8','ignore')

def force_stop():
    out=[]
    for cmd in [
        ['pkill','-f','openclaw-gatew'],
        ['pkill','-f','/app/openclaw/dist/index.js gateway'],
        ['pkill','-f','openclaw gateway']
    ]:
        try:
            p=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5)
            out.append((cmd,p.returncode,(p.stdout or b'').decode('utf-8','ignore')))
        except Exception as e:
            out.append((cmd,999,str(e)))
    return out

logs=[]
ok=True
if action in ('stop','restart'):
    rc, txt = run(['/var/packages/openclaw2/target/bin/openclaw','gateway','stop','--json'], timeout=35)
    logs.append({'cmd':'gateway stop --json','rc':rc,'out':txt[-800:]})
    force = force_stop()
    logs.append({'cmd':'force-stop','out':str(force)[:800]})
    time.sleep(1)

if action in ('start','restart'):
    # 启动前执行一次模型同步脚本（不阻塞启动）
    sync_script = '/root/openclaw-sync-models.sh'
    if os.path.exists(sync_script):
        try:
            rc_sync, out_sync = run([sync_script, cfg], timeout=120)
            logs.append({'cmd': f'{sync_script} {cfg}', 'rc': rc_sync, 'out': out_sync[-1200:]})
        except Exception as e:
            logs.append({'cmd': f'{sync_script} {cfg}', 'error': str(e)})

    # 启动前强制清理 agents.defaults.models，只保留当前 providers.models 存在的引用
    try:
        c2 = json.load(open(cfg,'r',encoding='utf-8')) if cfg and os.path.exists(cfg) else {}
        defs2 = c2.setdefault('agents', {}).setdefault('defaults', {})
        providers2 = ((c2.get('models') or {}).get('providers') or {})
        active_refs = set()
        for pid, pv in providers2.items():
            if not isinstance(pv, dict):
                continue
            for m in (pv.get('models') or []):
                if isinstance(m, dict):
                    mid = (m.get('modelId') or m.get('id') or '').strip()
                    if mid:
                        active_refs.add(f'{pid}/{mid}')
        cur_models = defs2.get('models')
        if isinstance(cur_models, list):
            cur_models = {k:{} for k in cur_models if isinstance(k, str)}
        if not isinstance(cur_models, dict):
            cur_models = {}
        new_models = {k: (cur_models.get(k) if isinstance(cur_models.get(k), dict) else {}) for k in sorted(active_refs)}
        defs2['models'] = new_models
        # primary 若失效则兜底到第一个可用模型
        mobj = defs2.get('model')
        primary = ''
        if isinstance(mobj, dict):
            primary = (mobj.get('primary') or '').strip()
        elif isinstance(mobj, str):
            primary = mobj.strip()
        if primary and primary not in active_refs and active_refs:
            first_ref = sorted(active_refs)[0]
            if isinstance(mobj, dict):
                mobj['primary'] = first_ref
            else:
                defs2['model'] = {'primary': first_ref}
        with open(cfg,'w',encoding='utf-8') as f:
            json.dump(c2,f,ensure_ascii=False,indent=2); f.write('\n')
        logs.append({'cmd':'sanitize defaults.models','active':len(active_refs),'kept':len(new_models)})
    except Exception as e:
        logs.append({'cmd':'sanitize defaults.models','error':str(e)})

    try:
        logf = open('/tmp/openclaw-gateway.spawn.log','ab', buffering=0)
        p = subprocess.Popen(
            ['/var/packages/openclaw2/target/bin/openclaw','gateway'],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=logf,
            stderr=logf,
            close_fds=True,
            start_new_session=True
        )
        logs.append({'cmd':'gateway(spawn-detached)','pid':p.pid})
        time.sleep(3)
    except Exception as e:
        ok = False
        logs.append({'cmd':'gateway(spawn-detached)','error':str(e)})

import socket

def is_running(port=44539):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(0.6)
    try:
        s.connect(('127.0.0.1',port)); return True
    except Exception:
        return False
    finally:
        s.close()

running = is_running(44539)
if action in ('start','restart') and not running:
    for _ in range(12):
        time.sleep(1)
        running = is_running(44539)
        if running:
            break
print(json.dumps({'ok': ok, 'action': action, 'logs': logs, 'running': running}, ensure_ascii=False))
PY
            exit 0
            ;;
        logs)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            OCL_LOG="/tmp/openclaw-0/openclaw-$(date +%Y-%m-%d).log"
            [ -f "$OCL_LOG" ] || OCL_LOG="/tmp/openclaw-0/openclaw-$(date -d yesterday +%Y-%m-%d 2>/dev/null).log"
            APP_LOG="$LOG_FILE"
            SPAWN_LOG="/tmp/openclaw-gateway.spawn.log"
            [ -f "$OCL_LOG" ] || touch "$OCL_LOG"
            [ -f "$APP_LOG" ] || touch "$APP_LOG"
            [ -f "$SPAWN_LOG" ] || touch "$SPAWN_LOG"
            merged=$( \
              printf '===== openclaw (gateway) :: %s =====\n' "$OCL_LOG"; tail -n 500 "$OCL_LOG" 2>/dev/null; \
              printf '\n===== openclaw2 app :: %s =====\n' "$APP_LOG"; tail -n 220 "$APP_LOG" 2>/dev/null; \
              printf '\n===== spawn log :: %s =====\n' "$SPAWN_LOG"; tail -n 180 "$SPAWN_LOG" 2>/dev/null \
            )
            logs_json=$(printf '%s' "$merged" | sed ':a;N;$!ba;s/\\/\\\\/g;s/"/\\"/g;s/\r/\\r/g;s/\n/\\n/g')
            src_json=$(printf '%s | %s | %s' "$OCL_LOG" "$APP_LOG" "$SPAWN_LOG" | sed 's/\\/\\\\/g;s/"/\\"/g')
            printf '{"log":"%s","source":"%s"}' "$logs_json" "$src_json"
            exit 0
            ;;
        weixin_qr_proxy)
            body=$(read_body)
            qr_encoded=$(urldecode "$(get_param url "$QUERY")")
            python3 - <<'PY' "$body" "$qr_encoded"
import sys, json, urllib.request
raw = sys.argv[1] if len(sys.argv) > 1 else ''
query_url = sys.argv[2] if len(sys.argv) > 2 else ''
url = query_url
if raw:
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get('url'):
            url = str(payload.get('url'))
    except Exception:
        pass
if not url:
    sys.stdout.write('Status: 400 Bad Request\\r\\nContent-Type: text/plain; charset=UTF-8\\r\\n\\r\\nmissing url')
    raise SystemExit
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://liteapp.weixin.qq.com/'
})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        ctype = (r.headers.get('Content-Type') or 'image/png').split(';')[0]
        data = r.read()
    sys.stdout.write(f'Content-Type: {ctype}\\r\\nCache-Control: no-store\\r\\n\\r\\n')
    sys.stdout.flush()
    sys.stdout.buffer.write(data)
except Exception as e:
    sys.stdout.write('Status: 502 Bad Gateway\\r\\nContent-Type: text/plain; charset=UTF-8\\r\\n\\r\\n')
    sys.stdout.write('qr proxy failed: ' + str(e))
PY
            exit 0
            ;;
        weixin_qr_data)
            body=$(read_body)
            qr_encoded=$(urldecode "$(get_param url "$QUERY")")
            DEBUG_LOG="${APP_VAR_DIR}/weixin-login-debug.log"
            {
              echo "[$(date '+%Y-%m-%d %H:%M:%S')] weixin_qr_data requested url_prefix=${qr_encoded%%\?*}"
            } >> "$DEBUG_LOG" 2>/dev/null || true
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            /var/packages/openclaw2/target/bin/node - <<'NODE' "$body" "$qr_encoded"
const body = process.argv[2] || '';
const queryUrl = process.argv[3] || '';
let url = queryUrl;
if (body) {
  try {
    const payload = JSON.parse(body);
    if (payload && typeof payload.url === 'string' && payload.url) url = payload.url;
  } catch {}
}
if (!url) {
  process.stdout.write(JSON.stringify({ ok: false, error: 'missing url' }));
  process.exit(0);
}
try {
  const QRCode = require('/volume1/@appstore/openclaw2/app/openclaw/node_modules/qrcode-terminal/vendor/QRCode');
  const qr = new QRCode(-1, 'M');
  qr.addData(url);
  qr.make();
  const count = qr.getModuleCount();
  const cell = 6;
  const margin = 4;
  const size = (count + margin * 2) * cell;
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges">`;
  svg += `<rect width="100%" height="100%" fill="#ffffff"/>`;
  for (let r = 0; r < count; r++) {
    for (let c = 0; c < count; c++) {
      if (qr.isDark(r, c)) {
        const x = (c + margin) * cell;
        const y = (r + margin) * cell;
        svg += `<rect x="${x}" y="${y}" width="${cell}" height="${cell}" fill="#000000"/>`;
      }
    }
  }
  svg += '</svg>';
  const dataUrl = 'data:image/svg+xml;base64,' + Buffer.from(svg, 'utf8').toString('base64');
  process.stdout.write(JSON.stringify({ ok: true, contentType: 'image/svg+xml', dataUrl }));
} catch (e) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(e && e.message || e) }));
}
NODE
            exit 0
            ;;
        weixin_qr_data2)
            body=$(read_body)
            qr_encoded=$(urldecode "$(get_param url "$QUERY")")
            DEBUG_LOG="${APP_VAR_DIR}/weixin-login-debug.log"
            {
              echo "[$(date '+%Y-%m-%d %H:%M:%S')] weixin_qr_data2 requested url_prefix=${qr_encoded%%\?*}"
            } >> "$DEBUG_LOG" 2>/dev/null || true
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "$qr_encoded" "$DEBUG_LOG"
import json, os, subprocess, sys, tempfile
raw = sys.argv[1] if len(sys.argv) > 1 else ''
query_url = sys.argv[2] if len(sys.argv) > 2 else ''
debug_log = sys.argv[3] if len(sys.argv) > 3 else ''
url = query_url
if raw:
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get('url'):
            url = str(payload.get('url'))
    except Exception:
        pass
if not url:
    print(json.dumps({'ok': False, 'error': 'missing url'}, ensure_ascii=False))
    raise SystemExit

def log(msg):
    if not debug_log:
        return
    try:
        with open(debug_log, 'a', encoding='utf-8') as f:
            from time import strftime
            f.write(f"[{strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

try:
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        png_path = tmp.name
    p = subprocess.run(['qrencode', '-o', png_path, '-m', '2', '-s', '8', url], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    if p.returncode != 0:
        raise RuntimeError((p.stdout or b'').decode('utf-8', 'ignore') or 'qrencode failed')
    with open(png_path, 'rb') as f:
        data = f.read()
    import base64
    data_url = 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')
    log(f'weixin_qr_data2 qrencode_ok bytes={len(data)}')
    print(json.dumps({'ok': True, 'contentType': 'image/png', 'dataUrl': data_url}, ensure_ascii=False))
except Exception as e:
    log(f'weixin_qr_data2 qrencode_err={e}')
    print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False))
finally:
    try:
        if 'png_path' in locals() and os.path.exists(png_path):
            os.remove(png_path)
    except Exception:
        pass
PY
            exit 0
            ;;
        weixin_qr_latest)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "${APP_VAR_DIR}/weixin-login-debug.log"
import json, os, re, sys
p = sys.argv[1]
if not os.path.exists(p):
    print(json.dumps({'ok': False, 'error': 'debug log not found'}, ensure_ascii=False)); raise SystemExit
try:
    txt = open(p, 'r', encoding='utf-8', errors='ignore').read()[-200000:]
except Exception as e:
    print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False)); raise SystemExit
matches = re.findall(r'https://liteapp\.weixin\.qq\.com/q/\S+', txt)
if not matches:
    print(json.dumps({'ok': False, 'error': 'no qr url found'}, ensure_ascii=False)); raise SystemExit
print(json.dumps({'ok': True, 'qrUrl': matches[-1]}, ensure_ascii=False))
PY
            exit 0
            ;;
        *)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"error":"unknown action"}'
            exit 0
            ;;
    esac
fi

printf 'Content-Type: text/html; charset=UTF-8\r\nCache-Control: no-store, no-cache, must-revalidate, max-age=0\r\nPragma: no-cache\r\nExpires: 0\r\n\r\n'
cat <<'HTML'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OpenClaw2</title>
  <style>
    html, body { scroll-behavior: auto; overscroll-behavior: contain; height:100%; }
    body { margin:0; overflow:hidden; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif; background:#f5f6f8; color:#222; }
    body.modal-open { overflow: hidden; }
    .wrap { padding:12px; height:100%; box-sizing:border-box; display:flex; flex-direction:column; zoom:.93; }
    .title { font-size:24px; font-weight:700; margin-bottom:6px; }
    .sub { color:#667085; font-size:13px; margin-bottom:14px; }
    .tabs { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
    .tab { border:1px solid #d0d5dd; background:#fff; border-radius:10px; padding:10px 14px; cursor:pointer; }
    .tab.active { background:#1677ff; color:#fff; border-color:#1677ff; }
    .panel { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:16px; min-height:0; flex:1; display:flex; flex-direction:column; overflow:hidden; }
    .toolbar { display:flex; gap:8px; margin-bottom:12px; align-items:center; }
    #content { flex:1; min-height:0; overflow:hidden; }
    .btn { border:1px solid #d0d5dd; background:#fff; border-radius:10px; padding:8px 12px; cursor:pointer; }
    .btn.primary { background:#1677ff; color:#fff; border-color:#1677ff; }
    .btn:disabled { cursor:not-allowed; color:#98a2b3; background:#f2f4f7; border-color:#d0d5dd; }
    .btn.primary:disabled { color:#98a2b3; background:#e5e7eb; border-color:#d0d5dd; }
    .grid { display:grid; grid-template-columns:180px 1fr; border-top:1px solid #eee; }
    .cellk,.cellv { padding:10px 8px; border-bottom:1px solid #eee; }
    .cellk { color:#667085; }
    textarea { width:100%; min-height:520px; resize:vertical; box-sizing:border-box; border:1px solid #d0d5dd; border-radius:10px; padding:12px; font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
    pre { white-space:pre-wrap; word-break:break-word; background:#111827; color:#dbeafe; border-radius:10px; padding:14px; min-height:420px; max-height:calc(100vh - 300px); overflow-y:scroll; overflow-x:auto; font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
    .msg { margin-bottom:12px; font-size:14px; color:#667085; }
    .err { color:#b42318; }
    .ok { color:#067647; }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; margin-bottom:16px; }
    .card { border:1px solid #e5e7eb; border-radius:12px; padding:14px; background:#fff; }
    .card h3 { margin:0 0 10px; font-size:16px; }
    .field { margin-bottom:10px; }
    .field label { display:block; font-size:13px; color:#667085; margin-bottom:4px; }
    .field input, .field select, .field textarea { width:100%; box-sizing:border-box; border:1px solid #d0d5dd; border-radius:8px; padding:8px 10px; }
    .field select[multiple] { min-height: 96px; max-height: 140px; overflow-y: auto; }
    .list { display:flex; flex-direction:column; gap:10px; margin-bottom:16px; }
    .list-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:10px; margin-bottom:16px; }
    .item { border:1px solid #e5e7eb; border-radius:12px; padding:14px; background:#fff; }
    .item-title { font-size:16px; font-weight:600; margin-bottom:6px; }
    .item-meta { font-size:13px; color:#667085; margin-bottom:8px; }
    .chips { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }
    .chip { background:#eef4ff; color:#175cd3; border:1px solid #c7d7fe; border-radius:999px; padding:2px 8px; font-size:13px; }
    .modal-mask { position:fixed; inset:0; background:rgba(15,23,42,.45); display:none; align-items:center; justify-content:center; z-index:9999; overflow:hidden; padding:16px; }
    .modal { width:min(700px,90vw); max-height:calc(100vh - 32px); overflow:auto; background:#fff; border-radius:16px; padding:14px; box-shadow:0 20px 60px rgba(0,0,0,.25); }
    .modal.model-modal { width:min(560px,90vw); }
    .modal h3 { margin:0 0 14px; font-size:18px; }
    .modal-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:14px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="title">OpenClaw2</div>
    <div class="tabs">
      <button class="tab active" data-tab="status">概览</button>
      <button class="tab" data-tab="models">模型配置</button>
      <button class="tab" data-tab="channels">渠道配置</button>
      <button class="tab" data-tab="terminal">终端</button>
      <button class="tab" data-tab="logs">运行日志</button>
    </div>
    <div class="panel">
      <div id="msg" class="msg"></div>
      <div id="content"></div>
    </div>
  </div>

  <script>
    const API_BASE = '/webman/3rdparty/openclaw2/index.cgi?native_api=1&action=';
    const PROVIDER_PRESETS = {
      anthropic: { label: 'Anthropic', baseUrl: 'https://api.anthropic.com', api: 'anthropic-messages', models: ['claude-3-5-sonnet-latest','claude-3-7-sonnet-latest','claude-sonnet-4-20250514','claude-opus-4-20250514'] },
      google: { label: 'Google', baseUrl: 'https://generativelanguage.googleapis.com/v1beta', api: 'openai-completions', models: ['gemini-2.5-pro','gemini-2.5-flash','gemini-2.0-flash'] },
      'minimax-cn': { label: 'MiniMax CN', baseUrl: 'https://api.minimaxi.com/anthropic', api: 'anthropic-messages', models: ['MiniMax-M2.5','MiniMax-Text-01'] },
      minimax: { label: 'MiniMax', baseUrl: 'https://api.minimax.io/anthropic', api: 'anthropic-messages', models: ['MiniMax-M2.5','MiniMax-Text-01'] },
      'kimi-coding': { label: 'Kimi Coding', baseUrl: 'https://api.kimi.com/coding/', api: 'anthropic-messages', models: ['kimi-k2-0905-preview','kimi-latest'] },
      mistral: { label: 'Mistral', baseUrl: 'https://api.mistral.ai/v1', api: 'openai-completions', models: ['mistral-large-latest','mistral-small-latest'] },
      moonshot: { label: 'Moonshot', baseUrl: 'https://api.moonshot.ai/v1', api: 'openai-completions', models: ['moonshot-v1-8k','moonshot-v1-32k','moonshot-v1-128k'] },
      openai: { label: 'OpenAI', baseUrl: 'https://api.openai.com/v1', api: 'openai-completions', models: ['gpt-5.4-mini','gpt-5.3-codex','gpt-4.1','o4-mini'] },
      ollama: { label: 'Ollama', baseUrl: 'http://127.0.0.1:11434', api: 'ollama', models: ['qwen2.5:7b','llama3.1:8b','deepseek-r1:8b'] },
      openrouter: { label: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1', api: 'openai-completions', models: ['openai/gpt-4.1','anthropic/claude-sonnet-4','google/gemini-2.5-pro'] },
      together: { label: 'Together', baseUrl: 'https://api.together.xyz/v1', api: 'openai-completions', models: ['Qwen/Qwen2.5-72B-Instruct-Turbo','meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo'] },
      xai: { label: 'xAI', baseUrl: 'https://api.x.ai/v1', api: 'openai-completions', models: ['grok-4','grok-3-mini'] },
      zai: { label: 'Z.AI', baseUrl: 'https://api.z.ai/api/paas/v4', api: 'openai-completions', models: ['glm-4.5','glm-4.5-air'] }
    };
    const BUILTIN_CHANNEL_PLUGINS = ['feishu','qqbot','dingtalk','wecom','openclaw-weixin'];
    let currentTab = 'status';
    let statusLine = '';
    let logsTimer = null;
    let statusTimer = null;
    let installBusy = false;
    let installBusyAction = '';
    let terminalSessionId = '';
    let terminalOffset = 0;
    let terminalPollTimer = null;
    let terminalWriteQueue = Promise.resolve();
    let terminalSuggest = ['openclaw doctor', 'openclaw gateway status', 'openclaw gateway restart', 'openclaw config validate'];
    window.__openclaw2ClientErrors = [];

    function captureClientError(type, payload) {
      try {
        const rec = {
          ts: new Date().toISOString(),
          type,
          payload: payload || {}
        };
        window.__openclaw2ClientErrors.push(rec);
        if (window.__openclaw2ClientErrors.length > 50) window.__openclaw2ClientErrors.shift();
        const text = JSON.stringify(rec);
        if (console && console.error) console.error('[openclaw2-ui-error]', text);
        const merged = (rec.payload && (rec.payload.message || '')) + '\n' + (rec.payload && (rec.payload.stack || ''));
        if (/flexcroll|document\.write|asynchronously-loaded external script/i.test(merged)) {
          setMsg('检测到 DSM 内置 flexcroll 脚本兼容报错（document.write 异步限制）。已记录错误详情，可继续使用当前页面功能。', 'err');
        }
      } catch (_) {}
    }

    window.openclaw2ClientErrors = function () {
      return (window.__openclaw2ClientErrors || []).slice();
    };

    window.addEventListener('error', function (ev) {
      captureClientError('error', {
        message: ev && ev.message,
        filename: ev && ev.filename,
        lineno: ev && ev.lineno,
        colno: ev && ev.colno,
        stack: ev && ev.error && ev.error.stack ? String(ev.error.stack) : ''
      });
    });

    window.addEventListener('unhandledrejection', function (ev) {
      const reason = ev && ev.reason;
      captureClientError('unhandledrejection', {
        message: reason && reason.message ? String(reason.message) : String(reason || ''),
        stack: reason && reason.stack ? String(reason.stack) : ''
      });
    });

    function esc(s) {
      return String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }
    function setMsg(text, cls='') {
      const el = document.getElementById('msg');
      el.className = 'msg ' + cls;
      el.textContent = text || '';
    }
    function formatUptime(seconds) {
      const s = Math.max(0, Number(seconds) || 0);
      const d = Math.floor(s / 86400);
      const h = Math.floor((s % 86400) / 3600);
      const m = Math.floor((s % 3600) / 60);
      const sec = s % 60;
      const parts = [];
      if (d) parts.push(d + '天');
      if (h || d) parts.push(h + '小时');
      if (m || h || d) parts.push(m + '分');
      parts.push(sec + '秒');
      return parts.join(' ');
    }
    function setTabs(tab) {
      currentTab = tab;
      if (logsTimer) { clearInterval(logsTimer); logsTimer = null; }
      if (statusTimer) { clearInterval(statusTimer); statusTimer = null; }
      if (terminalPollTimer) { clearInterval(terminalPollTimer); terminalPollTimer = null; }
      document.querySelectorAll('.tab').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));
    }
    async function api(action, method='GET', payload=null) {
      const url = API_BASE + encodeURIComponent(action) + '&_ts=' + Date.now();
      const resp = await fetch(url, {
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
      if (tab === 'status') setMsg('');
      else setMsg('加载中…');
      const content = document.getElementById('content');
      content.innerHTML = '';
      try {
        const data = await api(tab);
        if (tab === 'status') {
          const uptimeText = data.running ? formatUptime(data.uptimeSeconds || 0) : '-';
          const hostFix = (window.location && window.location.hostname) ? window.location.hostname : 'LAN_HOST';
          const mappedDashboard = String(data.dashboardUrl || '').replace(/127\.0\.0\.1|localhost/g, hostFix);
          const mappedTokenized = String(data.dashboardTokenizedUrl || '').replace(/127\.0\.0\.1|localhost/g, hostFix);
          const rows = [
            ['实例 ID', data.instanceId || '-'],
            ['显示名', data.displayName || '-'],
            ['已安装', data.installed ? '是' : '否'],
            ['运行中', data.running ? '是' : '否'],
            ['Gateway 运行时间', uptimeText],
            ['版本', data.version || '-'],
            ['端口', data.port || '-'],
            ['代理路径', data.proxyBasePath || '-'],
            ['Gateway 地址', mappedDashboard || '-'],
            ['Gateway 地址(含token)', mappedTokenized || '-'],
            ['用户文件夹路径', data.workspaceDir || '/volume1/docker/openclaw'],
            ['配置文件', data.configPath || '-'],
            ['binaryPath', data.binaryPath || '-']
          ];
          const webUrl = (data.dashboardTokenizedUrl || data.dashboardUrl || 'http://LAN_HOST:18789/default/chat?session=main').replace('LAN_HOST', window.location.hostname);
          const runningText = data.running ? '运行中' : '已停止';
          content.innerHTML = ''
            + '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">'
            + '  <button class="btn" id="btn_oc_start" onclick="runInstallAction(\'start\')">启动 OpenClaw</button>'
            + '  <button class="btn" id="btn_oc_stop" onclick="runInstallAction(\'stop\')">停止 OpenClaw</button>'
            + '  <button class="btn" id="btn_oc_restart" onclick="runInstallAction(\'restart\')">重启 OpenClaw</button>'
            + '  <button class="btn" onclick="openUserSettingsDialog()">用户目录设置</button>'
            + '  <button class="btn primary" id="btn_open_web" onclick="openOpenclawWeb(decodeURIComponent(\'' + encodeURIComponent(webUrl) + '\'))">打开 OpenClaw Web</button>'
            + '</div>'
            + '<div class="grid">' + rows.map(([k,v]) => {
                const vv = String(v == null ? '' : v).replace(/127\.0\.0\.1|localhost/g, hostFix);
                return '<div class="cellk">'+esc(k)+'</div><div class="cellv">'+esc(vv)+'</div>';
              }).join('') + '</div>'
            + '<div class="modal-mask" id="userSettingsMask">'
            + '  <div class="modal">'
            + '    <h3>用户目录设置</h3>'
            + '    <div class="field"><label>用户目录</label><input id="workspace_dir" value="' + esc(data.workspaceDir || '/volume1/docker/openclaw') + '" placeholder="/volume1/docker/openclaw"></div>'
            + '    <div class="modal-actions">'
            + '      <button class="btn" onclick="closeUserSettingsDialog()">取消</button>'
            + '      <button class="btn primary" onclick="saveWorkspaceQuick();closeUserSettingsDialog();">保存</button>'
            + '    </div>'
            + '  </div>'
            + '</div>';
          if (installBusy && installBusyAction === 'restart') {
            setMsg('运行状态：正在重启', 'ok');
          } else {
            setMsg('运行状态：' + runningText, data.running ? 'ok' : 'err');
          }
          if (installBusy) {
            setInstallButtonsBusy(installBusyAction, true);
          } else {
            setInstallButtonsBusy('', false);
          }
          statusTimer = setInterval(async () => {
            try {
              if (currentTab !== 'status') return;
              const s = await api('status');
              const nextRunning = !!(s && s.running);
              const nextText = nextRunning ? '运行中' : '已停止';
              const nextUptime = nextRunning ? formatUptime((s && s.uptimeSeconds) || 0) : '-';
              const msgEl = document.getElementById('msg');
              if (msgEl) {
                if (installBusy && installBusyAction === 'restart') {
                  msgEl.className = 'msg ok';
                  msgEl.textContent = '运行状态：正在重启';
                } else {
                  msgEl.className = 'msg ' + (nextRunning ? 'ok' : 'err');
                  msgEl.textContent = '运行状态：' + nextText;
                }
              }
              const gridVals = document.querySelectorAll('.grid .cellv');
              if (gridVals && gridVals.length >= 5) {
                gridVals[3].textContent = nextRunning ? '是' : '否';
                gridVals[4].textContent = nextUptime;
              }
            } catch (_) {}
          }, 1500);
          return;
        }
        if (tab === 'logs') {
          content.innerHTML = ''
            + '<pre id="log_pre">' + esc(data.log || '') + '</pre>';
          const pre = document.getElementById('log_pre');
          if (pre) pre.scrollTop = pre.scrollHeight;
          setMsg('');
          logsTimer = setInterval(refreshLogsNow, 2000);
          return;
        }
        if (tab === 'terminal') {
          content.innerHTML = ''
            + '<div style="display:flex;flex-direction:column;height:100%;gap:8px;">'
            + '  <div id="terminal_cwd" style="font-size:13px;color:#667085;">当前目录：-</div>'
            + '  <div style="display:flex;gap:8px;align-items:center;">'
            + '    <button class="btn" onclick="sendTerminalCtrlC()">Ctrl+C</button>'
            + '    <button class="btn" onclick="sendTerminalCtrlD()">Ctrl+D</button>'
            + '    <button class="btn" onclick="clearTerminalView()">清屏</button>'
            + '    <button class="btn primary" onclick="restartTerminalSession()">重连</button>'
            + '  </div>'
            + '  <div style="font-size:13px;color:#667085;">交互终端（类 SSH 体验）：点击终端区域后可直接输入命令并回车。</div>'
            + '  <div id="terminal_box" tabindex="0" onclick="focusTerminal()" onkeydown="handleTerminalKey(event)" style="outline:none;display:flex;flex-direction:column;flex:1;min-height:0;border:1px solid #d0d5dd;border-radius:10px;overflow:hidden;background:#0b1220;">'
            + '    <div id="terminal_prompt_line" onclick="focusTerminal()" style="font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#93c5fd;padding:6px 10px;border-bottom:1px solid #1f2937;">-</div>'
            + '    <pre id="terminal_pre" onclick="focusTerminal()" style="margin:0;flex:1;min-height:0;max-height:none;overflow-y:auto;overflow-x:auto;border-radius:0;background:#0b1220;color:#dbeafe;">终端连接中...</pre>'
            + '  </div>'
            + '</div>';
          await ensureTerminalSession();
          focusTerminal();
          setMsg('终端已加载（交互模式）', 'ok');
          return;
        }
        if (tab === 'models') {
          const providers = data.configuredProviders || [];
          const workspaceDir = data.workspaceDir || '/volume1/docker/openclaw';
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
            + '  <div class="modal model-modal">'
            + '    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">'
            + '      <h3 id="modelModalTitle" style="margin:0;">添加模型服务器</h3>'
            + '      <button class="btn" style="padding:2px 10px;line-height:1;" onclick="closeModelDialog()" title="关闭">×</button>'
            + '    </div>'
            + '    <div id="dlg_model_hint" style="display:none;margin-top:8px;padding:8px 10px;border-radius:8px;font-size:13px;"></div>'
            + '    <div class="field"><label>服务商</label><select id="dlg_provider_preset" onchange="applyProviderPresetDialog()">' + options + '</select></div>'
            + '    <div class="field"><label>Provider ID（显示名与此一致）</label><input id="dlg_provider_id"></div>'
            + '    <div class="field"><label>API 类型</label><select id="dlg_api" onchange="invalidateModelDiscoverCache()"><option value="openai-completions">openai-completions</option><option value="openai-responses">openai-responses</option><option value="anthropic-messages">anthropic-messages</option><option value="ollama">ollama</option></select></div>'
            + '    <div class="field"><label>Base URL</label><input id="dlg_base_url" oninput="invalidateModelDiscoverCache()"></div>'
            + '    <div class="field"><label>API Key（留空表示不改）</label><input id="dlg_api_key" type="password" oninput="invalidateModelDiscoverCache()"></div>'
            + '    <div class="field"><label>模型列表</label>'
            + '      <div style="font-size:13px;color:#667085;margin-bottom:6px;">选择可用模型，或手动输入模型名称。</div>'
            + '      <div id="dlg_model_selected_line" onclick="openModelDropdown(event)" style="min-height:36px;border:1px solid #e4e7ec;border-radius:8px;padding:6px 8px;display:flex;align-items:center;gap:6px;overflow:auto;cursor:pointer;"></div>'
            + '      <div id="dlg_model_dropdown" style="display:none;max-height:260px;overflow-y:auto;overflow-x:hidden;border:1px solid #e4e7ec;border-radius:8px;padding:8px;margin-top:6px;text-align:left;line-height:1.4;"></div>'
            + '      <div style="display:flex;gap:8px;align-items:center;margin-top:8px;flex-wrap:nowrap;">'
            + '        <input id="dlg_model_manual_input" style="flex:1;min-width:0;" placeholder="手动输入模型名称（如 gpt-5.4-mini）" onkeydown="if(event.key===\'Enter\'){event.preventDefault();addManualModelFromInput();}">'
            + '        <button class="btn" style="white-space:nowrap;flex:0 0 auto;" onclick="addManualModelFromInput()">添加</button>'
            + '      </div>'
            + '      <input id="dlg_model_ids" type="hidden">'
            + '    </div>'
            + '    <div class="modal-actions">'
            + '      <button class="btn" onclick="syncProviderModelsToCache()">手动同步到本地缓存</button>'
            + '      <button class="btn" onclick="closeModelDialog()">取消</button>'
            + '      <button class="btn primary" onclick="saveModelDialog()">保存</button>'
            + '    </div>'
            + '  </div>'
            + '</div>';
          setMsg('模型配置已加载；可添加模型服务器，或编辑当前已配置的服务', 'ok');
          return;
        }
        if (tab === 'channels') {
          window.__channelsData = data || {};
          const configured = data.configuredChannelIds || [];
          const descMap = {
            feishu: '飞书',
            wecom: '企业微信',
            dingtalk: '钉钉',
            qqbot: 'QQ Bot',
            'openclaw-weixin': '微信',
            weixin: '微信（weixin）'
          };
          const ordered = configured.slice(); // 保持配置内插入顺序（即添加顺序）
          const rows = ordered.map(id => '<div class="item" style="margin-bottom:8px;">'
            + '<div class="item-title">' + esc(descMap[id] || id) + '</div>'
            + '<div class="item-meta">channelId=' + esc(id) + '</div>'
            + '<div style="display:flex;gap:8px;">'
            + '<button class="btn" onclick="openChannelDialog(\'' + id + '\')">编辑</button>'
            + '<button class="btn" onclick="deleteChannel(\'' + id + '\')">删除</button>'
            + '</div>'
            + '</div>').join('');
          content.innerHTML = ''
            + '<div style="height:100%;overflow:auto;padding-right:4px;">'
            + '<div class="card" style="margin-bottom:12px;">'
            + '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;">'
            + '    <h3 style="margin:0;">已配置渠道</h3>'
            + '    <button class="btn primary" onclick="openChannelDialog()">添加渠道</button>'
            + '  </div>'
            + (configured.length ? ('<div class="list" style="max-height:none;min-height:0;overflow:visible;">'+rows+'</div>') : '<span style="color:#667085;">暂无已配置渠道</span>')
            + '</div>'
            + '</div>'
            + '<div class="modal-mask" id="channelModalMask">'
            + '  <div class="modal">'
            + '    <h3>添加渠道</h3>'
            + '    <div class="field"><label>渠道</label><select id="dlg_channel_type" onchange="switchChannelDialog()">'
            + '      <option value="feishu">飞书</option>'
            + '      <option value="qqbot">QQ Bot</option>'
            + '      <option value="wecom">企业微信</option>'
            + '      <option value="dingtalk">钉钉</option>'
            + '      <option value="openclaw-weixin">微信</option>'
            + '    </select></div>'
            + '    <div id="channelFormArea"></div>'
            + '    <div class="modal-actions">'
            + '      <button class="btn" onclick="closeChannelDialog()">取消</button>'
            + '      <button class="btn primary" id="btn_channel_save" onclick="saveChannelDialog()">保存</button>'
            + '    </div>'
            + '  </div>'
            + '</div>'
            + '';
          setMsg('渠道配置已加载', 'ok');
          return;
        }
        content.innerHTML = '<textarea id="editor">' + esc(JSON.stringify(data, null, 2)) + '</textarea>';
        setMsg('JSON 已加载', 'ok');
      } catch (e) {
        setMsg('加载失败：' + (e.message || e), 'err');
      }
    }
    function setInstallButtonsBusy(actionName, busy) {
      installBusy = !!busy;
      installBusyAction = busy ? String(actionName || '') : '';
      const startBtn = document.getElementById('btn_oc_start');
      const stopBtn = document.getElementById('btn_oc_stop');
      const restartBtn = document.getElementById('btn_oc_restart');
      if (!startBtn || !stopBtn || !restartBtn) return;
      if (busy) {
        startBtn.disabled = true;
        stopBtn.disabled = true;
        restartBtn.disabled = true;
        startBtn.textContent = actionName === 'start' ? '启动中...' : '启动 OpenClaw';
        stopBtn.textContent = actionName === 'stop' ? '停止中...' : '停止 OpenClaw';
        restartBtn.textContent = actionName === 'restart' ? '重启中...' : '重启 OpenClaw';
        return;
      }
      startBtn.disabled = false;
      stopBtn.disabled = false;
      restartBtn.disabled = false;
      startBtn.textContent = '启动 OpenClaw';
      stopBtn.textContent = '停止 OpenClaw';
      restartBtn.textContent = '重启 OpenClaw';
    }
    function setHotReloadBusy(busy) {
      // 所有热重启动作统一映射到“重启中”状态展示。
      setInstallButtonsBusy('restart', !!busy);
    }
    async function waitHotReloadSettled(timeoutMs = 30000) {
      const end = Date.now() + timeoutMs;
      while (Date.now() < end) {
        try {
          const s = await api('status');
          if (s && s.running) return true;
        } catch (_) {}
        await new Promise(r => setTimeout(r, 900));
      }
      return false;
    }
    async function runInstallAction(actionName) {
      setInstallButtonsBusy(actionName, true);
      try {
        await api('install_run', 'POST', { method: 'bun', action: actionName });
        // 仅保留“运行状态”提示，不显示其它文案。
        if (actionName === 'start' || actionName === 'restart' || actionName === 'stop') {
          const wantRunning = (actionName !== 'stop');
          const maxTries = 40; // 最多约 36s，覆盖重启后端口恢复慢的场景
          for (let i = 0; i < maxTries; i += 1) {
            await new Promise(r => setTimeout(r, 900));
            try {
              const s = await api('status');
              if (actionName === 'restart') {
                // 重启期间保持“正在重启”，直到真正 running 才结束
                setMsg('运行状态：正在重启', 'ok');
                if (s && s.running) {
                  if (currentTab === 'status') await load('status');
                  return;
                }
              } else {
                if (s && !!s.running === wantRunning) {
                  setMsg('运行状态：' + (s.running ? '运行中' : '已停止'), s.running ? 'ok' : 'err');
                  if (currentTab === 'status') await load('status');
                  return;
                }
              }
            } catch {}
          }
          // 超时后再拉一次真实状态，避免停留在旧显示。
          if (currentTab === 'status') await load('status');
          return;
        }
        if (currentTab === 'status') await load('status');
      } catch (e) {
        // 概览页按要求不展示其它提示。
        if (currentTab === 'status') await load('status');
      } finally {
        setInstallButtonsBusy('', false);
      }
    }
    // 按用户要求："打开 OpenClaw Web" 按钮始终可用，不做状态检测。
    function openOpenclawWeb(url) {
      let u = (url || '').trim();
      if (!u) u = 'http://' + window.location.hostname + ':18789/default/chat?session=main';
      u = u.replace('LAN_HOST', window.location.hostname);
      if (!/[?&]token=/.test(u)) {
        const token = '123456';
        u += (u.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(token);
      }
      window.open(u, '_blank', 'noopener,noreferrer');
      setMsg('已打开 OpenClaw Web（自动附带 token）', 'ok');
    }
    function openUserSettingsDialog() {
      const m = document.getElementById('userSettingsMask');
      if (!m) return;
      m.style.display = 'flex';
      document.body.classList.add('modal-open');
    }
    function closeUserSettingsDialog() {
      const m = document.getElementById('userSettingsMask');
      if (!m) return;
      m.style.display = 'none';
      document.body.classList.remove('modal-open');
    }
    function applyProviderPresetDialog() {
      const presetId = document.getElementById('dlg_provider_preset').value;
      if (presetId === 'custom-openai') {
        document.getElementById('dlg_provider_id').value = 'custom-openai';
        document.getElementById('dlg_api').value = 'openai-completions';
        document.getElementById('dlg_base_url').value = 'http://127.0.0.1:8317/v1';
        const keyEl = document.getElementById('dlg_api_key');
        if (keyEl && !keyEl.value) keyEl.value = 'sk-V5zPkG6MJrIpxgmDw';
        setModelSelectOptions([], []);
        document.getElementById('dlg_model_ids').value = '';
        setMsg('已切换到 custom-openai 默认模板', 'ok');
        return;
      }
      const preset = PROVIDER_PRESETS[presetId];
      if (!preset) return;
      document.getElementById('dlg_provider_id').value = presetId;
      document.getElementById('dlg_base_url').value = preset.baseUrl || '';
      document.getElementById('dlg_api').value = preset.api || 'openai-completions';
      const builtin = (preset.models || []).filter(Boolean);
      setModelSelectOptions(builtin, builtin);
      setMsg('已按内置模板填充服务商模型列表（不联网拉取）', 'ok');
    }
    function getSelectedModelIdsFromHidden() {
      const raw = (document.getElementById('dlg_model_ids').value || '').trim();
      if (!raw) return [];
      return raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    }
    function setSelectedModelIdsToHidden(ids) {
      document.getElementById('dlg_model_ids').value = (ids || []).join('\n');
    }
    function getAvailableModelIdsFromDropdown() {
      const wrap = document.getElementById('dlg_model_dropdown');
      if (!wrap) return [];
      return Array.from(new Set(Array.from(wrap.querySelectorAll('input[type="checkbox"][value]')).map(i => i.value).filter(Boolean)));
    }
    function renderModelDropdown(ids, selectedIds) {
      const wrap = document.getElementById('dlg_model_dropdown');
      if (!wrap) return;
      const all = Array.from(new Set((ids || []).concat(selectedIds || []))).filter(Boolean);
      wrap.innerHTML = all.map(id => {
        const checked = (selectedIds || []).includes(id) ? ' checked' : '';
        return '<label style="display:grid;grid-template-columns:18px minmax(0,1fr);column-gap:8px;align-items:start;padding:4px 2px;width:100%;text-align:left;cursor:pointer;">'
          + '<input style="margin:0;" type="checkbox" value="' + esc(id) + '"' + checked + ' onchange="toggleModelSelection(this.value,this.checked)">'
          + '<span title="' + esc(id) + '" style="font-size:13px;text-align:left;white-space:normal;word-break:break-all;overflow:visible;">' + esc(id) + '</span>'
          + '</label>';
      }).join('') || '<div style="font-size:13px;color:#98a2b3;">暂无模型</div>';
    }
    function renderModelChips(ids) {
      const box = document.getElementById('dlg_model_selected_line');
      if (!box) return;
      const arr = ids || [];
      if (!arr.length) {
        box.innerHTML = '<span style="font-size:13px;color:#98a2b3;">点击选择模型（可多选）</span>';
        return;
      }
      box.innerHTML = arr.map(id => {
        return '<span class="chip" onclick="openModelDropdown()" onmousedown="openModelDropdown()" style="display:inline-flex;align-items:center;gap:6px;white-space:nowrap;cursor:pointer;">'
          + '<span onclick="openModelDropdown()" onmousedown="openModelDropdown()">' + esc(id) + '</span>'
          + '<button class="btn" style="padding:0 6px;line-height:1;min-height:18px;" onclick="event.stopPropagation();removeModelSelection(\'' + esc(id) + '\')" title="移除">×</button>'
          + '</span>';
      }).join('');
    }
    function setModelSelectOptions(ids, selectedIds) {
      const pool = Array.isArray(window.__modelOptionPool) ? window.__modelOptionPool : [];
      const all = Array.from(new Set((pool || []).concat(ids || []).concat(selectedIds || []))).filter(Boolean);
      window.__modelOptionPool = all.slice();
      const selected = Array.from(new Set(selectedIds || [])).filter(Boolean);
      setSelectedModelIdsToHidden(selected);
      renderModelDropdown(all, selected);
      renderModelChips(selected);
    }
    function toggleModelSelection(id, checked) {
      const curr = getSelectedModelIdsFromHidden();
      const all = getAvailableModelIdsFromDropdown();
      const next = checked ? Array.from(new Set(curr.concat([id]))) : curr.filter(x => x !== id);
      setModelSelectOptions(Array.from(new Set(all.concat([id]))), next);
    }
    function removeModelSelection(id) {
      const curr = getSelectedModelIdsFromHidden();
      const all = getAvailableModelIdsFromDropdown();
      const next = curr.filter(x => x !== id);
      setModelSelectOptions(Array.from(new Set(all.concat([id]))), next);
    }
    function openModelDropdown(ev) {
      const line = document.getElementById('dlg_model_selected_line');
      // 点击滚动条区域时不展开下拉（避免拖动滚动条误触）。
      if (line && ev) {
        const hScroll = line.scrollWidth > line.clientWidth;
        const vScroll = line.scrollHeight > line.clientHeight;
        const x = typeof ev.offsetX === 'number' ? ev.offsetX : -1;
        const y = typeof ev.offsetY === 'number' ? ev.offsetY : -1;
        const nearBottom = hScroll && y >= (line.clientHeight - 14);
        const nearRight = vScroll && x >= (line.clientWidth - 14);
        if (nearBottom || nearRight) return;
      }
      const el = document.getElementById('dlg_model_dropdown');
      if (!el) return;
      window.__suppressModelDropdownAutoCloseUntil = Date.now() + 250;
      if (el.style.display !== 'block') {
        el.style.display = 'block';
        triggerDiscoverModelsForDialog();
      }
    }
    function toggleModelDropdown() {
      const el = document.getElementById('dlg_model_dropdown');
      if (!el) return;
      const open = (el.style.display === 'none' || !el.style.display);
      el.style.display = open ? 'block' : 'none';
      if (open) triggerDiscoverModelsForDialog();
    }
    function addManualModelFromInput() {
      const inp = document.getElementById('dlg_model_manual_input');
      if (!inp) return;
      const v = (inp.value || '').trim();
      if (!v) return;
      const curr = getSelectedModelIdsFromHidden();
      const next = Array.from(new Set(curr.concat([v])));
      setModelSelectOptions(next, next);
      inp.value = '';
    }
    function syncModelTextareaFromSelect() {}
    function syncModelSelectFromTextarea() {}
    function getDiscoverCacheKey() {
      return '';
    }
    function invalidateModelDiscoverCache() {}
    async function triggerDiscoverModelsForDialog() {
      const presetId = document.getElementById('dlg_provider_preset').value;
      const preset = PROVIDER_PRESETS[presetId];
      const ids = (preset && Array.isArray(preset.models)) ? preset.models : [];
      const existing = getSelectedModelIdsFromHidden();
      const pool = Array.isArray(window.__modelOptionPool) ? window.__modelOptionPool : [];
      const merged = Array.from(new Set(pool.concat(ids).concat(existing)));
      // 保持用户当前勾选状态：即使全部取消，也不要在下次打开时自动重新选中。
      setModelSelectOptions(merged, existing);
    }
    function setModelDialogHint(msg, type) {
      const el = document.getElementById('dlg_model_hint');
      if (!el) return;
      const text = (msg || '').trim();
      if (!text) {
        el.style.display = 'none';
        el.textContent = '';
        return;
      }
      el.style.display = 'block';
      if (type === 'err') {
        el.style.background = '#fef3f2';
        el.style.color = '#b42318';
        el.style.border = '1px solid #fecdca';
      } else {
        el.style.background = '#ecfdf3';
        el.style.color = '#027a48';
        el.style.border = '1px solid #abefc6';
      }
      el.textContent = text;
    }

    function openModelDialog(index) {
      const data = window.__modelsData || {};
      const providers = data.configuredProviders || [];
      const editing = typeof index === 'number';
      const p = editing ? (providers[index] || {}) : {};
      const currentIds = (p.models || []).map(m => m.modelId || m.id).filter(Boolean);
      document.getElementById('modelModalTitle').textContent = editing ? '编辑模型服务器' : '添加模型服务器';
      document.getElementById('dlg_provider_preset').value = p.id && PROVIDER_PRESETS[p.id] ? p.id : (p.id === 'custom-openai' ? 'custom-openai' : 'custom-openai');
      document.getElementById('dlg_provider_id').value = p.id || '';
      document.getElementById('dlg_api').value = p.api || 'openai-completions';
      document.getElementById('dlg_base_url').value = p.baseUrl || '';
      document.getElementById('dlg_api_key').value = p.apiKeyMasked || '';
      document.getElementById('dlg_api_key').dataset.raw = p.apiKeyRaw || '';
      setModelSelectOptions(currentIds, currentIds);
      if (!editing) {
        applyProviderPresetDialog();
      }
      window.__modelOptionPool = Array.isArray(currentIds) ? currentIds.slice() : [];
      window.__modelsDiscovering = false;
      window.__modelsDiscoveredKey = '';
      document.getElementById('modelModalMask').style.display = 'flex';
      document.body.classList.add('modal-open');
      setModelDialogHint('', 'ok');
      document.getElementById('modelModalMask').dataset.editIndex = editing ? String(index) : '';
      const dd = document.getElementById('dlg_model_dropdown');
      if (dd) dd.style.display = 'none';
    }

    // 点击模型下拉外区域自动折叠
    document.addEventListener('click', function(ev) {
      const dd = document.getElementById('dlg_model_dropdown');
      const line = document.getElementById('dlg_model_selected_line');
      if (!dd || !line) return;
      if (dd.style.display !== 'block') return;
      if ((window.__suppressModelDropdownAutoCloseUntil || 0) > Date.now()) return;
      const t = ev.target;
      if (dd.contains(t) || line.contains(t)) return;
      dd.style.display = 'none';
    });
    function closeModelDialog() {
      document.getElementById('modelModalMask').style.display = 'none';
      document.body.classList.remove('modal-open');
      document.getElementById('modelModalMask').dataset.editIndex = '';
    }
    async function discoverModelsForDialog() {
      await triggerDiscoverModelsForDialog();
      const count = getSelectedModelIdsFromHidden().length;
      setMsg('已加载内置模型列表，共 ' + count + ' 个', 'ok');
    }
    async function syncProviderModelsToCache() {
      try {
        setMsg('正在同步服务商模型到本地缓存...');
        const keyInput = document.getElementById('dlg_api_key').value || '';
        const keyRaw = document.getElementById('dlg_api_key').dataset.raw || '';
        const payload = {
          baseUrl: document.getElementById('dlg_base_url').value,
          apiKey: (keyInput && keyInput.replace(/\*/g,'').trim().length>0) ? keyInput : keyRaw,
          api: document.getElementById('dlg_api').value
        };
        const data = await api('models_sync_provider', 'POST', payload);
        const ids = (data.models || []).map(m => m.modelId || m.id).filter(Boolean);
        if (!ids.length) {
          const msg = data.error ? ('同步失败：' + data.error) : '未同步到模型';
          setModelDialogHint(msg, data.error ? 'err' : 'ok');
          setMsg(msg, data.error ? 'err' : '');
          return;
        }
        // 按原逻辑：同步后全部选中
        setModelSelectOptions(ids, ids);
        setModelDialogHint('已同步并写入本地缓存，共 ' + ids.length + ' 个', 'ok');
        setMsg('已同步并写入本地缓存，共 ' + ids.length + ' 个', 'ok');
      } catch (e) { setModelDialogHint('同步失败：' + (e.message || e), 'err'); setMsg('同步失败：' + (e.message || e), 'err'); }
    }
    async function saveModelDialog() {
      const btns = Array.from(document.querySelectorAll('#modelModalMask .modal-actions .btn.primary'));
      const saveBtn = btns.find(b => (b.textContent || '').includes('保存')) || btns[0] || null;
      const oldText = saveBtn ? saveBtn.textContent : '';
      let hotReloadTriggered = false;
      try {
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = '正在应用模型...'; }
        const data = window.__modelsData || {};
        const providers = (data.configuredProviders || []).slice();
        const idxRaw = document.getElementById('modelModalMask').dataset.editIndex;
        const idx = idxRaw === '' ? -1 : parseInt(idxRaw, 10);
        const providerId = (document.getElementById('dlg_provider_id').value || 'custom-openai').trim();
        const baseUrl = (document.getElementById('dlg_base_url').value || '').trim();
        const selectedModelIds = getSelectedModelIdsFromHidden();

        // 模型列表不能为空：禁止添加/保存，并在弹窗内提示。
        if (!selectedModelIds.length) {
          setModelDialogHint('添加失败：模型列表不能为空，请至少选择或手动添加一个模型', 'err');
          setMsg('添加失败：模型列表不能为空，请至少选择或手动添加一个模型', 'err');
          if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = oldText || '保存'; }
          return;
        }

        // 仅在“添加”时校验：Provider ID 或 Base URL 任一重复都禁止添加。
        if (idx < 0) {
          const duplicatedId = providers.some(p => ((p && p.id) || '').trim() === providerId);
          const duplicatedBase = baseUrl && providers.some(p => ((p && p.baseUrl) || '').trim() === baseUrl);
          if (duplicatedId || duplicatedBase) {
            const reason = duplicatedId ? 'Provider ID 已存在' : 'Base URL 已存在';
            setModelDialogHint('添加失败：' + reason + '，请修改后重试', 'err');
            setMsg('添加失败：' + reason + '，请修改后重试', 'err');
            if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = oldText || '保存'; }
            return;
          }
        }

        const provider = {
          id: providerId,
          displayName: providerId,
          api: document.getElementById('dlg_api').value,
          baseUrl: baseUrl,
          apiKey: document.getElementById('dlg_api_key').value,
          models: selectedModelIds.map(id => ({ modelId: id, id: id }))
        };
        if (idx >= 0) providers[idx] = provider; else providers.push(provider);
        const payload = { providers, applyNow: true };
        hotReloadTriggered = true;
        setHotReloadBusy(true);
        await api('models_save', 'POST', payload);
        setModelDialogHint('保存成功，正在刷新列表...', 'ok');
        closeModelDialog();
        await load('models');
        setMsg('模型服务器保存成功', 'ok');
      } catch (e) {
        setModelDialogHint('保存失败：' + (e.message || e), 'err');
        setMsg('模型服务器保存失败：' + (e.message || e), 'err');
      } finally {
        if (hotReloadTriggered) {
          await waitHotReloadSettled(30000);
          setHotReloadBusy(false);
        }
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = oldText || '保存'; }
      }
    }
    async function deleteModelProvider(index) {
      try {
        const data = window.__modelsData || {};
        const providers = (data.configuredProviders || []).slice();
        providers.splice(index, 1);
        await api('models_save', 'POST', { providers, applyNow: false });
        await load('models');
        setMsg('模型服务器已删除，重启后生效', 'ok');
      } catch (e) { setMsg('删除失败：' + (e.message || e), 'err'); }
    }
    async function saveWorkspaceQuick() {
      let hotReloadTriggered = false;
      try {
        const workspaceDir = (document.getElementById('workspace_dir').value || '').trim() || '/volume1/docker/openclaw';
        const m = await api('models');
        const payload = { providers: (m.configuredProviders || []), workspaceDir, applyNow: true };
        hotReloadTriggered = true;
        setHotReloadBusy(true);
        await api('models_save', 'POST', payload);
        setMsg('用户目录保存成功：' + workspaceDir, 'ok');
      } catch (e) { setMsg('用户目录保存失败：' + (e.message || e), 'err'); }
      finally {
        if (hotReloadTriggered) {
          await waitHotReloadSettled(30000);
          setHotReloadBusy(false);
        }
      }
    }
    async function saveQQBotQuick() {}
    function openChannelDialog(editId) {
      const data = window.__channelsData || {};
      const configured = new Set(data.configuredChannelIds || []);
      const allOptions = [
        ['feishu','飞书'],
        ['qqbot','QQ Bot'],
        ['wecom','企业微信'],
        ['dingtalk','钉钉'],
        ['openclaw-weixin','微信']
      ];
      const options = allOptions.filter(([id]) => editId ? (id === editId) : !configured.has(id));
      if (!options.length) { setMsg('可添加渠道为空（已全部配置）', 'ok'); return; }
      const select = document.getElementById('dlg_channel_type');
      select.innerHTML = options.map(([id,label]) => '<option value="'+id+'">'+label+'</option>').join('');
      if (editId) select.value = editId;
      document.getElementById('channelModalMask').dataset.editId = editId || '';
      document.getElementById('channelModalMask').style.display = 'flex';
      document.body.classList.add('modal-open');
      switchChannelDialog();
    }
    function closeChannelDialog() {
      document.getElementById('channelModalMask').style.display = 'none';
      document.getElementById('channelModalMask').dataset.editId = '';
      document.body.classList.remove('modal-open');
    }
    function syncChannelSaveButtonState() {
      const t = (document.getElementById('dlg_channel_type') || {}).value || '';
      const btn = document.getElementById('btn_channel_save');
      if (!btn) return;
      if (t === 'openclaw-weixin') {
        // 微信扫码流程改为“仅自动保存”，不显示手动保存按钮。
        btn.style.display = 'none';
        btn.disabled = true;
        btn.title = '微信扫码后自动保存';
      } else {
        btn.style.display = '';
        btn.disabled = false;
        btn.title = '';
      }
    }
    function switchChannelDialog() {
      const t = document.getElementById('dlg_channel_type').value;
      const data = window.__channelsData || {};
      const area = document.getElementById('channelFormArea');
      if (t === 'feishu') {
        const appId = (((data.feishu||{}).accounts||{})[((data.feishu||{}).defaultAccount)||'default']||{}).appId || '';
        const appSecret = (((data.feishu||{}).accounts||{})[((data.feishu||{}).defaultAccount)||'default']||{}).appSecret || '';
        area.innerHTML = '<div class="field"><label>App ID</label><input id="dlg_feishu_appId" value="'+esc(appId)+'"></div><div class="field"><label>App Secret</label><input id="dlg_feishu_appSecret" type="password" value="'+esc(appSecret)+'"></div>';
      } else if (t === 'qqbot') {
        const appId = (data.qqbot||{}).appId || '';
        const secret = (data.qqbot||{}).clientSecret || '';
        area.innerHTML = '<div class="field"><label>App ID</label><input id="dlg_qqbot_appId" value="'+esc(appId)+'"></div><div class="field"><label>Client Secret</label><input id="dlg_qqbot_secret" type="password" value="'+esc(secret)+'"></div>';
      } else if (t === 'wecom') {
        const botId = (data.wecom||{}).botId || '';
        const secret = (data.wecom||{}).secret || '';
        area.innerHTML = '<div class="field"><label>Bot ID</label><input id="dlg_wecom_botId" value="'+esc(botId)+'"></div><div class="field"><label>Secret</label><input id="dlg_wecom_secret" type="password" value="'+esc(secret)+'"></div>';
      } else if (t === 'dingtalk') {
        const clientId = (data.dingtalk||{}).clientId || '';
        const secret = (data.dingtalk||{}).clientSecret || '';
        area.innerHTML = '<div class="field"><label>Client ID</label><input id="dlg_dd_clientId" value="'+esc(clientId)+'"></div><div class="field"><label>Client Secret</label><input id="dlg_dd_secret" type="password" value="'+esc(secret)+'"></div>';
      } else {
        window.__weixinConnected = false;
        area.innerHTML = '<div style="font-size:13px;color:#667085;">微信通过 openclaw-weixin 插件扫码登录。</div><div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;"><button id="btn_wx_start" class="btn" onclick="startWeixinLogin(false)">开始微信登录</button><button id="btn_wx_poll" class="btn" onclick="regenerateWeixinQr()">重新生成</button></div><div id="weixin_status" style="font-size:13px;color:#667085;margin-top:8px;">未查询</div><div id="weixin_qr" style="margin-top:8px;"></div>';
      }
      syncChannelSaveButtonState();
    }
    async function saveChannelDialog(opts) {
      const fastAutoSave = !!(opts && opts.fastAutoSave);
      const t = document.getElementById('dlg_channel_type').value;
      let payload = {};
      if (t === 'feishu') {
        const appId = (document.getElementById('dlg_feishu_appId').value || '').trim();
        const appSecret = (document.getElementById('dlg_feishu_appSecret').value || '').trim();
        if (!appId || !appSecret) { setMsg('飞书 App ID / App Secret 不能为空', 'err'); return; }
        payload = { feishu: { appId, appSecret } };
      } else if (t === 'qqbot') {
        const appId = (document.getElementById('dlg_qqbot_appId').value || '').trim();
        const clientSecret = (document.getElementById('dlg_qqbot_secret').value || '').trim();
        if (!appId || !clientSecret) { setMsg('QQ App ID / Client Secret 不能为空', 'err'); return; }
        payload = { qqbot: { appId, clientSecret } };
      } else if (t === 'wecom') {
        const botId = (document.getElementById('dlg_wecom_botId').value || '').trim();
        const secret = (document.getElementById('dlg_wecom_secret').value || '').trim();
        if (!botId || !secret) { setMsg('企业微信 Bot ID / Secret 不能为空', 'err'); return; }
        payload = { wecom: { botId, secret } };
      } else if (t === 'dingtalk') {
        const clientId = (document.getElementById('dlg_dd_clientId').value || '').trim();
        const clientSecret = (document.getElementById('dlg_dd_secret').value || '').trim();
        if (!clientId || !clientSecret) { setMsg('钉钉 Client ID / Client Secret 不能为空', 'err'); return; }
        payload = { dingtalk: { clientId, clientSecret } };
      } else {
        payload = { weixin: { enabled: true } };
      }
      const btn = document.getElementById('btn_channel_save');
      const oldText = btn ? btn.textContent : '';
      let hotReloadTriggered = false;
      try {
        if (btn) { btn.disabled = true; btn.textContent = '正在添加...'; }
        hotReloadTriggered = true;
        setHotReloadBusy(true);
        const ret = await api('channels_save', 'POST', payload);
        closeChannelDialog();
        await load('channels');
        if (ret && ret.reloaded) setMsg('运行状态：正在重启', 'ok');
      } catch (e) {
        setMsg('渠道保存失败：' + (e.message || e), 'err');
      } finally {
        if (hotReloadTriggered) {
          // 微信扫码自动保存走快速模式：不阻塞等待重启完成，减少“已连接后还要等10秒”。
          if (fastAutoSave) {
            setTimeout(async () => {
              await waitHotReloadSettled(30000);
              setHotReloadBusy(false);
            }, 0);
          } else {
            await waitHotReloadSettled(30000);
            setHotReloadBusy(false);
          }
        }
        if (btn) { btn.disabled = false; btn.textContent = oldText || '保存'; }
      }
    }
    function getWeixinUiEls() {
      return {
        statusEl: document.getElementById('weixin_status'),
        qrEl: document.getElementById('weixin_qr'),
        startBtn: document.getElementById('btn_wx_start'),
        pollBtn: document.getElementById('btn_wx_poll')
      };
    }
    function setWeixinBusy(mode, busy) {
      const { startBtn, pollBtn } = getWeixinUiEls();
      if (startBtn) {
        startBtn.disabled = !!busy;
        startBtn.textContent = (busy && mode === 'start') ? '登录中...' : '开始微信登录';
      }
      if (pollBtn) {
        pollBtn.disabled = !!busy;
        pollBtn.textContent = (busy && mode === 'poll') ? '生成中...' : '重新生成';
      }
    }
    function renderWeixinQrInline(dataUrl, qrUrl, qrEl, note) {
      qrEl.innerHTML = ''
        + '<div style="display:flex;flex-direction:column;gap:8px;align-items:flex-start;">'
        + '  <div style="font-size:13px;color:#667085;">' + esc(note || '请使用微信扫码完成登录') + '</div>'
        + '  <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:8px;">'
        + '    <img src="' + esc(dataUrl) + '" style="max-width:320px;width:100%;display:block;" />'
        + '  </div>'
        + '</div>';
    }
    let __qrLibPromise = null;
    function ensureQrLib() {
      if (window.QRCode) return Promise.resolve(window.QRCode);
      if (__qrLibPromise) return __qrLibPromise;
      __qrLibPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/qrcodejs2-fix@0.0.2/qrcode.min.js';
        script.async = true;
        script.onload = () => {
          if (window.QRCode) resolve(window.QRCode);
          else reject(new Error('二维码库加载完成但未找到 QRCode 对象'));
        };
        script.onerror = () => reject(new Error('二维码库加载失败'));
        document.head.appendChild(script);
      });
      return __qrLibPromise;
    }
    async function buildQrDataUrlFromText(text) {
      await ensureQrLib();
      const mount = document.createElement('div');
      mount.style.cssText = 'position:fixed;left:-99999px;top:-99999px;visibility:hidden;';
      document.body.appendChild(mount);
      try {
        new window.QRCode(mount, {
          text: text,
          width: 320,
          height: 320,
          correctLevel: window.QRCode.CorrectLevel.M
        });
        await new Promise(r => setTimeout(r, 80));
        const canvas = mount.querySelector('canvas');
        if (canvas && canvas.toDataURL) return canvas.toDataURL('image/png');
        const img = mount.querySelector('img');
        if (img && img.src) return img.src;
        throw new Error('二维码绘制结果为空');
      } finally {
        if (mount && mount.parentNode) mount.parentNode.removeChild(mount);
      }
    }
    async function renderWeixinQr(qrUrl, qrEl) {
      try {
        window.__weixinQrUrl = qrUrl;
        let dataUrl = '';
        try {
          dataUrl = await buildQrDataUrlFromText(qrUrl);
          console.info('[channels:weixin:inline-qr:local-draw]', { qrUrl: qrUrl, hasDataUrl: !!dataUrl });
        } catch (localErr) {
          console.warn('[channels:weixin:inline-qr:local-draw:failed]', localErr);
          const resp = await fetch(API_BASE + 'weixin_qr_data2', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: qrUrl }),
            cache: 'no-store'
          });
          const data = await resp.json();
          if (!resp.ok || !data || !data.ok || !data.dataUrl) {
            throw new Error((data && data.error) || ('二维码服务回退失败：HTTP ' + resp.status));
          }
          dataUrl = data.dataUrl;
          console.info('[channels:weixin:inline-qr:server-fallback]', { qrUrl: qrUrl, hasDataUrl: !!dataUrl });
        }
        window.__weixinQrDataUrl = dataUrl;
        renderWeixinQrInline(dataUrl, qrUrl, qrEl, '请使用微信扫码完成登录（已在本地/服务端重绘）');
      } catch (e) {
        console.error('[channels:weixin:inline-qr:error]', e);
        qrEl.innerHTML = '<div style="font-size:13px;color:#b42318;margin-bottom:8px;">二维码重绘失败：' + esc(e.message || e) + '</div><a class="btn" target="_blank" rel="noopener" href="' + esc(qrUrl) + '">新窗口打开二维码</a>';
        throw e;
      }
    }
    let __weixinPollTimer = null;
    async function startWeixinLogin(force) {
      const startTs = Date.now();
      // 新一轮登录开始：重置连接态，避免旧轮询导致“未刷新二维码就自动保存”。
      window.__weixinConnected = false;
      window.__weixinAutoSaveArmed = false;
      window.__weixinRoundId = '';
      syncChannelSaveButtonState();
      if (__weixinPollTimer) {
        clearInterval(__weixinPollTimer);
        __weixinPollTimer = null;
      }
      setWeixinBusy('start', true);
      try {
        const { statusEl, qrEl } = getWeixinUiEls();
        if (!statusEl || !qrEl) {
          setMsg('微信面板未打开，请先在“渠道设置”中切换到微信后再操作。', 'err');
          return;
        }
        statusEl.textContent = '正在获取二维码...';
        qrEl.innerHTML = '<div style="font-size:13px;color:#667085;">二维码加载中...</div>';
        console.info('[channels:weixin:start] request login start');
        const data = await api('weixin_login_start', 'POST', { force: !!force });
        console.info('[channels:weixin:start:timing]', { elapsedMs: Date.now() - startTs, force: !!force });
        if (data && data.qrUrl) {
          await renderWeixinQr(data.qrUrl, qrEl);
          statusEl.textContent = '会话：' + (data.sessionKey || '-') + '，请扫码。';
          window.__weixinSessionKey = data.sessionKey || '';
          window.__weixinRoundId = data.roundId || '';
          window.__weixinAutoSaveArmed = true;
          setMsg('二维码已生成，请扫码登录。', 'ok');
          __weixinPollTimer = setInterval(() => { pollWeixinLogin({ silent: true }); }, 1000);
        } else {
          statusEl.textContent = data.message || data.error || '当前版本不支持微信扫码登录';
          const extra = data && data.debugLog ? ('（调试日志：' + data.debugLog + '）') : '';
          setMsg((data.message || data.error || '当前版本不支持微信扫码登录') + extra, data.supported === false ? '' : 'err');
        }
      } catch (e) { setMsg('微信登录启动失败：' + (e.message || e), 'err'); }
      finally { setWeixinBusy('start', false); }
    }
    async function pollWeixinLogin(opts) {
      const silent = !!(opts && opts.silent);
      if (!silent) setWeixinBusy('poll', true);
      try {
        const sessionKey = window.__weixinSessionKey || '';
        const roundId = window.__weixinRoundId || '';
        const { statusEl, qrEl } = getWeixinUiEls();
        if (!statusEl) {
          setMsg('微信面板未打开，请先在“渠道设置”中切换到微信后再操作。', 'err');
          return;
        }
        if (!silent) statusEl.textContent = '正在查询登录状态...';
        const data = await api('weixin_login_wait', 'POST', { sessionKey, roundId, timeoutMs: 300 });
        console.info('[channels:weixin:poll]', data);
        const msg = data.message || data.status || '未知状态';
        statusEl.textContent = msg;
        let latestQr = data && data.qrUrl ? data.qrUrl : '';
        if (!latestQr) {
          try {
            const l = await api('weixin_qr_latest');
            if (l && l.ok && l.qrUrl) latestQr = l.qrUrl;
          } catch {}
        }
        if (latestQr && qrEl && window.__weixinQrUrl !== latestQr) {
          window.__weixinQrUrl = latestQr;
          await renderWeixinQr(latestQr, qrEl);
        }
        if (data.connected && window.__weixinAutoSaveArmed) {
          window.__weixinConnected = true;
          window.__weixinAutoSaveArmed = false;
          syncChannelSaveButtonState();
          if (__weixinPollTimer) {
            clearInterval(__weixinPollTimer);
            __weixinPollTimer = null;
          }
          try {
            setMsg('微信已连接，正在自动保存...', 'ok');
            if (statusEl) statusEl.textContent = '已连接，正在自动保存...';
            await saveChannelDialog({ fastAutoSave: true });
          } catch {}
          setMsg('微信已连接（已自动保存）', 'ok');
        }
      } catch (e) {
        if (!silent) setMsg('查询微信状态失败：' + (e.message || e), 'err');
      } finally {
        if (!silent) setWeixinBusy('poll', false);
      }
    }
    async function regenerateWeixinQr() {
      await startWeixinLogin(true);
    }
    async function disconnectWeixin() {
      try {
        const data = await api('weixin_disconnect', 'POST', { accountId: '' });
        const { statusEl, qrEl } = getWeixinUiEls();
        if (statusEl) statusEl.textContent = '已断开';
        if (qrEl) qrEl.innerHTML = '';
        window.__weixinSessionKey = '';
        window.__weixinQrDataUrl = '';
        window.__weixinQrUrl = '';
        setMsg('微信已断开', 'ok');
      } catch (e) { setMsg('断开微信失败：' + (e.message || e), 'err'); }
    }
    async function deleteChannel(id) {
      const btns = Array.from(document.querySelectorAll('button'));
      const targetBtn = btns.find(b => (b.textContent || '').trim() === '删除' && (b.getAttribute('onclick') || '').includes("deleteChannel('" + id + "')"));
      const old = targetBtn ? targetBtn.textContent : '';
      try {
        if (targetBtn) { targetBtn.disabled = true; targetBtn.textContent = '正在删除...'; }
        setMsg('正在删除渠道：' + id + ' ...');
        await api('channels_delete', 'POST', { id });
        await load('channels');
        const descMap = {
          feishu: '飞书',
          wecom: '企业微信',
          dingtalk: '钉钉',
          qqbot: 'QQ Bot',
          'openclaw-weixin': '微信',
          weixin: '微信'
        };
        const label = descMap[id] || id;
        setMsg('已删除' + label + '消息渠道，重启后生效', 'ok');
      } catch (e) {
        setMsg('删除渠道失败：' + (e.message || e), 'err');
      } finally {
        if (targetBtn) { targetBtn.disabled = false; targetBtn.textContent = old || '删除'; }
      }
    }
    async function refreshLogsNow() {
      try {
        const data = await api('logs');
        const pre = document.getElementById('log_pre');
        if (!pre) return;
        pre.textContent = data.log || '';
        pre.scrollTop = pre.scrollHeight;
      } catch (e) {}
    }
    function sanitizeTerminalText(text) {
      let s = String(text || '');
      s = s.replace(/\x1B\[[0-9;?]*[ -\/]*[@-~]/g, '');
      s = s.replace(/\[[0-9;]{1,20}m/g, '');
      // 非 TTY 交互 shell 常见噪声，直接过滤
      s = s.replace(/^bash: cannot set terminal process group.*\n?/gm, '');
      s = s.replace(/^bash: no job control in this shell\n?/gm, '');
      // 将退格控制符按“删除前一字符”语义应用，避免显示特殊符号。
      const out = [];
      for (const ch of s) {
        if (ch === '\b' || ch === '\x7f') {
          if (out.length) out.pop();
          continue;
        }
        if (ch === '\r') continue;
        out.push(ch);
      }
      return out.join('');
    }
    async function ensureTerminalSession() {
      const pre = document.getElementById('terminal_pre');
      if (!pre) return;
      if (!terminalSessionId) {
        const ret = await api('terminal_session_start', 'POST', {});
        if (!ret || !ret.ok) {
          pre.textContent = '终端启动失败：' + ((ret && (ret.error || ret.message)) || 'unknown');
          return;
        }
        terminalSessionId = ret.sessionId || '';
        terminalOffset = Number(ret.offset || 0);
        window.__terminalUser = ret.user || 'root';
        window.__terminalHost = ret.host || 'localhost';
        const initCwd = (ret.cwd || '/volume1/@appdata/openclaw2/data/home');
        const initUser = (ret.user || 'root');
        const initHost = (ret.host || 'localhost');
        pre.textContent = '';
        const promptEl = document.getElementById('terminal_prompt_line');
        if (promptEl) promptEl.textContent = initUser + '@' + initHost + ':' + initCwd + '$';
        const cwdEl = document.getElementById('terminal_cwd');
        if (cwdEl) cwdEl.textContent = '当前目录：' + initCwd;
      }
      if (terminalPollTimer) clearInterval(terminalPollTimer);
      terminalPollTimer = setInterval(readTerminalOutput, 500);
      await readTerminalOutput();
    }
    async function readTerminalOutput() {
      if (!terminalSessionId) return;
      const pre = document.getElementById('terminal_pre');
      if (!pre) return;
      try {
        const ret = await api('terminal_session_read', 'POST', { sessionId: terminalSessionId, offset: terminalOffset });
        if (!ret || !ret.ok) return;
        terminalOffset = Number(ret.nextOffset || terminalOffset);
        if (ret.output) {
          pre.textContent += sanitizeTerminalText(ret.output);
          pre.scrollTop = pre.scrollHeight;
        }
        const cwdEl = document.getElementById('terminal_cwd');
        if (cwdEl && ret.cwd) cwdEl.textContent = '当前目录：' + ret.cwd;
        const promptEl = document.getElementById('terminal_prompt_line');
        if (promptEl && ret.cwd) {
          const user = (window.__terminalUser || 'root');
          const host = (window.__terminalHost || 'localhost');
          promptEl.textContent = user + '@' + host + ':' + ret.cwd + '$';
        }
        if (ret.alive === false && terminalPollTimer) {
          clearInterval(terminalPollTimer);
          terminalPollTimer = null;
          pre.textContent += '\n[session ended]\n';
        }
      } catch (_) {}
    }
    function focusTerminal() {
      const box = document.getElementById('terminal_box');
      if (box) { box.focus(); return; }
      const pre = document.getElementById('terminal_pre');
      if (pre) pre.focus();
    }
    async function sendTerminalText(text) {
      terminalWriteQueue = terminalWriteQueue.then(async () => {
        if (!terminalSessionId) await ensureTerminalSession();
        if (!terminalSessionId) return;
        await api('terminal_session_write', 'POST', { sessionId: terminalSessionId, text: text });
      }).catch(() => {});
      await terminalWriteQueue;
      // 输入按键不立即强制读回，交给定时轮询，避免输入与输出错序串扰。
    }
    async function handleTerminalKey(ev) {
      if (!ev) return;
      const pre = document.getElementById('terminal_pre');
      if (!pre) return;

      // 全部按键直通 shell，确保 TAB/历史/路径补全与 SSH 一致。
      if (ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        if (ev.key === 'c' || ev.key === 'C') { ev.preventDefault(); await sendTerminalText('\u0003'); return; }
        if (ev.key === 'd' || ev.key === 'D') { ev.preventDefault(); await sendTerminalText('\u0004'); return; }
      }

      if (ev.key === 'Tab') { ev.preventDefault(); await sendTerminalText('\t'); return; }
      if (ev.key === 'Enter') { ev.preventDefault(); await sendTerminalText('\n'); return; }
      if (ev.key === 'Backspace') { ev.preventDefault(); await sendTerminalText('\u007f'); return; }

      if (ev.key === 'ArrowUp') { ev.preventDefault(); await sendTerminalText('\u001b[A'); return; }
      if (ev.key === 'ArrowDown') { ev.preventDefault(); await sendTerminalText('\u001b[B'); return; }
      if (ev.key === 'ArrowRight') { ev.preventDefault(); await sendTerminalText('\u001b[C'); return; }
      if (ev.key === 'ArrowLeft') { ev.preventDefault(); await sendTerminalText('\u001b[D'); return; }

      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      if (ev.key && ev.key.length === 1) {
        ev.preventDefault();
        await sendTerminalText(ev.key);
        pre.scrollTop = pre.scrollHeight;
      }
    }
    async function sendTerminalCtrlC() { await sendTerminalText('\u0003'); }
    async function sendTerminalCtrlD() { await sendTerminalText('\u0004'); }
    function clearTerminalView() {
      const pre = document.getElementById('terminal_pre');
      if (pre) pre.textContent = '';
    }
    async function restartTerminalSession() {
      try {
        if (terminalSessionId) await api('terminal_session_stop', 'POST', { sessionId: terminalSessionId });
      } catch (_) {}
      terminalSessionId = '';
      terminalOffset = 0;
      if (terminalPollTimer) { clearInterval(terminalPollTimer); terminalPollTimer = null; }
      await ensureTerminalSession();
    }
    document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => load(btn.dataset.tab)));
    load('status');
  </script>
</body>
</html>
HTML
