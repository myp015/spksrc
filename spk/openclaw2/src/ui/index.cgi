#!/bin/sh
APP_VAR_DIR="/var/packages/openclaw2/var"
if [ -d "/volume1/@appdata/openclaw2" ]; then
    APP_VAR_DIR="/volume1/@appdata/openclaw2"
fi

LOG_FILE="${APP_VAR_DIR}/openclaw2.log"
GATEWAY_PORT="44539"
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
            python3 - <<'PY' "$GATEWAY_PORT" "/volume1/docker/openclaw/.openclaw/openclaw.json"
import json, os, socket, sys
port = int(sys.argv[1]) if len(sys.argv) > 1 else 44539
cfg_path = sys.argv[2] if len(sys.argv) > 2 else ''
running = False
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.6)
try:
    s.connect(('127.0.0.1', port))
    running = True
except Exception:
    running = False
finally:
    s.close()
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
workspace = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/docker/openclaw')
token = ((((cfg.get('gateway') or {}).get('auth') or {}).get('token')) or '123456')
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
  'configPath': cfg_path
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
out = {
  'configPath': cfg_path,
  'configExists': bool(cfg),
  'configuredChannelIds': list(ch.keys()),
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
    w['enabled'] = True
if isinstance(payload.get('dingtalk'), dict):
    d = ch.setdefault('dingtalk', {})
    cid = (payload['dingtalk'].get('clientId') or '').strip()
    csec = (payload['dingtalk'].get('clientSecret') or '').strip()
    if cid: d['clientId'] = cid
    if csec: d['clientSecret'] = csec
    d['enabled'] = True
if isinstance(payload.get('qqbot'), dict):
    q = ch.setdefault('qqbot', {})
    aid = (payload['qqbot'].get('appId') or '').strip()
    sec = (payload['qqbot'].get('clientSecret') or '').strip()
    if aid: q['appId'] = aid
    if sec: q['clientSecret'] = sec
    q['enabled'] = True; q['dmPolicy']='open'; q['groupPolicy']='open'; q['allowFrom']=['*']
os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')
out = {
  'configPath': cfg_path, 'configExists': True,
  'configuredChannelIds': list((cfg.get('channels') or {}).keys()),
  'feishu': (cfg.get('channels') or {}).get('feishu') or {},
  'wecom': (cfg.get('channels') or {}).get('wecom') or {},
  'dingtalk': (cfg.get('channels') or {}).get('dingtalk') or {},
  'qqbot': (cfg.get('channels') or {}).get('qqbot') or {},
  'weixin': (cfg.get('channels') or {}).get('weixin') or {}
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
if cid and cid in ch:
    del ch[cid]
os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')
out = {
  'configPath': cfg_path, 'configExists': True,
  'configuredChannelIds': list((cfg.get('channels') or {}).keys()),
  'feishu': (cfg.get('channels') or {}).get('feishu') or {},
  'wecom': (cfg.get('channels') or {}).get('wecom') or {},
  'dingtalk': (cfg.get('channels') or {}).get('dingtalk') or {},
  'qqbot': (cfg.get('channels') or {}).get('qqbot') or {},
  'weixin': (cfg.get('channels') or {}).get('weixin') or {}
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
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "${APP_VAR_DIR}/data/home" "/volume1/docker/openclaw/.openclaw/openclaw.json"
import json, os, re, subprocess, sys
home_dir = sys.argv[1]
cfg_path = sys.argv[2]
env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/openclaw2/data'
env['HOME'] = home_dir
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = '/volume1/docker/openclaw/.openclaw'
cmd = ['/var/packages/openclaw2/target/bin/openclaw', 'channels', 'login', '--channel', 'openclaw-weixin', '--verbose']
text = ''
try:
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=25)
    text = (p.stdout or b'').decode('utf-8', 'ignore')
except subprocess.TimeoutExpired as e:
    text = ((e.stdout or b'') + (e.stderr or b'')).decode('utf-8', 'ignore')
url = None
m = re.search(r'https://liteapp\.weixin\.qq\.com/q/\S+', text)
if m:
    url = m.group(0)
if url:
    print(json.dumps({'supported': True, 'qrUrl': url, 'sessionKey': 'openclaw-weixin', 'message': '请用微信扫码完成登录'}, ensure_ascii=False))
else:
    print(json.dumps({'supported': False, 'message': '未获取到二维码，请确认 openclaw-weixin 插件已安装并重试', 'raw': text[-800:]}, ensure_ascii=False))
PY
            exit 0
            ;;
        weixin_login_wait)
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
cmd = ['/var/packages/openclaw2/target/bin/openclaw', 'channels', 'status']
try:
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=8)
    text = (p.stdout or b'').decode('utf-8', 'ignore')
