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
DEFAULT_OPENCLAW=2026.7.1-2
DEFAULT_FEISHU=2026.7.1
DEFAULT_DINGTALK=3.6.10
DEFAULT_WECOM=3.4.0
DEFAULT_QQBOT=2.0.0
DEFAULT_WEIXIN=2.4.6

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
        | awk 'begin{in_tags=0} /"dist-tags"[[:space:]]*:/{in_tags=1;next} in_tags && /"latest"[[:space:]]*:/{gsub(/[",]/,""); for(i=1;i<=NF;i++){if($i ~ /^latest:/){split($i,a,":");print a[2];exit}}} in_tags && /}/{in_tags=0}')"
    fi
  fi
  # If curl missing or empty, try node-less fallback: none available; echo default upstream later.
  printf '%s' "$_out"
}

# strip_build_suffix <version> -> clean base semver (drops trailing -N)
# e.g. 2026.7.1-2 -> 2026.7.1 ; 2026.7.1 -> 2026.7.1
strip_build_suffix() {
  printf '%s' "$1" | sed -E 's/-[0-9]+$//'
}

OPENCLAW="$(fetch_latest "openclaw")"
[ -z "$OPENCLAW" ] && OPENCLAW="$DEFAULT_OPENCLAW"

FEISHU="$(fetch_latest "@openclaw%2Ffeishu")"
[ -z "$FEISHU" ] && FEISHU="$DEFAULT_FEISHU"

DINGTALK="$(fetch_latest "@soimy%2Fdingtalk")"
[ -z "$DINGTALK" ] && DINGTALK="$DEFAULT_DINGTALK"

WECOM="$(fetch_latest "@sunnoy%2Fwecom")"
[ -z "$WECOM" ] && WECOM="$DEFAULT_WECOM"

QQBOT="$(fetch_latest "@tencent-connect%2Fopenclaw-qqbot")"
[ -z "$QQBOT" ] && QQBOT="$DEFAULT_QQBOT"

WEIXIN="$(fetch_latest "@tencent-weixin%2Fopenclaw-weixin")"
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
