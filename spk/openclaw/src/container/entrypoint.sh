#!/bin/sh
# OpenClaw container entrypoint (overrides the image default).
#
# The container image is FIXED and serves only as:
#   - the Node.js runtime environment
#   - the initial OpenClaw seed (/app)
#
# The OpenClaw application itself lives in the persistent volume /data/runtime
# so it can be updated in-place (npm) without changing the image, and updates
# survive container restarts.
set -eu

RUNTIME_DIR="${OPENCLAW_RUNTIME_DIR:-/data/runtime}"
CONF_DIR="${OPENCLAW_CONF_DIR:-/home/node/.openclaw}"
SEED_DIR="/app"

# --- 1. Seed: copy the fixed image's OpenClaw into the persistent volume ---
if [ ! -f "${RUNTIME_DIR}/openclaw.mjs" ]; then
    echo "[openclaw-entry] seeding runtime from image ${SEED_DIR} -> ${RUNTIME_DIR}"
    mkdir -p "${RUNTIME_DIR}"
    cp -a "${SEED_DIR}/." "${RUNTIME_DIR}/"
    # record the seeded image version so the UI can show base vs. running
    if [ -f "${SEED_DIR}/package.json" ]; then
        seed_ver="$(grep -m1 '"version"' "${SEED_DIR}/package.json" | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
        echo "seeded=${seed_ver:-unknown}" > "${RUNTIME_DIR}/.image-version"
    fi
fi

# --- 2. Optional update marker: if the updater left a request, run it ---
UPDATE_MARKER="${RUNTIME_DIR}/.update-requested"
if [ -f "${UPDATE_MARKER}" ]; then
    echo "[openclaw-entry] update marker present, running updater"
    if [ -x /data/scripts/update-openclaw.sh ]; then
        /data/scripts/update-openclaw.sh || {
            echo "[openclaw-entry] update failed; starting with existing runtime" >&2
        }
    fi
    rm -f "${UPDATE_MARKER}"
fi

# --- 3. Start the gateway from the persistent runtime ---
if [ ! -f "${RUNTIME_DIR}/openclaw.mjs" ]; then
    echo "[openclaw-entry] FATAL: no openclaw runtime at ${RUNTIME_DIR}/openclaw.mjs" >&2
    exit 1
fi

cd "${RUNTIME_DIR}"
exec node openclaw.mjs gateway --allow-unconfigured "$@"
