#!/bin/sh
APP_VAR_DIR="/var/packages/ainasclaw/var"
if [ -d "/volume1/@appdata/ainasclaw" ]; then
    APP_VAR_DIR="/volume1/@appdata/ainasclaw"
fi

LOG_FILE="${APP_VAR_DIR}/ainasclaw.log"
GATEWAY_PORT="58789"
QUERY="${QUERY_STRING:-}"
BASE_CFG_FILE="/volume1/openclaw/.openclaw/openclaw.json"

# Resolve active config path from configured workspace:
# workspace=/volume1/openclaw -> cfg=/volume1/openclaw/.openclaw/openclaw.json
CFG_FILE="$(python3 - <<'PY' "$BASE_CFG_FILE"
import json, os, sys
base = sys.argv[1] if len(sys.argv) > 1 else '/volume1/openclaw/.openclaw/openclaw.json'
workspace = '/volume1/openclaw'
ptr = '/var/packages/ainasclaw/var/workspace.path'
home_ptr = '/var/packages/ainasclaw/var/workspace.home.path'
ptr_hit = False
try:
    if os.path.exists(ptr):
        ws_ptr = (open(ptr, 'r', encoding='utf-8').read() or '').strip()
        if ws_ptr:
            ws_home = '/volume1/openclaw'
            try:
                if os.path.exists(home_ptr):
                    ws_home_raw = (open(home_ptr, 'r', encoding='utf-8').read() or '').strip()
                    if ws_home_raw:
                        ws_home = ws_home_raw
            except Exception:
                pass
            if ws_ptr == '$HOME':
                ws_ptr = ws_home
            elif ws_ptr.startswith('$HOME/'):
                ws_ptr = ws_home.rstrip('/') + '/' + ws_ptr[len('$HOME/'):]
            workspace = ws_ptr
            ptr_hit = True
except Exception:
    pass
# base cfg is fallback only; never override explicit persisted pointer
if (not ptr_hit) and workspace == '/volume1/openclaw':
    try:
        if os.path.exists(base):
            c = json.load(open(base, 'r', encoding='utf-8'))
            ws = (((c.get('agents') or {}).get('defaults') or {}).get('workspace') or '').strip()
            if ws:
                workspace = ws
    except Exception:
        pass
# normalize: workspace should be user directory, not nested .openclaw path
if workspace.endswith('/.openclaw'):
    workspace = workspace[:-10]
cfg_path = os.path.join(workspace or '/volume1/openclaw', '.openclaw', 'openclaw.json')
print(cfg_path)
PY
)"

# Dynamic gateway port from active config (fallback 58789)
GATEWAY_PORT="$(python3 - <<'PY' "$CFG_FILE"
import json, os, sys
cfg = sys.argv[1] if len(sys.argv) > 1 else ''
port = 58789
try:
    if cfg and os.path.exists(cfg):
        c = json.load(open(cfg, 'r', encoding='utf-8'))
        v = int((((c.get('gateway') or {}).get('port')) or 0))
        if 1024 <= v <= 65535:
            port = v
except Exception:
    pass
print(port)
PY
)"

get_param() {
    printf '%s' "$2" | tr '&' '\n' | awk -F= -v k="$1" '$1==k{print substr($0,index($0,"=")+1)}' | tail -n1
}

urldecode() {
    data=$(printf '%s' "$1" | sed 's/+/ /g;s/%/\\x/g')
    printf '%b' "$data"
}

read_body() {
    if [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -gt 0 ] 2>/dev/null; then
        # Read exact bytes from stdin (more reliable than dd across DSM CGI variants).
        python3 -c 'import sys
n=int(sys.argv[1]) if len(sys.argv)>1 else 0
sys.stdout.buffer.write(sys.stdin.buffer.read(n) if n>0 else b"")
' "$CONTENT_LENGTH"
    else
        # Some DSM CGI flows don't provide CONTENT_LENGTH for JSON POST.
        # Read stdin in non-blocking/idle-timeout mode to avoid hanging forever.
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

# 仅允许 DSM 登录会话访问（避免未登录直接打开）
REQ_COOKIE="${HTTP_COOKIE:-}"
if ! printf '%s' "$REQ_COOKIE" | grep -Eq '(^|;[[:space:]]*)id='; then
    printf "Status: 403 Forbidden
"
    printf "Content-Type: text/plain; charset=UTF-8

"
    printf "Forbidden: DSM login required
"
    exit 0
fi

# native_api=1 接口请求不受此限制。
# launchApp=1 仅允许套件内带 fromApp=1 的入口；普通直链（无标记）直接拦截。
if [ "$native_api" != "1" ] && [ "$launch_app" = "1" ]; then
    if [ "$from_app" != "1" ]; then
        printf "Status: 403 Forbidden
"
        printf "Content-Type: text/plain; charset=UTF-8

"
        printf "Forbidden: direct launch blocked
"
        exit 0
    fi
fi

if [ "$native_api" = "1" ]; then
    case "$action" in
        status)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$GATEWAY_PORT" "${CFG_FILE}"
import json, os, socket, subprocess, sys, time
port = int(sys.argv[1]) if len(sys.argv) > 1 else 44539
cfg_path = sys.argv[2] if len(sys.argv) > 2 else ''
running = False
service_running = False
# 避免单次探测抖动导致“已停止 -> 运行中”闪烁：做短重试（端口探测）。
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

# gateway 进程探测兜底：按钮语义是“停止 gateway”，不是“停止套件”。
# 不能用 pgrep -f 正则（会误匹配当前检查命令自身 argv），改为精确 comm 匹配。
if not running:
    try:
        r = subprocess.run([
            'pgrep', '-x', 'openclaw-gatewa'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1.5)
        running = (r.returncode == 0)
    except Exception:
        pass

# 套件运行态（独立于 gateway 端口探活）：用于按钮可用性判断。
# 目标：即便 gateway 进程异常，仍允许“停止 OpenClaw”按钮可点击。
try:
    r = subprocess.run([
        '/usr/syno/bin/synopkg', 'status', 'ainasclaw'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=2)
    txt = (r.stdout or '').strip()
    low = txt.lower()
    # 兼容 JSON 和纯文本两种返回。
    service_running = ('"status":"running"' in low) or ('package is started' in low)
    if (not service_running) and txt.startswith('{'):
        try:
            j = json.loads(txt)
            service_running = str(j.get('status') or '').lower() == 'running'
        except Exception:
            pass
except Exception:
    service_running = False

# Fallback: 读取守护占位 pid（由 start-stop-status 维护）
if not service_running:
    try:
        pid_file = '/var/packages/ainasclaw/var/ainasclaw.pid'
        if os.path.exists(pid_file):
            pid_txt = (open(pid_file, 'r', encoding='utf-8').read() or '').strip().split()
            ok = False
            for p in pid_txt:
                if p.isdigit() and os.path.exists(f'/proc/{p}'):
                    ok = True
                    break
            service_running = ok
    except Exception:
        service_running = False

# 计算 gateway 运行时长（秒）
started_ts = None
uptime_seconds = 0
if running:
    try:
        # 优先按 PID 读取 etimes，避免字符串匹配误差导致一直 0 秒。
        cmdline = "pgrep -af 'openclaw.*gateway|dist/index.js gateway' | grep -v 'app/fn-port/server' | head -n1"
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
workspace = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/openclaw')
if isinstance(workspace, str) and workspace.endswith('/.openclaw'):
    workspace = workspace[:-10]
# 版本实时读取：优先展示当前安装包 INFO 的 version（编译版本），回退到 app package.json。
spk_ver = ''
for p in ('/var/packages/ainasclaw/INFO', '/var/packages/openclaw/INFO'):
    try:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith('version='):
                        spk_ver = line.split('=', 1)[1].strip().strip('"')
                        break
        if spk_ver:
            break
    except Exception:
        pass
app_ver = ''
for p in ('/var/packages/ainasclaw/target/app/openclaw/package.json', '/var/packages/openclaw/target/app/openclaw/package.json'):
    try:
        if os.path.exists(p):
            j = json.load(open(p, 'r', encoding='utf-8'))
            app_ver = str(j.get('version') or '').strip()
            if app_ver:
                break
    except Exception:
        pass
version = spk_ver or app_ver or 'unknown'
binary_path = '/var/packages/ainasclaw/target/bin/openclaw' if os.path.exists('/var/packages/ainasclaw/target/bin/openclaw') else ''
gateway_token = str((((cfg.get('gateway') or {}).get('auth') or {}).get('token')) or '')
out = {
  'instanceId': 'default',
  'displayName': 'Default Gateway',
  'running': running,
  'serviceRunning': service_running,
  'installed': True,
  'version': version,
  'port': port,
  'proxyBasePath': '/default',
  'workspaceDir': workspace,
  'configPath': cfg_path,
  'binaryPath': binary_path,
  'uptimeSeconds': uptime_seconds,
  'startedAt': started_ts,
  'gatewayToken': gateway_token
}
print(json.dumps(out, ensure_ascii=False))
PY
            exit 0
            ;;
        models)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "${CFG_FILE}"
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
workspace_dir = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/openclaw')
if isinstance(workspace_dir, str) and workspace_dir.endswith('/.openclaw'):
    workspace_dir = workspace_dir[:-10]
print(json.dumps({'configuredProviders': providers, 'workspaceDir': workspace_dir, 'configPath': cfg_path, 'configExists': bool(cfg)}, ensure_ascii=False))
PY
            exit 0
            ;;
        models_save)
            body=$(read_body)
            cfg_file="${CFG_FILE}"
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "$cfg_file" "${APP_VAR_DIR}/openclaw-gateway.spawn.log"
import json, os, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
cfg_path = sys.argv[2] if len(sys.argv) > 2 else ''
spawn_log = sys.argv[3] if len(sys.argv) > 3 else '/tmp/openclaw-gateway.spawn.log'
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}
prev_workspace = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '').strip()
if prev_workspace.endswith('/.openclaw'):
    prev_workspace = prev_workspace[:-10]
workspace_input = (payload.get('workspaceDir') or '').strip()
workspace_explicit = bool(workspace_input)
workspace = workspace_input
if workspace:
    # 用户目录保护：不允许将用户目录命名为 .openclaw（该名称保留给内部工作目录）
    norm_ws = '/' + workspace.strip('/')
    if norm_ws.endswith('/.openclaw') or '/.openclaw/' in norm_ws + '/':
        print(json.dumps({
            'ok': False,
            'error': '用户目录不能包含 .openclaw（该名称为内部工作目录保留）',
            'workspaceDir': workspace
        }, ensure_ascii=False))
        raise SystemExit
    # normalize user input: if user accidentally passes .../.openclaw, store parent dir as workspace
    if workspace.endswith('/.openclaw'):
        workspace = workspace[:-10]
else:
    # 优先从当前 cfg_path 反推工作目录，避免被配置内容里的旧 workspace 值污染。
    workspace = ''
    if cfg_path:
        cp = cfg_path.strip()
        suffix = '/.openclaw/openclaw.json'
        if cp.endswith(suffix):
            workspace = cp[:-len(suffix)]
        else:
            workspace = os.path.dirname(cp)
    if not workspace:
        workspace = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/openclaw').strip()
# normalize no matter where workspace value comes from
if workspace.endswith('/.openclaw'):
    workspace = workspace[:-10]

if not cfg_path:
    cfg_path = os.path.join(workspace or '/volume1/openclaw', '.openclaw', 'openclaw.json')

qmd = cfg.setdefault('memory', {}).setdefault('qmd', {})
paths = qmd.setdefault('paths', [])
state_path = os.path.join(workspace, '.openclaw')
cfg.setdefault('agents', {}).setdefault('defaults', {})['workspace'] = state_path
if not paths:
    paths.append({'path': state_path, 'name': 'workspace', 'pattern': '**/*.md'})