except Exception as e:
    text = str(e)
ok = ('openclaw-weixin' in text.lower()) and ('connected' in text.lower() or 'ready' in text.lower() or 'online' in text.lower())
print(json.dumps({'supported': True, 'connected': bool(ok), 'status': 'connected' if ok else 'pending', 'message': '已连接' if ok else '等待扫码确认', 'raw': text[-400:]}, ensure_ascii=False))
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

# 强制保持 LAN 可访问（44539）
try:
    c = json.load(open(cfg,'r',encoding='utf-8')) if cfg and os.path.exists(cfg) else {}
except Exception:
    c = {}
gw = c.setdefault('gateway', {})
gw['bind'] = 'lan'
gw['mode'] = 'local'
cu = gw.setdefault('controlUi', {})
cu['allowInsecureAuth'] = True
cu['dangerouslyDisableDeviceAuth'] = True
cu['allowedOrigins'] = ['*']
os.makedirs(os.path.dirname(cfg), exist_ok=True)
with open(cfg,'w',encoding='utf-8') as f:
    json.dump(c,f,ensure_ascii=False,indent=2); f.write('\n')

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
    .field select[multiple] { min-height: 96px; max-height: 140px; overflow-y: auto; }
    .list { display:flex; flex-direction:column; gap:10px; margin-bottom:16px; }
    .list-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:10px; margin-bottom:16px; }
    .item { border:1px solid #e5e7eb; border-radius:12px; padding:14px; background:#fff; }
    .item-title { font-size:16px; font-weight:600; margin-bottom:6px; }
    .item-meta { font-size:12px; color:#667085; margin-bottom:8px; }
    .chips { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }
    .chip { background:#eef4ff; color:#175cd3; border:1px solid #c7d7fe; border-radius:999px; padding:2px 8px; font-size:12px; }
    .modal-mask { position:fixed; inset:0; background:rgba(15,23,42,.45); display:none; align-items:flex-start; justify-content:center; z-index:9999; overflow:hidden; padding:32px 0; }
    .modal { width:min(700px,90vw); max-height:none; overflow:visible; background:#fff; border-radius:16px; padding:14px; box-shadow:0 20px 60px rgba(0,0,0,.25); }
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
      <button class="tab" data-tab="channels">渠道配置</button>
      <button class="tab" data-tab="logs">运行日志</button>
    </div>
    <div class="panel">
      <div class="toolbar">
        <button class="btn" id="refreshBtn">刷新当前页</button>
      </div>
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
    const BUILTIN_CHANNEL_PLUGINS = ['browser','feishu','qqbot','dingtalk','wecom'];
    let currentTab = 'status';
    let statusLine = '';
    let logsTimer = null;

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
      if (logsTimer) { clearInterval(logsTimer); logsTimer = null; }
      document.querySelectorAll('.tab').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));
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
            ['用户文件夹路径', data.workspaceDir || '/volume1/docker/openclaw'],
            ['配置文件', data.configPath || '-'],
            ['binaryPath', data.binaryPath || '-']
          ];
          const webUrl = (data.dashboardTokenizedUrl || data.dashboardUrl || 'http://LAN_HOST:44539/default/chat?session=main').replace('LAN_HOST', window.location.hostname);
          const runningText = data.running ? '运行中' : '已停止';
          content.innerHTML = ''
            + '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">'
            + '  <button class="btn" onclick="runInstallAction(\'start\')">启动 OpenClaw</button>'
            + '  <button class="btn" onclick="runInstallAction(\'stop\')">停止 OpenClaw</button>'
            + '  <button class="btn" onclick="runInstallAction(\'restart\')">重启 OpenClaw</button>'
            + '  <button class="btn" onclick="openUserSettingsDialog()">用户设置</button>'
            + '  <button class="btn primary" onclick="openOpenclawWeb(decodeURIComponent(\'' + encodeURIComponent(webUrl) + '\'))">打开 OpenClaw Web</button>'
            + '</div>'
            + '<div class="grid">' + rows.map(([k,v]) => '<div class="cellk">'+esc(k)+'</div><div class="cellv">'+esc(v)+'</div>').join('') + '</div>'
            + '<div class="modal-mask" id="userSettingsMask">'
            + '  <div class="modal">'
            + '    <h3>用户设置</h3>'
            + '    <div class="field"><label>Workspace</label><input id="workspace_dir" value="' + esc(data.workspaceDir || '/volume1/docker/openclaw') + '" placeholder="/volume1/docker/openclaw"></div>'
            + '    <div class="modal-actions">'
            + '      <button class="btn" onclick="closeUserSettingsDialog()">取消</button>'
            + '      <button class="btn primary" onclick="saveWorkspaceQuick();closeUserSettingsDialog();">保存</button>'
            + '    </div>'
            + '  </div>'
            + '</div>';
          setMsg('运行状态：' + runningText, data.running ? 'ok' : 'err');
          return;
        }
        if (tab === 'logs') {
          content.innerHTML = ''
            + '<div class="item-meta" style="margin-bottom:8px;display:flex;gap:8px;align-items:center;">日志来源：' + esc(data.source || '-')
            + '  <button class="btn" onclick="refreshLogsNow()">立即刷新</button>'
            + '</div>'
            + '<pre id="log_pre">' + esc(data.log || '') + '</pre>';
          setMsg('OpenClaw 日志已加载（实时刷新中）', 'ok');
          logsTimer = setInterval(refreshLogsNow, 2000);
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
            + '    <div style="display:flex;gap:8px;justify-content:flex-end;">'
            + '      <button class="btn" onclick="syncProviderModelsToCache()">手动同步到本地缓存</button>'
            + '    </div>'
            + '    <div class="modal-actions">'
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
            'openclaw-weixin': '微信（openclaw-weixin）',
            weixin: '微信（weixin）'
          };
          const rows = configured.map(id => '<div class="item">'
            + '<div class="item-title">' + esc(descMap[id] || id) + '</div>'
            + '<div class="item-meta">channelId=' + esc(id) + '</div>'
            + '<div style="display:flex;gap:8px;">'
            + '<button class="btn" onclick="openChannelDialog(\'' + id + '\')">编辑</button>'
            + '<button class="btn" onclick="deleteChannel(\'' + id + '\')">删除</button>'
            + '</div>'
            + '</div>').join('');
          content.innerHTML = ''
            + '<div class="card" style="margin-bottom:12px;">'
            + '  <h3>已配置渠道</h3>'
            + (configured.length ? ('<div class="list-grid">'+rows+'</div>') : '<span style="color:#667085;">暂无已配置渠道</span>')
            + '  <div style="display:flex;gap:8px;margin-top:10px;">'
            + '    <button class="btn primary" onclick="openChannelDialog()">添加渠道</button>'
            + '  </div>'
            + '</div>'
            + '<div class="modal-mask" id="channelModalMask">'
            + '  <div class="modal">'
            + '    <h3>添加渠道</h3>'
            + '    <div class="field"><label>渠道</label><select id="dlg_channel_type" onchange="switchChannelDialog()">'
            + '      <option value="feishu">飞书</option>'
            + '      <option value="qqbot">QQ Bot</option>'
            + '      <option value="wecom">企业微信</option>'
            + '      <option value="dingtalk">钉钉</option>'
            + '      <option value="openclaw-weixin">微信（扫码）</option>'
            + '    </select></div>'
            + '    <div id="channelFormArea"></div>'
            + '    <div class="modal-actions">'
            + '      <button class="btn" onclick="closeChannelDialog()">取消</button>'
            + '      <button class="btn primary" onclick="saveChannelDialog()">保存</button>'
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
    async function runInstallAction(actionName) {
      try {
        setMsg('正在执行：' + actionName + ' ...');
        await api('install_run', 'POST', { method: 'bun', action: actionName });
        setMsg('操作已提交：' + actionName, 'ok');
        await load('status');
      } catch (e) {
        setMsg('操作失败：' + (e.message || e), 'err');
      }
    }
    function openOpenclawWeb(url) {
      let u = (url || '').trim();
      if (!u) u = 'http://' + window.location.hostname + ':44539/default/chat?session=main';
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
        document.getElementById('dlg_display_name').value = '自定义 OpenAI 兼容';
        document.getElementById('dlg_api').value = 'openai-completions';
        document.getElementById('dlg_base_url').value = '';
        setModelSelectOptions([], []);
        document.getElementById('dlg_model_ids').value = '';
        setMsg('已切换到自定义 OpenAI 兼容，请手动填写服务器地址', 'ok');
        return;
      }
      const preset = PROVIDER_PRESETS[presetId];
      if (!preset) return;
      document.getElementById('dlg_provider_id').value = presetId;
      document.getElementById('dlg_display_name').value = preset.label;
      document.getElementById('dlg_base_url').value = preset.baseUrl || '';
      document.getElementById('dlg_api').value = preset.api || 'openai-completions';
      const builtin = (preset.models || []).filter(Boolean);
      setModelSelectOptions(builtin, builtin);
      document.getElementById('dlg_model_ids').value = builtin.join('\n');
      setMsg('已按内置模板填充服务商模型列表（不联网拉取）', 'ok');
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
      return '';
    }
    function invalidateModelDiscoverCache() {}
    async function triggerDiscoverModelsForDialog() {
      const presetId = document.getElementById('dlg_provider_preset').value;
      const preset = PROVIDER_PRESETS[presetId];
      const ids = (preset && Array.isArray(preset.models)) ? preset.models : [];
      const existing = (document.getElementById('dlg_model_ids').value || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
      const merged = Array.from(new Set(ids.concat(existing)));
      setModelSelectOptions(merged, existing.length ? existing : ids);
      if (!existing.length) document.getElementById('dlg_model_ids').value = merged.join('\n');
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
      document.getElementById('dlg_api_key').value = p.apiKeyMasked || '';
      document.getElementById('dlg_api_key').dataset.raw = p.apiKeyRaw || '';
      document.getElementById('dlg_model_ids').value = currentIds.join('\n');
      setModelSelectOptions(currentIds, currentIds);
      window.__modelsDiscovering = false;
      window.__modelsDiscoveredKey = '';
      document.getElementById('modelModalMask').style.display = 'flex';
      document.body.classList.add('modal-open');
      document.getElementById('modelModalMask').dataset.editIndex = editing ? String(index) : '';
    }
    function closeModelDialog() {
      document.getElementById('modelModalMask').style.display = 'none';
      document.body.classList.remove('modal-open');
      document.getElementById('modelModalMask').dataset.editIndex = '';
    }
    async function discoverModelsForDialog() {
      await triggerDiscoverModelsForDialog();
      const count = (document.getElementById('dlg_model_ids').value || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean).length;
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
          setMsg(data.error ? ('同步失败：' + data.error) : '未同步到模型', data.error ? 'err' : '');
          return;
        }
        document.getElementById('dlg_model_ids').value = ids.join('\n');
        setModelSelectOptions(ids, ids);
        setMsg('已同步并写入本地缓存，共 ' + ids.length + ' 个', 'ok');
      } catch (e) { setMsg('同步失败：' + (e.message || e), 'err'); }
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
        await api('models_save', 'POST', payload);
        closeModelDialog();
        await load('models');
        setMsg('模型服务器保存成功', 'ok');
      } catch (e) { setMsg('模型服务器保存失败：' + (e.message || e), 'err'); }
    }
    async function deleteModelProvider(index) {
      try {
        const data = window.__modelsData || {};
        const providers = (data.configuredProviders || []).slice();
        providers.splice(index, 1);
        await api('models_save', 'POST', { providers });
        await load('models');
        setMsg('模型服务器已删除', 'ok');
      } catch (e) { setMsg('删除失败：' + (e.message || e), 'err'); }
    }
    async function saveWorkspaceQuick() {
      try {
        const workspaceDir = (document.getElementById('workspace_dir').value || '').trim() || '/volume1/docker/openclaw';
        const m = await api('models');
        const payload = { providers: (m.configuredProviders || []), workspaceDir };
        await api('models_save', 'POST', payload);
        setMsg('用户目录保存成功：' + workspaceDir, 'ok');
      } catch (e) { setMsg('用户目录保存失败：' + (e.message || e), 'err'); }
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
        ['openclaw-weixin','微信（扫码）']
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
        area.innerHTML = '<div style="font-size:12px;color:#667085;">微信通过 openclaw-weixin 插件扫码登录。</div><div style="display:flex;gap:8px;margin-top:8px;"><button class="btn" onclick="startWeixinLogin()">开始微信登录</button><button class="btn" onclick="pollWeixinLogin()">检查状态</button></div><div id="weixin_status" style="font-size:12px;color:#667085;margin-top:8px;">未查询</div><div id="weixin_qr" style="margin-top:8px;"></div>';
      }
    }
    async function saveChannelDialog() {
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
        setMsg('微信渠道请使用扫码按钮完成登录。', 'ok');
        return;
      }
      try {
        await api('channels_save', 'POST', payload);
        closeChannelDialog();
        await load('channels');
        setMsg('渠道保存成功', 'ok');
      } catch (e) { setMsg('渠道保存失败：' + (e.message || e), 'err'); }
    }
    async function startWeixinLogin() {
      try {
        const data = await api('weixin_login_start', 'POST', {});
        if (data && data.qrUrl) {
          document.getElementById('weixin_qr').innerHTML = '<img src="' + esc(data.qrUrl) + '" style="max-width:220px;border:1px solid #e5e7eb;border-radius:8px;padding:6px;background:#fff;" />';
          document.getElementById('weixin_status').textContent = '会话：' + (data.sessionKey || '-') + '，请扫码。';
          window.__weixinSessionKey = data.sessionKey || '';
          setMsg('二维码已生成，请扫码登录。', 'ok');
        } else {
          document.getElementById('weixin_status').textContent = data.message || data.error || '当前版本不支持微信扫码登录';
          setMsg(data.message || data.error || '当前版本不支持微信扫码登录', data.supported === false ? '' : 'err');
        }
      } catch (e) { setMsg('微信登录启动失败：' + (e.message || e), 'err'); }
    }
    async function pollWeixinLogin() {
      try {
        const sessionKey = window.__weixinSessionKey || '';
        const data = await api('weixin_login_wait', 'POST', { sessionKey, timeoutMs: 1000 });
        const msg = data.message || data.status || '未知状态';
        document.getElementById('weixin_status').textContent = msg;
        if (data.connected) setMsg('微信已连接', 'ok');
      } catch (e) { setMsg('查询微信状态失败：' + (e.message || e), 'err'); }
    }
    async function disconnectWeixin() {
      try {
        const data = await api('weixin_disconnect', 'POST', { accountId: '' });
        document.getElementById('weixin_status').textContent = '已断开';
        document.getElementById('weixin_qr').innerHTML = '';
        window.__weixinSessionKey = '';
        setMsg('微信已断开', 'ok');
      } catch (e) { setMsg('断开微信失败：' + (e.message || e), 'err'); }
    }
    async function deleteChannel(id) {
      try {
        await api('channels_delete', 'POST', { id });
        await load('channels');
        setMsg('渠道已删除：' + id, 'ok');
      } catch (e) { setMsg('删除渠道失败：' + (e.message || e), 'err'); }
    }
    async function refreshLogsNow() {
      try {
        const data = await api('logs');
        const pre = document.getElementById('log_pre');
        if (!pre) return;
        const atBottom = (pre.scrollTop + pre.clientHeight + 24) >= pre.scrollHeight;
        pre.textContent = data.log || '';
        if (atBottom) pre.scrollTop = pre.scrollHeight;
      } catch (e) {}
    }
    document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => load(btn.dataset.tab)));
    document.getElementById('refreshBtn').addEventListener('click', () => load(currentTab));
    load('status');
  </script>
</body>
</html>
HTML
