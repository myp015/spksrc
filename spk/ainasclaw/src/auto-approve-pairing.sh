#!/bin/sh
# auto-approve-pairing.sh
# Background script that auto-approves pending device pairing requests.
# Runs as the service user alongside the gateway.
#
# Usage: auto-approve-pairing.sh <token>

TOKEN="${1:-}"
[ -z "$TOKEN" ] && exit 0

OPENCLAW="/var/packages/ainasclaw/target/bin/openclaw"
export PATH="$(dirname "$OPENCLAW"):$PATH"

# Wait for gateway to be ready
for i in $(seq 1 30); do
  if "$OPENCLAW" gateway status >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# Poll for pending pairing requests and approve them
while true; do
  # List pending requests and extract request IDs
  pending=$("$OPENCLAW" devices list --json --token "$TOKEN" 2>/dev/null | "$OPENCLAW" -e 'const fs=require("fs");let x="";process.stdin.on("data",d=>x+=d).on("end",()=>{try{const j=JSON.parse(x);for(const r of (j.pending||j.requests||[]))if(r.requestId)console.log(r.requestId)}catch{}})' | head -5)
  for reqid in $pending; do
    "$OPENCLAW" devices approve --token "$TOKEN" "$reqid" >/dev/null 2>&1 && \
      echo "[auto-approve] approved device pairing: $reqid" >> /var/packages/ainasclaw/var/ainasclaw.log
  done
  sleep 10
done