elif isinstance(paths[0], dict):
    paths[0]['path'] = state_path

# after workspace change, always write into target workspace config path
cfg_path = os.path.join(workspace or '/volume1/openclaw', '.openclaw', 'openclaw.json')

# 规则：仅允许在 gateway 停止后修改用户目录。
workspace_changed = bool(workspace and workspace != prev_workspace)
try:
    import socket
    try:
        gw_port_chk = int((((cfg.get('gateway') or {}).get('port')) or 0))
    except Exception:
        gw_port_chk = 0
    if not (1024 <= gw_port_chk <= 65535):
        gw_port_chk = 58789
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(('127.0.0.1', gw_port_chk))
        gateway_running = True
    except Exception:
        gateway_running = False
    finally:
        try:
            s.close()
        except Exception:
            pass
except Exception:
    gateway_running = False

if workspace_explicit and workspace_changed and gateway_running:
    print(json.dumps({
        'ok': False,
        'error': '请先停止 gateway，再修改用户目录。',
        'workspaceDir': workspace,
        'configPath': cfg_path,
        'gatewayRunning': True
    }, ensure_ascii=False))
    raise SystemExit

# 用户目录变更时：将旧工作目录下 .openclaw 全量迁移到新目录，保证文件统一落在 用户目录/.openclaw。
if workspace_explicit and workspace_changed:
    try:
        import shutil
        old_state = os.path.join(prev_workspace or '/volume1/openclaw', '.openclaw')
        new_state = os.path.join(workspace or '/volume1/openclaw', '.openclaw')
        if old_state != new_state and os.path.isdir(old_state):
            os.makedirs(new_state, exist_ok=True)
            for name in os.listdir(old_state):
                src = os.path.join(old_state, name)
                dst = os.path.join(new_state, name)
                try:
                    # 强制以新目录为准：目录做合并覆盖，文件直接覆盖复制。
                    if os.path.isdir(src):
                        os.makedirs(dst, exist_ok=True)
                        for item in os.listdir(src):
                            s2 = os.path.join(src, item)
                            d2 = os.path.join(dst, item)
                            if os.path.isdir(s2):
                                shutil.copytree(s2, d2, dirs_exist_ok=True)
                                shutil.rmtree(s2, ignore_errors=True)
                            else:
                                shutil.copy2(s2, d2)
                                try:
                                    os.remove(s2)
                                except Exception:
                                    pass
                    else:
                        shutil.copy2(src, dst)
                        try:
                            os.remove(src)
                        except Exception:
                            pass
                except Exception:
                    pass

            # 旧目录清理：切目录后不再保留核心运行位，避免“看起来还在默认目录”。
            for stale in ['openclaw.json', 'skills', 'extensions']:
                p = os.path.join(old_state, stale)
                try:
                    if os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                    elif os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
    except Exception:
        pass

# persist workspace pointer outside workspace directory to survive workspace deletion
pointer_write_err = ''
try:
    ptr = '/var/packages/ainasclaw/var/workspace.path'
    home_ptr = '/var/packages/ainasclaw/var/workspace.home.path'
    os.makedirs(os.path.dirname(ptr), exist_ok=True)
    # 仅在显式改目录（或指针缺失）时写 pointer，避免“保存模型”误把目录改回默认。
    if workspace_explicit or (not os.path.exists(ptr)) or (not os.path.exists(home_ptr)):
        with open(ptr, 'w', encoding='utf-8') as pf:
            pf.write('$HOME')
        with open(home_ptr, 'w', encoding='utf-8') as hpf:
            hpf.write(workspace)
except Exception as e:
    pointer_write_err = str(e)

# 目录显式修改时，pointer 写失败必须直接报错，避免“保存成功但实际不生效”。
if workspace_explicit and pointer_write_err:
    print(json.dumps({
        'ok': False,
        'error': 'workspace pointer 写入失败: ' + pointer_write_err,
        'workspaceDir': workspace,
        'configPath': cfg_path,
        'pointerWriteErr': pointer_write_err
    }, ensure_ascii=False))
    raise SystemExit

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
# workspace changed explicitly: normalize gateway default port to 58789
try:
    if workspace_explicit and (workspace or '/volume1/openclaw') != (prev_workspace or '/volume1/openclaw'):
        gw = cfg.setdefault('gateway', {})
        gw['port'] = 58789
except Exception:
    pass
os.makedirs(os.path.dirname(cfg_path), exist_ok=True)

# user requirement: changing workspace should initialize by defaults only (no migration)
if (not os.path.exists(cfg_path)) and os.path.exists('/var/packages/ainasclaw/target/app/openclaw/config/openclaw.template.json'):
    try:
        cfg = json.load(open('/var/packages/ainasclaw/target/app/openclaw/config/openclaw.template.json', 'r', encoding='utf-8'))
        qmd = cfg.setdefault('memory', {}).setdefault('qmd', {})
        paths = qmd.setdefault('paths', [])
        state_path = os.path.join(workspace or '/volume1/openclaw', '.openclaw')
        cfg.setdefault('agents', {}).setdefault('defaults', {})['workspace'] = state_path
        if not paths:
            paths.append({'path': state_path, 'name': 'workspace', 'pattern': '**/*.md'})
        elif isinstance(paths[0], dict):
            paths[0]['path'] = state_path
        # no model configured => remove stale primaries/default provider remnants
        try:
            if not providers_map:
                defaults = (cfg.get('agents') or {}).get('defaults') or {}
                if isinstance(defaults.get('model'), dict):
                    defaults['model'].pop('primary', None)
                if isinstance(defaults.get('imageModel'), dict):
                    defaults['imageModel'].pop('primary', None)
                models_obj = cfg.get('models') or {}
                if isinstance(models_obj, dict):
                    models_obj['providers'] = {}
        except Exception:
            pass
        cfg.setdefault('models', {})['providers'] = providers_map
    except Exception:
        pass

with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')

