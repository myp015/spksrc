#!/bin/sh
# resolve-versions.sh
#
# Dynamically resolve the LATEST STABLE version of the OpenClaw core package
# and its bundled channel plugins from the npm registry (dist-tags.latest).
# This lets the ainasclaw build track upstream releases automatically instead
# of requiring maintainers to hand-pin versions in the Makefile.
#
# Usage:
#   resolve-versions.sh [--json]
#
# Without --json it prints shell lines consumable by Make:
#   OPENCLAW_NPM_VERSION=2026.7.1-2
#   OPENCLAW_SPK_VERSION=2026.7.1
#   FEISHU_VERSION=2026.7.1
#   DINGTALK_VERSION=3.6.10
#   WECOM_VERSION=3.4.0
#   QQ_BOT_VERSION=2.0.0
#   WEIXIN_VERSION=2.4.6
#
# With --json it prints a single JSON object of the same data.
#
# Robustness: uses curl against the public npm registry (no npm binary needed,
# matching how the Makefile resolves the Node runtime version). If a lookup
# fails, the script falls back to a pinned default so the build never hard-fails
# purely on registry unavailability.

set -u

# ---------------------------------------------------------------------------
# Fallback pins (used only when the npm registry is unreachable). Keep these
# roughly current; they are overridden by live registry lookups when online.
# ---------------------------------------------------------------------------
DEFAULT_OPENCLAW=2026.8.1-2
DEFAULT_FEISHU=2026.8.1
DEFAULT_DINGTALK=3.7.1
DEFAULT_WECOM=3.5.0
DEFAULT_QQBOT=2.1.0
DEFAULT_WEIXIN=2.5.1

REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"

# fetch_latest <package-name> -> prints dist-tags.latest
fetch_latest() {
  _pkg="$1"
  _out=""
  if command -v curl >/dev/null 2>&1; then
    _out="$(curl -fsSL --retry 3 --retry-delay 1 --max-time 20 \
      "${REGISTRY}/${_pkg}" 2>/dev/null \
      | sed -n 's/.*"latest":[[:space:]]*"\([^"]*\)".*/\1/p')"
    # The regex above only catches "latest" on the same line as a quoted value.
    # Fallback: parse with a small awk that finds the dist-tags.latest robustly.
    if [ -z "$_out" ]; then
      _out="$(curl -fsSL --retry 3 --retry-delay 1 --max-time 20 \
        "${REGISTRY}/${_pkg}" 2>/dev/null \
        | awk 'BEGIN{in_tags=0} /"dist-tags"[[:space:]]*:/{in_tags=1;next} in_tags && /"latest"[[:space:]]*:/{gsub(/[",]/,""); for(i=1;i<=NF;i++){if($i ~ /^latest:/){split($i,a,":");print a[2];exit}}} in_tags && /}/{in_tags=0}')"
    fi
  fi
  # If curl missing or empty, try node-less fallback: none available; echo default upstream later.
  printf '%s' "$_out"
}

# fetch_matching_or_latest <package-name> <target-base-version>
# Try to find a published version matching the target base version (e.g. 2026.7.1).
# If no exact match exists, fall back to dist-tags.latest.
# This prevents channel plugins from jumping ahead of the core version.
fetch_matching_or_latest() {
  _pkg="$1"
  _target="$2"
  _latest="$(fetch_latest "${_pkg}")"

  # If target is empty, just return latest.
  if [ -z "$_target" ]; then
    printf '%s' "$_latest"
    return
  fi

  # Fetch all versions and check if target exists.
  _matched=""
  if command -v curl >/dev/null 2>&1; then
    _matched="$(curl -fsSL --retry 3 --retry-delay 1 --max-time 20 \
      "${REGISTRY}/${_pkg}" 2>/dev/null \
      | python3 -c '
import json,sys
d=json.load(sys.stdin)
vs=d.get("versions",{})
target=sys.argv[1]
if target in vs:
    print(target)
' "${_target}" 2>/dev/null)"
  fi

  if [ -n "$_matched" ]; then
    printf '%s' "$_matched"
  else
    printf '%s' "$_latest"
  fi
}

# strip_build_suffix <version> -> clean base semver (drops trailing -N)
# e.g. 2026.7.1-2 -> 2026.7.1 ; 2026.7.1 -> 2026.7.1
strip_build_suffix() {
  printf '%s' "$1" | sed -E 's/-[0-9]+$//'
}

OPENCLAW="$(fetch_latest "openclaw")"
[ -z "$OPENCLAW" ] && OPENCLAW="$DEFAULT_OPENCLAW"

# Derive base version for channel plugin alignment.
# e.g. 2026.7.1-2 -> 2026.7.1 ; 2026.8.1 -> 2026.8.1
OPENCLAW_BASE="$(strip_build_suffix "$OPENCLAW")"

# Channel plugins: prefer the version matching the core base, fall back to latest.
# This prevents a 2026.8.x plugin from being bundled with a 2026.7.x core.
FEISHU="$(fetch_matching_or_latest "@openclaw%2Ffeishu" "$OPENCLAW_BASE")"
[ -z "$FEISHU" ] && FEISHU="$DEFAULT_FEISHU"

DINGTALK="$(fetch_matching_or_latest "@soimy%2Fdingtalk" "$OPENCLAW_BASE")"
[ -z "$DINGTALK" ] && DINGTALK="$DEFAULT_DINGTALK"

WECOM="$(fetch_matching_or_latest "@sunnoy%2Fwecom" "$OPENCLAW_BASE")"
[ -z "$WECOM" ] && WECOM="$DEFAULT_WECOM"

QQBOT="$(fetch_matching_or_latest "@tencent-connect%2Fopenclaw-qqbot" "$OPENCLAW_BASE")"
[ -z "$QQBOT" ] && QQBOT="$DEFAULT_QQBOT"

WEIXIN="$(fetch_matching_or_latest "@tencent-weixin%2Fopenclaw-weixin" "$OPENCLAW_BASE")"
[ -z "$WEIXIN" ] && WEIXIN="$DEFAULT_WEIXIN"

SPK_VERSION="$(strip_build_suffix "$OPENCLAW")"
[ -z "$SPK_VERSION" ] && SPK_VERSION="$(strip_build_suffix "$DEFAULT_OPENCLAW")"

if [ "${1:-}" = "--json" ]; then
  printf '{"openclaw":"%s","spkVersion":"%s","feishu":"%s","dingtalk":"%s","wecom":"%s","qqbot":"%s","weixin":"%s"}\n' \
    "$OPENCLAW" "$SPK_VERSION" "$FEISHU" "$DINGTALK" "$WECOM" "$QQBOT" "$WEIXIN"
else
  printf 'OPENCLAW_NPM_VERSION=%s\n' "$OPENCLAW"
  printf 'OPENCLAW_SPK_VERSION=%s\n' "$SPK_VERSION"
  printf 'FEISHU_VERSION=%s\n' "$FEISHU"
  printf 'DINGTALK_VERSION=%s\n' "$DINGTALK"
  printf 'WECOM_VERSION=%s\n' "$WECOM"
  printf 'QQ_BOT_VERSION=%s\n' "$QQBOT"
  printf 'WEIXIN_VERSION=%s\n' "$WEIXIN"
fi
