#!/bin/sh
# OpenClaw terminal entry — launched by ttyd (host side).
#
# After the one-time panel authorization (授权面板操作), /etc/sudoers.d/openclaw-ui
# lets the service user (sc-openclaw) re-exec this script as root, so the web
# terminal becomes a root shell that starts in /root and shows the
# root@hostname:/root# prompt. Before authorization it runs as sc-openclaw in
# the OpenClaw data workspace. Either way the prompt shows user@host:current-dir.
set -eu

SELF="/var/packages/openclaw/target/scripts/openclaw-terminal-entry.sh"

# Resolve the OpenClaw data dir (workspace for the unprivileged fallback).
DATA_DIR="/volume1/docker/openclaw"
if [ -r "/var/packages/openclaw/var/data-dir" ]; then
  d="$(cat /var/packages/openclaw/var/data-dir 2>/dev/null | tr -d '\r' | tr -d '\n')"
  [ -n "$d" ] && DATA_DIR="$d"
fi
WS="${DATA_DIR}/workspace"

# --- Elevate to root once authorized ------------------------------------
# sudo -n -l only checks whether the NOPASSWD rule allows this script; it does
# not run anything. When the rule exists (授权面板操作 done), re-exec as root.
if [ "$(id -u)" != "0" ]; then
  if sudo -n -l "$SELF" >/dev/null 2>&1; then
    exec sudo -n "$SELF"
  fi
  # otherwise: unprivileged fallback below (pre-authorization).
fi

export PATH="/usr/local/bin:/usr/sbin:/usr/bin:/bin:${PATH}"

if [ "$(id -u)" = "0" ]; then
  # Root shell: sudo already reset HOME to /root; start there.
  cd /root 2>/dev/null || cd "$WS" 2>/dev/null || true
  export HOME="/root"
else
  # Pre-authorization: workspace shell as the service user.
  mkdir -p "$WS" 2>/dev/null || true
  cd "$WS" 2>/dev/null || true
  export OPENCLAW_WORKSPACE_DIR="$WS"
  if touch "$WS/.bashrc" 2>/dev/null; then
    export HOME="$WS"
  else
    ALT_HOME="/tmp/openclaw-term-$(id -u)"
    mkdir -p "$ALT_HOME"
    export HOME="$ALT_HOME"
  fi
fi

# Prompt: user@hostname:current-dir ($ for users, # for root). Set in env and
# persisted in ~/.bashrc (idempotent) so it survives `exec bash -i`.
export PS1='\[\e[0;32m\]\u@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '

RC="$HOME/.bashrc"
if [ ! -e "$RC" ]; then
  touch "$RC" 2>/dev/null || true
fi
if [ -w "$RC" ] && ! grep -q "openclaw-terminal-rc" "$RC" 2>/dev/null; then
  cat >> "$RC" <<'EOF'
# --- openclaw-terminal-rc (idempotent) ---
# Prompt: user@hostname:current-dir ($/#). Overrides the bare DSM hostname prompt.
PS1='\[\e[0;32m\]\u@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '
# docker helpers (root needs no sudo; before authorization sudo -n fails cleanly)
docker() { command sudo -n /usr/local/bin/docker "$@"; }
alias oc-exec='command sudo -n /usr/local/bin/docker exec openclaw node /data/runtime/openclaw.mjs'
alias oc-compose='command sudo -n /usr/local/bin/docker compose -f /var/packages/openclaw/target/app/docker-compose.admin.yaml'
alias oc-logs='command sudo -n /usr/local/bin/docker logs --tail 200 openclaw'
alias oc-restart='command sudo -n /usr/local/bin/docker restart openclaw'
# --- end openclaw-terminal-rc ---
EOF
fi

if [ -x /bin/bash ]; then
  exec /bin/bash -i
fi
exec /bin/sh -i