# user requirement: after adding/updating model providers, trigger provider-model sync script automatically
model_sync_triggered = False
model_sync_exit = None
try:
    import subprocess, datetime
    if providers_map:
        model_sync_triggered = True
        state_dir_for_sync = os.path.dirname(cfg_path)
        # NOTE: service-setup initializes OPENCLAW_CONFIG_FILE to base defaults when sourced.
        # Re-assign target cfg path AFTER source so sync runs on the active workspace config.
        sync_cmd = (
            'bash -lc "source /var/packages/ainasclaw/scripts/service-setup >/dev/null 2>&1; '
            'OPENCLAW_CONFIG_FILE=\"{cfg}\"; '
            'OPENCLAW_CONFIG_PATH=\"{cfg}\"; '
            'OPENCLAW_STATE_DIR=\"{state}\"; '
            'OPENCLAW_WORKSPACE_DIR=\"{workspace}\"; '
            'HOME=\"{workspace}\"; '
            'OPENCLAW_GATEWAY_RESTART_START=1; '
            'sync_provider_models_from_upstream"'
        ).format(cfg=cfg_path, state=state_dir_for_sync, workspace=workspace)
        r = subprocess.run(sync_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
        model_sync_exit = int(r.returncode)
        # lightweight marker for troubleshooting whether auto-sync path was executed
        try:
            with open(os.path.join(state_dir_for_sync, 'model-sync.last-run.txt'), 'w', encoding='utf-8') as mf:
                mf.write(datetime.datetime.utcnow().isoformat() + 'Z\n')
                mf.write('exit=' + str(r.returncode) + '\n')
                out = (r.stdout or b'').decode('utf-8', errors='ignore')
                if out:
                    mf.write(out[-4000:])
        except Exception:
            pass
except Exception:
    pass

# keep default workspace clean when active workspace is non-default
try:
    default_state = '/volume1/openclaw/.openclaw'
    if (workspace or '/volume1/openclaw') != '/volume1/openclaw':
        import shutil
        shutil.rmtree(os.path.join(default_state, 'agents'), ignore_errors=True)
        shutil.rmtree(os.path.join(default_state, 'flows'), ignore_errors=True)
except Exception:
    pass

# Initialize workspace runtime assets immediately after workspace switch/save
state_dir = os.path.dirname(cfg_path) if cfg_path else os.path.join(workspace or '/volume1/openclaw', '.openclaw')
skills_dir = os.path.join(state_dir, 'skills', '_bundled')
ext_dir = os.path.join(state_dir, 'extensions')
os.makedirs(skills_dir, exist_ok=True)
os.makedirs(ext_dir, exist_ok=True)

app_dir = '/var/packages/ainasclaw/target/app/openclaw'

# sync extension skills from app dist/extensions/*/skills
try:
    dist_ext = os.path.join(app_dir, 'dist', 'extensions')
    if os.path.isdir(dist_ext):
        for plugin_id in os.listdir(dist_ext):
            src = os.path.join(dist_ext, plugin_id, 'skills')
            if not os.path.isdir(src):
                continue
            dst = os.path.join(skills_dir, plugin_id)
            if os.path.exists(dst):
                import shutil
                shutil.rmtree(dst, ignore_errors=True)
            import shutil
            shutil.copytree(src, dst, dirs_exist_ok=True)
except Exception:
    pass

# keep workspace/extensions free of channel plugin copies (DSM trust checks may block uid!=0).
# channel plugins are staged under app/dist/extensions by service script.
for pkg_name in ['feishu-openclaw-plugin', 'dingtalk', 'wecom', 'openclaw-qqbot', 'openclaw-weixin']:
    try:
        dst = os.path.join(ext_dir, pkg_name)
        import shutil
        if os.path.lexists(dst):
            if os.path.islink(dst) or os.path.isfile(dst):
                os.unlink(dst)
            else:
                shutil.rmtree(dst, ignore_errors=True)
    except Exception:
        pass

workspace_changed = bool(workspace and workspace != prev_workspace)

# 用户目录切换后的自动初始化：从套件系统文件同步 skills / 插件资源到新目录。
workspace_init_sync_ok = False
workspace_init_sync_err = ''
workspace_init_deps_ok = True
workspace_init_deps_err = 'skipped: workspace change does not run doctor --fix'
if workspace_explicit and workspace_changed:
    try:
        # 与 SPK 安装初始化路径一致：复用 service-setup 的同步函数，不调用 doctor。
        init_cmd = (
            'bash -lc "set -e; '
            'export SYNOPKG_PKGNAME=ainasclaw; '
            'export SYNOPKG_DSM_VERSION_MAJOR=7; '
            'export SYNOPKG_PKGDEST=/var/packages/ainasclaw/target; '
            'export SYNOPKG_PKGVAR=/var/packages/ainasclaw/var; '
            'source /var/packages/ainasclaw/scripts/service-setup >/dev/null 2>&1; '
            'OPENCLAW_CONFIG_FILE=\"{cfg}\"; '
            'OPENCLAW_CONFIG_PATH=\"{cfg}\"; '
            'OPENCLAW_STATE_DIR=\"{state}\"; '
            'OPENCLAW_WORKSPACE=\"{workspace}\"; '
            'OPENCLAW_WORKSPACE_DIR=\"{workspace}\"; '
            'rm -rf \"{state}/extensions/node_modules\"; '
            'sync_bundled_channel_plugins_to_stock_extensions; '
            'sync_bundled_channel_plugins_to_extensions; '
            'sync_skills_to_workspace; '
            'harden_extension_permissions"'
        ).format(cfg=cfg_path, state=os.path.dirname(cfg_path), workspace=workspace)
        rr = subprocess.run(init_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        workspace_init_sync_ok = (rr.returncode == 0)
        if not workspace_init_sync_ok:
            workspace_init_sync_err = ((rr.stdout or b'').decode('utf-8', errors='ignore')[-1200:] or f'rc={rr.returncode}')
    except Exception as e:
        workspace_init_sync_ok = False
        workspace_init_sync_err = str(e)
# Mark one-shot default-port reset when user explicitly switches workspace.
try:
    if workspace_explicit and workspace_changed:
        marker = '/var/packages/ainasclaw/var/force-default-port-on-next-start.flag'
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, 'w', encoding='utf-8') as mf:
            mf.write('1\n')
except Exception:
    pass
ptr_val = ''
hptr_val = ''
try:
    ptr_val = (open('/var/packages/ainasclaw/var/workspace.path', 'r', encoding='utf-8').read() or '').strip()
except Exception:
    pass
try:
    hptr_val = (open('/var/packages/ainasclaw/var/workspace.home.path', 'r', encoding='utf-8').read() or '').strip()
except Exception:
    pass
out = {
    'configuredProviders': providers_payload,
    'workspaceDir': workspace or '/volume1/openclaw',
    'configPath': cfg_path,
    'configExists': True,
    'workspaceChanged': workspace_changed,
    'modelSyncTriggered': model_sync_triggered,
    'modelSyncExit': model_sync_exit,
    'workspacePointer': ptr_val,
    'workspaceHomePointer': hptr_val,
    'pointerWriteErr': pointer_write_err,
    'workspaceInitSyncOk': workspace_init_sync_ok,
    'workspaceInitSyncErr': workspace_init_sync_err,
    'workspaceInitDepsOk': workspace_init_deps_ok,
    'workspaceInitDepsErr': workspace_init_deps_err
}
# applyNow=true 时自动启用 gateway；false 时仅落配置。
if apply_now:
    try:
        import subprocess, time, socket
        env = os.environ.copy()
        env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
        env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/ainasclaw/data'
        state_dir = (os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw')
        user_dir = (os.path.dirname(state_dir) if state_dir.endswith('/.openclaw') else state_dir)
        env['HOME'] = user_dir
        env['OPENCLAW_CONFIG_PATH'] = cfg_path
        env['OPENCLAW_STATE_DIR'] = state_dir
        env['OPENCLAW_WORKSPACE_DIR'] = user_dir
        env['NPM_CONFIG_CACHE'] = state_dir + '/.npm'
        env['XDG_CACHE_HOME'] = state_dir + '/.cache'
        env['XDG_CONFIG_HOME'] = state_dir + '/.config'
        env['XDG_DATA_HOME'] = state_dir + '/.local/share'
        env['OPENCLAW_TOOLS_PROFILE'] = 'full'
        env['OPENCLAW_TOOLS_ELEVATED_ENABLED'] = '1'
        env['OPENCLAW_ELEVATED_DEFAULT'] = 'full'
        env['OPENCLAW_EXEC_SECURITY_DEFAULT'] = 'full'

        try:
            with open(cfg_path, 'r', encoding='utf-8') as _rf:
                _c = json.load(_rf)
            gw_port = int((((_c.get('gateway') or {}).get('port')) or 0))
            if not (1024 <= gw_port <= 65535):
                gw_port = 58789
        except Exception:
            gw_port = 58789

        def is_running(port=None):
            port = gw_port if port is None else port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.6)
            try:
                s.connect(('127.0.0.1', port))
                return True
            except Exception:
                return False
            finally:
                try:
                    s.close()
                except Exception:
                    pass

        currently_running = is_running(gw_port)
        # 如果已运行且目录未变化，避免重复拉起导致 EADDRINUSE。
        # 若目录变化则必须重启，确保 gateway 切到新 workspace。
        if currently_running and not workspace_changed:
            out['gatewayAutoStartTriggered'] = False
            out['gatewayRunning'] = True
            out['message'] = 'gateway already running'
        else:
            # 仅在当前确实在运行时先停旧进程；未运行时直接拉起，避免无意义超时。
            if currently_running:
                for cmd in (
                    ['/var/packages/ainasclaw/target/bin/openclaw', 'gateway', 'stop', '--json'],
                    ['pkill', '-f', 'openclaw-gatew'],
                    ['pkill', '-f', '/app/openclaw/dist/index.js gateway'],
                    ['pkill', '-f', 'openclaw gateway'],
                ):
                    try:
                        subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=4)
                    except Exception:
                        pass

            os.makedirs(os.path.dirname(spawn_log), exist_ok=True)
            try:
                with open(spawn_log, 'a', encoding='utf-8') as sf:
                    sf.write('[gateway-spawn] request start\n')
            except Exception:
                pass
            try:
                logf = open(spawn_log, 'ab', buffering=0)
            except Exception:
                logf = None
            p = subprocess.Popen(
                ['/var/packages/ainasclaw/target/bin/openclaw', 'gateway', 'run', '--allow-unconfigured', '--port', str(gw_port)],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=(logf if logf is not None else subprocess.DEVNULL),
                stderr=(logf if logf is not None else subprocess.DEVNULL),
                close_fds=True,
                start_new_session=True,
            )
            out['gatewayAutoStartTriggered'] = True
            out['gatewayAutoStartPid'] = p.pid
            try:
                with open(spawn_log, 'a', encoding='utf-8') as sf:
                    sf.write(f'[gateway-spawn] started pid={p.pid}\n')
            except Exception:
                pass

            running = False
            for _ in range(12):
                if is_running(gw_port):
                    running = True
                    break
                time.sleep(1)
            out['gatewayRunning'] = running

        try:
            subprocess.run(
                [
                    'bash', '-lc',
                    'source /var/packages/ainasclaw/scripts/service-setup >/dev/null 2>&1; sync_dsm_package_info_port "' + str(gw_port) + '"'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=12
            )
            # 若 synopkg metadata 仍未刷新，直接补写 INFO/adminport 作为兜底（防止套件详情仍显示 58789）。
            try:
                info_file = '/var/packages/ainasclaw/INFO'
                if not os.path.exists(info_file):
                    info_file = '/var/packages/openclaw/INFO'
                if os.path.exists(info_file):
                    txt = open(info_file, 'r', encoding='utf-8', errors='ignore').read()
                    import re as _re
                    n_txt = txt
                    if _re.search(r'^adminport="\d+"', n_txt, flags=_re.M):
                        n_txt = _re.sub(r'^adminport="\d+"', f'adminport="{gw_port}"', n_txt, flags=_re.M)
                    else:
                        n_txt = n_txt.rstrip('\n') + f'\nadminport="{gw_port}"\n'
                    if _re.search(r'^adminurl=".*"', n_txt, flags=_re.M):
                        n_txt = _re.sub(r'^adminurl=".*"', 'adminurl="/default/chat"', n_txt, flags=_re.M)
                    else:
                        n_txt = n_txt.rstrip('\n') + 'adminurl="/default/chat"\n'
                    if n_txt != txt:
                        open(info_file, 'w', encoding='utf-8').write(n_txt)
            except Exception:
                pass
        except Exception:
            pass
    except Exception as e:
        out['gatewayAutoStartTriggered'] = False
        out['gatewayAutoStartErr'] = str(e)
else:
    out['gatewayAutoStartTriggered'] = False
    out['message'] = '配置已保存（未自动启用）'
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
headers = {'User-Agent': 'ainasclaw-native-ui/1.0'}
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
headers = {'User-Agent': 'ainasclaw-native-ui/1.0'}
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
            python3 - <<'PY' "${CFG_FILE}"
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
  'weixin': ch.get('openclaw-weixin') or ch.get('weixin') or {}
}
print(json.dumps(out, ensure_ascii=False))
PY
            exit 0
            ;;
        channels_save)
            body=$(read_body)
            cfg_file="${CFG_FILE}"
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "$cfg_file"
import json, os, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
cfg_path = sys.argv[2] if len(sys.argv) > 2 else ''
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
skip_reload = bool(payload.get('noReload', False))
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
wx_payload = payload.get('openclaw-weixin') if isinstance(payload.get('openclaw-weixin'), dict) else payload.get('weixin')
if isinstance(wx_payload, dict):
    w = ch.setdefault('openclaw-weixin', {})
    w['enabled'] = bool(wx_payload.get('enabled', True))
    # Auto-heal doctor requirement: channels.openclaw-weixin.accounts.default
    acc = w.get('accounts')
    if isinstance(acc, dict):
        cur_default = acc.get('default') if isinstance(acc.get('default'), str) else ''
        account_ids = [k for k, v in acc.items() if k != 'default' and isinstance(v, dict)]
        if (not cur_default or cur_default not in acc) and account_ids:
            acc['default'] = account_ids[0]
            w['accounts'] = acc

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

# 保存渠道后默认热重载 gateway；微信扫码自动保存可传 noReload=true，避免等待 30~60s。
reload_ok = False
reload_out = ''
if not skip_reload:
    try:
        import subprocess
        env = os.environ.copy()
        env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
        env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/ainasclaw/data'
        state_dir = (os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw')
        user_dir = (os.path.dirname(state_dir) if state_dir.endswith('/.openclaw') else state_dir)
        env['HOME'] = user_dir
        env['OPENCLAW_CONFIG_PATH'] = cfg_path
        env['OPENCLAW_STATE_DIR'] = state_dir
        env['OPENCLAW_WORKSPACE_DIR'] = user_dir
        env['NPM_CONFIG_CACHE'] = state_dir + '/.npm'
        env['XDG_CACHE_HOME'] = state_dir + '/.cache'
        env['XDG_CONFIG_HOME'] = state_dir + '/.config'
        env['XDG_DATA_HOME'] = state_dir + '/.local/share'
        env['OPENCLAW_GATEWAY_RESTART_START'] = '1'
        cmd = ['/var/packages/ainasclaw/target/bin/openclaw', 'gateway', 'restart', '--json']
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
            cfg_file="${CFG_FILE}"
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
            python3 - <<'PY' "${APP_VAR_DIR}/data/home" "${CFG_FILE}" "${APP_VAR_DIR}/weixin-login-debug.log" "${APP_VAR_DIR}/weixin-login-worker.pid" "$body"
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
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/ainasclaw/data'
env['HOME'] = home_dir
env['OPENCLAW_CONFIG_PATH'] = cfg_path
state_dir = (os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw')
user_dir = (os.path.dirname(state_dir) if state_dir.endswith('/.openclaw') else state_dir)
env['OPENCLAW_STATE_DIR'] = state_dir
env['OPENCLAW_WORKSPACE_DIR'] = user_dir
env['NPM_CONFIG_CACHE'] = state_dir + '/.npm'
env['XDG_CACHE_HOME'] = state_dir + '/.cache'
env['XDG_CONFIG_HOME'] = state_dir + '/.config'
env['XDG_DATA_HOME'] = state_dir + '/.local/share'
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

# 关键：ainasclaw 内部有并发流程会覆写 openclaw.json，导致 weixin 插件配置丢失。
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
# 注意：扫码“开始”阶段不自动创建 channels.openclaw-weixin，
# 避免用户取消后配置里残留微信通道。
os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')
log('openclaw_weixin_config_repaired=1')
# 提速：不再每次执行 plugins enable（该操作经常阻塞 15s+），仅在配置层保证可用。
bootstrap_log = 'openclaw-weixin config repaired (fast path)'
log('openclaw_weixin_ensure_enabled=1 fast_path=1')

# 直接调用微信二维码接口（对齐 sc-openclaw_v0.0.10 的“秒出码”路径），避免走 CLI login 阻塞。
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
        with open('/tmp/ainasclaw-weixin-login-state.json', 'w', encoding='utf-8') as sf:
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
            python3 - <<'PY' "${CFG_FILE}" "${APP_VAR_DIR}/weixin-login-debug.log" "${APP_VAR_DIR}/weixin-login-worker.pid" "$body"
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
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/ainasclaw/data'
state_dir = (os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw')
user_dir = (os.path.dirname(state_dir) if state_dir.endswith('/.openclaw') else state_dir)
env['HOME'] = user_dir
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = state_dir
env['OPENCLAW_WORKSPACE_DIR'] = user_dir
env['NPM_CONFIG_CACHE'] = state_dir + '/.npm'
env['XDG_CACHE_HOME'] = state_dir + '/.cache'
env['XDG_CONFIG_HOME'] = state_dir + '/.config'
env['XDG_DATA_HOME'] = state_dir + '/.local/share'
# 性能优化：轮询接口不再调用 channels status（该命令可阻塞数秒），
# 直接走二维码状态 API 判断连接结果。
raw = ''
connected = False
message = ''

# 新实现：直接轮询二维码状态接口（对齐 sc-openclaw_v0.0.10），不再依赖日志关键字判定连接。
import urllib.request, urllib.error
state_file = '/tmp/ainasclaw-weixin-login-state.json'
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
message = ''
try:
    req = urllib.request.Request(f"{base_url}/ilink/bot/get_qrcode_status?qrcode={qrcode}", headers={'iLink-App-ClientVersion': '1'})
    with urllib.request.urlopen(req, timeout=4) as r:
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
            state_dir = os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw'
            acc_dir = os.path.join(state_dir, 'openclaw-weixin', 'accounts')
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
            ids_path = os.path.join(state_dir, 'openclaw-weixin', 'accounts.json')
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
                ocfg_path = cfg_path
                ocfg = json.load(open(ocfg_path, 'r', encoding='utf-8')) if os.path.exists(ocfg_path) else {}
                chs = ocfg.setdefault('channels', {})
                wx = chs.get('openclaw-weixin')
                if not isinstance(wx, dict):
                    wx = {}
                wx['enabled'] = True
                wx['defaultAccount'] = aid
                # Keep both legacy defaultAccount and schema-required accounts.default.
                wx['accounts'] = {aid: {'enabled': True}, 'default': aid}
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

            # 不在扫码确认后重启包：避免 UI 额外等待 10~45 秒。
            # 后续由前端即时保存 channels 配置并让网关按热重载策略生效。
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
        message = ''
except Exception as e:
    connected = False
    status = 'pending'
    message = ''
    log(f'weixin_qr_status_poll_err={e}')

log(f'weixin_login_wait connected={bool(connected)} status={status} message={message}')
print(json.dumps({'supported': True, 'connected': bool(connected), 'status': status, 'message': message, 'qrUrl': qr_url, 'raw': raw[-300:]}, ensure_ascii=False))
PY
            exit 0
            ;;
        weixin_disconnect)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "${CFG_FILE}"
import json, os, subprocess, sys
cfg_path = sys.argv[1]
env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/ainasclaw/data'
state_dir = (os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw')
user_dir = (os.path.dirname(state_dir) if state_dir.endswith('/.openclaw') else state_dir)
env['HOME'] = user_dir
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = state_dir
env['OPENCLAW_WORKSPACE_DIR'] = user_dir
env['NPM_CONFIG_CACHE'] = state_dir + '/.npm'
env['XDG_CACHE_HOME'] = state_dir + '/.cache'
env['XDG_CONFIG_HOME'] = state_dir + '/.config'
env['XDG_DATA_HOME'] = state_dir + '/.local/share'
cmd = ['/var/packages/ainasclaw/target/bin/openclaw', 'channels', 'logout', '--channel', 'openclaw-weixin']
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
        terminal_health)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY'
import json, socket
port = 17682
ok = False
reason = ''
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.8)
    s.connect(('127.0.0.1', port))
    ok = True
    s.close()
except Exception as e:
    reason = str(e)
print(json.dumps({'ok': True, 'available': ok, 'port': port, 'reason': reason}, ensure_ascii=False))
PY
            exit 0
            ;;
        terminal_unlock)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body"
