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
# 模型新增/编辑后立即生效：重启 openclaw2
try:
    import subprocess
    pr = subprocess.run(['/usr/syno/bin/synopkg', 'restart', 'openclaw2'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
    out['restartTriggered'] = True
    out['restartRc'] = pr.returncode
    out['restartOutTail'] = ((pr.stdout or b'').decode('utf-8', 'ignore'))[-180:]
except Exception as e:
    out['restartTriggered'] = False
    out['restartErr'] = str(e)
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
if isinstance(payload.get('weixin'), dict):
    w = ch.setdefault('openclaw-weixin', {})
    w['enabled'] = bool(payload['weixin'].get('enabled', True))
    # 保存微信渠道时，强制保持插件启用状态，避免后续被覆盖为仅 browser。
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
    e = entries.get('openclaw-weixin')
    if not isinstance(e, dict):
        e = {}
    e['enabled'] = True
    entries['openclaw-weixin'] = e
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
channels_obj = (cfg.get('channels') or {})
out = {
  'configPath': cfg_path, 'configExists': True,
  'configuredChannelIds': enabled_ids(channels_obj),
  'feishu': channels_obj.get('feishu') or {},
  'wecom': channels_obj.get('wecom') or {},
  'dingtalk': channels_obj.get('dingtalk') or {},
  'qqbot': channels_obj.get('qqbot') or {},
  'weixin': channels_obj.get('weixin') or {}
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
need_restart = False
if cid:
    # 渠道配置置为 disabled
    if cid in ch:
        if isinstance(ch.get(cid), dict):
            ch[cid]['enabled'] = False
        else:
            ch[cid] = {'enabled': False}

    # 常见别名联动
    if cid == 'weixin' and 'openclaw-weixin' in ch:
        if isinstance(ch.get('openclaw-weixin'), dict):
            ch['openclaw-weixin']['enabled'] = False
        else:
            ch['openclaw-weixin'] = {'enabled': False}
    if cid == 'openclaw-weixin' and 'weixin' in ch and isinstance(ch.get('weixin'), dict):
        ch['weixin']['enabled'] = False

    # 关闭对应插件 entry/allow（按 channel->plugin 映射）
    channel_plugins = {
        'feishu': ['feishu', 'feishu-openclaw-plugin'],
        'dingtalk': ['dingtalk', 'openclaw-dingtalk'],
        'wecom': ['wecom', 'wecom-openclaw-plugin', 'openclaw-wecom'],
        'qqbot': ['qqbot', 'openclaw-qqbot'],
        'openclaw-weixin': ['openclaw-weixin'],
        'weixin': ['openclaw-weixin']
    }
    plugs = cfg.setdefault('plugins', {})
    ents = plugs.get('entries')
    if not isinstance(ents, dict):
        ents = {}
    allow = plugs.get('allow')
    if not isinstance(allow, list):
        allow = []
    for pid in channel_plugins.get(cid, [cid]):
        pe = ents.get(pid)
        if not isinstance(pe, dict):
            pe = {}
        pe['enabled'] = False
        ents[pid] = pe
        allow = [x for x in allow if x != pid]
    plugs['entries'] = ents
    plugs['allow'] = allow

    # 删除后立即生效：统一重启包
    need_restart = True


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
  'weixin': channels_obj.get('weixin') or {}
}

# 删除微信渠道后，强制重启 openclaw2，确保旧 webhook/monitor 立即停止。
if need_restart:
    try:
        import subprocess
        pr = subprocess.run(['/usr/syno/bin/synopkg', 'restart', 'openclaw2'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        out['restartTriggered'] = True
        out['restartRc'] = pr.returncode
        out['restartOutTail'] = ((pr.stdout or b'').decode('utf-8', 'ignore'))[-180:]
    except Exception as e:
        out['restartTriggered'] = False
        out['restartErr'] = str(e)

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
# 兼容清理：移除当前版本不支持的键，避免启动时报 Invalid config
defs = c.setdefault('agents', {}).setdefault('defaults', {})
if isinstance(defs, dict) and 'fallbackModels' in defs:
    defs.pop('fallbackModels', None)
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
    .grid { display:grid; grid-template-columns:180px 1fr; border-top:1px solid #eee; }
    .cellk,.cellv { padding:10px 8px; border-bottom:1px solid #eee; }
    .cellk { color:#667085; }
    textarea { width:100%; min-height:520px; resize:vertical; box-sizing:border-box; border:1px solid #d0d5dd; border-radius:10px; padding:12px; font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
    pre { white-space:pre-wrap; word-break:break-word; background:#111827; color:#dbeafe; border-radius:10px; padding:14px; min-height:420px; max-height:calc(100vh - 300px); overflow-y:scroll; overflow-x:auto; font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
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
            + '  <button class="btn" onclick="openUserSettingsDialog()">用户目录设置</button>'
            + '  <button class="btn primary" onclick="openOpenclawWeb(decodeURIComponent(\'' + encodeURIComponent(webUrl) + '\'))">打开 OpenClaw Web</button>'
            + '</div>'
            + '<div class="grid">' + rows.map(([k,v]) => '<div class="cellk">'+esc(k)+'</div><div class="cellv">'+esc(v)+'</div>').join('') + '</div>'
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
          setMsg('运行状态：' + runningText, data.running ? 'ok' : 'err');
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
            + '    <div class="field"><label>服务商</label><select id="dlg_provider_preset" onchange="applyProviderPresetDialog()">' + options + '</select></div>'
            + '    <div class="field"><label>Provider ID（显示名与此一致）</label><input id="dlg_provider_id"></div>'
            + '    <div class="field"><label>API 类型</label><select id="dlg_api" onchange="invalidateModelDiscoverCache()"><option value="openai-completions">openai-completions</option><option value="openai-responses">openai-responses</option><option value="anthropic-messages">anthropic-messages</option><option value="ollama">ollama</option></select></div>'
            + '    <div class="field"><label>Base URL</label><input id="dlg_base_url" oninput="invalidateModelDiscoverCache()"></div>'
            + '    <div class="field"><label>API Key（留空表示不改）</label><input id="dlg_api_key" type="password" oninput="invalidateModelDiscoverCache()"></div>'
            + '    <div class="field"><label>模型列表</label>'
            + '      <div style="font-size:12px;color:#667085;margin-bottom:6px;">选择可用模型，或手动输入模型名称。</div>'
            + '      <div id="dlg_model_selected_line" onclick="toggleModelDropdown()" style="min-height:36px;border:1px solid #e4e7ec;border-radius:8px;padding:6px 8px;display:flex;align-items:center;gap:6px;overflow:auto;cursor:pointer;"></div>'
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
          + '<span title="' + esc(id) + '" style="font-size:12px;text-align:left;white-space:normal;word-break:break-all;overflow:visible;">' + esc(id) + '</span>'
          + '</label>';
      }).join('') || '<div style="font-size:12px;color:#98a2b3;">暂无模型</div>';
    }
    function renderModelChips(ids) {
      const box = document.getElementById('dlg_model_selected_line');
      if (!box) return;
      const arr = ids || [];
      if (!arr.length) {
        box.innerHTML = '<span style="font-size:12px;color:#98a2b3;">点击选择模型（可多选）</span>';
        return;
      }
      box.innerHTML = arr.map(id => {
        return '<span class="chip" style="display:inline-flex;align-items:center;gap:6px;white-space:nowrap;">'
          + esc(id)
          + '<button class="btn" style="padding:0 6px;line-height:1;min-height:18px;" onclick="event.stopPropagation();removeModelSelection(\'' + esc(id) + '\')" title="移除">×</button>'
          + '</span>';
      }).join('');
    }
    function setModelSelectOptions(ids, selectedIds) {
      const all = Array.from(new Set((ids || []).concat(selectedIds || []))).filter(Boolean);
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
      const merged = Array.from(new Set(ids.concat(existing)));
      setModelSelectOptions(merged, existing.length ? existing : ids);
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
      window.__modelsDiscovering = false;
      window.__modelsDiscoveredKey = '';
      document.getElementById('modelModalMask').style.display = 'flex';
      document.body.classList.add('modal-open');
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
          setMsg(data.error ? ('同步失败：' + data.error) : '未同步到模型', data.error ? 'err' : '');
          return;
        }
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
          displayName: (document.getElementById('dlg_provider_id').value || 'custom-openai'),
          api: document.getElementById('dlg_api').value,
          baseUrl: document.getElementById('dlg_base_url').value,
          apiKey: document.getElementById('dlg_api_key').value,
          models: getSelectedModelIdsFromHidden().map(id => ({ modelId: id, id: id }))
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
        area.innerHTML = '<div style="font-size:12px;color:#667085;">微信通过 openclaw-weixin 插件扫码登录。</div><div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;"><button id="btn_wx_start" class="btn" onclick="startWeixinLogin(false)">开始微信登录</button><button id="btn_wx_poll" class="btn" onclick="regenerateWeixinQr()">重新生成</button></div><div id="weixin_status" style="font-size:12px;color:#667085;margin-top:8px;">未查询</div><div id="weixin_qr" style="margin-top:8px;"></div>';
      }
      syncChannelSaveButtonState();
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
        payload = { weixin: { enabled: true } };
      }
      try {
        await api('channels_save', 'POST', payload);
        closeChannelDialog();
        await load('channels');
        setMsg('渠道保存成功', 'ok');
      } catch (e) { setMsg('渠道保存失败：' + (e.message || e), 'err'); }
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
        + '  <div style="font-size:12px;color:#667085;">' + esc(note || '请使用微信扫码完成登录') + '</div>'
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
        qrEl.innerHTML = '<div style="font-size:12px;color:#b42318;margin-bottom:8px;">二维码重绘失败：' + esc(e.message || e) + '</div><a class="btn" target="_blank" rel="noopener" href="' + esc(qrUrl) + '">新窗口打开二维码</a>';
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
        qrEl.innerHTML = '<div style="font-size:12px;color:#667085;">二维码加载中...</div>';
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
          __weixinPollTimer = setInterval(() => { pollWeixinLogin({ silent: true }); }, 3000);
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
        const data = await api('weixin_login_wait', 'POST', { sessionKey, roundId, timeoutMs: 1000 });
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
            await saveChannelDialog();
            await load('channels');
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
        pre.textContent = data.log || '';
        pre.scrollTop = pre.scrollHeight;
      } catch (e) {}
    }
    document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => load(btn.dataset.tab)));
    load('status');
  </script>
</body>
</html>
HTML
