#!/bin/sh
APP_VAR_DIR="/var/packages/openclaw/var"
if [ -d "/volume1/@appdata/openclaw" ]; then
    APP_VAR_DIR="/volume1/@appdata/openclaw"
fi

LOG_FILE="${APP_VAR_DIR}/openclaw.log"
GATEWAY_PORT="58789"
QUERY="${QUERY_STRING:-}"

# ---- OpenClaw (container mode) HOME 布局 ----
# 所有 OpenClaw 文件位于安装向导确定的 HOME 基目录下（home-dir，兼容旧 data-dir）：
#   config    $HOME/.openclaw/openclaw.json
#             (= /home/node/.openclaw/openclaw.json inside the container)
#   workspace $HOME/.openclaw            (= /home/node/.openclaw inside container)
HOME_DIR="/volume1/openclaw"
if [ -r "${APP_VAR_DIR}/home-dir" ]; then
    d="$(cat "${APP_VAR_DIR}/home-dir" 2>/dev/null | tr -d '\r' | tr -d '\n')"
    [ -n "$d" ] && HOME_DIR="$d"
elif [ -r "${APP_VAR_DIR}/data-dir" ]; then
    d="$(cat "${APP_VAR_DIR}/data-dir" 2>/dev/null | tr -d '\r' | tr -d '\n')"
    [ -n "$d" ] && HOME_DIR="$d"
fi
CFG_FILE="${HOME_DIR}/.openclaw/openclaw.json"
WORKSPACE_DIR="${HOME_DIR}/.openclaw"
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
# 容器模式：gateway 是容器内 supervisor（PID 1）的子进程。优先用 sudo docker
# 读容器内 pidfile（/data/runtime/.gateway.pid）判定 gateway 存活；未授权（无
# sudo）时回退为对 host 端口的 socket 探活 —— 只有 gateway 真正监听时才连得
# 通；若容器已停（端口释放）或 docker-proxy 转发到已死进程，连接失败/立即关闭，
# 不会误报。这让未授权状态下概览页仍能显示真实运行状态。
def http_alive():
    try:
        s = socket.create_connection(('127.0.0.1', port), timeout=3)
        s.sendall(b'GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n')
        s.settimeout(3)
        data = s.recv(1)
        s.close()
        return len(data) > 0
    except Exception:
        return False