import json, os, subprocess, socket, time, sys, textwrap, shlex
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
cmd = str(payload.get('command') or '').strip()
admin_user = str(payload.get('adminUser') or '').strip()
admin_password = str(payload.get('adminPassword') or '')
force_password_flow = bool(payload.get('forcePasswordFlow'))
legacy_cmd = 'sudo -n /usr/syno/bin/synopkg restart ainasclaw'
admin_fix_cmd = "sudo -n ln -sfn /var/packages/ainasclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && sudo -n sh -lc 'nginx -t && systemctl reload nginx'"
if cmd not in (admin_fix_cmd, legacy_cmd):
    print(json.dumps({'ok': False, 'error': '修复命令不匹配', 'adminFixCommand': admin_fix_cmd}, ensure_ascii=False)); raise SystemExit

logs = []

def run(argv):
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = (p.stdout or '').strip()
    if out:
        logs.append(out[-700:])
    return p.returncode

def run_admin_password_flow(user, password):
    if not user or not password:
        return 127
    if any(ch in user for ch in ' \t\r\n:'):
        logs.append('invalid admin username')
        return 126
    inner = "ln -sfn /var/packages/ainasclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && nginx -t && systemctl reload nginx"
    su_cmd = "sudo -S -p '' sh -lc " + shlex.quote(inner)
    try:
        p = subprocess.Popen(['su', '-s', '/bin/sh', user, '-c', su_cmd], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out, _ = p.communicate((password + '\n' + password + '\n'), timeout=25)
        out = (out or '').strip()
        if out:
            logs.append(out[-700:])
        return p.returncode
    except Exception as e:
        logs.append('admin password flow error: ' + str(e))
        return 125

# 针对 root cause：修复 terminal alias 并重载 nginx
# 注意：不要在 CGI 请求里重启本套件，否则会中断当前请求导致前端拿不到返回。
alias_content = textwrap.dedent('''\
location ~ ^/openclaw-terminal(.*)$ {
    if ($http_cookie !~* "(^|;\\s*)id=") {
        return 403;
    }

    proxy_http_version      1.1;
    proxy_set_header        Host $host;
    proxy_set_header        Upgrade $http_upgrade;
    proxy_set_header        Connection "upgrade";
    proxy_set_header        X-Real-IP $remote_addr;
    proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header        X-Forwarded-Proto $scheme;
    proxy_set_header        X-Forwarded-Host $host;
    proxy_set_header        Cookie $http_cookie;
    proxy_read_timeout      3600s;
    proxy_send_timeout      3600s;
    proxy_connect_timeout   60s;

    add_header              'Access-Control-Allow-Origin' $scheme://$http_host always;
    add_header              'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
    add_header              'Access-Control-Allow-Headers' 'Authorization,Content-Type,Accept,Origin,User-Agent,DNT,Cache-Control,X-Mx-ReqToken,Keep-Alive,X-Requested-With,If-Modified-Since';
    add_header              'Access-Control-Allow-Credentials' 'true';
    add_header              'Cross-Origin-Embedder-Policy' 'require-corp';
    add_header              'Cross-Origin-Opener-Policy' 'same-origin';
    add_header              'Cross-Origin-Resource-Policy' 'same-site';

    proxy_pass              http://127.0.0.1:17682;
    proxy_buffering         off;
}
''')

alias_src = '/var/packages/ainasclaw/var/alias.openclaw-terminal.conf'
alias_dst = '/etc/nginx/conf.d/alias.openclaw-terminal.conf'
os.makedirs(os.path.dirname(alias_src), exist_ok=True)
try:
    with open(alias_src, 'w', encoding='utf-8') as f:
        f.write(alias_content)
except Exception as e:
    logs.append(f'write alias failed: {e}')

# 软链落地 + nginx reload：默认走 sudo -n；可由前端显式选择“强制密码修复”路径。
ln_rc = 1
nginx_test_rc = 1
nginx_reload_rc = 1
if force_password_flow and admin_user and admin_password:
    pw_rc = run_admin_password_flow(admin_user, admin_password)
    logs.append(f'password flow(forced) rc={pw_rc}')
else:
    ln_rc = run(['sudo', '-n', 'ln', '-sfn', alias_src, alias_dst])
    nginx_test_rc = run(['sudo', '-n', 'sh', '-lc', 'nginx -t'])
    if nginx_test_rc == 0:
        nginx_reload_rc = run(['sudo', '-n', 'sh', '-lc', 'systemctl reload nginx'])

    if (ln_rc != 0 or nginx_test_rc != 0 or nginx_reload_rc != 0) and admin_user and admin_password:
        pw_rc = run_admin_password_flow(admin_user, admin_password)
        logs.append(f'password flow rc={pw_rc}')


def check_port(port=17682, tries=20, interval=0.5):
    for _ in range(tries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.8)
        try:
            s.connect(('127.0.0.1', port))
            s.close()
            return True
        except Exception:
            try: s.close()
            except Exception: pass
            time.sleep(interval)
    return False


def check_alias_https(tries=6, interval=0.4):
    for _ in range(tries):
        p = subprocess.run([
            'curl', '-k', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
            '-H', 'Cookie: id=fake',
            'https://127.0.0.1:5001/openclaw-terminal/token'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        code = (p.stdout or '').strip()[-3:]
        if code and code not in ('404', '000'):
            return True, code
        time.sleep(interval)
    return False, (code if 'code' in locals() else '000')

port_ok = check_port()
alias_ok, alias_code = check_alias_https()
print(json.dumps({
    'ok': True,
    'patched': True,
    'available': bool(port_ok and alias_ok),
    'portAvailable': bool(port_ok),
    'aliasAvailable': bool(alias_ok),
    'aliasStatusCode': alias_code,
    'adminFixCommand': admin_fix_cmd,
    'logs': '\n'.join(logs)[-1200:]
}, ensure_ascii=False))
PY
            exit 0
            ;;
        terminal_session_start)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"builtin terminal removed"}'
            exit 0
            ;;
        terminal_session_start_removed_backup)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "${APP_VAR_DIR}" "${CFG_FILE}"
import json, os, signal, socket, subprocess, sys, time
base = (sys.argv[1] if len(sys.argv) > 1 else '/tmp').rstrip('/')
cfg_path = sys.argv[2] if len(sys.argv) > 2 else '/volume1/openclaw/.openclaw/openclaw.json'
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

workspace_dir = '/volume1/openclaw'
try:
    if os.path.exists(cfg_path):
        cfg = json.load(open(cfg_path, 'r', encoding='utf-8'))
        ws = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '').strip()
        if ws:
            workspace_dir = ws
except Exception:
    pass
# Terminal default path must be HOME/workspace root, not state dir.
if isinstance(workspace_dir, str) and workspace_dir.endswith('/.openclaw'):
    workspace_dir = workspace_dir[:-10] or '/volume1/openclaw'
try:
    os.makedirs(workspace_dir, exist_ok=True)
except Exception:
    workspace_dir = '/volume1/openclaw'

env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/ainasclaw/data'
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = (os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw')
# Align terminal env with wrapper semantics: HOME=workspace root, state under HOME/.openclaw
state_dir = env['OPENCLAW_STATE_DIR']
workspace_root = state_dir[:-10] if state_dir.endswith('/.openclaw') else '/volume1/openclaw'
env['OPENCLAW_WORKSPACE_DIR'] = workspace_root
env['HOME'] = workspace_root
env['NPM_CONFIG_CACHE'] = env['OPENCLAW_STATE_DIR'] + '/.npm'
env['XDG_CACHE_HOME'] = env['OPENCLAW_STATE_DIR'] + '/.cache'
env['XDG_CONFIG_HOME'] = env['OPENCLAW_STATE_DIR'] + '/.config'
env['XDG_DATA_HOME'] = env['OPENCLAW_STATE_DIR'] + '/.local/share'
# 提示符直接显示当前目录（由 shell 原生渲染）。
env['PS1'] = '\\w$ '
# 确保 openclaw 原生命令任意目录可用
env['PATH'] = '/var/packages/ainasclaw/target/bin:/var/packages/openclaw/target/bin:/usr/local/bin:' + env.get('PATH', '')
try:
    cli = '/var/packages/ainasclaw/target/bin/openclaw'
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
    with open(os.path.join(sdir, 'cwd.txt'), 'w', encoding='utf-8') as f:
        f.write(workspace_dir)
except Exception:
    pass
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
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"builtin terminal removed"}'
            exit 0
            ;;
        terminal_session_write_removed_backup)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "${APP_VAR_DIR}"
