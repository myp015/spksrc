#!/bin/sh
# resolve-versions.sh
#
# Dynamically resolve the LATEST STABLE release tag of CLIProxyAPI from
# GitHub. This lets the cliproxy SPK track upstream releases automatically
# instead of hand-pinning a version in the Makefile.
#
# Usage:
#   resolve-versions.sh [--json]
#
# Without --json it prints shell lines consumable by Make:
#   PKG_VERSION=7.2.147
#   SPK_VERSION=7.2.147
#
# With --json it prints a single JSON object of the same data.
#
# Robustness: uses curl against the public GitHub API. If the lookup fails
# (offline, rate limit, curl missing) it falls back to a pinned default so the
# build never hard-fails purely on registry unavailability.

set -u

# Fallback pin (used only when the GitHub API is unreachable). Keep roughly
# current; it is overridden by the live lookup when online.
DEFAULT_VERSION=6.9.26

REPO="router-for-me/CLIProxyAPI"

fetch_latest() {
  _out=""
  if command -v curl >/dev/null 2>&1; then
    _out="$(curl -fsSL --retry 3 --retry-delay 1 --max-time 20 \
      "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null \
      | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
      | head -n1)"
  fi
  printf '%s' "$_out"
}

VERSION="$(fetch_latest)"
# Strip any leading 'v' (tags look like v7.2.147).
VERSION="${VERSION#v}"
[ -z "$VERSION" ] && VERSION="$DEFAULT_VERSION"

if [ "${1:-}" = "--json" ]; then
  printf '{"PKG_VERSION":"%s","SPK_VERSION":"%s"}\n' "$VERSION" "$VERSION"
else
  printf 'PKG_VERSION=%s\n' "$VERSION"
  printf 'SPK_VERSION=%s\n' "$VERSION"
fi
