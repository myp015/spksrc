#!/bin/sh
# OpenClaw terminal entry — launched by ttyd.
#
# The terminal shell starts in the OpenClaw data workspace. Commands like
# `docker compose` (host) and `openclaw` (in-container) can be run from here.
set -eu

DATA_DIR="/volume1/docker/openclaw"
if [ -r "/var/packages/openclaw/var/data-dir" ]; then
  d="$(cat /var/packages/openclaw/var/data-dir 2>/dev/null | tr -d '\r' | tr -d '\n')"
  [ -n "$d" ] && DATA_DIR="$d"
fi

WS="${DATA_DIR}/workspace"
mkdir -p "$WS" 2>/dev/null || true
cd "$WS" 2>/dev/null || true
export HOME="$WS"
export OPENCLAW_WORKSPACE_DIR="$WS"
export PATH="/usr/local/bin:/usr/sbin:/usr/bin:/bin:${PATH}"

# Convenience aliases for common host-level operations.
alias oc-compose='docker compose -f /var/packages/openclaw/target/app/docker-compose.admin.yaml'
alias oc-logs='docker logs --tail 200 openclaw'
alias oc-restart='synopkg restart openclaw'

if [ -x /bin/bash ]; then
  exec /bin/bash -i
fi
exec /bin/sh -i
