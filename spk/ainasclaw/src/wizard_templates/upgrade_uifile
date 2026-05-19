#!/bin/bash
set -eu

json_get() {
  python3 - "$1" "$2" <<'PY'
import json, sys
path = sys.argv[1]
key = sys.argv[2]
try:
    data = json.load(open(path, 'r', encoding='utf-8'))
except Exception:
    print('')
    raise SystemExit(0)
cur = data
for part in key.split('.'):
    if isinstance(cur, dict):
        cur = cur.get(part)
    else:
        cur = None
    if cur is None:
        break
if cur is None:
    print('')
elif isinstance(cur, (int, float)):
    print(str(cur))
else:
    print(str(cur).strip())
PY
}

read_first_existing() {
  for p in "$@"; do
    [ -f "$p" ] || continue
    cat "$p" 2>/dev/null | tr -d '\r' | tr -d '\n'
    return 0
  done
  printf ''
}

normalize_workspace() {
  case "$1" in
    */.openclaw) printf '%s' "${1%/.openclaw}" ;;
    *) printf '%s' "$1" ;;
  esac
}

workspace_home="$(read_first_existing \
  /var/packages/ainasclaw/var/workspace.home.path \
  /var/packages/openclaw/var/workspace.home.path)"

if [ -z "$workspace_home" ]; then
  workspace_home="$(read_first_existing \
    /var/packages/ainasclaw/var/workspace.path \
    /var/packages/openclaw/var/workspace.path)"
fi

if [ -z "$workspace_home" ]; then
  workspace_home="/volume1/openclaw"
fi
workspace_home="$(normalize_workspace "$workspace_home")"

config_path=""
for p in \
  "$workspace_home/.openclaw/openclaw.json" \
  /var/packages/ainasclaw/var/openclaw.json \
  /var/packages/openclaw/var/openclaw.json \
  "$workspace_home/openclaw.json"
do
  if [ -f "$p" ]; then
    config_path="$p"
    break
  fi
done

current_workspace="$workspace_home"
current_port="58789"

if [ -n "$config_path" ]; then
  cfg_workspace="$(json_get "$config_path" 'agents.defaults.workspace')"
  cfg_port="$(json_get "$config_path" 'gateway.port')"
  if [ -n "$cfg_workspace" ]; then
    current_workspace="$(normalize_workspace "$cfg_workspace")"
  fi
  if [ -n "$cfg_port" ]; then
    current_port="$cfg_port"
  fi
fi

cat >"${SYNOPKG_TEMP_LOGFILE}" <<EOF
[{ 
  "step_title": "{{{CONFIGURATION_TITLE}}}",
  "items": [{
    "type": "textfield",
    "desc": "{{{WORKSPACE_DIR_DESCRIPTION}}}",
    "subitems": [{
      "key": "wizard_workspace_dir",
      "defaultValue": "${current_workspace}",
      "desc": "{{{WORKSPACE_DIR_LABEL}}}",
      "disabled": true,
      "validator": {
        "allowBlank": false
      }
    }]
  },{
    "type": "textfield",
    "desc": "{{{GATEWAY_PORT_DESCRIPTION}}}",
    "subitems": [{
      "key": "wizard_gateway_port",
      "defaultValue": "${current_port}",
      "desc": "{{{GATEWAY_PORT_LABEL}}}",
      "disabled": true,
      "validator": {
        "allowBlank": false
      }
    }]
  },{
    "desc": "升级时自动读取当前已安装实例的用户目录和端口，不允许在向导中修改。"
  },{
    "desc": "{{{INSTALLATION_NOTES_TITLE}}}{{{INSTALLATION_NOTES_TEXT1}}}"
  }]
}]
EOF