import errno, json, os, signal, sys
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
if not os.path.exists(pid_file):
    print(json.dumps({'ok': False, 'error': 'session not found'}, ensure_ascii=False)); raise SystemExit
try:
    pid = int((open(pid_file, 'r', encoding='utf-8').read() or '0').strip() or '0')
    os.kill(pid, 0)
except Exception:
    print(json.dumps({'ok': False, 'error': 'session not alive'}, ensure_ascii=False)); raise SystemExit

# 优先直写 shell 的控制终端（更接近 syno-terminal/真实 TTY 行为）
wrote = False
try:
    tty_path = os.readlink(f'/proc/{pid}/fd/0')
    fd_tty = os.open(tty_path, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(fd_tty, text.encode('utf-8', 'ignore'))
        wrote = True
    finally:
        os.close(fd_tty)
except Exception:
    wrote = False

# 回退：写 cmd fifo（兼容旧会话）
if (not wrote) and os.path.exists(cmd_fifo):
    try:
        fd = os.open(cmd_fifo, os.O_WRONLY | os.O_NONBLOCK)
        try:
            os.write(fd, text.encode('utf-8', 'ignore'))
            wrote = True
        finally:
            os.close(fd)
    except OSError as e:
        if e.errno not in (errno.ENXIO, errno.EPIPE):
            raise

if not wrote:
    print(json.dumps({'ok': False, 'error': 'relay not alive'}, ensure_ascii=False)); raise SystemExit

print(json.dumps({'ok': True}, ensure_ascii=False))
PY
            exit 0
            ;;
        terminal_exec_line)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"builtin terminal removed"}'
            exit 0
            ;;
        terminal_exec_line_removed_backup)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "${APP_VAR_DIR}"
import json, os, re, shlex, subprocess, sys
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
base = (sys.argv[2] if len(sys.argv) > 2 else '/tmp').rstrip('/')
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
sid = str(payload.get('sessionId') or '').strip()
line = str(payload.get('line') or '')
if not sid:
    print(json.dumps({'ok': False, 'error': 'missing sessionId'}, ensure_ascii=False)); raise SystemExit
if not line.strip():
    print(json.dumps({'ok': True, 'output': '', 'cwd': ''}, ensure_ascii=False)); raise SystemExit
sdir = os.path.join(base, 'terminal-sessions', sid)
cwd_file = os.path.join(sdir, 'cwd.txt')
cwd = '/volume1/openclaw'
try:
    if os.path.exists(cwd_file):
        cwd = (open(cwd_file, 'r', encoding='utf-8').read() or '').strip() or cwd
except Exception:
    pass

m = re.match(r'^\s*cd(?:\s+(.+))?\s*$', line)
if m:
    target = (m.group(1) or '~').strip()
    if target in ('', '~'):
        target = os.path.expanduser('~')
    else:
        try:
            target = shlex.split(target)[0]
        except Exception:
            target = target.strip('"\'')
        if not os.path.isabs(target):
            target = os.path.abspath(os.path.join(cwd, target))
    if os.path.isdir(target):
        cwd = target
        try:
            with open(cwd_file, 'w', encoding='utf-8') as f: f.write(cwd)
        except Exception:
            pass
        print(json.dumps({'ok': True, 'output': '', 'cwd': cwd, 'code': 0}, ensure_ascii=False)); raise SystemExit
    print(json.dumps({'ok': True, 'output': f'bash: cd: {target}: No such file or directory\n', 'cwd': cwd, 'code': 1}, ensure_ascii=False)); raise SystemExit

env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG'] = '0'
env['OPENCLAW_DATA_DIR'] = '/volume1/@appdata/ainasclaw/data'
state_dir = (os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw')
user_dir = (os.path.dirname(state_dir) if state_dir.endswith('/.openclaw') else state_dir)
env['HOME'] = user_dir
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = state_dir
env['OPENCLAW_WORKSPACE_DIR'] = user_dir
env['NPM_CONFIG_CACHE'] = state_dir + '/.npm'
env['XDG_CACHE_HOME'] = state_dir + '/.cache'
env['XDG_CONFIG_HOME'] = state_dir + '/.config'
env['XDG_DATA_HOME'] = state_dir + '/.local/share'
env['PATH'] = '/var/packages/ainasclaw/target/bin:/var/packages/openclaw/target/bin:/usr/local/bin:' + env.get('PATH','')

p = subprocess.run(['/bin/bash', '-lc', line], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
out = p.stdout or ''
print(json.dumps({'ok': True, 'output': out, 'cwd': cwd, 'code': int(p.returncode)}, ensure_ascii=False))
PY
            exit 0
            ;;
        terminal_session_read)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"builtin terminal removed"}'
            exit 0
            ;;
        terminal_session_read_removed_backup)
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
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"builtin terminal removed"}'
            exit 0
            ;;
        terminal_session_stop_removed_backup)
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
            python3 - <<'PY' "$body" "${CFG_FILE}" "${APP_VAR_DIR}/openclaw-gateway.spawn.log"
import json, os, subprocess, sys, time, fcntl
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
cfg = sys.argv[2] if len(sys.argv) > 2 else '/volume1/openclaw/.openclaw/openclaw.json'
spawn_log = sys.argv[3] if len(sys.argv) > 3 else '/tmp/openclaw-gateway.spawn.log'
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
action = (payload.get('action') or '').strip().lower()
if action not in ('start','stop','restart'):
    print(json.dumps({'ok': False, 'error': 'unsupported action'}, ensure_ascii=False)); raise SystemExit

req_workspace = str(payload.get('workspaceDir') or '').strip()
req_port_raw = payload.get('port')
req_port = 0
try:
    req_port = int(req_port_raw)
except Exception:
    req_port = 0
if req_workspace.endswith('/.openclaw'):
    req_workspace = req_workspace[:-10]
if req_workspace:
    ws_norm = ('/' + req_workspace.strip('/')).lower()
    if ws_norm.endswith('/.openclaw') or '/.openclaw/' in ws_norm:
        print(json.dumps({'ok': False, 'error': '用户目录不能包含 .openclaw（该名称为内部工作目录保留）'}, ensure_ascii=False)); raise SystemExit

# 安装向导：start/restart 支持一次性指定用户目录与端口。
if action in ('start', 'restart') and req_workspace:
    cfg = os.path.join(req_workspace, '.openclaw', 'openclaw.json')
    try:
        os.makedirs('/var/packages/ainasclaw/var', exist_ok=True)
        with open('/var/packages/ainasclaw/var/workspace.path', 'w', encoding='utf-8') as pf:
            pf.write('$HOME')
        with open('/var/packages/ainasclaw/var/workspace.home.path', 'w', encoding='utf-8') as hpf:
            hpf.write(req_workspace)
        # 非默认目录时，清理默认目录残留配置，避免被误判为当前配置。
        if req_workspace != '/volume1/openclaw':
            try:
                os.remove('/volume1/openclaw/.openclaw/openclaw.json')
            except Exception:
                pass
    except Exception:
        pass