def gateway_running():
    try:
        r = subprocess.run(
            ['sudo', '-n', '/usr/local/bin/docker', 'exec', 'openclaw', 'sh', '-c',
             'p=$(cat /data/runtime/.gateway.pid 2>/dev/null); [ -n "$p" ] && kill -0 "$p" 2>/dev/null'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        if r.returncode == 0:
            return True
    except Exception:
        pass
    # 未授权（sudo 不可用）或 exec 失败：无 sudo 的 socket 探活兜底。
    return http_alive()
running = gateway_running()

# 套件运行态（独立于 gateway 端口探活）：用于按钮可用性判断。
# 目标：即便 gateway 进程异常，仍允许“停止 OpenClaw”按钮可点击。
try:
    r = subprocess.run([
        'sudo', '-n', '/usr/local/bin/docker', 'inspect', '-f', '{{.State.Running}}', 'openclaw'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=2)
    txt = (r.stdout or '').strip()
    low = txt.lower()
    service_running = ('true' in low) and ('false' not in low)
    if (not service_running) and txt.startswith('{'):
        try:
            j = json.loads(txt)
            service_running = str(j.get('status') or '').lower() == 'running'
        except Exception:
            pass
    if not service_running:
        # 未授权（sudo 不可用）：socket 探活兜底判断容器/网关可达。
        service_running = http_alive()
except Exception:
    service_running = http_alive()

# Fallback: 读取守护占位 pid（由 start-stop-status 维护）
if not service_running:
    try:
        pid_file = '/var/packages/openclaw/var/openclaw.pid'
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

try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_path and os.path.exists(cfg_path) else {}
except Exception:
    cfg = {}

# 计算 gateway 运行时长（秒）
# 关键：优先按“当前监听配置端口的真实进程 PID”来算，避免误命中 supervisor / 旧 pgrep 结果，
# 否则重启后概览页运行时间可能不归零。
def _first_int(text):
    for token in str(text or '').replace(',', ' ').split():
        if token.isdigit():
            return int(token)
    return None

def _pid_from_listening_port(port_value):
    if not isinstance(port_value, int) or port_value <= 0:
        return None
    commands = [
        ['sh', '-lc', f"ss -ltnp '( sport = :{port_value} )' 2>/dev/null | head -n 5"],
        ['sh', '-lc', f"netstat -ltnp 2>/dev/null | awk '$4 ~ /:{port_value}$/ {{print}}' | head -n 5"],
        ['sh', '-lc', f"lsof -nP -iTCP:{port_value} -sTCP:LISTEN 2>/dev/null | head -n 5"],
    ]
    for cmd in commands:
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1.5)
            txt = (r.stdout or '').strip()
            if not txt:
                continue
            for line in txt.splitlines():
                for part in line.split():
                    if '/openclaw' in part or '/node' in part or 'users:(("node",pid=' in part or 'LISTEN' in line:
                        pid = None
                        if 'pid=' in part:
                            pid = _first_int(part.split('pid=', 1)[1])
                        if pid is None:
                            pid = _first_int(part)
                        if pid is None and 'pid=' in line:
                            pid = _first_int(line.split('pid=', 1)[1])
                        if pid and os.path.exists(f'/proc/{pid}'):
                            return pid
        except Exception:
            continue
    return None

def _pid_from_gateway_process_name():
    try:
        r = subprocess.run(
            ['pgrep', '-x', 'openclaw-gatewa'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1.5,
        )
        for token in (r.stdout or '').split():
            if token.isdigit() and os.path.exists(f'/proc/{token}'):
                return int(token)
    except Exception:
        pass
    try:
        r = subprocess.run(
            ['sh', '-lc', "pgrep -af 'openclaw.*gateway|dist/index.js gateway' | grep -v 'app/fn-port/server' | head -n1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1.5,
        )
        line = (r.stdout or '').strip()
        if line:
            token = line.split(None, 1)[0]
            if token.isdigit() and os.path.exists(f'/proc/{token}'):
                return int(token)
    except Exception:
        pass
    return None

started_ts = None
uptime_seconds = 0
if running:
    try:
        # 优先以 runtime pid 文件的 mtime 作为“本次启动时间”，这样从停止到再次运行一定从 0 开始计时。
        pidfile_started_ts = None
        for pidfile in ('/var/packages/openclaw/var/openclaw-gateway.runtime.pid', '/volume1/openclaw/openclaw-gateway.runtime.pid'):
            if os.path.exists(pidfile):
                try:
                    pidfile_started_ts = int(os.stat(pidfile).st_mtime)
                    break
                except Exception:
                    pass
        if pidfile_started_ts:
            started_ts = pidfile_started_ts
            uptime_seconds = max(0, int(time.time()) - started_ts)
        else:
            pid = _pid_from_listening_port(port) or _pid_from_gateway_process_name()
            if pid:
                p2 = subprocess.run(
                    ['ps', '-o', 'etimes=', '-p', str(pid)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=1.5,
                )
                et = (p2.stdout or '').strip()
                if et.isdigit():
                    uptime_seconds = int(et)
                    started_ts = int(time.time()) - uptime_seconds
    except Exception:
        uptime_seconds = 0
        started_ts = None
workspace = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/openclaw')
if isinstance(workspace, str) and workspace.endswith('/.openclaw'):
    workspace = workspace[:-10]
# 版本实时读取：优先展示当前安装包 INFO 的 version（编译版本），回退到 app package.json。
spk_ver = ''
for p in ('/var/packages/openclaw/INFO', '/var/packages/openclaw/INFO'):
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
for p in ('/var/packages/openclaw/target/app/openclaw/package.json', '/var/packages/openclaw/target/app/openclaw/package.json'):
    try:
        if os.path.exists(p):
            j = json.load(open(p, 'r', encoding='utf-8'))
            app_ver = str(j.get('version') or '').strip()
            if app_ver:
                break
    except Exception:
        pass
version = spk_ver or app_ver or 'unknown'
# Container-mode CLI helper: the openclaw CLI lives inside the 'openclaw'
# container at /data/runtime/openclaw.mjs and is invoked via docker exec.
# Returns subprocess.CompletedProcess (rc, stdout+stderr in .stdout).
import shlex as _shlex
def run_openclaw_cmd(args, timeout=90):
    inner = 'cd /data/runtime && node openclaw.mjs ' + _shlex.quote(' '.join(args))
    return subprocess.run(
        ['docker', 'exec', 'openclaw', 'sh', '-c', inner],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
binary_path = 'docker exec openclaw node /data/runtime/openclaw.mjs'
gateway_token = (((cfg.get('gateway') or {}).get('auth') or {}).get('token'))
if isinstance(gateway_token, dict) and gateway_token.get('source') == 'file':
    try:
        provider = (((cfg.get('secrets') or {}).get('providers') or {}).get(gateway_token.get('provider')) or {})
        if provider.get('source') == 'file' and provider.get('path'):
            secret_value = json.load(open(provider['path'], 'r', encoding='utf-8'))
            for segment in str(gateway_token.get('id') or '').split('/'):
                if segment:
                    secret_value = secret_value[segment]
            gateway_token = secret_value
    except Exception:
        gateway_token = ''
gateway_token = gateway_token if isinstance(gateway_token, str) else ''

def get_config_val(cfg, *keys):
    try:
        v = cfg
        for k in keys:
            v = v[k]
        return v
    except (KeyError, TypeError, IndexError):
        return None

terminal_port = get_config_val(cfg, 'gateway', 'port') or 58789
# terminal ttyd port is 17682 by default, configured via openclaw-bundle.json
# but we hardcode it for now since the DSM UI panel doesn't need to read it from config
terminal_port = 17682

# Panel-operation authorization: can this CGI (http) run docker via sudo?
# Granted interactively by the 授权面板操作 flow (one-shot root scheduled task,
# SimplePermissionManager-style). Until then the panel is read-only.
def _auth_check():
    # 面板 CGI 以套件服务用户 sc-openclaw 运行（非 root）：无法 stat /etc/sudoers.d
    # （目录 750 root:root，文件不可见），文件存在性检查恒假。正确判定 = 直接探测
    # sc-openclaw 能否免密 sudo docker（正是 sudoers 规则授予的能力）。root CGI 平台
    # 才用 文件存在 + 嵌套 sudo 探测。
    try:
        if os.geteuid() == 0:
            if not os.path.exists('/etc/sudoers.d/openclaw-ui'):
                return False, '未找到 /etc/sudoers.d/openclaw-ui（面板操作未授权，请点击“授权面板操作”）'
            p = subprocess.run(['sudo', '-n', '-u', 'sc-openclaw', 'sudo', '-n',
                                '/usr/local/bin/docker', 'version'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
            if p.returncode == 0:
                return True, ''
            return False, 'sudoers 存在但 sc-openclaw 无法 sudo docker (rc=%s)' % p.returncode
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker', 'version'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
        if p.returncode == 0:
            return True, ''
        return False, '未授权：sc-openclaw 无法免密 sudo docker（面板操作未授权，请点击“授权面板操作”）'
    except Exception as e:
        return False, '授权检查异常: %s' % e

authorized, auth_error = _auth_check()
# Report who actually executes this CGI (uid). DSM's synoscgi runs webman
# 3rdparty app CGIs as ROOT (uid=0) — that is why the sudoers file is the real
# authorization gate (it constrains the non-root components), not the CGI's own
# sudo ability (root trivially "sudo"s anything).
_un = _u = None
try:
    import pwd
    _u = os.getuid()
    _un = pwd.getpwuid(_u).pw_name
except Exception:
    pass
out = {
  'instanceId': 'default',
  'displayName': 'Default Gateway',
  'running': running,
  'serviceRunning': service_running,
  'installed': True,
  'version': version,
  'cgiUser': _un,
  'cgiUid': _u,
  'port': port,
  'proxyBasePath': (((cfg.get('gateway') or {}).get('controlUi') or {}).get('basePath') or '/openclaw-web'),
  'workspaceDir': workspace,
  'configPath': cfg_path,
  'binaryPath': binary_path,
  'uptimeSeconds': uptime_seconds,
  'startedAt': started_ts,
  'gatewayPort': port,
  'terminalPort': terminal_port,
  'gatewayToken': gateway_token,
  'authorized': authorized,
  'authError': auth_error
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
read_error = ''
cfg_exists = bool(cfg_path and os.path.exists(cfg_path))
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_exists else {}
except Exception as e:
    cfg = {}
    read_error = f"{type(e).__name__}: {e}"
providers_map = ((cfg.get('models') or {}).get('providers') or {})

# Secrets store for provider SecretRefs ({"source":"file","id":"/models/providers/<pid>/apiKey"}).
# Resolve it up-front so the edit/sync dialog can show the real current API key
# when the provider apiKey is stored as a SecretRef (a dict), not only a plain
# string. Otherwise '手动同步到本地缓存' fires with an empty key and fails.
_SECRETS = {}
_state_dir = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/openclaw')
if _state_dir.endswith('/.openclaw'):
    _state_dir = _state_dir[:-len('/.openclaw')]
for _sp_cand in (os.path.join(_state_dir, '.openclaw', 'secrets.json'), os.path.join(_state_dir, 'secrets.json')):
    if os.path.exists(_sp_cand):
        try:
            _SECRETS = json.load(open(_sp_cand, 'r', encoding='utf-8')) or {}
        except Exception:
            _SECRETS = {}
        break


def _resolve_secret_ref(ref):
    """Resolve a file-backed SecretRef dict into its stored string value."""
    if not isinstance(ref, dict) or not ref.get('id'):
        return ''
    try:
        _seg = [s for s in str(ref.get('id')).split('/') if s]
        _t = _SECRETS
        for _k in _seg:
            if isinstance(_t, dict) and _k in _t:
                _t = _t[_k]
            else:
                return ''
        return _t if isinstance(_t, str) else ''
    except Exception:
        return ''

def default_model_for_provider(pid, cfg, kind):
    """Return the default model ref for a provider. The default text/image
    model is stored globally at agents.defaults.model/.imageModel (primary).
    When present, expose it to the edit dialog so it auto-fills from
    openclaw.json regardless of which provider owns it. Returns '' only
    when no default is configured."""
    try:
        defaults = (cfg.get('agents') or {}).get('defaults') or {}
        primary = defaults.get(kind)
        if isinstance(primary, dict):
            ref = str(primary.get('primary') or '').strip()
        elif isinstance(primary, str):
            ref = primary.strip()
        else:
            ref = ''
        return ref
    except Exception:
        return ''

providers = []
for pid, p in providers_map.items():
    if not isinstance(p, dict):
        continue
    item = {
        'id': pid,
        'displayName': p.get('displayName') or pid,
        'api': p.get('api') or 'openai-completions',
        'baseUrl': p.get('baseUrl') or '',
        'models': [],
        # Preserve configured metadata so manual models remain resolver-ready.
        'rawModels': p.get('models') if isinstance(p.get('models'), list) else [],
        'defaultTextModel': default_model_for_provider(p.get('id') or pid, cfg, 'model') or '',
        'defaultImageModel': default_model_for_provider(p.get('id') or pid, cfg, 'imageModel') or ''
    }
    if isinstance(p.get('apiKey'), str) and p.get('apiKey'):
        item['apiKeyMasked'] = '*' * min(16, max(8, len(p.get('apiKey'))))
        item['apiKeyRaw'] = p.get('apiKey')
    elif isinstance(p.get('apiKey'), dict):
        # SecretRef (e.g. {"source":"file","id":"/models/providers/<pid>/apiKey"})
        # points into the file-backed secrets store. Resolve it so the edit/sync
        # dialog receives the real key (apiKeyRaw) and a masked placeholder
        # (apiKeyMasked) — otherwise '手动同步到本地缓存' sends an empty key.
        _resolved = _resolve_secret_ref(p.get('apiKey'))
        if _resolved:
            item['apiKeyMasked'] = '*' * min(16, max(8, len(_resolved)))
            item['apiKeyRaw'] = _resolved
    for m in (p.get('models') or []):
        if isinstance(m, dict):
            mid = m.get('modelId') or m.get('id') or ''
            if mid:
                item['models'].append({'id': mid, 'modelId': mid})
    providers.append(item)
workspace_dir = (((cfg.get('agents') or {}).get('defaults') or {}).get('workspace') or '/volume1/openclaw')
if isinstance(workspace_dir, str) and workspace_dir.endswith('/.openclaw'):
    workspace_dir = workspace_dir[:-10]
print(json.dumps({'configuredProviders': providers, 'workspaceDir': workspace_dir, 'configPath': cfg_path, 'configExists': cfg_exists, 'readError': read_error}, ensure_ascii=False))
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
    _md_diag = '/tmp/ms_defaults_diag.log'
    _md_lines = []
    for _p in (payload.get('providers') or []):
        if isinstance(_p, dict):
            _md_lines.append('%s txt=%r img=%r' % (
                _p.get('id'), _p.get('defaultTextModel'), _p.get('defaultImageModel')))
    with open(_md_diag, 'a', encoding='utf-8') as _f:
        _f.write('%s SAVE providers:\n%s\n' % (
            __import__('time').strftime('%H:%M:%S'), '\n'.join(_md_lines) if _md_lines else '(none)'))
except Exception:
    pass
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

if not workspace_explicit and prev_workspace:
    # 前端保存模型/删除 provider 不传 workspaceDir：workspace 仅用于确定物理
    # 配置文件位置，配置内容中的 workspace 值必须保持原有（容器内
    # /home/node/.openclaw），绝不能反推为宿主路径写入——容器内网关读不到
    # /volume1/... 路径。
    workspace = prev_workspace

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

# 物理写入路径：仅当用户显式改目录（或缺少初始路径）时按 workspace 重算；
# 否则沿用面板传入的 cfg_file（宿主 HOME 下实际路径 /volume1/openclaw/
# .openclaw/openclaw.json），避免把容器路径 /home/node 当作物理位置去写
# （http 用户写不到容器内路径）。
if workspace_explicit or not cfg_path:
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
    ptr = '/var/packages/openclaw/var/workspace.path'
    home_ptr = '/var/packages/openclaw/var/workspace.home.path'
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
        'models': [],
        '_textDefault': (p.get('defaultTextModel') or '').strip(),
        '_imageDefault': (p.get('defaultImageModel') or '').strip(),
        # Keep the RAW default fields untouched so the backend can distinguish
        # 'omitted' (undefined / missing key) from 'explicit clear' (empty string)
        # and 'chosen model' (non-empty). The str() coercion below preserves that:
        # None stays unset, '' signals delete-intent, a value is a chosen model.
        'defaultTextModel': p.get('defaultTextModel'),
        'defaultImageModel': p.get('defaultImageModel')
    }
    # normalize None vs missing consistently: treat a non-string/None leniently so
    # the collection loop below and the main pipeline agree.
    _dtm_raw = provider['defaultTextModel']
    _dim_raw = provider['defaultImageModel']
    provider['defaultTextModel'] = _dtm_raw if isinstance(_dtm_raw, str) else None
    provider['defaultImageModel'] = _dim_raw if isinstance(_dim_raw, str) else None
    old_key = ''
    _existing_pv = existing_providers.get(pid)
    if isinstance(_existing_pv, dict):
        _ek = _existing_pv.get('apiKey')
        if isinstance(_ek, str):
            old_key = _ek.strip()
        elif isinstance(_ek, dict):
            # SecretRef: keep the reference so editing (masked key) does not drop it.
            old_key = _ek
    _old_key_ref = old_key if isinstance(old_key, dict) else (old_key if old_key else '')
    api_key = p.get('apiKey')
    if isinstance(api_key, str):
        key_trim = api_key.strip()
        if key_trim and set(key_trim) == {'*'}:
            if _old_key_ref:
                provider['apiKey'] = _old_key_ref
        elif key_trim:
            provider['apiKey'] = key_trim
        elif _old_key_ref:
            provider['apiKey'] = _old_key_ref
    elif _old_key_ref:
        provider['apiKey'] = _old_key_ref
    raw_models = p.get('rawModels') if isinstance(p.get('rawModels'), list) else []
    raw_by_id = {}
    for raw_model in raw_models:
        if not isinstance(raw_model, dict):
            continue
        raw_id = (raw_model.get('id') or raw_model.get('modelId') or '').strip()
        if raw_id:
            raw_by_id[raw_id] = raw_model
    for m in (p.get('models') or []):
        if not isinstance(m, dict):
            continue
        mid = (m.get('modelId') or m.get('id') or '').strip()
        if not mid:
            continue
        # Catalog-selected models retain their richer metadata. A manually
        # entered model gets the fields OpenClaw's resolver requires instead
        # of the old incomplete `{id,name}` entry.
        saved = dict(raw_by_id.get(mid) or {})
        saved['id'] = mid
        saved['name'] = str(saved.get('name') or (f"{pid} / {mid}"))
        saved.setdefault('contextWindow', 1048576)
        saved.setdefault('maxTokens', 16384)
        provider['models'].append(saved)
    providers_map[pid] = provider

# Always persist the (possibly empty) providers map, even for a delete that
# removes the last provider. If the payload has providers:[], the loop above
# never runs; without this assignment the existing providers would be kept and
# a deleted provider would reappear on reload.
cfg.setdefault('models', {})['providers'] = providers_map
os.makedirs(os.path.dirname(cfg_path), exist_ok=True)

# Set defaults.model / defaults.imageModel from provider config
try:
    defaults = cfg.setdefault('agents', {}).setdefault('defaults', {})
    text_refs = []
    image_refs = []
    img_clear_requested = False
    for pid, pv in providers_map.items():
        if not isinstance(pv, dict):
            continue
        # 文本默认：只在显式提交（字段存在且非空）时参与。未提交字段（省略）
        # 不参与默认决策。
        txt_f = pv.get('defaultTextModel')
        if isinstance(txt_f, str) and txt_f.strip():
            text_refs.append(txt_f.strip())
        # 图像默认：字段存在且非空 -> 候选；字段存在但为空 -> 显式删除请求；
        # 字段缺失（省略）-> 不参与（保留现有全局图像默认，不误删其它 provider）。
        img_f = pv.get('defaultImageModel')
        if img_f is not None:
            img_v = str(img_f).strip()
            if img_v:
                image_refs.append(img_v)
            else:
                img_clear_requested = True
    # Normalize defaults to OpenClaw's canonical provider/model format (split on
    # first '/'). A bare model id like "deepseek-v4-flash" is stored without a
    # provider prefix, while image default may carry it — keep both consistent so
    # the edit dialog matches them the same way.
    def _normalize_ref(ref):
        ref = ref.strip()
        if not ref:
            return ref
        # If the leading path segment is an already-configured provider id, the
        # ref is already fully qualified (provider/id) — keep it. We must NOT
        # treat 'contains /' as 'already prefixed': a model id may itself contain
        # '/' (e.g. siliconflow 'Qwen/Qwen3-VL-32B-Instruct'); OpenClaw still
        # wants provider/model, i.e. siliconflow/Qwen/Qwen3-VL-32B-Instruct.
        _known = set(str(_p).strip() for _p in providers_map.keys())
        if ref.split('/')[0] in _known:
            return ref
        # bare/partial id: prepend the provider that owns it (first match, incl.
        # model ids that contain '/').
        for _pid, _pv in providers_map.items():
            for _m in (_pv.get('models') or []):
                if isinstance(_m, dict) and str(_m.get('modelId') or _m.get('id') or '') == ref:
                    ref = "%s/%s" % (_pid, ref)
                    return ref
        return ref
    if text_refs:
        defaults['model'] = {'primary': _normalize_ref(text_refs[0])}
    if image_refs:
        dim_ref = image_refs[0]
        # Normalize the image default to provider/model too (a model id may itself
        # contain '/', e.g. siliconflow Qwen/Qwen3-VL-32B-Instruct => the ref must
        # become siliconflow/Qwen/Qwen3-VL-32B-Instruct).
        # NOTE: do NOT clear/guard here when image default equals text default.
        # That would break multimodal providers where the same model is used for
        # both text and image defaults. Just persist what the operator set; the
        # frontend __imageDefaultCleared intent handles actual clearing.
        defaults['imageModel'] = {'primary': _normalize_ref(dim_ref)}
        # Auto-add image input support for the default image model
        for pid2, pv2 in providers_map.items():
            if not isinstance(pv2, dict):
                continue
            for m in (pv2.get('models') or []):
                if not isinstance(m, dict):
                    continue
                mid = m.get('modelId') or m.get('id') or ''
                full_ref = (pv2.get('id') or pid2) + '/' + mid
                if full_ref == dim_ref or mid == dim_ref:
                    inp = m.setdefault('input', ['text'])
                    if 'image' not in inp:
                        inp.append('image')
                    break
    elif img_clear_requested:
        # 显式清空默认图像模型（用户选'无'并提交空）：
        # 移除 imageModel 残留，并删除之前为支持图片而加进模型的 input 里的
        # 'image'，恢复纯文本，避免模型被误标为支持图片而发 image_url 报 400。
        defaults['imageModel'] = {'primary': ''}
        for pid2, pv2 in providers_map.items():
            if not isinstance(pv2, dict):
                continue
            for m in (pv2.get('models') or []):
                if not isinstance(m, dict):
                    continue
                _inp = m.get('input')
                if isinstance(_inp, list) and 'image' in _inp:
                    _inp2 = [x for x in _inp if x != 'image']
                    if _inp2:
                        m['input'] = _inp2
                    else:
                        m.pop('input', None)
    else:
        # 没有图像默认提交，且无显式删除请求：保留现有全局 imageModel 不变
        # （编辑无关 provider 时不会误删其它 provider 的图像默认）。
        pass
except Exception:
    pass

# Hard backend guarantee: only clear the image default when the operator
# EXPLICITLY requested deletion in this save (submitted an empty image default).
# Without that, preserve the existing global image default — editing an unrelated
# provider must NOT clear another provider's image default.
try:
    defaults = cfg.setdefault('agents', {}).setdefault('defaults', {})
    if img_clear_requested:
        defaults['imageModel'] = {'primary': ''}
except Exception:
    pass

# user requirement: changing workspace should initialize by defaults only (no migration)
if (not os.path.exists(cfg_path)) and os.path.exists('/var/packages/openclaw/target/app/openclaw/config/openclaw.template.json'):
    try:
        cfg = json.load(open('/var/packages/openclaw/target/app/openclaw/config/openclaw.template.json', 'r', encoding='utf-8'))
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

# DeepSeek V4: selected models get thinking=xhigh; visible reasoning applies when V4 is the primary model.
try:
    import re
    defaults = cfg.setdefault('agents', {}).setdefault('defaults', {})
    model_defaults = defaults.get('models')
    if not isinstance(model_defaults, dict):
        model_defaults = {}
    active_refs = []
    for pid, pv in providers_map.items():
        if not isinstance(pv, dict):
            continue
        for m in (pv.get('models') or []):
            if not isinstance(m, dict):
                continue
            mid = str(m.get('id') or m.get('modelId') or '').strip()
            if mid:
                active_refs.append(f'{pid}/{mid}')
    active_set = set(active_refs)
    # Prune stale defaults.models entries that no longer match any current
    # provider/model reference (e.g. leftover keys from providers removed during
    # a previous delete or a provider whose model list shrank).
    for key in list(model_defaults.keys()):
        if key not in active_set:
            model_defaults.pop(key, None)
    for ref in active_refs:
        ref_key = ref.strip()
        if re.search(r'(?:^|/)deepseek-v4-(?:flash|pro)$', ref_key.lower().split('@', 1)[0]):
            ent = model_defaults.get(ref_key)
            if not isinstance(ent, dict):
                ent = {}
            params = ent.get('params')
            if not isinstance(params, dict):
                params = {}
            params['thinking'] = 'xhigh'
            ent['params'] = params
            model_defaults[ref_key] = ent
    if model_defaults:
        defaults['models'] = model_defaults
    # Sanitize default primary refs: if they point to a model that no longer
    # exists after deletion, drop the primary (gateway will auto-pick) instead
    # of leaving a dangling reference.
    def _valid_ref(value):
        v = str(value or '').strip().lower().split('@', 1)[0]
        if not v:
            return False
        base = v.split('/')[-1]
        for av in active_refs:
            a = av.strip().lower().split('@', 1)[0]
            if a == v or a.split('/')[-1] == base:
                return True
        return False
    for _k in ('model', 'imageModel'):
        _d = defaults.get(_k)
        if isinstance(_d, dict):
            if not _valid_ref(_d.get('primary')):
                if _k == 'model' and active_refs:
                    # text default: keep one (fall back to first model)
                    _d['primary'] = active_refs[0]
                else:
                    # image default: an empty/invalid value must stay unset — do
                    # NOT auto-fill with the first provider model (that is why the
                    # cleared image default kept coming back as deepseek-v4-flash).
                    _d.pop('primary', None)
        elif isinstance(_d, str) and not _valid_ref(_d):
            if _k == 'model' and active_refs:
                defaults[_k] = {'primary': active_refs[0]}
            else:
                defaults.pop(_k, None)
    default_model = defaults.get('model')
    if isinstance(default_model, str):
        default_model_ref = default_model.strip().lower()
    elif isinstance(default_model, dict):
        default_model_ref = str(default_model.get('primary') or '').strip().lower()
    else:
        default_model_ref = ''
    if not default_model_ref and active_refs:
        default_model_ref = active_refs[0].strip().lower()
    default_model_ref = default_model_ref.split('@', 1)[0]
    if re.search(r'(?:^|/)deepseek-v4-(?:flash|pro)$', default_model_ref):
        defaults['thinkingDefault'] = 'xhigh'
        defaults['reasoningDefault'] = 'stream'
except Exception:
    pass

# Strip transient provider fields before writing to config
for _pid in list(providers_map.keys()):
    _pv = providers_map.get(_pid)
    if isinstance(_pv, dict):
        _pv.pop('_textDefault', None)
        _pv.pop('_imageDefault', None)
        _pv.pop('defaultTextModel', None)
        _pv.pop('defaultImageModel', None)

# Migrate plaintext provider apiKeys into the private file-backed SecretRef
# store (cfg.secrets.providers.openclaw), so openclaw doctor reports no
# 'plaintext secret-bearing config fields' after adding/editing a provider.
try:
    secrets_path = ''
    _ain = (((cfg.get('secrets') or {}).get('providers') or {}).get('openclaw') or {})
    if _ain.get('source') == 'file' and _ain.get('path'):
        secrets_path = _ain['path']
    if not secrets_path:
        secrets_path = os.path.join(os.path.dirname(cfg_path), 'secrets.json')
    _sec = {}
    try:
        if os.path.exists(secrets_path):
            _sec = json.load(open(secrets_path, 'r', encoding='utf-8'))
            if not isinstance(_sec, dict):
                _sec = {}
    except Exception:
        _sec = {}
    _def_ref = lambda _ptr: {'source': 'file', 'provider': 'openclaw', 'id': _ptr}
    # helper inline
    def _store(pointer, value):
        cur = _sec
        parts = [p for p in pointer.split('/') if p]
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = value
    _changed = False
    for _pname, _pvmap in providers_map.items():
        _k = _pvmap.get('apiKey') if isinstance(_pvmap, dict) else None
        if isinstance(_k, str) and _k.strip() and not (set(_k.strip()) == {'*'}):
            _esc = _pname.replace('~', '~0').replace('/', '~1')
            _ptr = '/models/providers/' + _esc + '/apiKey'
            _store(_ptr, _k.strip())
            _pvmap['apiKey'] = _def_ref(_ptr)
            _changed = True
        elif isinstance(_k, dict) and _k.get('id'):
            # already a ref; ensure value exists in secrets store
            _ptr = _k.get('id')
            _pth = _ptr.split('/')
            cur = _sec
            for p in _pth[1:]:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    cur = None
                    break
            if cur is None:
                # recoverable only if... skip; leave as-is
                pass
    # migrate channel appSecrets (feishu) into the same store
    _facc = (((cfg.get('channels') or {}).get('feishu') or {}).get('accounts') or {})
    for _aid, _acct in _facc.items():
        if isinstance(_acct, dict) and isinstance(_acct.get('appSecret'), str) and _acct.get('appSecret').strip():
            _esc_a = _aid.replace('~', '~0').replace('/', '~1')
            _ptr2 = '/channels/feishu/accounts/' + _esc_a + '/appSecret'
            _store(_ptr2, _acct['appSecret'].strip())
            _acct['appSecret'] = _def_ref(_ptr2)
            _changed = True
    if _changed:
        os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
        cfg.setdefault('secrets', {}).setdefault('providers', {})['openclaw'] = {
            'source': 'file', 'path': secrets_path, 'mode': 'json'
        }
        with open(secrets_path, 'w', encoding='utf-8') as _sf:
            json.dump(_sec, _sf, ensure_ascii=False, indent=2)
        try:
            os.chmod(secrets_path, 0o600)
        except Exception:
            pass
except Exception:
    pass

with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')

try:
    _md_final = (cfg.get('agents') or {}).get('defaults') or {}
    with open('/tmp/ms_defaults_diag.log', 'a', encoding='utf-8') as _f:
        _f.write('  -> WRITTEN model=%r imageModel=%r\n' % (
            _md_final.get('model'), _md_final.get('imageModel')))
except Exception:
    pass

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
            'bash -lc "source /var/packages/openclaw/scripts/service-setup >/dev/null 2>&1; '
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

# OpenClaw owns skill publication. The UI only cleans obsolete workspace plugin
# copies and never creates a competing skills/_bundled tree.
state_dir = os.path.dirname(cfg_path) if cfg_path else os.path.join(workspace or '/volume1/openclaw', '.openclaw')
ext_dir = os.path.join(state_dir, 'extensions')
os.makedirs(ext_dir, exist_ok=True)
import shutil
shutil.rmtree(os.path.join(state_dir, 'plugin-skills'), ignore_errors=True)
shutil.rmtree(os.path.join(state_dir, 'skills', 'plugin-skills'), ignore_errors=True)

# keep workspace/extensions free of channel plugin copies (DSM trust checks may block uid!=0).
# channel plugins are staged under app/dist/extensions by service script.
for pkg_name in ['feishu', 'feishu-openclaw-plugin', 'wecom', 'qqbot', 'openclaw-qqbot']:
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
            'export SYNOPKG_PKGNAME=openclaw; '
            'export SYNOPKG_DSM_VERSION_MAJOR=7; '
            'export SYNOPKG_PKGDEST=/var/packages/openclaw/target; '
            'export SYNOPKG_PKGVAR=/var/packages/openclaw/var; '
            'source /var/packages/openclaw/scripts/service-setup >/dev/null 2>&1; '
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
ptr_val = ''
hptr_val = ''
try:
    ptr_val = (open('/var/packages/openclaw/var/workspace.path', 'r', encoding='utf-8').read() or '').strip()
except Exception:
    pass
try:
    hptr_val = (open('/var/packages/openclaw/var/workspace.home.path', 'r', encoding='utf-8').read() or '').strip()
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
    # Container mode: the gateway runs inside the docker container 'openclaw',
    # managed by Container Manager. Restarting the container via docker restart.
    # restarts the container, which reloads the config from the bind-mounted
    # openclaw.json. We do NOT spawn/stop the gateway process here.
    try:
        import subprocess, time, socket
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

        restart_rc = -1
        restart_out = ''
        try:
            p = subprocess.run(
                ['sudo', '-n', '/usr/local/bin/docker', 'restart', 'openclaw'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            restart_rc = p.returncode
            restart_out = (p.stdout or b'').decode('utf-8', 'ignore')[-600:]
        except Exception as e:
            restart_out = '%s: %s' % (type(e).__name__, e)

        out['gatewayAutoStartTriggered'] = True
        out['gatewayRestartRc'] = restart_rc
        out['gatewayRestartOut'] = restart_out
        # Wait for the container's gateway to come back up on gw_port.
        running = False
        for _ in range(30):
            if is_running(gw_port):
                running = True
                break
            time.sleep(1)
        out['gatewayRunning'] = running
        out['message'] = '配置已保存并重启网关' if restart_rc == 0 else '配置已保存，但网关重启未返回成功'
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
headers = {'User-Agent': 'openclaw-native-ui/1.0'}
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
headers = {'User-Agent': 'openclaw-native-ui/1.0'}
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
read_error = ''
cfg_exists = bool(cfg_path and os.path.exists(cfg_path))
try:
    cfg = json.load(open(cfg_path, 'r', encoding='utf-8')) if cfg_exists else {}
except Exception as e:
    cfg = {}
    read_error = f"{type(e).__name__}: {e}"
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
  'configExists': cfg_exists,
  'readError': read_error,
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

# 保存渠道时，自动补齐插件 allow/entries（完整权限），避免插件未加载导致渠道不可用。
plugins = cfg.setdefault('plugins', {})
plugins['enabled'] = True
plugins.pop('bundledDiscovery', None)
allow = plugins.get('allow')
if not isinstance(allow, list):
    allow = []
entries = plugins.get('entries')
if not isinstance(entries, dict):
    entries = {}

if isinstance(payload.get('feishu'), dict):
    app_id = (payload['feishu'].get('appId') or '').strip()
    app_secret = (payload['feishu'].get('appSecret') or '').strip()
    has_cred = bool(app_id and app_secret)
    if has_cred:
        f = ch.setdefault('feishu', {})
        f.setdefault('defaultAccount', 'default')
        ac = f.setdefault('accounts', {}).setdefault(f['defaultAccount'], {})
        ac['appId'] = app_id
        ac['appSecret'] = app_secret
        f['dmPolicy'] = 'open'; f['groupPolicy'] = 'open'; f['allowFrom'] = ['*']; f['enabled'] = True
    else:
        # Empty/partial Feishu input should not leave a half-configured shell behind.
        ch.pop('feishu', None)
if isinstance(payload.get('wecom'), dict):
    bot_id = (payload['wecom'].get('botId') or '').strip()
    sec = (payload['wecom'].get('secret') or '').strip()
    has_cred = bool(bot_id and sec)
    if has_cred:
        w = ch.setdefault('wecom', {})
        w['botId'] = bot_id
        w['secret'] = sec
        w['enabled'] = True
        w['dmPolicy'] = 'open'; w['groupPolicy'] = 'open'; w['allowFrom'] = ['*']
        # SPK guardrails: avoid dynamic agent/config churn that can trigger gateway restarts.
        w['agentId'] = 'main'
        dyn = w.get('dynamicAgents') if isinstance(w.get('dynamicAgents'), dict) else {}
        dyn['enabled'] = False
        dyn['adminBypass'] = False
        w['dynamicAgents'] = dyn
        dm = w.get('dm') if isinstance(w.get('dm'), dict) else {}
        dm['createAgentOnFirstMessage'] = False
        w['dm'] = dm
        # 保存企业微信后默认启用 wecom 插件，避免 doctor 报 channels.wecom 已配置但插件 disabled。
        if 'wecom' not in allow:
            allow.append('wecom')
        we = entries.get('wecom')
        if not isinstance(we, dict):
            we = {}
        we['enabled'] = True
        if isinstance(we.get('config'), dict):
            we.pop('config', None)
        entries['wecom'] = we
    else:
        # Empty/partial WeCom input should not leave a half-configured shell behind.
        ch.pop('wecom', None)
if False and isinstance(payload.get('dingtalk'), dict):
    cid = (payload['dingtalk'].get('clientId') or '').strip()
    csec = (payload['dingtalk'].get('clientSecret') or '').strip()
    has_cred = bool(cid and csec)
    if has_cred:
        d = ch.setdefault('dingtalk', {})
        d['clientId'] = cid
        d['clientSecret'] = csec
        d['enabled'] = True; d['dmPolicy'] = 'open'; d['groupPolicy'] = 'open'; d['allowFrom'] = ['*']
    else:
        # Empty/partial DingTalk input should not leave a half-configured shell behind.
        ch.pop('dingtalk', None)
if isinstance(payload.get('qqbot'), dict):
    aid = (payload['qqbot'].get('appId') or '').strip()
    sec = (payload['qqbot'].get('clientSecret') or '').strip()
    has_cred = bool(aid and sec)
    if has_cred:
        q = ch.setdefault('qqbot', {})
        q['appId'] = aid
        q['clientSecret'] = sec
        q['enabled'] = True; q['dmPolicy']='open'; q['groupPolicy']='open'; q['allowFrom']=['*']
    else:
        # Empty/partial QQBot input should not leave a half-configured shell behind.
        ch.pop('qqbot', None)
wx_payload = None
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

channel_plugin_map = {
    'feishu': ['feishu'],
    'qqbot': ['qqbot'],
    'dingtalk': ['dingtalk'],
    'wecom': ['wecom'],
    'openclaw-weixin': ['openclaw-weixin'],
    'weixin': ['openclaw-weixin']
}
for cid, cv in (ch or {}).items():
    enabled = True
    if isinstance(cv, dict):
        enabled = bool(cv.get('enabled', True))
    if not enabled:
        continue
    pids = channel_plugin_map.get(cid)
    if not pids:
        continue
    if isinstance(pids, str):
        pids = [pids]
    for pid in pids:
        if not isinstance(pid, str) or not pid.strip():
            continue
        pid = pid.strip()
        if pid not in allow:
            allow.append(pid)
        e = entries.get(pid)
        if not isinstance(e, dict):
            e = {}
        e['enabled'] = True
        # 渠道保存时仅触发渠道级热更新，不要把 provider/plugin 细项写入，
        # 否则 gateway 会判定为“需要整网关重启”。
        if isinstance(e.get('config'), dict):
            e.pop('config', None)
        entries[pid] = e

stale_plugin_ids = {'feishu-openclaw-plugin', 'openclaw-qqbot', 'wecom-openclaw-plugin'}
allow = [pid for pid in allow if pid not in stale_plugin_ids]
for pid in stale_plugin_ids:
    entries.pop(pid, None)
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

# Migrate plaintext channel credentials into the private file-backed SecretRef
# store so openclaw doctor reports no 'plaintext secret-bearing config fields'.
try:
    secrets_path = ''
    _ain = (((cfg.get('secrets') or {}).get('providers') or {}).get('openclaw') or {})
    if _ain.get('source') == 'file' and _ain.get('path'):
        secrets_path = _ain['path']
    if not secrets_path:
        secrets_path = os.path.join(os.path.dirname(cfg_path), 'secrets.json')
    _sec = {}
    try:
        if os.path.exists(secrets_path):
            _sec = json.load(open(secrets_path, 'r', encoding='utf-8'))
            if not isinstance(_sec, dict):
                _sec = {}
    except Exception:
        _sec = {}
    def _store(pointer, value):
        cur = _sec
        parts = [p for p in pointer.split('/') if p]
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = value
    def _def_ref(ptr):
        return {'source': 'file', 'provider': 'openclaw', 'id': ptr}
    def _migr(obj, base_ptr, field):
        # returns True if migrated
        v = obj.get(field)
        if isinstance(v, str) and v.strip():
            _store(base_ptr, v.strip())
            obj[field] = _def_ref(base_ptr)
            return True
        return False
    _ch_changed = False
    _ch = ch or {}
    _f = _ch.get('feishu')
    if isinstance(_f, dict):
        # top-level feishu.appSecret
        if _migr(_f, '/channels/feishu/appSecret', 'appSecret'):
            _ch_changed = True
        for _aid, _acct in ((_f.get('accounts') or {}).items() or []):
            if isinstance(_acct, dict):
                _ea = _aid.replace('~','~0').replace('/','~1')
                if _migr(_acct, '/channels/feishu/accounts/'+_ea+'/appSecret', 'appSecret'):
                    _ch_changed = True
    # dingtalk.clientSecret supports SecretRef (anyOf string|ref)
    _d = _ch.get('dingtalk')
    if isinstance(_d, dict):
        if _migr(_d, '/channels/dingtalk/clientSecret', 'clientSecret'):
            _ch_changed = True
    # NOTE: qqbot.clientSecret and wecom.secret are schema type=string ONLY
    # (no SecretRef variant) — they must stay plaintext, so they are NOT
    # migrated here.
    if _ch_changed:
        os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
        cfg.setdefault('secrets', {}).setdefault('providers', {})['openclaw'] = {
            'source': 'file', 'path': secrets_path, 'mode': 'json'
        }
        with open(secrets_path, 'w', encoding='utf-8') as _sf:
            json.dump(_sec, _sf, ensure_ascii=False, indent=2)
        try:
            os.chmod(secrets_path, 0o600)
        except Exception:
            pass
except Exception:
    pass

os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')

# 保存渠道后：若 gateway 正在运行则热重载；若 gateway 已停止则直接启动。
reload_ok = False
reload_out = ''
if not skip_reload:
    # Container mode: the gateway runs in the 'openclaw' container managed by
    # Container Manager. Restarting the container via docker restart.
    # restarts the container so it reloads the freshly saved openclaw.json.
    try:
        import subprocess, time, socket
        def is_gateway_running():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                try:
                    s.connect(('127.0.0.1', gw_port))
                    return True
                except Exception:
                    return False
                finally:
                    try:
                        s.close()
                    except Exception:
                        pass
            except Exception:
                return False

        p = subprocess.run(
            ['sudo', '-n', '/usr/local/bin/docker', 'restart', 'openclaw'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90,
        )
        reload_ok = (p.returncode == 0)
        reload_out = (p.stdout or b'').decode('utf-8', 'ignore')[-800:]
        if reload_ok:
            # Wait for the container gateway to come back up.
            time.sleep(2)
            for _ in range(30):
                if is_gateway_running():
                    break
                time.sleep(1)
            reload_ok = is_gateway_running()
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
  'weixin': channels_obj.get('openclaw-weixin') or channels_obj.get('weixin') or {},
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
  'weixin': channels_obj.get('openclaw-weixin') or channels_obj.get('weixin') or {},
  'reloaded': False,
  'message': 'deleted in config only, no hot restart'
}

print(json.dumps(out, ensure_ascii=False))
PY
            exit 0
            ;;
        weixin_status)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"connected":false,"status":"disabled","message":"容器版未启用微信渠道"}'
            exit 0
            ;;
        weixin_login_start)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"supported":false,"error":"容器版未启用微信渠道","message":"容器版未启用微信渠道"}'
            exit 0
            ;;
        weixin_login_wait)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"supported":false,"error":"容器版未启用微信渠道","message":"容器版未启用微信渠道"}'
            exit 0
            ;;
        weixin_disconnect)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"supported":false,"error":"容器版未启用微信渠道","message":"容器版未启用微信渠道"}'
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
legacy_cmd = 'sudo -n /usr/local/bin/docker restart openclaw'
admin_fix_cmd = "sudo -n ln -sfn /var/packages/openclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && sudo -n sh -lc 'nginx -t && systemctl reload nginx'"
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
    inner = "ln -sfn /var/packages/openclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && nginx -t && systemctl reload nginx"
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

alias_src = '/var/packages/openclaw/var/alias.openclaw-terminal.conf'
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
env['OPENCLAW_DATA_DIR'] = '/volume1/openclaw/data'
env['OPENCLAW_CONFIG_PATH'] = cfg_path
env['OPENCLAW_STATE_DIR'] = (os.path.dirname(cfg_path) if cfg_path else '/volume1/openclaw/.openclaw')
# Align terminal env with wrapper semantics: HOME=workspace root, state under HOME/.openclaw
state_dir = env['OPENCLAW_STATE_DIR']
workspace_root = state_dir[:-10] if state_dir.endswith('/.openclaw') else '/volume1/openclaw'
env['OPENCLAW_WORKSPACE_DIR'] = state_dir
env['HOME'] = state_dir
env['NPM_CONFIG_CACHE'] = env['OPENCLAW_STATE_DIR'] + '/.npm'
env['XDG_CACHE_HOME'] = env['OPENCLAW_STATE_DIR'] + '/.cache'
env['XDG_CONFIG_HOME'] = env['OPENCLAW_STATE_DIR'] + '/.config'
env['XDG_DATA_HOME'] = env['OPENCLAW_STATE_DIR'] + '/.local/share'
# 提示符直接显示当前目录（由 shell 原生渲染）。
env['PS1'] = '\\w$ '
# 容器模式：宿主无 openclaw 二进制（CLI 在容器内，用 docker exec 调用）。
# 终端 shell 跑在宿主，用户可自行输入 docker exec 命令。不创建指向不存在二进制的软链。
env['PATH'] = '/usr/local/bin:/usr/syno/bin:/usr/bin:/bin:' + env.get('PATH', '')

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
env['OPENCLAW_DATA_DIR'] = '/volume1/openclaw/data'
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
env['PATH'] = '/var/packages/openclaw/target/bin:/var/packages/openclaw/target/bin:/usr/local/bin:' + env.get('PATH','')

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
            # Container mode: "install" = ensure the openclaw container is
            # running with auto-restart; its supervisor entrypoint then starts
            # the in-container gateway. Docker ops require panel authorization.
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY'
import json, os, subprocess, sys
def auth_ok():
    # 面板 CGI 以套件服务用户 sc-openclaw 运行（非 root）：直接探测 sc-openclaw 能否
    # 免密 sudo docker（正是 sudoers 规则授予的能力）。root CGI 平台才查文件+嵌套探测。
    try:
        if os.geteuid() == 0:
            if not os.path.exists('/etc/sudoers.d/openclaw-ui'):
                return False
            p = subprocess.run(['sudo', '-n', '-u', 'sc-openclaw', 'sudo', '-n',
                                '/usr/local/bin/docker', 'version'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
            return p.returncode == 0
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker', 'version'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
        return p.returncode == 0
    except Exception:
        return False
def run(argv):
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        return p.returncode, (p.stdout or b'').decode('utf-8', 'ignore')[-400:]
    except Exception as e:
        return -1, '%s: %s' % (type(e).__name__, e)
if not auth_ok():
    print(json.dumps({'ok': False, 'authorized': False, 'error': '面板操作未授权：请先点击“授权面板操作”输入管理员密码'}, ensure_ascii=False))
    raise SystemExit
rc1, o1 = run(['sudo','-n','/usr/local/bin/docker','start','openclaw'])
rc2, o2 = run(['sudo','-n','/usr/local/bin/docker','update','--restart=always','openclaw'])
print(json.dumps({'ok': rc1 == 0, 'authorized': True, 'action': 'install',
                  'logs': [{'cmd': 'docker start openclaw', 'rc': rc1, 'out': o1},
                           {'cmd': 'docker update --restart=always openclaw', 'rc': rc2, 'out': o2}]}, ensure_ascii=False))
PY
            exit 0
            ;;
        authorize)
            # 只读的授权状态检查（浏览器轮询用）。实际的 sudoers 写入由
            # authorize_write 完成：浏览器在 授权面板操作 流程里用管理员密码
            # （SYNO.Core.User.PasswordConfirm → SynoConfirmPWToken）建好一次性
            # root 任务后，面板 CGI（root）直接执行 target/scripts/authorize-root.sh。
            # 这里只做判定——sudoers 文件存在 且 sc-openclaw 能 sudo docker——并
            # 在失败时给出准确原因。
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY'
import json, os, subprocess, sys
def auth_check():
    # 面板 CGI 以套件服务用户 sc-openclaw 运行（非 root）：直接探测 sc-openclaw 能否
    # 免密 sudo docker（正是 sudoers 规则授予的能力）。root CGI 平台才查文件+嵌套探测。
    try:
        if os.geteuid() == 0:
            if not os.path.exists('/etc/sudoers.d/openclaw-ui'):
                return False, '未找到 /etc/sudoers.d/openclaw-ui（面板操作未授权）'
            p = subprocess.run(['sudo', '-n', '-u', 'sc-openclaw', 'sudo', '-n',
                                '/usr/local/bin/docker', 'version'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
            if p.returncode == 0:
                return True, ''
            return False, 'sudoers 存在但 sc-openclaw 无法 sudo docker (rc=%s)' % p.returncode
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker', 'version'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
        if p.returncode == 0:
            return True, ''
        return False, '授权未生效：sc-openclaw 无法免密 sudo docker（sudoers 未写入成功）'
    except Exception as e:
        return False, '授权检查异常: %s' % e
activated, reason = auth_check()
print(json.dumps({'ok': activated, 'activated': activated, 'authorized': activated,
                  'sudoers': '/etc/sudoers.d/openclaw-ui',
                  'reason': '' if activated else (reason or '授权未生效'),
                  'logs': []}, ensure_ascii=False))
PY
            exit 0
            ;;

        authorize_write)
            # 同步写 sudoers（授权流程第 3 步的快速尝试，POST）：浏览器在
            # doAuthorizePanel 里已用管理员密码换到 SynoConfirmPWToken，并通过
            # SYNO.Core.EventScheduler.Root create v1 建好一次性 root 任务（create
            # 需要 token —— 管理员身份验证 + CSRF 防护都在这一步由 DSM 完成）。
            # 这里尝试由面板 CGI 直接执行 authorize-root.sh 写 sudoers。
            #
            # ⚠ 实测：本 NAS 上 3rdparty 面板 CGI 以套件服务用户 sc-openclaw 运行
            # （并非 root），写 /etc/sudoers.d 与 root 属主的 authorize-root.log 全部
            # Permission denied（见 var/authorize-write.log），本 action 在此平台必然
            # 失败返回（<1s）。保留它仅为面板 CGI 以 root 运行的平台提供秒级路径；
            # 真正的写入由 doAuthorizePanel 触发的 EventScheduler run（真 root）完成，
            # 配合 240s 宽窗口轮询（run 在这台 NAS 上异步，落地晚约 60~100 秒）。
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body"
import json, os, subprocess, sys, time, traceback

STEP_LOG = '/var/packages/openclaw/var/authorize-write.log'
def slog(msg):
    try:
        with open(STEP_LOG, 'a', encoding='utf-8') as f:
            f.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg))
    except Exception:
        pass

def auth_check():
    # 面板 CGI 以套件服务用户 sc-openclaw 运行（非 root）：直接探测 sc-openclaw 能否
    # 免密 sudo docker（正是 sudoers 规则授予的能力）。root CGI 平台才查文件+嵌套探测。
    try:
        if os.geteuid() == 0:
            if not os.path.exists('/etc/sudoers.d/openclaw-ui'):
                return False, '未找到 /etc/sudoers.d/openclaw-ui（面板操作未授权）'
            p = subprocess.run(['sudo', '-n', '-u', 'sc-openclaw', 'sudo', '-n',
                                '/usr/local/bin/docker', 'version'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
            if p.returncode == 0:
                return True, ''
            return False, 'sudoers 存在但 sc-openclaw 无法 sudo docker (rc=%s)' % p.returncode
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker', 'version'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
        if p.returncode == 0:
            return True, ''
        return False, '授权未生效：sc-openclaw 无法免密 sudo docker（sudoers 未写入成功）'
    except Exception as e:
        return False, '授权检查异常: %s' % e

def task_exists(task_name):
    """一次性授权任务是否真实存在（create 需要管理员密码 token，任务存在 =
    管理员验证 + CSRF 防护已通过的服务端证据）。无法核实（无 sqlite3）时返回
    None 放行，依赖浏览器侧 create 已成功的既定事实。"""
    if not task_name:
        return False
    db = '/usr/syno/etc/esynoscheduler/esynoscheduler.db'
    if not os.path.exists(db):
        return None
    try:
        import sqlite3
        con = sqlite3.connect('file:%s?mode=ro' % db, uri=True, timeout=3)
        try:
            row = con.execute(
                "SELECT operation FROM task WHERE task_name=? AND operation_type='script'",
                (task_name,)).fetchone()
            return bool(row and 'authorize-root.sh' in (row[0] or ''))
        finally:
            con.close()
    except Exception:
        return None

raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
task_name = str(payload.get('task_name') or '')
script = '/var/packages/openclaw/target/scripts/authorize-root.sh'

slog('authorize_write raw_len=%d task_name=%r' % (len(raw), task_name))
activated, reason = auth_check()
slog('auth_check(initial) activated=%s reason=%s' % (activated, reason))
write_log = ''
if not activated:
    exists = task_exists(task_name)
    slog('task_exists -> %r' % (exists,))
    if exists is False:
        reason = '授权任务未创建（管理员密码验证未完成），请重试'
    elif not os.path.exists(script):
        reason = '缺少授权脚本：%s' % script
    else:
        try:
            slog('exec %s' % script)
            # 显式 /bin/sh 执行，绕开 shebang / 直接 exec 的权限边角问题。
            p = subprocess.run(['/bin/sh', script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            write_log = (p.stdout or b'').decode('utf-8', 'ignore')[-500:]
            slog('exec rc=%s out=%r' % (p.returncode, write_log))
        except Exception as e:
            write_log = '%s: %s\n%s' % (type(e).__name__, e, traceback.format_exc()[-800:])
            slog('exec EXC: %s' % write_log)
        activated, reason = auth_check()
        slog('auth_check(after write) activated=%s reason=%s' % (activated, reason))
        if not activated:
            # 兜底：exec 未生效（无论何种原因）时由 Python 直接写 sudoers，内容
            # 与 authorize-root.sh 的 RULE 保持一致（两处同步更新）。
            RULE = ('http ALL=(root) NOPASSWD: /usr/syno/bin/synopkg, /usr/local/bin/docker, /usr/bin/docker, /bin/systemctl, /usr/sbin/nginx, /usr/bin/nginx, /bin/ln, /var/packages/openclaw/target/scripts/ui-run.sh\n'
                    'sc-openclaw ALL=(root) NOPASSWD: /usr/local/bin/docker, /usr/bin/docker, /usr/syno/bin/synopkg, /var/packages/openclaw/target/scripts/openclaw-terminal-entry.sh')
            try:
                tmp = '/etc/sudoers.d/.openclaw-ui.tmp.%d' % os.getpid()
                with open(tmp, 'w') as f:
                    f.write(RULE + '\n')
                os.chmod(tmp, 0o440)
                os.rename(tmp, '/etc/sudoers.d/openclaw-ui')
                os.chmod('/etc/sudoers.d/openclaw-ui', 0o440)
                slog('fallback wrote sudoers')
            except Exception as e:
                slog('fallback EXC: %s: %s' % (type(e).__name__, e))
            activated, reason = auth_check()
            slog('auth_check(after fallback) activated=%s reason=%s' % (activated, reason))
print(json.dumps({'ok': activated, 'activated': activated, 'authorized': activated,
                  'reason': '' if activated else (reason or '授权未生效'),
                  'log': write_log}, ensure_ascii=False))
PY
            exit 0
            ;;

        install_run)
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body" "${CFG_FILE}"
import json, os, socket, subprocess, sys, time
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
cfg = sys.argv[2] if len(sys.argv) > 2 else ''
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {}
action = (payload.get('action') or '').strip().lower()
if action not in ('start', 'stop', 'restart', 'force-stop'):
    print(json.dumps({'ok': False, 'action': action, 'logs': [], 'running': False, 'initialized': True,
                      'error': 'unsupported action'}, ensure_ascii=False))
    raise SystemExit

# Panel-operation authorization gate: start/stop/restart need docker sudo.
def auth_ok():
    # 面板 CGI 以套件服务用户 sc-openclaw 运行（非 root）：直接探测 sc-openclaw 能否
    # 免密 sudo docker（正是 sudoers 规则授予的能力）。root CGI 平台才查文件+嵌套探测。
    try:
        if os.geteuid() == 0:
            if not os.path.exists('/etc/sudoers.d/openclaw-ui'):
                return False
            p = subprocess.run(['sudo', '-n', '-u', 'sc-openclaw', 'sudo', '-n',
                                '/usr/local/bin/docker', 'version'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
            return p.returncode == 0
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker', 'version'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
        return p.returncode == 0
    except Exception:
        return False
if not auth_ok():
    print(json.dumps({'ok': False, 'authorized': False, 'action': action, 'logs': [], 'running': False,
                      'initialized': True, 'error': '面板操作未授权：请先点击“授权面板操作”输入管理员密码'}, ensure_ascii=False))
    raise SystemExit

# Container mode: the gateway lives in the 'openclaw' container managed by
# Container Manager. The container entrypoint (/data/scripts/entrypoint.sh) is
# a SUPERVISOR that runs the gateway as its CHILD (not PID 1), so stop/start
# control the IN-CONTAINER gateway while the container itself stays running:
#   - 停止:      docker exec openclaw kill -s USR1 1  -> supervisor TERMs the
#                gateway and keeps it stopped (container stays up)
#   - 启动:      docker exec openclaw kill -s USR2 1  -> supervisor starts it
#   - 强制停止:  USR2 (clear any stop state) + SIGKILL the gateway via its
#                pidfile (/data/runtime/.gateway.pid) -> supervisor treats it
#                as a crash and auto-restarts it (recovery)
# The gateway process is the only thing that goes up/down; `docker stop` is
# never used from the panel. If the container is fully down (e.g. after a
# Package Center stop) start just brings the container back up.
def docker_cmd(args):
    try:
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker'] + args,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        return p.returncode, (p.stdout or b'').decode('utf-8', 'ignore')[-600:]
    except Exception as e:
        return -1, '%s: %s' % (type(e).__name__, e)

def container_running():
    try:
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker', 'inspect', '-f',
                            '{{.State.Running}}', 'openclaw'],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True, timeout=8)
        return p.stdout.strip() == 'true'
    except Exception:
        return False

def container_started_at():
    try:
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker', 'inspect', '-f',
                            '{{.State.StartedAt}}', 'openclaw'],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True, timeout=8)
        return p.stdout.strip()
    except Exception:
        return ''

gw_port = 58789
try:
    if cfg and os.path.exists(cfg):
        c = json.load(open(cfg, 'r', encoding='utf-8'))
        v = int((((c.get('gateway') or {}).get('port')) or 0))
        if 1024 <= v <= 65535:
            gw_port = v
except Exception:
    pass

def port_listening(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
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

logs = []
hung = False

def gateway_running():
    # Container mode: the gateway is the supervisor's (PID 1) child, so
    # "running" = the supervisor's pidfile (/data/runtime/.gateway.pid) points
    # at a live process INSIDE the container. Host port probes are unreliable
    # here: docker-proxy keeps the host port mapped while the container is up,
    # so a stopped gateway would still answer TCP handshakes on the host.
    try:
        r = subprocess.run(
            ['sudo', '-n', '/usr/local/bin/docker', 'exec', 'openclaw', 'sh', '-c',
             'p=$(cat /data/runtime/.gateway.pid 2>/dev/null); [ -n "$p" ] && kill -0 "$p" 2>/dev/null'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        return r.returncode == 0
    except Exception:
        return False

def gateway_pid():
    # In-container gateway PID recorded by the supervisor (PID 1) in
    # /data/runtime/.gateway.pid, so force-stop can SIGKILL it directly and
    # the supervisor auto-restarts it (crash-recovery loop).
    rc, out = docker_cmd(['exec', 'openclaw', 'cat', '/data/runtime/.gateway.pid'])
    if rc == 0 and out:
        for tok in (out or '').split():
            if tok.strip().isdigit():
                return tok.strip()
    return ''

if action in ('stop', 'force-stop'):
    if container_running():
        if action == 'stop':
            # Graceful in-container stop: signal the supervisor (PID 1) with
            # USR1. It TERMs the gateway and keeps it stopped — the container
            # stays up, only the gateway goes down.
            rc, out = docker_cmd(['exec', 'openclaw', 'kill', '-s', 'USR1', '1'])
            logs.append({'cmd': 'docker exec openclaw kill -s USR1 1 (stop in-container gateway)',
                         'rc': rc, 'out': (out or '').strip() or 'sent stop signal to gateway'})
            # A healthy gateway drains in ~1-2s after SIGTERM. If it is still
            # alive after STOP_WAIT it ignored the signal (hung) — report that
            # so the UI can offer 强制停止 instead of pretending it stopped.
            hung = False
            for _ in range(8):
                time.sleep(1)
                if not gateway_running():
                    break
            else:
                hung = True
        else:
            # 强制停止: first clear any stop state (USR2), then SIGKILL the
            # in-container gateway via its pidfile. The supervisor treats the
            # SIGKILL as a crash and auto-restarts the gateway — recovery.
            rc, out = docker_cmd(['exec', 'openclaw', 'kill', '-s', 'USR2', '1'])
            logs.append({'cmd': 'docker exec openclaw kill -s USR2 1 (clear stop, prepare recovery)',
                         'rc': rc, 'out': (out or '').strip() or 'sent recovery signal'})
            pid = gateway_pid()
            if pid:
                rc2, out2 = docker_cmd(['exec', 'openclaw', 'kill', '-s', 'KILL', pid])
                logs.append({'cmd': 'docker exec openclaw kill -s KILL %s (in-container gateway; supervisor auto-restarts)' % pid,
                             'rc': rc2, 'out': (out2 or '').strip() or 'sent SIGKILL to gateway'})
                rc = rc2
            else:
                logs.append({'cmd': 'force-stop', 'rc': 0,
                             'out': 'no gateway pidfile (gateway already stopped) — recovery will start it'})
    else:
        # Container fully down: bring it back up (supervisor starts the gateway).
        rc, out = docker_cmd(['start', 'openclaw'])
        rc2, o2 = docker_cmd(['update', '--restart=always', 'openclaw'])
        rc = rc if rc == 0 else rc2
        logs.append({'cmd': 'docker start openclaw', 'rc': rc, 'out': out})
        logs.append({'cmd': 'docker update --restart=always openclaw', 'rc': rc2, 'out': o2})
elif action == 'start':
    if container_running():
        # Container up but gateway stopped (supervisor holds it): ask the
        # supervisor to start the gateway with USR2.
        rc, out = docker_cmd(['exec', 'openclaw', 'kill', '-s', 'USR2', '1'])
        logs.append({'cmd': 'docker exec openclaw kill -s USR2 1 (start in-container gateway)',
                     'rc': rc, 'out': (out or '').strip() or 'sent start signal'})
    else:
        rc, out = docker_cmd(['start', 'openclaw'])
        rc2, o2 = docker_cmd(['update', '--restart=always', 'openclaw'])
        rc = rc if rc == 0 else rc2
        logs.append({'cmd': 'docker start openclaw', 'rc': rc, 'out': out})
        logs.append({'cmd': 'docker update --restart=always openclaw', 'rc': rc2, 'out': o2})
else:  # restart
    rc, out = docker_cmd(['restart', 'openclaw'])
    logs.append({'cmd': 'docker restart openclaw', 'rc': rc, 'out': out})

# Wait for the gateway to reach the target state (stop: down; start /
# force-stop / restart: up). The container itself stays up in all cases —
# only the in-container gateway changes state, and docker-proxy keeps the
# host port mapped, so state must be read via the supervisor's pidfile.
if action == 'stop' and not hung:
    for _ in range(30):
        time.sleep(1)
        if not gateway_running():
            break
elif action != 'stop':
    for _ in range(30):
        time.sleep(1)
        if gateway_running():
            break
running = gateway_running()
error = ''
if action == 'stop':
    # stop succeeds when the in-container gateway is down; the container stays up.
    ok = (rc == 0) and (not running)
    if hung and running:
        error = '容器内 gateway 未响应停止信号（疑似卡死），请使用“强制停止”'
else:
    ok = (rc == 0) and running
print(json.dumps({'ok': ok, 'action': action, 'logs': logs, 'running': running, 'error': error,
                  'initialized': True}, ensure_ascii=False))
PY
            exit 0
            ;;
        logs)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            # Container mode: gateway logs live inside the container. Show ONLY
            # `docker logs openclaw` output (like `docker logs -f`), nothing else.
            python3 - <<'PY'
import json, os, subprocess, sys
def auth_ok():
    # 面板 CGI 以套件服务用户 sc-openclaw 运行（非 root）：直接探测 sc-openclaw 能否
    # 免密 sudo docker（正是 sudoers 规则授予的能力）。root CGI 平台才查文件+嵌套探测。
    try:
        if os.geteuid() == 0:
            if not os.path.exists('/etc/sudoers.d/openclaw-ui'):
                return False
            p = subprocess.run(['sudo', '-n', '-u', 'sc-openclaw', 'sudo', '-n',
                                '/usr/local/bin/docker', 'version'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
            return p.returncode == 0
        p = subprocess.run(['sudo', '-n', '/usr/local/bin/docker', 'version'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=8)
        return p.returncode == 0
    except Exception:
        return False
if not auth_ok():
    print(json.dumps({'ok': False, 'authorized': False,
                      'reason': '面板操作未授权：请先点击“授权面板操作”输入管理员密码', 'log': ''}, ensure_ascii=False))
    raise SystemExit
try:
    p = subprocess.run(['sudo','-n','/usr/local/bin/docker','logs','--tail','300','openclaw'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=20)
    log = p.stdout or ''
except Exception as e:
    log = 'error: %s' % e
print(json.dumps({'ok': True, 'authorized': True, 'log': log, 'source': 'docker logs openclaw'}, ensure_ascii=False))
PY
            exit 0
            ;;
        weixin_qr_proxy)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"容器版未启用微信渠道"}'
            exit 0
            ;;
        weixin_qr_data)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"容器版未启用微信渠道"}'
            exit 0
            ;;
        weixin_qr_data2)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"容器版未启用微信渠道"}'
            exit 0
            ;;
        weixin_qr_latest)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            printf '{"ok":false,"error":"容器版未启用微信渠道"}'
            exit 0
            ;;
        panel_log)
            # 浏览器端调试日志（http 用户可写 /tmp）：记录 dsmApi 失败响应与
            # 授权流程每一步，便于排查 DSM webapi 错误码。仅调试用，无敏感信息。
            body=$(read_body)
            printf 'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            python3 - <<'PY' "$body"
import json, os, sys, time
raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
try:
    payload = json.loads(raw or '{}')
except Exception:
    payload = {'raw': raw[:300]}
if not isinstance(payload, dict):
    payload = {'raw': str(payload)[:300]}
LOG = '/tmp/openclaw-panel.log'
try:
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%d %H:%M:%S'), **payload}, ensure_ascii=False) + '\n')
    print(json.dumps({'ok': True}))
except Exception as e:
    print(json.dumps({'ok': False, 'error': str(e)}))
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
    .sidebar { width:220px; min-width:220px; background:#fff; border:1px solid #dfe3ea; border-radius:12px; padding:12px; box-sizing:border-box; display:flex; flex-direction:column; overflow-y:auto; max-height:100%; }
    .title { font-size:20px; font-weight:700; margin:0 0 10px; }
    .sub { color:#667085; font-size:12px; margin:0 0 10px; }
    .tabs { display:flex; flex-direction:column; gap:6px; }
    .tab { text-align:left; border:1px solid #d0d5dd; background:#fff; border-radius:8px; padding:9px 10px; cursor:pointer; }
    .tab.active { background:#eaf2ff; color:#175cd3; border-color:#b7cdfa; font-weight:600; }
    .tab.disabled { opacity:1; cursor:pointer; }
    .main { min-width:0; flex:1; display:flex; min-height:0; overflow:auto; }
    .panel { background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:14px; min-height:0; flex:1; display:flex; flex-direction:column; overflow:auto; }
    .toolbar { display:flex; gap:8px; margin-bottom:12px; align-items:center; }
    #content { flex:1; min-height:0; overflow:auto; }
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
    /* 持久错误信息：显示在运行状态（#msg）下方，失败后一直保留到下一次成功，
       不会被状态轮询/切页刷掉。带浅红背景以便长时间停留时仍醒目。 */
    #persistMsg.msg { margin:0 0 12px; padding:10px 12px; border:1px solid #fecaca; border-radius:10px; background:#fef2f2; color:#b42318; white-space:pre-wrap; word-break:break-word; }
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
    .modal.model-modal { width:min(1400px,96vw); max-height:calc(100vh - 24px); }
    .modal h3 { margin:0 0 14px; font-size:18px; }
    .modal-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:14px; }
    @media (max-width: 900px) {
      .layout { flex-direction:column; }
      .sidebar { width:100%; min-width:0; }
      .tabs { flex-direction:row; flex-wrap:wrap; }
      .tab { min-width:120px; }
    }
  </style>
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
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
          <!-- 持久错误信息：位于运行状态下方；失败后保留，成功时由 setMsg(ok) 清除 -->
          <div id="persistMsg" class="msg err" style="display:none;"></div>
          <div id="content"></div>
        </div>
      </main>
    </div>
  </div>

  <!-- 授权面板操作：管理员密码输入框（掩码显示，不用明文 prompt） -->
  <div class="modal-mask" id="authModalMask">
    <div class="modal" style="width:min(440px,90vw);">
      <h3>授权面板操作</h3>
      <p style="margin:0 0 14px;font-size:13px;color:#475569;line-height:1.6;">
        请输入 DSM 管理员密码（当前登录账号，仅本次验证，密码不会保存）。验证通过后通过一次性的
        root 计划任务写入面板所需的 sudoers，使面板可以启动/停止 OpenClaw、查看日志与使用终端。
      </p>
      <div class="field">
        <label>管理员密码</label>
        <input id="auth_admin_password" type="password" autocomplete="current-password"
               onkeydown="if(event.key==='Enter'){event.preventDefault();submitAuthDialog();}">
      </div>
      <div class="modal-actions">
        <button class="btn" onclick="closeAuthDialog()">取消</button>
        <button class="btn primary" id="btn_auth_confirm" onclick="submitAuthDialog()">授权</button>
      </div>
    </div>
  </div>

  <script>
    const API_BASE = '/webman/3rdparty/openclaw/index.cgi?native_api=1&action=';
    const PROVIDER_PRESETS = {
      anthropic: { label: 'Anthropic', baseUrl: 'https://api.anthropic.com', api: 'anthropic-messages', models: ['claude-3-5-sonnet-latest','claude-3-7-sonnet-latest','claude-sonnet-4-20250514','claude-opus-4-20250514'] },
      google: { label: 'Google', baseUrl: 'https://generativelanguage.googleapis.com/v1beta', api: 'openai-completions', models: ['gemini-2.5-pro','gemini-2.5-flash','gemini-2.0-flash'] },
      siliconflow: { label: '硅基流', baseUrl: 'https://api.siliconflow.cn/v1', api: 'openai-completions', models: ['Pro/MiniMaxAI/MiniMax-M2.5','deepseek-ai/DeepSeek-V4-Flash'] },
      deepseek: { label: 'DeepSeek', baseUrl: 'https://api.deepseek.com', api: 'openai-completions', models: ['deepseek-v4-flash','deepseek-v4-pro'] },
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
    const BUILTIN_CHANNEL_PLUGINS = ['feishu','qqbot','wecom'];
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
    window.__openclawClientErrors = [];

    function captureClientError(type, payload) {
      try {
        const rec = {
          ts: new Date().toISOString(),
          type,
          payload: payload || {}
        };
        window.__openclawClientErrors.push(rec);
        if (window.__openclawClientErrors.length > 50) window.__openclawClientErrors.shift();
        const text = JSON.stringify(rec);
        if (console && console.error) console.error('[openclaw-ui-error]', text);
        const merged = (rec.payload && (rec.payload.message || '')) + '\n' + (rec.payload && (rec.payload.stack || ''));
        if (/flexcroll|document\.write|asynchronously-loaded external script/i.test(merged)) {
          setMsg('检测到 DSM 内置 flexcroll 脚本兼容报错（document.write 异步限制）。已记录错误详情，可继续使用当前页面功能。', 'err');
        }
      } catch (_) {}
    }

    window.openclawClientErrors = function () {
      return (window.__openclawClientErrors || []).slice();
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
      // 错误信息只进 #persistMsg（运行状态下方），绝不覆盖 #msg 的运行状态行
      // （#msg 由状态渲染/轮询直接维护，见 renderStatus）。失败后一直保留，
      // 不会被状态轮询（每 1.5s 覆写 #msg）或切换标签清除；下一次成功(ok)才清除。
      if (cls === 'err') {
        const pel = document.getElementById('persistMsg');
        if (pel) {
          pel.style.display = '';
          pel.className = 'msg err';
          pel.textContent = text || '';
        }
        return;
      }
      // 非错误：临时提示写 #msg；ok 时顺带清除持久错误区。
      el.className = 'msg ' + cls;
      el.textContent = text || '';
      if (cls === 'ok') clearPersistMsg();
    }
    function clearPersistMsg() {
      const pel = document.getElementById('persistMsg');
      if (!pel) return;
      pel.style.display = 'none';
      pel.className = 'msg err';
      pel.textContent = '';
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
    // Call the DSM web API on the same origin as the panel (/webapi/entry.cgi).
    // Used by the 授权面板操作 flow exactly like SimplePermissionManager does:
    // verify the admin password, then create/run/delete a one-shot ROOT
    // scheduled task that writes the package sudoers.
    //
    // DSM 7.2 开启 SynoToken（/etc/synoinfo.conf enable_syno_token="yes"）后，
    // 敏感 webapi 调用必须携带当前会话的 SynoToken，否则返回 119（会话已过期）——
    // 这正是此前面板"输入密码显示登录会话已过期"的根因：普通 fetch 不带 token。
    // 这里复刻 SurveillanceStation 的 SYNO.SDS.UpdateSynoToken 机制：
    //   1) 内嵌在 DSM 桌面时，直接复用框架缓存的 token（parent.SYNO.SDS.Session.SynoToken），
    //      与登录页同一会话、必定有效，且零额外请求；
    //   2) 独立打开（非嵌入）时，GET /webman/login.cgi（带会话 cookie）返回当前会话的
    //      SynoToken，与 SS 的 login.cgi 用法完全一致；
    //   3) 随请求同时以 X-SYNO-TOKEN 请求头 + SynoToken 查询参数发出（SS 用头，DSM 框架
    //      用查询参数，两者都发兼容两条校验路径）。
    let dsmSynoToken = '';
    let dsmSynoTokenLoading = null;
    async function ensureDsmSynoToken() {
      if (dsmSynoToken) return dsmSynoToken;
      try {
        if (window.parent && window.parent.SYNO && window.parent.SYNO.SDS
            && window.parent.SYNO.SDS.Session && window.parent.SYNO.SDS.Session.SynoToken) {
          dsmSynoToken = window.parent.SYNO.SDS.Session.SynoToken;
          return dsmSynoToken;
        }
      } catch (_) {}
      if (dsmSynoTokenLoading) return dsmSynoTokenLoading;
      dsmSynoTokenLoading = (async () => {
        try {
          const resp = await fetch('/webman/login.cgi', { cache: 'no-store' });
          const j = await resp.json();
          if (j && j.success && j.SynoToken) dsmSynoToken = j.SynoToken;
          else if (j && j.SynoToken) dsmSynoToken = j.SynoToken;
        } catch (_) {}
        dsmSynoTokenLoading = null;
        return dsmSynoToken;
      })();
      return dsmSynoTokenLoading;
    }
    // 调试日志：POST 到面板自身的 panel_log action，落到 /tmp/openclaw-panel.log
    //（http 用户可写）。fire-and-forget，不阻塞也不影响业务请求。
    function logPanel(obj) {
      try {
        fetch(API_BASE + 'panel_log', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(obj || {}),
          cache: 'no-store'
        }).catch(() => {});
      } catch (_) {}
    }
    async function dsmApiFetch(apiName, methodName, version, params, token, opts) {
      const jsonMode = !!(opts && opts.jsonMode);
      const q = '/webapi/entry.cgi?api=' + encodeURIComponent(apiName)
        + '&method=' + encodeURIComponent(methodName)
        + '&version=' + encodeURIComponent(version)
        + (token ? '&SynoToken=' + encodeURIComponent(token) : '')
        + '&_dc=' + Date.now();
      // 手工拼 form body：key 保留原始方括号（与 DSM 自带 Ext.Ajax 序列化一致，
      // 如 extra[script]=...、schedule[date_type]=0、tasks[0][id]=...），value 才
      // encodeURIComponent（URLSearchParams 会把方括号转义成 %5B%5D，后端就解析
      // 不出嵌套了）。
      //
      // jsonMode：DSM 的 entry.cgi 默认 requestFormat=JSON
      // （见 /usr/syno/synoman/webapi/lib.def），官方任务计划 UI 把每个顶层参数值
      // JSON.stringify 后放进 form 字段（schedule={...}、extra={...}、tasks=[...]、
      // owner={"0":"root"}），后端逐个 JSON.parse。这很重要：schedule.monthly_week
      // 对 weekly 任务是空数组 []，必须作为真实 JSON 数组传输；若用 bracket 序列化
      // 会变成 schedule[monthly_week]=（空值，后端解析成空字符串），导致 4800
      // "monthly_week expected/type invalid"。
      // 授权流程（doAuthorizePanel）用 SYNO.Core.EventScheduler.Root v1，
      // owner 为 {0:"root"}（与已安装的 SimplePermissionManager 套件同款）。
      const pairs = [];
      const appendFlat = (key, val) => {
        if (val === null || val === undefined) { pairs.push(key + '='); return; }
        if (typeof val === 'object') {
          const keys = Object.keys(val);
          if (keys.length === 0) { pairs.push(key + '='); return; }
          for (const k of keys) appendFlat(key + '[' + k + ']', val[k]);
          return;
        }
        pairs.push(key + '=' + encodeURIComponent(String(val)));
      };
      let body;
      if (jsonMode) {
        const enc = [];
        for (const k of Object.keys(params || {})) {
          enc.push(k + '=' + encodeURIComponent(JSON.stringify(params[k])));
        }
        body = enc.join('&');
      } else {
        for (const k of Object.keys(params || {})) appendFlat(k, params[k]);
        body = pairs.join('&');
      }
      const headers = { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' };
      if (token) headers['X-SYNO-TOKEN'] = token;
      const resp = await fetch(q, {
        method: 'POST',
        headers: headers,
        body: body,
        cache: 'no-store'
      });
      const text = await resp.text();
      let parsed = {};
      try { parsed = text ? JSON.parse(text) : {}; } catch (e) { parsed = { success: false, error: { message: 'webapi 返回非 JSON: ' + String(text).slice(0, 120) } }; }
      if (!parsed || !parsed.success) {
        const code = parsed && parsed.error && parsed.error.code;
        const msg = parsed && parsed.error && parsed.error.message;
        // 记录请求体便于定位（脱敏 password / SynoConfirmPWToken / SynoToken）
        const redactedBody = body.replace(/(password|SynoConfirmPWToken|SynoToken)=[^&]*/gi, '$1=***');
        logPanel({ ev: 'dsmApiFail', api: apiName, method: methodName, code: code != null ? code : null, msg: msg || '', body: redactedBody.slice(0, 2500), raw: text.slice(0, 1000) });
      }
      return parsed;
    }
    async function dsmApi(apiName, methodName, version, params, opts) {
      const token = await ensureDsmSynoToken();
      let r = await dsmApiFetch(apiName, methodName, version, params, token, opts);
      // 119 = token 缺失/失效（如首次取 token 前请求已失败，或桌面 token 过期）：
      // 清缓存重取一次再重试，避免一次性的偶发失败直接报"会话已过期"。
      if (r && !r.success && r.error && r.error.code === 119 && token) {
        logPanel({ ev: 'dsmApiRetry119', api: apiName, method: methodName });
        dsmSynoToken = '';
        const t2 = await ensureDsmSynoToken();
        if (t2) r = await dsmApiFetch(apiName, methodName, version, params, t2, opts);
      }
      return r;
    }
    // Panel-operation authorization state, refreshed from status / authorize.
    let authState = 'unknown';          // 'authorized' | 'unauthorized' | 'unknown'
    let authReason = '';
    function setAuthState(authorized, reason) {
      authState = (authorized === true) ? 'authorized' : ((authorized === false) ? 'unauthorized' : 'unknown');
      authReason = reason || '';
      const btn = document.getElementById('btn_oc_auth');
      if (btn && btn.textContent !== '授权中...') btn.textContent = (authState === 'authorized') ? '已授权' : '授权面板操作';
    }
    // 从后端重新拉一次授权状态（status 端点里跑 sudo -n docker 探测），用于
    // 标签页重新可见/聚焦时立刻刷新——后台标签的 1.5s 轮询会被浏览器限频，
    // 切回面板页时可能还停留在旧状态。
    async function refreshAuthFromBackend() {
      try {
        const s = await api('status');
        if (s && typeof s.authorized === 'boolean') {
          setAuthState(s.authorized, s.authError || '');
          const authBannerEl = document.getElementById('auth_banner');
          if (authBannerEl) {
            if (authState === 'authorized') {
              authBannerEl.remove();
            } else {
              authBannerEl.innerHTML = '<b>面板操作未授权</b>：' + esc(authReason || '请点击下方“授权面板操作”，输入管理员密码后即可使用启动/停止/日志/终端。');
            }
          }
        }
      } catch (_) {}
    }
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) refreshAuthFromBackend();
    });
    window.addEventListener('focus', refreshAuthFromBackend);
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
      const patchCmd = "sudo -n ln -sfn /var/packages/openclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && sudo -n sh -lc 'nginx -t && systemctl reload nginx'";
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
          window.__ainasTerminalPort = data.terminalPort || 17682;
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
            ['binaryPath', data.binaryPath || '-'],
            ['面板运行用户', (data.cgiUser || '-') + (data.cgiUid != null ? ' (uid ' + data.cgiUid + ')' : '')],
            ['面板版本', PANEL_VER]
          ];
          const runningText = data.running ? '运行中' : '已停止';
          setAuthState(!!data.authorized, data.authError || '');
          // 已有持久错误（如"授权未生效"）时不再重复渲染"面板操作未授权"横幅，
          // 避免同一信息显示两行；persistMsg 被下一次成功(ok)清除后横幅恢复。
          const pelErr = document.getElementById('persistMsg');
          const persistErrActive = !!(pelErr && pelErr.style.display !== 'none' && String(pelErr.textContent || '').trim());
          const authBanner = (authState === 'authorized' || persistErrActive)
            ? ''
            : '<div id="auth_banner" style="margin-bottom:12px;padding:10px 12px;border-radius:8px;background:#fef3f2;border:1px solid #fda29b;color:#b42318;font-size:13px;line-height:1.6;">'
              + '<b>面板操作未授权</b>：' + esc(authReason || '请点击下方“授权面板操作”，输入管理员密码后即可使用启动/停止/日志/终端。')
              + '</div>';
          const authDisable = (authState === 'authorized') ? '' : ' disabled';
          content.innerHTML = ''
            + authBanner
            + '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">'
            + '  <button class="btn" id="btn_oc_start" onclick="runInstallAction(\'start\')"' + authDisable + '>启动 OpenClaw</button>'
            + '  <button class="btn" id="btn_oc_stop" onclick="runStopOrForce()"' + authDisable + '>停止 OpenClaw</button>'
            + '  <button class="btn" id="btn_oc_auth" onclick="openAuthDialog()">' + (authState === 'authorized' ? '已授权' : '授权面板操作') + '</button>'
            + '  <button class="btn primary" onclick="openOpenclawWeb()">打开 OpenClaw Web</button>'
            + '</div>'
            + '<div class="grid">' + rows.map(([k,v]) => {
                const vv = String(v == null ? '' : v).replace(/127\.0\.0\.1|localhost/g, hostFix);
                return '<div class="cellk">'+esc(k)+'</div><div class="cellv">'+esc(vv)+'</div>';
              }).join('') + '</div>';
          // 运行状态行直接写 #msg（不经 setMsg 的持久错误路由——"已停止"是状态
          // 不是错误，不应进入持久区；轮询每 1.5s 也会同步这一行）。
          const statusMsgEl = document.getElementById('msg');
          if (statusMsgEl) {
            statusMsgEl.className = 'msg ' + (data.running ? 'ok' : 'err');
            statusMsgEl.textContent = '运行状态：' + runningText;
          }
          window.__statusRunning = !!data.running;
          // A completed stop may still leave a package keepalive process, so
          // always derive button state from the Gateway port, not a stale busy
          // marker left by an earlier async request.
          if (installBusy && installBusyAction === 'stop' && !data.running) {
            setInstallButtonsBusy('', false);
          } else if (installBusy) {
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
              if (s && typeof s.authorized === 'boolean') {
                setAuthState(s.authorized, s.authError || '');
              }
              const authBannerEl = document.getElementById('auth_banner');
              if (authBannerEl) {
                if (authState === 'authorized') {
                  authBannerEl.remove();
                } else {
                  authBannerEl.innerHTML = '<b>面板操作未授权</b>：' + esc(authReason || '请点击下方“授权面板操作”，输入管理员密码后即可使用启动/停止/日志/终端。');
                }
              }
              const msgEl = document.getElementById('msg');
              if (msgEl) {
                msgEl.className = 'msg ' + (nextRunning ? 'ok' : 'err');
                msgEl.textContent = '运行状态：' + nextText;
              }
              window.__statusRunning = nextRunning;
              if (installBusy && installBusyAction === 'stop' && !nextRunning) {
                setInstallButtonsBusy('', false);
              } else if (!installBusy) {
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
              window.__ainasTerminalPort = (s && s.terminalPort) || window.__ainasTerminalPort || 17682;
            } catch (_) {}
          }, 1500);
          return;
        }
        if (tab === 'logs') {
          logsAutoRefresh = true;
          const logText = (data && data.authorized === false)
            ? '[面板操作未授权] ' + (data.reason || '请先点击“授权面板操作”输入管理员密码')
            : (data.log || '');
          content.innerHTML = ''
            + '<div style="height:100%;display:flex;flex-direction:column;gap:8px;">'
            + '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">'
            + '    <div style="font-size:13px;color:#667085;">实时显示容器网关日志（docker logs openclaw，自动刷新）。</div>'
            + '    <div style="display:flex;gap:8px;">'
            + '      <button class="btn" onclick="refreshLogsNow(true)">刷新一次</button>'
            + '      <button class="btn" id="btn_logs_toggle" onclick="toggleLogsAutoRefresh()">停止刷新</button>'
            + '      <button class="btn" onclick="copyLogsText()">复制日志</button>'
            + '    </div>'
            + '  </div>'
            + '  <pre id="log_pre" style="flex:1;min-height:0;max-height:none;margin:0;">' + esc(logText) + '</pre>'
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
              + '  <div style="font-size:12px;color:#667085;">修复命令（系统内置执行）：<code>sudo -n ln -sfn /var/packages/openclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && sudo -n sh -lc \'nginx -t && systemctl reload nginx\'</code></div>'
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
              + '  <div style="font-size:12px;color:#667085;">修复命令（系统内置执行）：<code>sudo -n ln -sfn /var/packages/openclaw/var/alias.openclaw-terminal.conf /etc/nginx/conf.d/alias.openclaw-terminal.conf && sudo -n sh -lc \'nginx -t && systemctl reload nginx\'</code></div>'
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
            + '<div style="display:flex;flex-direction:column;height:100%;min-height:0;">'
            + '  <div style="margin-bottom:12px;flex:0 0 auto;"><button class="btn primary" onclick="openModelDialog()">添加模型服务器</button></div>'
            + '  <div class="list" style="flex:1 1 auto;min-height:0;overflow:auto;padding-right:4px;">'
            + providers.map((p, idx) => {
                const modelIds = (p.models || []).map(m => m.modelId || m.id).filter(Boolean);
                const dtm = (p.defaultTextModel || '').trim();
                const dim = (p.defaultImageModel || '').trim();
                let defaultHtml = '';
                if (dtm) defaultHtml += '<div style="font-size:12px;color:#1d2939;margin-top:4px;"><span style="color:#667085;">默认文本：</span>' + esc(dtm) + '</div>';
                if (dim) defaultHtml += '<div style="font-size:12px;color:#1d2939;margin-top:2px;"><span style="color:#667085;">默认图像：</span>' + esc(dim) + '</div>';
                return '<div class="item">'
                  + '<div class="item-title">' + esc(p.displayName || p.id || '未命名服务') + '</div>'
                  + '<div class="item-meta">providerId=' + esc(p.id || '-') + ' / api=' + esc(p.api || '-') + ' / baseUrl=' + esc(p.baseUrl || '-') + '</div>'
                  + '<div class="chips">' + modelIds.map(m => '<span class="chip">' + esc(m) + '</span>').join('') + '</div>'
                  + defaultHtml
                  + '<div style="display:flex;gap:8px;">'
                  + '<button class="btn" onclick="openModelDialog(' + idx + ')">编辑</button>'
                  + '<button class="btn" onclick="deleteModelProvider(\'' + esc(p.id || '') + '\')">删除</button>'
                  + '</div>'
                  + '</div>';
              }).join('')            + '  </div>'
            + '</div>'
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
            + '      <div style="display:flex;gap:8px;align-items:center;margin-top:8px;flex-wrap:wrap;">'
            + '        <button class="btn" style="white-space:nowrap;flex:0 0 auto;" onclick="selectAllModelSelections()">全选</button>'
            + '        <button class="btn" style="white-space:nowrap;flex:0 0 auto;" onclick="clearAllModelSelections()">取消全选</button>'
            + '        <input id="dlg_model_manual_input" style="flex:1;min-width:0;" placeholder="手动输入模型名称（如 gpt-5.4-mini）" onkeydown="if(event.key===\'Enter\'){event.preventDefault();addManualModelFromInput();}">'
            + '        <button class="btn" style="white-space:nowrap;flex:0 0 auto;" onclick="addManualModelFromInput()">添加</button>'
            + '      </div>'
            + '      <input id="dlg_model_ids" type="hidden">'
            + '    </div>'
            + '    <div class="field"><label>默认文本模型</label>'
            + '      <div style="font-size:13px;color:#667085;margin-bottom:4px;">选择默认文本模型，留空则自动选择第一个可用模型。</div>'
            + '      <select id="dlg_default_text_model" style="width:100%;"><option value="">（自动选择）</option></select>'
            + '      <div style="display:flex;gap:6px;align-items:center;margin-top:4px;">'
            + '        <input id="dlg_default_text_model_manual" style="flex:1;" placeholder="输入模型名（自动补全 ProviderID）">'
            + '        <button class="btn" style="white-space:nowrap;" onclick="setDefaultTextModelFromManual()">添加</button>'
            + '      </div>'
            + '    </div>'
            + '    <div class="field"><label>默认图像模型</label>'
            + '      <div style="font-size:13px;color:#667085;margin-bottom:4px;">选择默认图像模型，留空则无默认图像模型。勾选后自动为该模型添加 image 输入支持。</div>'
            + '      <select id="dlg_default_image_model" style="width:100%;" onchange="trackImageDefaultClear(this)"><option value="">（无默认图像模型）</option></select>'
            + '      <div style="display:flex;gap:6px;align-items:center;margin-top:4px;">'
            + '        <input id="dlg_default_image_model_manual" style="flex:1;" placeholder="输入模型名（自动补全 ProviderID）">'
            + '        <button class="btn" style="white-space:nowrap;" onclick="setDefaultImageModelFromManual()">添加</button>'
            + '      </div>'
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
        if (actionName === 'stop') {
          startBtn.disabled = true;
          stopBtn.disabled = true;
          startBtn.textContent = '启动 OpenClaw';
          stopBtn.textContent = '停止中...';
          return;
        }
        startBtn.disabled = true;
        stopBtn.disabled = false;
        startBtn.textContent = actionName === 'start' ? '启动中...' : '启动 OpenClaw';
        stopBtn.textContent = '强制停止中...';
        return;
      }
      const running = !!window.__statusRunning;
      const authed = (authState === 'authorized');
      // 运行中 -> 停止（优雅停容器内 gateway，容器保持运行）；
      // 已停止 / 上次停止失败（疑似卡死）-> 强制停止（杀 gateway 后自动重启恢复）。
      const forceMode = !running || !!window.__stopFailed;
      startBtn.disabled = running || !authed;
      stopBtn.disabled = !authed;
      startBtn.textContent = '启动 OpenClaw';
      stopBtn.textContent = forceMode ? '强制停止 OpenClaw' : '停止 OpenClaw';
    }
    // 停止按钮：根据当前 gateway 状态在“停止”/“强制停止”间切换动作。
    function runStopOrForce() {
      const running = !!window.__statusRunning;
      const forceMode = !running || !!window.__stopFailed;
      runInstallAction(forceMode ? 'force-stop' : 'stop');
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
    async function ocFetchToken(password) {
      const r = await dsmApi('SYNO.Core.User.PasswordConfirm', 'auth', 2, { password: password });
      if (!r || !r.success) {
        const code = r && r.error && r.error.code;
        const msg = r && r.error && r.error.message;
        logPanel({ ev: 'ocFetchTokenFail', code: code != null ? code : null, msg: msg || '' });
        if (code === 119) {
          throw new Error('登录会话已过期：请刷新页面重新登录后再试（119）');
        }
        throw new Error('管理员密码校验失败：密码错误，或当前登录账号不是管理员'
          + (msg ? ('（' + (code != null ? code + ': ' : '') + msg + '）')
                : '（请确认输入的是当前登录账号的 DSM 管理员密码，而非 SSH 密码）'));
      }
      const token = r.data && r.data.SynoConfirmPWToken;
      if (!token) throw new Error('未取得授权令牌（SynoConfirmPWToken 为空）');
      return token;
    }
    // 授权面板操作：输入管理员密码 -> 校验密码取得 SynoConfirmPWToken ->
    // 用 token 建一次性 root 计划任务（管理员身份验证 + CSRF 防护，与已安装的
    // “权限管理器”套件同一机制）-> 后端 authorize_write 由面板 CGI（root）同步
    // 执行 authorize-root.sh 写 sudoers -> 删除计划任务。
    // 不走 EventScheduler run：实测该 NAS 上 run 也是异步执行（滞后约 1 分钟），
    // 同步直写彻底消除轮询超时的误报。
    function openAuthDialog() {
      const mask = document.getElementById('authModalMask');
      const el = document.getElementById('auth_admin_password');
      if (!mask || !el) return;
      mask.style.display = 'flex';
      el.value = '';
      setTimeout(() => { el.focus(); }, 50);
    }
    function closeAuthDialog() {
      const mask = document.getElementById('authModalMask');
      if (mask) mask.style.display = 'none';
    }
    async function submitAuthDialog() {
      const el = document.getElementById('auth_admin_password');
      const password = (el && el.value) || '';
      if (!password) { setMsg('请输入管理员密码', 'err'); if (el) el.focus(); return; }
      closeAuthDialog();
      await doAuthorizePanel(password);
    }
    // 从 TaskScheduler list v3 里按任务名取回刚创建的任务的 id + real_owner。
    // run/delete v2 都要求这两个字段（任务身份 + 真实属主），以后端返回的为准，
    // 不猜用户名。刚创建的任务可能尚未入列表，所以带重试。
    async function findTaskRefByName(name, tries = 6) {
      for (let i = 0; i < tries; i++) {
        try {
          // jsonMode：TaskScheduler 走 requestFormat=JSON（lib.def 默认），参数值
          // 需 JSON.stringify 传输（官方 UI 同款），避免 bracket 序列化歧义。
          const r = await dsmApi('SYNO.Core.TaskScheduler', 'list', 3, { offset: 0, limit: 100 }, { jsonMode: true });
          const tasks = (r && r.success && r.data && r.data.tasks) || [];
          const hit = tasks.find(t => t && t.name === name);
          if (hit && hit.id != null) {
            return { id: hit.id, real_owner: hit.real_owner || '' };
          }
        } catch (_) {}
        await new Promise(r => setTimeout(r, 600));
      }
      return null;
    }
    // 从 TaskScheduler 后端取"新建脚本任务"骨架（get id=-1, type:"script"）。
    // v4 后端会逐字段校验字段存在性（如 schedule.monthly_week 缺失报 4800），
    // 所以用后端自己的默认结构最稳：schedule / extra / real_owner 都是后端认可
    // 的模板。拿不到就回退到等价的官方默认值（EditSchedulePanelV2.getData）。
    async function fetchCreateSkeleton() {
      const fallback = {
        schedule: {
          date_type: 0,
          week_day: '0,1,2,3,4,5,6',
          repeat_date: 1001,
          monthly_week: [],
          hour: 3,
          minute: 0,
          repeat_hour: 0,
          repeat_min: 0,
          last_work_hour: 3,
          repeat_min_store_config: [],
          repeat_hour_store_config: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]
        },
        realOwner: '',
        extra: {}
      };
      try {
        const r = await dsmApi('SYNO.Core.TaskScheduler', 'get', 4, { id: -1, type: 'script' }, { jsonMode: true });
        if (r && r.success && r.data) {
          // 完整记录骨架响应（real_owner + schedule JSON）便于诊断 4800 类字段问题。
          logPanel({ ev: 'authorize', step: 'skeleton', ok: true,
                     real_owner: (r.data.real_owner || ''), has_schedule: !!r.data.schedule,
                     schedule: (r.data.schedule && typeof r.data.schedule === 'object')
                       ? JSON.stringify(r.data.schedule) : String(r.data.schedule || '').slice(0, 2000) });
          return {
            schedule: (r.data.schedule && typeof r.data.schedule === 'object') ? r.data.schedule : fallback.schedule,
            realOwner: r.data.real_owner || '',
            extra: (r.data.extra && typeof r.data.extra === 'object') ? r.data.extra : fallback.extra
          };
        }
        logPanel({ ev: 'authorize', step: 'skeleton', ok: false, err: 'get v4 id=-1 failed', code: r && r.error ? r.error.code : null, msg: r && r.error ? r.error.message : '' });
      } catch (e) {
        logPanel({ ev: 'authorize', step: 'skeleton', ok: false, err: String(e) });
      }
      return fallback;
    }
    // 面板脚本版本号：改版后递增，便于确认浏览器加载的是新代码
    // （旧标签页不会热更新，需强制刷新 Ctrl+Shift+R 才能取到新脚本）。
    const PANEL_VER = '2026.09.05-fix9';
    console.log('OpenClaw panel v' + PANEL_VER);
    async function doAuthorizePanel(adminPassword) {
      const btn = document.getElementById('btn_oc_auth');
      if (btn) { btn.disabled = true; btn.textContent = '授权中...'; }
      // 授权流程开始：立即清掉可能残留的持久错误（如"面板操作未授权"），
      // 避免旧错误在流程进行中仍挂在面板上；失败时会写入新的错误。
      const pel = document.getElementById('persistMsg');
      if (pel) { pel.style.display = 'none'; pel.className = 'msg err'; pel.textContent = ''; }
      // 进度只体现在按钮文案（“授权中...”），不覆盖 #msg 的“运行状态”行——
      // 授权过程中运行状态保持可见，不被进度文字顶掉。
      const taskName = 'openclaw-authorize-' + Math.floor(Date.now() / 1000);
      try {
        // 1) verify the admin password -> one-time SynoConfirmPWToken
        const token = await ocFetchToken(adminPassword);
        logPanel({ ev: 'authorize', step: 'token', ok: true });
        // 2) create a one-shot ROOT script task via the LEGACY v1
        //    SYNO.Core.EventScheduler.Root —— 与已安装的「权限管理器」
        //    (SimplePermissionManager) 套件同一机制（其 UI 输密码授权是秒级完成）。
        //
        //    为什么授权要走计划任务执行（而不是面板 CGI 直写）：
        //    TaskScheduler.Root v4 + run v2 是「异步排队」——root 脚本要等
        //    synoscheduled 守护进程下一轮扫描才执行，实测滞后 5~10 分钟，弃用。
        //    EventScheduler 的 run v1 能触发执行，但在这台 NAS 上同样是异步
        //    （脚本实际以 root 运行比 run 返回晚约 60~100 秒），所以轮询窗口
        //    放宽到 240s——fix3 用 60s 就是因此超时误报"授权未生效"。
        //    面板 CGI 实测以套件服务用户 sc-openclaw 运行（并非 root），无法直接
        //    写 /etc/sudoers.d（var/authorize-write.log 里全是 Permission denied），
        //    所以 sudoers 必须由计划任务以真 root 执行 authorize-root.sh 写入。
        //    create 仍是必须的：携带 PasswordConfirm 换来的一次性 SynoConfirmPWToken
        //    = 管理员身份验证 + CSRF 防护，浏览器无法绕过。
        //
        //    script 任务的 operation 填完整路径（esynoscheduler 存的是命令本身，
        //    例如系统自带的 shutdown 任务 operation=/usr/bin/loader-reboot.sh），
        //    直接指向已安装的 authorize-root.sh，无需任何符号链接。
        // jsonMode：lib.def 默认 requestFormat=JSON（TaskScheduler/EventScheduler 均
        // 继承），顶层对象值需 JSON.stringify 传输——owner 发送为 owner={"0":"root"}，
        // 与 DSM 官方 UI / SPM 的实际编码一致。
        const createResp = await dsmApi('SYNO.Core.EventScheduler.Root', 'create', 1, {
          task_name: taskName,
          owner: { 0: 'root' },
          event: 'bootup',
          enable: true,
          depend_on_task: '',
          notify_enable: false,
          notify_mail: '',
          notify_if_error: false,
          operation_type: 'script',
          operation: '/var/packages/openclaw/target/scripts/authorize-root.sh',
          SynoConfirmPWToken: token
        }, { jsonMode: true });
        if (!createResp || !createResp.success) {
          const m = createResp && createResp.error
            ? (createResp.error.code + ': ' + (createResp.error.message || ''))
            : '未知错误';
          logPanel({ ev: 'authorize', step: 'create', ok: false, err: m });
          throw new Error('创建计划任务失败：' + m);
        }
        logPanel({ ev: 'authorize', step: 'create', ok: true });
        // 3) 并行触发两条写入路径，谁先生效由轮询判定：
        //    - run：计划任务以真 root 执行 authorize-root.sh（本 NAS 的生效路径，实测与请求同秒落地）；
        //    - authorize_write：面板 CGI 直写（root-CGI 平台秒级生效；本 NAS 上 CGI 是
        //      sc-openclaw，写 /etc/sudoers.d 必被拒，<1s 失败，作为 run 的兜底无碍）。
        //    authorize_write 不 await（fire-and-forget）：本 NAS 上它必失败，不该阻塞
        //    关键路径；结果在轮询结束后再回收用于日志。
        const wrPromise = api('authorize_write', 'POST', { task_name: taskName }).catch(() => null);
        const runResp = await dsmApi('SYNO.Core.EventScheduler', 'run', 1, { task_name: taskName });
        logPanel({ ev: 'authorize', step: 'run', ok: !!(runResp && runResp.success),
                   err: (runResp && runResp.error) ? (runResp.error.code + ': ' + (runResp.error.message || '')) : '' });
        let activated = false;
        let reason = 'sudoers 未写入成功';
        if (!(runResp && runResp.success)) {
          // run 失败时给直写一点时间收尾（root-CGI 平台直写可能已成功）。
          const wrEarly = await wrPromise;
          if (wrEarly && wrEarly.activated) activated = true;
        }
        if (!activated) {
          // 4b) 轮询授权状态；进度只显示在按钮上（“授权中… Ns”），绝不覆盖
          //     #msg 的“运行状态”行（用户要求：授权过程不影响运行状态显示）。
          //     先立即查一次再每 1s 轮询——run 在这台 NAS 上实测常与请求同秒落地，
          //     写入后即可立即检测，不再空等固定间隔。脚本幂等，轮询中可安全地
          //     重复 run 兜底。
          const pollStarted = Date.now();
          const pollDeadline = pollStarted + 240000;
          let hedged90 = false, hedged180 = false;
          for (;;) {
            const elapsed = Math.round((Date.now() - pollStarted) / 1000);
            if (btn) btn.textContent = elapsed >= 1 ? ('授权中… ' + elapsed + 's') : '授权中…';
            if (!hedged90 && elapsed >= 90) { hedged90 = true;
              try { await dsmApi('SYNO.Core.EventScheduler', 'run', 1, { task_name: taskName }); } catch (_) {} }
            if (!hedged180 && elapsed >= 180) { hedged180 = true;
              try { await dsmApi('SYNO.Core.EventScheduler', 'run', 1, { task_name: taskName }); } catch (_) {} }
            try {
              const ret = await api('authorize');
              if (ret && ret.activated) { activated = true; break; }
              if (ret && ret.reason) reason = ret.reason;
            } catch (_) {}
            if (Date.now() >= pollDeadline) break;
            await new Promise(r => setTimeout(r, 1000));
          }
          // 超时后立即再查一次，避免差一个 tick 误报失败。
          if (!activated) {
            try {
              const ret = await api('authorize');
              if (ret && ret.activated) activated = true;
              else if (ret && ret.reason) reason = ret.reason;
            } catch (_) {}
          }
        }
        // 回收直写结果（fire-and-forget 已结束，直接 await 拿日志数据，不阻塞）。
        const wr = await wrPromise;
        logPanel({ ev: 'authorize', step: 'write', ok: !!(wr && wr.activated), reason: (wr && wr.reason) || '' });
        // 两条路径都失败且轮询也未生效，才算触发失败。
        if (!activated && (!runResp || !runResp.success)) {
          const m = runResp && runResp.error
            ? (runResp.error.code + ': ' + (runResp.error.message || ''))
            : '未知错误';
          logPanel({ ev: 'authorize', step: 'run', ok: false, err: m });
          throw new Error('触发计划任务失败：' + m);
        }
        logPanel({ ev: 'authorize', step: 'poll', activated: activated, reason: reason });
        // 5) delete the one-shot task (best-effort; 任务只是管理员凭证)
        try {
          await dsmApi('SYNO.Core.EventScheduler', 'delete', 1, { task_name: taskName });
        } catch (_) {}
        if (activated) {
          setAuthState(true, '');
          // 成功：只清除持久错误区，绝不写 #msg（运行状态行由状态渲染/轮询维护）。
          clearPersistMsg();
          await load('status');
        } else {
          setAuthState(false, reason);
          // 只显示这一条错误，清掉状态区里重复的"面板操作未授权"横幅，避免两行。
          const bannerEl = document.getElementById('auth_banner');
          if (bannerEl) bannerEl.remove();
          // 错误进 #persistMsg（运行状态下方），不覆盖 #msg 的运行状态行。
          setMsg('授权未生效：' + reason + '（计划任务未在约 4 分钟内完成写入，请重试）', 'err');
        }
      } catch (e) {
        setAuthState(false, e && e.message ? e.message : String(e));
        setMsg('授权失败：' + (e && e.message ? e.message : String(e)), 'err');
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.textContent = (authState === 'authorized') ? '已授权' : '授权面板操作';
        }
      }
    }
    async function runInstallAction(actionName) {
      if (authState !== 'authorized') {
        setMsg('面板操作未授权：请先点击“授权面板操作”输入管理员密码后重试', 'err');
        return;
      }
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
        if (actionName === 'start' || actionName === 'stop' || actionName === 'force-stop') {
          // 启动/强制停止期待 gateway 恢复运行；停止期待 gateway 停下。
          // 容器本身始终由 supervisor 保持运行，只有容器内 gateway 变状态。
          const wantRunning = (actionName !== 'stop');
          const maxTries = 40; // 最多约 36s
          for (let i = 0; i < maxTries; i += 1) {
            await new Promise(r => setTimeout(r, 900));
            try {
              const s = await api('status');
              const gatewayRunning = !!(s && s.running);
              if (wantRunning) {
                if (gatewayRunning) {
                  window.__statusRunning = true;
                  window.__stopFailed = false;
                  setMsg(actionName === 'force-stop'
                    ? '运行状态：运行中（已强制重启容器内 gateway）'
                    : '运行状态：运行中', 'ok');
                  return;
                }
              } else {
                if (!gatewayRunning) {
                  window.__statusRunning = false;
                  window.__stopFailed = false;
                  // 状态行直接写 #msg（"已停止"是状态不是错误，不进持久区）
                  const mEl = document.getElementById('msg');
                  if (mEl) {
                    mEl.className = 'msg err';
                    mEl.textContent = '运行状态：已停止（容器内 gateway 已停止，容器保持运行）';
                  }
                  return;
                }
              }
            } catch {}
          }
          if (actionName === 'stop') {
            // 停止超时：gateway 疑似卡死（忽略 SIGTERM），切换按钮为强制停止。
            window.__statusRunning = true;
            window.__stopFailed = true;
            setMsg('停止失败：容器内 gateway 未响应，请点击“强制停止”', 'err');
            setInstallButtonsBusy('', false);
          } else if (actionName === 'force-stop') {
            window.__stopFailed = false;
            setMsg('强制停止失败：容器内 gateway 未能恢复', 'err');
          } else {
            window.__stopFailed = false;
            setMsg('启动失败：容器内 gateway 未就绪', 'err');
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
        // API Key 留空表示“不改/添加时由用户填写”——不预填示例 key。
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
      // Live-sync the default text/image model dropdowns with the available model list.
      refreshDefaultModelDropdownOptions(all);
    }
    // Track explicit intent to clear the default image model: picking
    // '（无默认图像模型）' sets a flag so later option rebuilds keep it empty
    // instead of resurrecting the previously set default.
    function trackImageDefaultClear(sel) {
      window.__imageDefaultCleared = (sel && sel.value === '');
    }
    function refreshDefaultModelDropdownOptions(modelIds) {
      const textSel = document.getElementById('dlg_default_text_model');
      const imageSel = document.getElementById('dlg_default_image_model');
      if (!textSel || !imageSel) return;
      const prevText = textSel.value;
      const prevImage = imageSel.value;
      const ids = Array.isArray(modelIds) ? modelIds.filter(Boolean) : [];
      // Robustly rebuild options. Avoid innerHTML + add() ordering quirks in
      // different WebKit/Safari versions used by the DSM UI shell.
      textSel.options.length = 0;
      imageSel.options.length = 0;
      textSel.appendChild(new Option('（自动选择）', ''));
      imageSel.appendChild(new Option('（无默认图像模型）', ''));
      for (const mid of ids) {
        textSel.appendChild(new Option(mid, mid));
        imageSel.appendChild(new Option(mid, mid));
      }
      // Restore previous selections if the value is still available, unless
      // the operator explicitly cleared the image default by picking
      // '（无默认图像模型）' — then keep it empty so a later refresh cannot
      // resurrect a previously set default image model.
      const textVals = Array.prototype.map.call(textSel.options, o => o.value);
      const imageVals = Array.prototype.map.call(imageSel.options, o => o.value);
      if (prevText && textVals.indexOf(prevText) >= 0) textSel.value = prevText;
      if (window.__imageDefaultCleared === true) {
        imageSel.value = '';
      } else if (prevImage && imageVals.indexOf(prevImage) >= 0) {
        imageSel.value = prevImage;
      }
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
    function setDefaultTextModelFromManual() {
      const providerId = (document.getElementById('dlg_provider_id').value || '').trim();
      let val = (document.getElementById('dlg_default_text_model_manual').value || '').trim();
      if (!val) { setModelDialogHint('请输入模型名', 'err'); return; }
      // Auto-prepend Provider ID if model name doesn't contain '/'
      if (providerId && val.indexOf('/') < 0) val = providerId + '/' + val;
      const sel = document.getElementById('dlg_default_text_model');
      let found = false;
      for (let i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === val) { sel.selectedIndex = i; found = true; break; }
      }
      if (!found) {
        const opt = document.createElement('option');
        opt.value = val; opt.textContent = val;
        sel.appendChild(opt); sel.value = val;
      }
      document.getElementById('dlg_default_text_model_manual').value = '';
      setModelDialogHint('默认文本模型已设置为: ' + val, 'ok');
    }
    function setDefaultImageModelFromManual() {
      const providerId = (document.getElementById('dlg_provider_id').value || '').trim();
      let val = (document.getElementById('dlg_default_image_model_manual').value || '').trim();
      if (!val) { setModelDialogHint('请输入模型名', 'err'); return; }
      // Auto-prepend Provider ID if model name doesn't contain '/'
      if (providerId && val.indexOf('/') < 0) val = providerId + '/' + val;
      const sel = document.getElementById('dlg_default_image_model');
      let found = false;
      for (let i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === val) { sel.selectedIndex = i; found = true; break; }
      }
      if (!found) {
        const opt = document.createElement('option');
        opt.value = val; opt.textContent = val;
        sel.appendChild(opt); sel.value = val;
      }
      document.getElementById('dlg_default_image_model_manual').value = '';
      setModelDialogHint('默认图像模型已设置为: ' + val, 'ok');
    }
    function populateDefaultModelDialogs(p) {
      // Reset explicit-clear intent on dialog open; the dropdown value set below
      // reflects the provider's real current default.
      window.__imageDefaultCleared = false;
      const textSel = document.getElementById('dlg_default_text_model');
      const imageSel = document.getElementById('dlg_default_image_model');
      if (!textSel || !imageSel) return;
      // Clear all options except placeholder (robust across WebKit variants)
      textSel.options.length = 0;
      imageSel.options.length = 0;
      // Add placeholders
      textSel.appendChild(new Option('（自动选择）', ''));
      imageSel.appendChild(new Option('（无默认图像模型）', ''));
      // Populate from provider's model list
      let modelIds = (p.models || []).map(m => m.modelId || m.id).filter(Boolean);
      // In adding mode (p.models empty), use __modelOptionPool which is populated by sync
      if (!modelIds.length && window.__modelOptionPool && window.__modelOptionPool.length) {
        modelIds = window.__modelOptionPool.slice();
      }
      for (const mid of modelIds) {
        textSel.appendChild(new Option(mid, mid));
        imageSel.appendChild(new Option(mid, mid));
      }
      // Ensure the current GLOBAL default image model appears as a chooseable
      // option even when it belongs to another provider. Otherwise editing a
      // provider whose own model list doesn't contain the global image default
      // shows （无默认图像模型）and saving clears it (误删其它 provider 的默认)
      // or cannot change it.
      const __gDim = (p.defaultImageModel || '').trim();
      if (__gDim) {
        const __gDimId = __gDim.indexOf('/') >= 0 ? __gDim.slice(__gDim.indexOf('/') + 1) : __gDim;
        let has = false;
        for (let i = 0; i < imageSel.options.length; i++) {
          if (imageSel.options[i].value === __gDim || imageSel.options[i].value === __gDimId) { has = true; break; }
        }
        if (!has && __gDimId) imageSel.appendChild(new Option(__gDim, __gDim));
      }
      // Set current defaults from provider data (display only). Show the CURRENT
      // value from the config, including the image default. This is safe now:
      // the auto-refill root cause (valid-ref normalize re-filling an empty/invalid
      // image default with the first model) is fixed in models_save, so displaying
      // the existing imageModel never re-persists it on save unless the operator
      // actively changes it. dtm/dim may be a full ref or bare id; match either.
      const dtm = (p.defaultTextModel || '').trim();
      const dtmId = dtm.indexOf('/') >= 0 ? dtm.slice(dtm.indexOf('/') + 1) : dtm;
      if (dtm) {
        for (let i = 0; i < textSel.options.length; i++) {
          const v = textSel.options[i].value;
          if (v === dtm || v === dtmId) { textSel.selectedIndex = i; break; }
        }
      }
      const dim = (p.defaultImageModel || '').trim();
      const dimId = dim.indexOf('/') >= 0 ? dim.slice(dim.indexOf('/') + 1) : dim;
      if (dim) {
        for (let i = 0; i < imageSel.options.length; i++) {
          const v = imageSel.options[i].value;
          if (v === dim || v === dimId) { imageSel.selectedIndex = i; break; }
        }
      }
    }
    function selectAllModelSelections() {
      const all = getAvailableModelIdsFromDropdown();
      setModelSelectOptions(all, all);
      setModelDialogHint('已全选模型', 'ok');
    }
    function clearAllModelSelections() {
      const all = getAvailableModelIdsFromDropdown();
      setModelSelectOptions(all, []);
      setModelDialogHint('已取消全选', 'ok');
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
      const originalId = (p.id || '').trim();
      const rawApiKey = (p.apiKeyRaw || '').trim();
      document.getElementById('modelModalTitle').textContent = editing ? '编辑模型服务器' : '添加模型服务器';
      document.getElementById('dlg_provider_preset').value = p.id && PROVIDER_PRESETS[p.id] ? p.id : (p.id === 'custom-openai' ? 'custom-openai' : 'custom-openai');
      document.getElementById('dlg_provider_id').value = p.id || '';
      document.getElementById('dlg_api').value = p.api || 'openai-completions';
      document.getElementById('dlg_base_url').value = p.baseUrl || '';
      document.getElementById('dlg_api_key').value = p.apiKeyMasked || '';
      document.getElementById('dlg_api_key').dataset.raw = rawApiKey;
      const modalMask = document.getElementById('modelModalMask');
      modalMask.dataset.originalProviderId = originalId;
      modalMask.dataset.rawModels = JSON.stringify(Array.isArray(p.rawModels) ? p.rawModels : []);
      setModelSelectOptions(currentIds, currentIds);
      if (!editing) {
        applyProviderPresetDialog();
      }
      window.__modelOptionPool = Array.isArray(currentIds) ? currentIds.slice() : [];
      populateDefaultModelDialogs(p);
      // The manual default-model inputs are entry points only; always start empty.
      document.getElementById('dlg_default_text_model_manual').value = '';
      document.getElementById('dlg_default_image_model_manual').value = '';
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
      document.getElementById('modelModalMask').dataset.originalProviderId = '';
      document.getElementById('modelModalMask').dataset.rawModels = '';
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
        // 按原逻辑：同步后全部选中。setModelSelectOptions 内部会实时刷新
        // 默认文本/图像模型下拉列表，使其与已同步/可用的模型列表保持一致。
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
        const modelModalMask = document.getElementById('modelModalMask');
        const originalProviderId = (modelModalMask.dataset.originalProviderId || '').trim();
        let rawModels = [];
        try {
          const parsed = JSON.parse(modelModalMask.dataset.rawModels || '[]');
          rawModels = Array.isArray(parsed) ? parsed : [];
        } catch (_) {}
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

        const apiKeyInput = document.getElementById('dlg_api_key');
        const apiKeyValue = (apiKeyInput && apiKeyInput.value ? apiKeyInput.value : '').trim();
        const apiKeyRaw = (apiKeyInput && apiKeyInput.dataset.raw ? apiKeyInput.dataset.raw : '').trim();
        const apiKey = (apiKeyValue && !/^\*+$/.test(apiKeyValue)) ? apiKeyValue : apiKeyRaw;

        const duplicatedId = providers.some((p, i) => i !== idx && ((p && p.id) || '').trim() === providerId);
        const duplicatedBase = baseUrl && providers.some((p, i) => i !== idx && ((p && p.baseUrl) || '').trim() === baseUrl);
        if (duplicatedId || duplicatedBase) {
          const reason = duplicatedId ? 'Provider ID 已存在' : 'Base URL 已存在';
          const prefix = idx < 0 ? '添加失败' : '保存失败';
          setModelDialogHint(prefix + '：' + reason + '，请修改后重试', 'err');
          setMsg(prefix + '：' + reason + '，请修改后重试', 'err');
          if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = oldText || '保存'; }
          return;
        }

        // 默认模型处理：图像默认只在 显式删除(选无) 或 选了值 时才提交；本来
        // 就没有（下拉显示无且用户未操作）则不提交该字段，避免误清其它 provider
        // 的全局图像默认。undefined 字段会被 JSON 省略，后端不收集。
        const __txtRaw = (document.getElementById('dlg_default_text_model').value || '').trim();
        const __imgRaw = (document.getElementById('dlg_default_image_model').value || '').trim();
        const __imgCleared = (window.__imageDefaultCleared === true);
        const provider = {
          id: providerId,
          displayName: providerId,
          api: document.getElementById('dlg_api').value,
          baseUrl: baseUrl,
          apiKey: apiKey,
          rawModels: rawModels,
          models: selectedModelIds.map(id => ({ modelId: id, id: id })),
          defaultTextModel: __txtRaw || undefined,
          defaultImageModel: (__imgCleared ? '' : (__imgRaw || undefined))
        };
        if (idx >= 0) providers[idx] = provider; else providers.push(provider);
        // 方案 C + 保护：OpenClaw 默认模型全局唯一。非编辑 provider 删除
        // defaultTextModel/defaultImageModel 字段（而非置空），使其完全不参与
        // 默认决策，也不触发误删（空字符串会让 image_refs 为空 -> else 清全局）。
        // 注意：添加模式 idx=-1，新 provider 在 push 后位于 providers.length-1，
        // 必须保留它（否则添加时设置的默认文本/图像模型会被误删，导致无法添加）。
        const __keepIdx = (idx >= 0) ? idx : (providers.length - 1);
        for (let i = 0; i < providers.length; i++) {
          if (i === __keepIdx) continue;
          if (providers[i] && typeof providers[i] === 'object') {
            delete providers[i].defaultTextModel;
            delete providers[i].defaultImageModel;
          }
        }
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
    async function deleteModelProvider(idOrIndex) {
      try {
      const data = window.__modelsData || {};
      const providers = (data.configuredProviders || []);
      // Resolve target index: delete by provider ID (string) or legacy index (number)
      let index = -1;
      if (typeof idOrIndex === 'string' && idOrIndex !== '') {
        index = providers.findIndex(p => (p && (p.id || '') === idOrIndex));
      } else if (typeof idOrIndex === 'number') {
        index = idOrIndex;
      }
      if (index < 0 || index >= providers.length) {
        setMsg('删除失败：未找到对应的模型服务器', 'err');
        return;
      }
      const pName = providers[index] ? (providers[index].displayName || providers[index].id || '未命名服务') : '该服务器';
      if (!confirm('确认要删除“' + pName + '”吗？')) { return; }
      const providersCopy = providers.slice();
      providersCopy.splice(index, 1);
      await api('models_save', 'POST', { providers: providersCopy, applyNow: false });
      await load('models');
      setMsg('模型服务器“' + pName + '”已删除，重启后生效', 'ok');
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
        payload = { 'openclaw-weixin': { enabled: true } };
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
              const sv = await api('channels_save', 'POST', { 'openclaw-weixin': { enabled: true }, noReload: true });
              if (sv && sv.error) throw new Error(sv.error);
              setMsg('微信已连接（已立即保存）', 'ok');
              // 第二步：后台再做热加载（不阻塞 UI）
              api('channels_save', 'POST', { 'openclaw-weixin': { enabled: true } }).catch(() => {});
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
        return p.indexOf('/webman/3rdparty/openclaw/') === 0 || p.indexOf('/webman/index.cgi') === 0;
      } catch (_) {
        return false;
      }
    }
    function resolveTerminalUrl() {
      // Direct ttyd port. ttyd runs with --base-path /openclaw-terminal/, so the
      // root path returns 404; the iframe must request the base-path URL.
      const port = String(window.__ainasTerminalPort || '17682');
      return 'http://' + window.location.hostname + ':' + port + '/openclaw-terminal/';
    }
    function buildOpenclawWebUrl() {
      // Direct gateway port only. DSM nginx alias is unreliable (lost on reboot).
      var token = String(window.__ainasGatewayToken || '').trim();
      var port = String(window.__ainasGatewayPort || '58789');
      var base = 'http://' + window.location.hostname + ':' + port + '/openclaw-web';
      return token ? (base + '/chat?token=' + encodeURIComponent(token)) : (base + '/chat');
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
