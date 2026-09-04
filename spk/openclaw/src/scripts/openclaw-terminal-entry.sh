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
# After one-time panel authorization (授权面板操作), you can run docker as
# root here with:  sudo docker exec ...  /  sudo docker logs ...
alias oc-exec='sudo docker exec openclaw node /data/runtime/openclaw.mjs'
alias oc-compose='sudo docker compose -f /var/packages/openclaw/target/app/docker-compose.admin.yaml'
alias oc-logs='sudo docker logs --tail 200 openclaw'
alias oc-restart='sudo synopkg restart openclaw'

if [ -x /bin/bash ]; then
  exec /bin/bash -i
fi
exec /bin/sh -i