# serialize install_run actions to avoid duplicate concurrent restarts causing double-spawn/port lock races
lock_path = '/var/packages/ainasclaw/var/install_run.lock'
os.makedirs(os.path.dirname(lock_path), exist_ok=True)
_lock_fp = open(lock_path, 'w')
try:
    fcntl.flock(_lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print(json.dumps({'ok': False, 'busy': True, 'error': 'another start/stop/restart is already running'}, ensure_ascii=False), flush=True)
    raise SystemExit

env = os.environ.copy()
env['OPENCLAW_USE_SYSTEM_CONFIG']='0'
env['OPENCLAW_DATA_DIR']='/volume1/@appdata/ainasclaw/data'
state_dir=(os.path.dirname(cfg) if cfg else '/volume1/openclaw/.openclaw')
workspace_root=(state_dir[:-10] if state_dir.endswith('/.openclaw') else '/volume1/openclaw')
env['HOME']=workspace_root
env['OPENCLAW_CONFIG_PATH']=cfg
env['OPENCLAW_STATE_DIR']=state_dir
env['OPENCLAW_WORKSPACE_DIR']=workspace_root
env['NPM_CONFIG_CACHE']=state_dir+'/.npm'
env['XDG_CACHE_HOME']=state_dir+'/.cache'
env['XDG_CONFIG_HOME']=state_dir+'/.config'
env['XDG_DATA_HOME']=state_dir+'/.local/share'
env['OPENCLAW_TOOLS_PROFILE']='full'
env['OPENCLAW_TOOLS_ELEVATED_ENABLED']='1'
env['OPENCLAW_ELEVATED_DEFAULT']='full'
env['OPENCLAW_EXEC_SECURITY_DEFAULT']='full'
# 避免 gateway run 以自愈/重生模式拉起，导致“停止 gateway”按钮失效。
env['OPENCLAW_NO_RESPAWN']='1'

initialized = False
# 默认端口：stop 分支也会用于 post-stop 检查，必须先定义。
try:
    c_port = json.load(open(cfg,'r',encoding='utf-8')) if cfg and os.path.exists(cfg) else {}
except Exception:
    c_port = {}
try:
    gw_port = int((((c_port.get('gateway') or {}).get('port')) or 0))
except Exception:
    gw_port = 0
if 1024 <= req_port <= 65535:
    gw_port = req_port
elif not (1024 <= gw_port <= 65535):
    gw_port = 58789

# On start/restart only, create runtime config if missing.
if action in ('start','restart'):
    try:
        if cfg and (not os.path.exists(cfg)):
            os.makedirs(os.path.dirname(cfg), exist_ok=True)
            template = '/var/packages/ainasclaw/target/app/openclaw/config/openclaw.template.json'
            if os.path.exists(template):
                c0 = json.load(open(template,'r',encoding='utf-8'))
            else:
                c0 = {}
            ws = os.path.dirname(os.path.dirname(cfg))
            state_path = os.path.dirname(cfg)
            c0.setdefault('agents', {}).setdefault('defaults', {})['workspace'] = state_path
            qmd = c0.setdefault('memory', {}).setdefault('qmd', {})
            paths = qmd.setdefault('paths', [])
            if not paths:
                paths.append({'path': state_path, 'name': 'workspace', 'pattern': '**/*.md'})
            elif isinstance(paths[0], dict):
                paths[0]['path'] = state_path
            with open(cfg,'w',encoding='utf-8') as wf:
                json.dump(c0,wf,ensure_ascii=False,indent=2); wf.write('\n')
            initialized = True
    except Exception:
        pass

if action in ('start','restart'):
    # 强制保持 LAN 可访问（44539）
    try:
        c = json.load(open(cfg,'r',encoding='utf-8')) if cfg and os.path.exists(cfg) else {}
    except Exception:
        c = {}
    gw = c.setdefault('gateway', {})
    gw['bind'] = 'lan'
    gw['mode'] = 'local'
    try:
        gw_port = int((((c.get('gateway') or {}).get('port')) or 0))
    except Exception:
        gw_port = 0
    if 1024 <= req_port <= 65535:
        gw_port = req_port
    elif not (1024 <= gw_port <= 65535):
        gw_port = 58789
    gw['port'] = gw_port
    cu = gw.setdefault('controlUi', {})
    cu['basePath'] = '/default'
    cu['allowInsecureAuth'] = True
    cu['dangerouslyDisableDeviceAuth'] = True
    cu['allowedOrigins'] = ['*']
    # 兼容清理：移除当前版本不支持的键，避免启动时报 Invalid config
    defs = c.setdefault('agents', {}).setdefault('defaults', {})
    defs['workspace'] = os.path.dirname(cfg) if cfg else '/volume1/openclaw/.openclaw'
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
            # 微信插件默认启用，避免渠道已配置但插件被禁用导致 doctor 报错。
            ent['enabled'] = True
            entries[pid] = ent
        plugins['entries'] = entries

        # 不在启动流程里强行重建/启用 channels，避免用户删除后的渠道在重启后“复活”。
        with open(cfg,'w',encoding='utf-8') as f2:
            json.dump(c,f2,ensure_ascii=False,indent=2); f2.write('\n')
    except Exception:
        pass

def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, (p.stdout or b'').decode('utf-8','ignore')
    except subprocess.TimeoutExpired as e:
        out = ''
        try:
            out = ((e.stdout or b'') + (e.stderr or b'')).decode('utf-8', 'ignore')
        except Exception:
            out = str(e)
        return 124, f'timeout: {out[-800:]}'
    except Exception as e:
        return 999, str(e)

def force_stop():
    out=[]
    # 1) prefer graceful gateway stop first (short timeout)
    try:
        rc, o = run(['/var/packages/ainasclaw/target/bin/openclaw','gateway','stop','--json'], timeout=12)
        out.append((['openclaw','gateway','stop','--json'], rc, o[-800:]))
    except Exception as e:
        out.append((['openclaw','gateway','stop','--json'], 999, str(e)))
    # 2) fallback precise kill patterns
    # 注意：不要使用 `pkill -f openclaw.*gateway`，否则会误杀当前 CGI python 进程
    # （其 argv 包含 openclaw-gateway.spawn.log 路径），导致接口空响应。
    for cmd in [
        ['pkill','-f','/var/packages/ainasclaw/target/bin/openclaw gateway run'],
        ['pkill','-f','/var/packages/ainasclaw/target/app/openclaw/dist/index.js gateway'],
        ['pkill','-f','^openclaw-gateway$'],
        ['pkill','-x','openclaw-gateway']
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
    # restart 语义由后续 start 分支完成（stop + start）。
    force = force_stop()
    logs.append({'cmd':('force-stop' if action == 'stop' else 'force-stop-restart'), 'out':str(force)[:1200]})
    time.sleep(1.0 if action == 'stop' else 1.2)

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
        os.makedirs(os.path.dirname(spawn_log), exist_ok=True)
        try:
            with open(spawn_log, 'a', encoding='utf-8') as sf:
                sf.write('[gateway-spawn] request start\n')
        except Exception:
            pass
        try:
            logf = open(spawn_log, 'ab', buffering=0)
        except Exception:
            logf = None
        p = subprocess.Popen(
            ['/var/packages/ainasclaw/target/bin/openclaw','gateway','run','--allow-unconfigured','--port',str(gw_port)],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=(logf if logf is not None else subprocess.DEVNULL),
            stderr=(logf if logf is not None else subprocess.DEVNULL),
            close_fds=True,
            start_new_session=True
        )
        logs.append({'cmd':'gateway(spawn-detached)','pid':p.pid})
        try:
            with open(spawn_log, 'a', encoding='utf-8') as sf:
                sf.write(f'[gateway-spawn] started pid={p.pid}\n')
        except Exception:
            pass
        time.sleep(3)
    except Exception as e:
        ok = False
        logs.append({'cmd':'gateway(spawn-detached)','error':str(e)})

import socket

def is_running(port=None):
    port = gw_port if port is None else port
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(0.6)
    try:
        s.connect(('127.0.0.1',port)); return True
    except Exception:
        return False
    finally:
        s.close()

running = is_running(gw_port)
if action in ('start','restart') and not running:
    for _ in range(12):
        time.sleep(1)
        running = is_running(gw_port)
        if running:
            break
if action == 'stop' and running:
    ok = False
    logs.append({'cmd':'post-stop-check','error':'gateway still running after stop sequence'})

# 同步 DSM 套件详情端口，确保 adminport/adminurl 与概览端口一致。
if action in ('start','restart') and running:
    try:
        rcp, o = run(['bash','-lc', 'source /var/packages/ainasclaw/scripts/service-setup >/dev/null 2>&1; sync_dsm_package_info_port "' + str(gw_port) + '"'], timeout=12)
        logs.append({'cmd':'sync_dsm_package_info_port', 'rc': rcp, 'out': (o or '')[-600:]})
    except Exception as e:
        logs.append({'cmd':'sync_dsm_package_info_port', 'error': str(e)})

print(json.dumps({'ok': ok, 'action': action, 'logs': logs, 'running': running, 'initialized': initialized}, ensure_ascii=False))
PY
            exit 0
            ;;
        logs)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            OCL_LOG="/tmp/openclaw/openclaw-$(date +%Y-%m-%d).log"
            [ -f "$OCL_LOG" ] || OCL_LOG="/tmp/openclaw/openclaw-$(date -d yesterday +%Y-%m-%d 2>/dev/null).log"
            [ -f "$OCL_LOG" ] || OCL_LOG="/tmp/openclaw-0/openclaw-$(date +%Y-%m-%d).log"
            [ -f "$OCL_LOG" ] || OCL_LOG="/tmp/openclaw-0/openclaw-$(date -d yesterday +%Y-%m-%d 2>/dev/null).log"
            APP_LOG="$LOG_FILE"
            SPAWN_LOG="${APP_VAR_DIR}/openclaw-gateway.spawn.log"
            [ -f "$SPAWN_LOG" ] || SPAWN_LOG="/tmp/openclaw-gateway.spawn.log"
            [ -f "$OCL_LOG" ] || touch "$OCL_LOG"
            [ -f "$APP_LOG" ] || touch "$APP_LOG"
            [ -f "$SPAWN_LOG" ] || touch "$SPAWN_LOG"
            merged=$( \
              printf '===== openclaw (gateway) :: %s =====\n' "$OCL_LOG"; tail -n 500 "$OCL_LOG" 2>/dev/null; \
              printf '\n===== ainasclaw app :: %s =====\n' "$APP_LOG"; tail -n 220 "$APP_LOG" 2>/dev/null; \
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
            /var/packages/ainasclaw/target/bin/node - <<'NODE' "$body" "$qr_encoded"
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
  const QRCode = require('/volume1/@appstore/ainasclaw/app/openclaw/node_modules/qrcode-terminal/vendor/QRCode');
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
  <title>AiNasClaw</title>
  <style>
    html, body { scroll-behavior: auto; overscroll-behavior: contain; height:100%; }
    body { margin:0; overflow:hidden; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif; background:#f5f6f8; color:#222; }
    body.modal-open { overflow: hidden; }
    .wrap { padding:10px; height:100%; box-sizing:border-box; zoom:.93; }
    .layout { height:100%; display:flex; gap:12px; }
    .sidebar { width:220px; min-width:220px; background:#fff; border:1px solid #dfe3ea; border-radius:12px; padding:12px; box-sizing:border-box; display:flex; flex-direction:column; }
    .title { font-size:20px; font-weight:700; margin:0 0 10px; }
    .sub { color:#667085; font-size:12px; margin:0 0 10px; }
    .tabs { display:flex; flex-direction:column; gap:6px; }
    .tab { text-align:left; border:1px solid #d0d5dd; background:#fff; border-radius:8px; padding:9px 10px; cursor:pointer; }
    .tab.active { background:#eaf2ff; color:#175cd3; border-color:#b7cdfa; font-weight:600; }
    .tab.disabled { opacity:1; cursor:pointer; }
    .main { min-width:0; flex:1; display:flex; }
    .panel { background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:14px; min-height:0; flex:1; display:flex; flex-direction:column; overflow:hidden; }
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
    @media (max-width: 900px) {
      .layout { flex-direction:column; }
      .sidebar { width:100%; min-width:0; }
      .tabs { flex-direction:row; flex-wrap:wrap; }
      .tab { min-width:120px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="layout">
      <aside class="sidebar">
        <div class="title">AiNasClaw</div>
        <div class="tabs">
          <button class="tab active" data-tab="status">概览</button>
          <button class="tab" data-tab="models">模型配置</button>
          <button class="tab" data-tab="channels">渠道配置</button>
          <button class="tab" data-tab="terminal">终端</button>
          <button class="tab" data-tab="logs">运行日志</button>
        </div>
      </aside>
      <main class="main">
        <div class="panel">
          <div id="msg" class="msg"></div>
          <div id="content"></div>
        </div>
      </main>
    </div>
  </div>

  <script>
    const API_BASE = '/webman/3rdparty/ainasclaw/index.cgi?native_api=1&action=';
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
    let logsAutoRefresh = true;
    let statusTimer = null;
    let installBusy = false;
    let installBusyAction = '';
    let terminalSessionId = '';
    let terminalOffset = 0;
    let terminalPollTimer = null;
    let terminalWriteQueue = Promise.resolve();
    let terminalSuggest = ['openclaw doctor', 'openclaw gateway status', 'openclaw gateway restart', 'openclaw config validate'];
    let terminalGlobalKeyHooked = false;
    let terminalLocked = false;
    window.__ainasclawClientErrors = [];

    function captureClientError(type, payload) {
      try {
        const rec = {
          ts: new Date().toISOString(),
          type,
          payload: payload || {}
        };
        window.__ainasclawClientErrors.push(rec);
        if (window.__ainasclawClientErrors.length > 50) window.__ainasclawClientErrors.shift();
        const text = JSON.stringify(rec);
        if (console && console.error) console.error('[ainasclaw-ui-error]', text);
        const merged = (rec.payload && (rec.payload.message || '')) + '\n' + (rec.payload && (rec.payload.stack || ''));
        if (/flexcroll|document\.write|asynchronously-loaded external script/i.test(merged)) {
          setMsg('检测到 DSM 内置 flexcroll 脚本兼容报错（document.write 异步限制）。已记录错误详情，可继续使用当前页面功能。', 'err');
        }
      } catch (_) {}
    }

    window.ainasclawClientErrors = function () {
      return (window.__ainasclawClientErrors || []).slice();
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
    function getTerminalTabButton() {
      return document.querySelector('.tab[data-tab="terminal"]');
    }
    function setTerminalTabDisabled(disabled) {
      const btn = getTerminalTabButton();
      if (!btn) return;
      btn.classList.toggle('disabled', !!disabled);
      btn.dataset.disabled = disabled ? '1' : '0';
      if (disabled) {
        btn.title = '外置 ttyd 不可用；输入补丁命令后可解锁终端';
      } else {
        btn.title = '';
      }
    }
    async function refreshTerminalHealth() {
      try {
        const h = await api('terminal_health');
        const available = !!(h && h.ok && h.available);
        terminalLocked = !available;
        setTerminalTabDisabled(!available);
      } catch (_) {
        terminalLocked = true;
        setTerminalTabDisabled(true);
      }
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
    function updateTerminalRepairBtnState() {
      const btn = document.getElementById('terminal_repair_btn');
      const userEl = document.getElementById('terminal_admin_user');
      const passEl = document.getElementById('terminal_admin_pass');
      if (!btn || !userEl || !passEl) return;
      const u = String(userEl.value || '').trim();
      const p = String(passEl.value || '');
      const halfFilled = (!!u && !p) || (!u && !!p);
      btn.disabled = halfFilled;
      btn.title = halfFilled ? '管理员账号和密码需同时填写，或都留空' : '';
    }
    async function unlockTerminalTab() {
      const adminUserEl = document.getElementById('terminal_admin_user');
      const adminPassEl = document.getElementById('terminal_admin_pass');
      const repairBtn = document.getElementById('terminal_repair_btn');
      const adminUser = String((adminUserEl && adminUserEl.value) || '').trim();
      const adminPassword = String((adminPassEl && adminPassEl.value) || '');
      const halfFilled = (!!adminUser && !adminPassword) || (!adminUser && !!adminPassword);
      if (halfFilled) {
        setMsg('请同时填写管理员账号和密码，或两项都留空后使用 sudo -n 路径。', 'err');
        return;
      }
      const forcePasswordFlow = !!(adminUser && adminPassword);
      const patchCmd = "sudo -n ln -sfn /var/packages/ainasclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && sudo -n sh -lc 'nginx -t && systemctl reload nginx'";
      const adminFixCmd = patchCmd;
      if (repairBtn) { repairBtn.disabled = true; repairBtn.textContent = '修复中...'; }
      setMsg('正在修复安装…');
      let ret = null;
      try {
        ret = await api('terminal_unlock', 'POST', { command: patchCmd, adminUser, adminPassword, forcePasswordFlow });
      } catch (e) {
        setMsg('修复安装失败：' + (e && e.message ? e.message : String(e)), 'err');
        if (repairBtn) { repairBtn.disabled = false; repairBtn.textContent = '修复安装'; }
        updateTerminalRepairBtnState();
        return;
      }
      if (adminPassEl) adminPassEl.value = '';
      if (!ret || !ret.ok) {
        const cmd = (ret && ret.adminFixCommand) || adminFixCmd;
        const detail = (ret && ret.logs) ? ('；日志：' + ret.logs) : '';
        setMsg('修复安装失败：' + ((ret && (ret.error || ret.message)) || 'unknown') + detail + '；若当前账号无 sudo 权限，请用管理员账号执行：' + cmd, 'err');
        if (repairBtn) { repairBtn.disabled = false; repairBtn.textContent = '修复安装'; }
        updateTerminalRepairBtnState();
        return;
      }
      if (ret && (ret.available === false || ret.portAvailable === false || ret.aliasAvailable === false)) {
        const cmd = (ret && ret.adminFixCommand) || adminFixCmd;
        const detail = (ret && ret.logs) ? ('；日志：' + ret.logs) : '';
        setMsg('修复执行完成，但检测仍未通过（port=' + String(!!ret.portAvailable) + ', alias=' + String(!!ret.aliasAvailable) + ', http=' + String(ret.aliasStatusCode || '-') + ')' + detail + '；请在 DSM SSH 执行：' + cmd, 'err');
        if (repairBtn) { repairBtn.disabled = false; repairBtn.textContent = '修复安装'; }
        updateTerminalRepairBtnState();
        return;
      }
      await refreshTerminalHealth();
      if (terminalLocked) {
        const cmd = (ret && ret.adminFixCommand) || adminFixCmd;
        const detail = (ret && ret.logs) ? ('；日志：' + ret.logs) : '';
        setMsg('修复安装完成，但终端仍不可用。请稍后重试；若仍失败，请用管理员账号执行：' + cmd + detail, 'err');
        if (repairBtn) { repairBtn.disabled = false; repairBtn.textContent = '修复安装'; }
        updateTerminalRepairBtnState();
        return;
      }
      setMsg('修复安装成功，终端已恢复。', 'ok');
      if (repairBtn) { repairBtn.disabled = false; repairBtn.textContent = '修复安装'; }
      updateTerminalRepairBtnState();
      await load('terminal');
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
          window.__ainasGatewayPort = data.port || 58789;
          window.__ainasGatewayToken = data.gatewayToken || '';
          const uptimeText = data.running ? formatUptime(data.uptimeSeconds || 0) : '-';
          const hostFix = (window.location && window.location.hostname) ? window.location.hostname : 'LAN_HOST';
          window.__statusWorkspaceDir = data.workspaceDir || '/volume1/openclaw';
          const rows = [
            ['实例 ID', data.instanceId || '-'],
            ['显示名', data.displayName || '-'],
            ['已安装', data.installed ? '是' : '否'],
            ['运行中', data.running ? '是' : '否'],
            ['Gateway 运行时间', uptimeText],
            ['版本', data.version || '-'],
            ['端口', data.port || '-'],
            ['代理路径', data.proxyBasePath || '-'],
            ['用户文件夹路径', data.workspaceDir || '/volume1/openclaw'],
            ['配置文件', data.configPath || '-'],
            ['binaryPath', data.binaryPath || '-']
          ];
          const runningText = data.running ? '运行中' : '已停止';
          content.innerHTML = ''
            + '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">'
            + '  <button class="btn" id="btn_oc_start" onclick="runInstallAction(\'start\')">启动 OpenClaw</button>'
            + '  <button class="btn" id="btn_oc_stop" onclick="runInstallAction(\'stop\')">停止 OpenClaw</button>'
            + '  <button class="btn primary" onclick="openOpenclawWeb()">打开 OpenClaw Web</button>'
            + '</div>'
            + '<div class="grid">' + rows.map(([k,v]) => {
                const vv = String(v == null ? '' : v).replace(/127\.0\.0\.1|localhost/g, hostFix);
                return '<div class="cellk">'+esc(k)+'</div><div class="cellv">'+esc(vv)+'</div>';
              }).join('') + '</div>';
          setMsg('运行状态：' + runningText, data.running ? 'ok' : 'err');
          window.__statusRunning = !!data.running;
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
              const nextPort = (s && s.port) || '-';
              const msgEl = document.getElementById('msg');
              if (msgEl) {
                msgEl.className = 'msg ' + (nextRunning ? 'ok' : 'err');
                msgEl.textContent = '运行状态：' + nextText;
              }
              window.__statusRunning = nextRunning;
              if (!installBusy) {
                setInstallButtonsBusy('', false);
              }
              const gridVals = document.querySelectorAll('.grid .cellv');
              if (gridVals && gridVals.length >= 7) {
                gridVals[3].textContent = nextRunning ? '是' : '否';
                gridVals[4].textContent = nextUptime;
                gridVals[6].textContent = String(nextPort);
              }
              window.__ainasGatewayPort = (s && s.port) || window.__ainasGatewayPort || 58789;
              window.__ainasGatewayToken = (s && s.gatewayToken) || window.__ainasGatewayToken || '';
            } catch (_) {}
          }, 1500);
          return;
        }
        if (tab === 'logs') {
          logsAutoRefresh = true;
          content.innerHTML = ''
            + '<div style="height:100%;display:flex;flex-direction:column;gap:8px;">'
            + '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">'
            + '    <div style="font-size:13px;color:#667085;">实时显示网关与套件日志（自动刷新）。</div>'
            + '    <div style="display:flex;gap:8px;">'
            + '      <button class="btn" onclick="refreshLogsNow(true)">刷新一次</button>'
            + '      <button class="btn" id="btn_logs_toggle" onclick="toggleLogsAutoRefresh()">停止刷新</button>'
            + '      <button class="btn" onclick="copyLogsText()">复制日志</button>'
            + '    </div>'
            + '  </div>'
            + '  <pre id="log_pre" style="flex:1;min-height:0;max-height:none;margin:0;">' + esc(data.log || '') + '</pre>'
            + '</div>';
          const pre = document.getElementById('log_pre');
          if (pre) pre.scrollTop = pre.scrollHeight;
          setMsg('');
          logsTimer = setInterval(() => refreshLogsNow(false), 2000);
          return;
        }

        if (tab === 'terminal') {
          const terminalUrl = resolveTerminalUrl();
          if (terminalLocked) {
            content.innerHTML = ''
              + '<div style="display:flex;flex-direction:column;gap:10px;max-width:760px;">'
              + '  <div style="font-size:14px;color:#667085;">终端需要root权限才可使用，请执行以下命令修复。</div>'
              + '  <div style="display:flex;gap:8px;align-items:center;">'
              + '    <input id="terminal_admin_user" oninput="updateTerminalRepairBtnState()" style="flex:1;height:34px;box-sizing:border-box;" placeholder="可选：管理员账号（无 sudo 时用于强制密码修复）">'
              + '    <input id="terminal_admin_pass" oninput="updateTerminalRepairBtnState()" type="password" style="flex:1;height:34px;box-sizing:border-box;" placeholder="可选：管理员密码">'
              + '    <button id="terminal_repair_btn" class="btn primary" style="height:34px;line-height:16px;" onclick="unlockTerminalTab()">修复安装</button>'
              + '  </div>'
              + '  <div style="font-size:12px;color:#667085;">修复命令（系统内置执行）：<code>sudo -n ln -sfn /var/packages/ainasclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && sudo -n sh -lc \'nginx -t && systemctl reload nginx\'</code></div>'
              + '</div>';
            setTimeout(updateTerminalRepairBtnState, 0);
            return;
          }

          const terminalReachable = await probeDsmTerminal(terminalUrl);
          if (!terminalReachable) {
            terminalLocked = true;
            setTerminalTabDisabled(true);
            content.innerHTML = ''
              + '<div style="display:flex;flex-direction:column;gap:10px;max-width:760px;">'
              + '  <div style="font-size:14px;color:#667085;">终端需要root权限才可使用，请执行以下命令修复。</div>'
              + '  <div style="display:flex;gap:8px;align-items:center;">'
              + '    <input id="terminal_admin_user" oninput="updateTerminalRepairBtnState()" style="flex:1;height:34px;box-sizing:border-box;" placeholder="可选：管理员账号（无 sudo 时用于强制密码修复）">'
              + '    <input id="terminal_admin_pass" oninput="updateTerminalRepairBtnState()" type="password" style="flex:1;height:34px;box-sizing:border-box;" placeholder="可选：管理员密码">'
              + '    <button id="terminal_repair_btn" class="btn primary" style="height:34px;line-height:16px;" onclick="unlockTerminalTab()">修复安装</button>'
              + '  </div>'
              + '  <div style="font-size:12px;color:#667085;">修复命令（系统内置执行）：<code>sudo -n ln -sfn /var/packages/ainasclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && sudo -n sh -lc \'nginx -t && systemctl reload nginx\'</code></div>'
              + '</div>';
            setMsg('终端连通性检测失败，请填写管理员账号和密码后点击“修复安装”，或执行下方命令手动修复。', 'err');
            setTimeout(updateTerminalRepairBtnState, 0);
            return;
          }

          content.innerHTML = ''
            + '<div style="display:flex;flex-direction:column;height:100%;gap:8px;">'
            + '  <div style="display:flex;justify-content:flex-end;align-items:center;gap:8px;">'
            + '    <button class="btn" onclick="refreshTerminalHealth().then(()=>load(\'terminal\'))">重试检测</button>'
            + '  </div>'
            + '  <div style="flex:1;min-height:0;border:1px solid #d0d5dd;border-radius:10px;overflow:hidden;background:#111827;">'
            + '    <iframe src="' + esc(terminalUrl) + '" style="width:100%;height:100%;border:none;"></iframe>'
            + '  </div>'
            + '</div>';
          setMsg('');
          return;
        }
        if (tab === 'models') {

          const providers = data.configuredProviders || [];
          const workspaceDir = data.workspaceDir || '/volume1/openclaw';
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
      if (!startBtn || !stopBtn) return;
      if (busy) {
        startBtn.disabled = true;
        stopBtn.disabled = true;
        startBtn.textContent = actionName === 'start' ? '启动中...' : '启动 OpenClaw';
        stopBtn.textContent = actionName === 'stop' ? '停止中...' : '停止 OpenClaw';
        return;
      }
      const running = !!window.__statusRunning;
      startBtn.disabled = running;
      stopBtn.disabled = !running;
      startBtn.textContent = '启动 OpenClaw';
      stopBtn.textContent = '停止 OpenClaw';
    }
    function setHotReloadBusy(busy) {
      setInstallButtonsBusy('', !!busy);
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
        let act;
        act = await api('install_run', 'POST', { method: 'bun', action: actionName });
        if (!act || typeof act !== 'object') {
          throw new Error('install_run 返回空结果');
        }
        if (actionName === 'start' && act && act.initialized) {
          setMsg('运行状态：正在初始化', 'ok');
        }
        // 仅保留“运行状态”提示，不显示其它文案。
        if (actionName === 'start' || actionName === 'stop') {
          const wantRunning = (actionName !== 'stop');
          const maxTries = 40; // 最多约 36s，覆盖重启后端口恢复慢的场景
          for (let i = 0; i < maxTries; i += 1) {
            await new Promise(r => setTimeout(r, 900));
            try {
              const s = await api('status');
              if (s && !!s.running === wantRunning) {
                setMsg('运行状态：' + (s.running ? '运行中' : '已停止'), s.running ? 'ok' : 'err');
                return;
              }
            } catch {}
          }
          return;
        }
      } catch (e) {
        // 保持当前页，不触发整页重绘。
      } finally {
        setInstallButtonsBusy('', false);
      }
    }
    function openInstallWizard() { setMsg('安装向导已移除。', 'ok'); }
    function closeInstallWizard() {}
    async function applyInstallWizard() {}
    function applyProviderPresetDialog() {
      const presetId = document.getElementById('dlg_provider_preset').value;
      // 用户要求：切换服务商时，先清空当前已选模型，再切到该服务商模型集。
      window.__modelOptionPool = [];
      setSelectedModelIdsToHidden([]);
      if (presetId === 'custom-openai') {
        document.getElementById('dlg_provider_id').value = 'custom-openai';
        document.getElementById('dlg_api').value = 'openai-completions';
        document.getElementById('dlg_base_url').value = 'http://127.0.0.1:8317/v1';
        const keyEl = document.getElementById('dlg_api_key');
        if (keyEl && !keyEl.value) keyEl.value = 'sk-V5zPkG6MJrIpxgmDw';
        setModelSelectOptions([], []);
        document.getElementById('dlg_model_ids').value = '';
        setMsg('已切换到 custom-openai 默认模板（已清空已选模型）', 'ok');
        return;
      }
      const preset = PROVIDER_PRESETS[presetId];
      if (!preset) return;
      document.getElementById('dlg_provider_id').value = presetId;
      document.getElementById('dlg_base_url').value = preset.baseUrl || '';
      document.getElementById('dlg_api').value = preset.api || 'openai-completions';
      const builtin = (preset.models || []).filter(Boolean);
      window.__modelOptionPool = builtin.slice();
      setModelSelectOptions(builtin, builtin);
      setMsg('已切换服务商并重置为该服务商模型列表', 'ok');
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
        const payload = { providers, applyNow: false };
        const ret = await api('models_save', 'POST', payload);
        setModelDialogHint((ret && ret.message) ? ret.message : '保存成功，重启 gateway 后生效', 'ok');
        closeModelDialog();
        await load('models');
        setMsg('模型服务器保存成功（未自动重启 gateway）', 'ok');
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
      setMsg('用户目录设置入口已移除，请使用安装向导。', 'ok');
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
      // 用户主动取消微信扫码时，立即撤销自动保存触发器。
      const wasActive = !!window.__weixinLoginActive;
      const wasConnected = !!window.__weixinConnected;
      const hadBefore = !!window.__weixinHadChannelBefore;
      window.__weixinLoginActive = false;
      window.__weixinAutoSaveArmed = false;
      if (__weixinPollTimer) {
        clearInterval(__weixinPollTimer);
        __weixinPollTimer = null;
      }
      // 若本次是新建微信通道流程且未连接就取消，清掉临时残留配置。
      if (wasActive && !wasConnected && !hadBefore) {
        api('channels_delete', 'POST', { id: 'openclaw-weixin' }).catch(() => {});
      }
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
        window.__weixinLoginActive = true;
        window.__weixinHadChannelBefore = !!((data.configuredChannelIds || []).includes('openclaw-weixin') || (data.configuredChannelIds || []).includes('weixin'));
        area.innerHTML = '<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;"><button id="btn_wx_start" class="btn" onclick="startWeixinLogin(false)">开始微信登录</button><button id="btn_wx_poll" class="btn" onclick="regenerateWeixinQr()">重新生成</button></div><div id="weixin_status" style="font-size:13px;color:#667085;margin-top:8px;"></div><div id="weixin_qr" style="margin-top:8px;"></div>';
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
        if (ret && ret.reloaded) setMsg('运行状态：配置已更新', 'ok');
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
        renderWeixinQrInline(dataUrl, qrUrl, qrEl, '请使用微信扫码完成登录');
      } catch (e) {
        console.error('[channels:weixin:inline-qr:error]', e);
        qrEl.innerHTML = '<div style="font-size:13px;color:#b42318;margin-bottom:8px;">二维码重绘失败：' + esc(e.message || e) + '</div><a class="btn" target="_blank" rel="noopener" href="' + esc(qrUrl) + '">新窗口打开二维码</a>';
        throw e;
      }
    }
    let __weixinPollTimer = null;
    function isWeixinDialogActive() {
      const m = document.getElementById('channelModalMask');
      const sel = document.getElementById('dlg_channel_type');
      return !!(m && m.style.display !== 'none' && sel && sel.value === 'openclaw-weixin');
    }
    async function startWeixinLogin(force) {
      const startTs = Date.now();
      // 新一轮登录开始：重置连接态，避免旧轮询导致“未刷新二维码就自动保存”。
      window.__weixinConnected = false;
      window.__weixinAutoSaveArmed = false;
      window.__weixinLoginActive = true;
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
          // 微信面板未展开时静默忽略，避免弹错误提示打断流程。
          return;
        }
        statusEl.textContent = '';
        qrEl.innerHTML = '';
        console.info('[channels:weixin:start] request login start');
        const data = await api('weixin_login_start', 'POST', { force: !!force });
        console.info('[channels:weixin:start:timing]', { elapsedMs: Date.now() - startTs, force: !!force });
        if (data && data.qrUrl) {
          if (!isWeixinDialogActive()) return;
          await renderWeixinQr(data.qrUrl, qrEl);
          statusEl.textContent = '';
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
          // 面板未展开时静默轮询，不弹错误。
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
        if (data.connected && window.__weixinAutoSaveArmed && window.__weixinLoginActive && isWeixinDialogActive()) {
          window.__weixinConnected = true;
          window.__weixinAutoSaveArmed = false;
          syncChannelSaveButtonState();
          if (__weixinPollTimer) {
            clearInterval(__weixinPollTimer);
            __weixinPollTimer = null;
          }
          setMsg('微信已连接，正在立即保存...', 'ok');
          if (statusEl) statusEl.textContent = '已连接，正在立即保存...';
          // 先立刻关闭弹窗并立即刷新渠道页，保存与热加载在后台串行执行，避免用户感知等待。
          closeChannelDialog();
          if (currentTab === 'channels') {
            load('channels').catch(() => {});
          }
          (async () => {
            try {
              // 第一步：立即落配置（不重载）
              const sv = await api('channels_save', 'POST', { weixin: { enabled: true }, noReload: true });
              if (sv && sv.error) throw new Error(sv.error);
              setMsg('微信已连接（已立即保存）', 'ok');
              // 第二步：后台再做热加载（不阻塞 UI）
              api('channels_save', 'POST', { weixin: { enabled: true } }).catch(() => {});
            } catch (e) {
              setMsg('微信已连接，但自动保存失败：' + (e.message || e), 'err');
            }
          })();
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
    async function refreshLogsNow(force) {
      if (!force && !logsAutoRefresh) return;
      try {
        const data = await api('logs');
        const pre = document.getElementById('log_pre');
        if (!pre) return;
        pre.textContent = data.log || '';
        pre.scrollTop = pre.scrollHeight;
      } catch (e) {}
    }
    function toggleLogsAutoRefresh() {
      logsAutoRefresh = !logsAutoRefresh;
      const btn = document.getElementById('btn_logs_toggle');
      if (btn) btn.textContent = logsAutoRefresh ? '停止刷新' : '开始刷新';
      setMsg(logsAutoRefresh ? '日志自动刷新：已开启' : '日志自动刷新：已停止', 'ok');
    }
    async function copyLogsText() {
      try {
        const pre = document.getElementById('log_pre');
        const allText = (pre && pre.textContent) ? pre.textContent : '';
        if (!allText) { setMsg('暂无可复制日志', 'err'); return; }

        // 优先复制用户当前选中文本；未选中时复制全部日志
        let text = '';
        try {
          const sel = window.getSelection ? window.getSelection() : null;
          text = sel ? String(sel.toString() || '') : '';
        } catch (_) {
          text = '';
        }
        if (!text) text = allText;

        // 优先 Clipboard API；失败则回退 execCommand，兼容 DSM iframe/旧浏览器权限模型
        let copied = false;
        if (navigator.clipboard && window.isSecureContext) {
          try {
            await navigator.clipboard.writeText(text);
            copied = true;
          } catch (_) {}
        }

        if (!copied) {
          const ta = document.createElement('textarea');
          ta.value = text;
          ta.setAttribute('readonly', 'readonly');
          ta.style.position = 'fixed';
          ta.style.left = '-99999px';
          ta.style.top = '0';
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          ta.setSelectionRange(0, ta.value.length);
          copied = !!document.execCommand('copy');
          document.body.removeChild(ta);
        }

        if (copied) {
          setMsg('日志已复制到剪贴板', 'ok');
        } else {
          setMsg('复制失败，请手动选择日志复制', 'err');
        }
      } catch (e) {
        setMsg('复制失败，请手动选择日志复制', 'err');
      }
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
    function isDsmPanelContext() {
      try {
        const p = String(window.location.pathname || '');
        return p.indexOf('/webman/3rdparty/ainasclaw/') === 0 || p.indexOf('/webman/index.cgi') === 0;
      } catch (_) {
        return false;
      }
    }
    function resolveTerminalUrl() {
      // 统一走 DSM nginx alias，避免 HTTPS 页面直连 HTTP:17682 触发混合内容拦截。
      return '/openclaw-terminal/';
    }
    function buildOpenclawWebUrl() {
      try {
        const protocol = window.location.protocol || 'https:';
        const host = window.location.hostname || '127.0.0.1';
        const port = Number(window.__ainasGatewayPort || 58789) || 58789;
        const token = String(window.__ainasGatewayToken || '').trim();
        const url = new URL(protocol + '//' + host + ':' + port + '/default/chat');
        if (token) url.searchParams.set('token', token);
        return url.toString();
      } catch (_) {
        return '/default/chat';
      }
    }
    function openOpenclawWeb() {
      const u = buildOpenclawWebUrl();
      try {
        window.open(u, '_blank', 'noopener');
        setMsg('已在新窗口打开 OpenClaw Web', 'ok');
      } catch (_) {
        window.location.href = u;
      }
    }
    async function probeDsmTerminal(url) {
      try {
        const u = url || resolveTerminalUrl();
        const target = new URL(u, window.location.href);
        // 跨域 URL（如 DSM 面板下直连 17682）fetch 探测会受 CORS/混合内容影响，不作为可用性判断。
        if (target.origin !== window.location.origin) return true;
        const r = await fetch(target.toString(), { method: 'GET', credentials: 'same-origin', cache: 'no-store' });
        return !!(r && r.ok);
      } catch (_) {
        return false;
      }
    }
    async function ensureTerminalSession() { return; }
    async function readTerminalOutput() { return; }
    function focusTerminal() { return; }
    function hookTerminalGlobalKeys() { return; }
    async function sendTerminalText(text) { return; }
    async function handleTerminalKey(ev) { return; }
    async function sendTerminalCtrlC() { return; }
    async function sendTerminalCtrlD() { return; }
    async function runTerminalRecoverCommand() { return; }
    async function runTerminalOneClickPatch() { return; }
    function clearTerminalView() { return; }
    async function restartTerminalSession() { return; }
    document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', (ev) => {
      if (btn.dataset && btn.dataset.tab === 'terminal' && btn.dataset.disabled === '1') {
        ev.preventDefault();
        setMsg('');
        load('terminal');
        return;
      }
      load(btn.dataset.tab);
    }));
    refreshTerminalHealth().finally(() => load('status'));
  </script>
</body>
</html>
HTML
