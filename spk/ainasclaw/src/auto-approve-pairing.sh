#!/bin/sh
set -u
OPENCLAW="/var/packages/ainasclaw/target/bin/openclaw"
NODE="/var/packages/ainasclaw/target/bin/node"
CFG="/volume1/openclaw/.openclaw/openclaw.json"
SECRETS="/volume1/openclaw/.openclaw/secrets.json"
export PATH="$(dirname "$OPENCLAW"):$PATH"

# Resolve the file-backed gateway SecretRef without exposing it in logs.
TOKEN="$($NODE - "$CFG" "$SECRETS" <<'NODE' 2>/dev/null
const fs=require("fs");
try {
  const c=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
  let s={}; try{s=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));}catch{}
  const t=c.gateway?.auth?.token;
  process.stdout.write(typeof t==="string" ? t : (s.gateway?.auth?.token || ""));
} catch {}
NODE
)"
[ -n "$TOKEN" ] || exit 0

for i in $(seq 1 30); do
  "$OPENCLAW" devices list --json --token "$TOKEN" >/dev/null 2>&1 && break
  sleep 2
done
while true; do
  "$OPENCLAW" devices list --json --token "$TOKEN" 2>/dev/null | "$NODE" -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{const j=JSON.parse(s);for(const r of (j.pending||[]))if(r.requestId)console.log(r.requestId)}catch{}})' | while read -r reqid; do
    "$OPENCLAW" devices approve --token "$TOKEN" "$reqid" >/dev/null 2>&1 || true
  done
  sleep 10
done
