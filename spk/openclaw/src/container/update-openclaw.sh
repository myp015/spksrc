#!/bin/sh
# OpenClaw self-update (runs INSIDE the container, invoked by the SPK host via
# `docker exec openclaw /data/scripts/update-openclaw.sh`).
#
# Updates ONLY the OpenClaw application payload (dist/, openclaw.mjs,
# package.json, docs/, skills/, extensions/, ...) while preserving the existing
# node_modules dependency tree. New/changed transitive deps are added with an
# incremental `npm install` against the retained node_modules. The image and
# container are untouched.
#
# Exit codes: 0 = updated or already-latest, 1 = failed.
set -eu

RUNTIME_DIR="${OPENCLAW_RUNTIME_DIR:-/data/runtime}"
TARGET_VERSION="${1:-latest}"          # 'latest', a semver, or explicit e.g. 2026.8.2
WORK_TMP="$(mktemp -d /tmp/oc-update.XXXXXX)"
trap 'rm -rf "${WORK_TMP}"' EXIT

log() { echo "[openclaw-update] $*"; }

if [ ! -f "${RUNTIME_DIR}/openclaw.mjs" ]; then
    log "FATAL: runtime missing at ${RUNTIME_DIR}/openclaw.mjs (seed first)" >&2
    exit 1
fi

# --- determine current installed version ---
CURRENT="unknown"
if [ -f "${RUNTIME_DIR}/package.json" ]; then
    CURRENT="$(grep -m1 '"version"' "${RUNTIME_DIR}/package.json" | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
fi

log "current=${CURRENT} target=${TARGET_VERSION}"

# --- resolve the actual target version from the npm registry ---
if [ "${TARGET_VERSION}" = "latest" ]; then
    TARGET_VERSION="$(npm view openclaw version 2>/dev/null || true)"
    if [ -z "${TARGET_VERSION}" ]; then
        log "FATAL: could not resolve latest openclaw version" >&2
        exit 1
    fi
fi

log "resolved target=${TARGET_VERSION}"

# already up to date?
if [ "${TARGET_VERSION}" = "${CURRENT}" ]; then
    log "already at ${CURRENT}, nothing to do"
    echo "{\"updated\":false,\"current\":\"${CURRENT}\",\"target\":\"${TARGET_VERSION}\"}"
    exit 0
fi

# --- download the openclaw package tarball for the target version ---
log "downloading openclaw@${TARGET_VERSION}"
if ! (cd "${WORK_TMP}" && npm pack "openclaw@${TARGET_VERSION}" --silent); then
    log "FATAL: npm pack openclaw@${TARGET_VERSION} failed" >&2
    exit 1
fi
TBALL="$(ls "${WORK_TMP}"/openclaw-*.tgz 2>/dev/null | head -n1 || true)"
if [ -z "${TBALL}" ]; then
    log "FATAL: no tarball produced" >&2
    exit 1
fi

mkdir -p "${WORK_TMP}/pkg"
tar -xzf "${TBALL}" -C "${WORK_TMP}/pkg" --strip-components=1

# --- verify the payload looks like an openclaw install ---
if [ ! -f "${WORK_TMP}/pkg/openclaw.mjs" ]; then
    log "FATAL: downloaded payload has no openclaw.mjs" >&2
    exit 1
fi

# --- staged swap: write into a sibling dir then flip, preserving node_modules ---
STAGE_DIR="$(dirname "${RUNTIME_DIR}")/.runtime-stage.$$"
rm -rf "${STAGE_DIR}"
cp -a "${RUNTIME_DIR}" "${STAGE_DIR}"

# overwrite the app payload, keep existing node_modules
( cd "${WORK_TMP}/pkg" && tar -cf - . ) | ( cd "${STAGE_DIR}" && tar -xf - )

# incremental install of any new/updated deps against retained node_modules
log "incremental npm install (new deps) ..."
( cd "${STAGE_DIR}" && npm install --omit=dev --legacy-peer-deps --no-audit --no-fund >/dev/null 2>&1 ) || log "warn: incremental npm install had issues (non-fatal)"

# --- flip stage into place ---
BACKUP_DIR="$(dirname "${RUNTIME_DIR}")/.runtime-bak.$$"
rm -rf "${BACKUP_DIR}"
mv "${RUNTIME_DIR}" "${BACKUP_DIR}"
mv "${STAGE_DIR}" "${RUNTIME_DIR}"
rm -rf "${BACKUP_DIR}"

NEW_VERSION="$(grep -m1 '"version"' "${RUNTIME_DIR}/package.json" | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
echo "{\"updated\":true,\"from\":\"${CURRENT}\",\"to\":\"${NEW_VERSION}\"}"
log "updated ${CURRENT} -> ${NEW_VERSION}"
exit 0
