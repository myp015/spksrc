OPENCLAW_NODE="${SYNOPKG_PKGDEST}/bin/node"
OPENCLAW_APP_DIR="${SYNOPKG_PKGDEST}/app/openclaw"
OPENCLAW_ENTRY="${OPENCLAW_APP_DIR}/dist/index.js"
OPENCLAW_WORKSPACE_DEFAULT="/volume1/docker/openclaw"
OPENCLAW_STATE_DIR_BASE="${OPENCLAW_WORKSPACE_DEFAULT}/.openclaw"
OPENCLAW_CONFIG_FILE_BASE="${OPENCLAW_STATE_DIR_BASE}/openclaw.json"
OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE_DEFAULT}"
OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR_BASE}"
OPENCLAW_CONFIG_FILE="${OPENCLAW_CONFIG_FILE_BASE}"
OPENCLAW_LEGACY_CONFIG_FILE="${SYNOPKG_PKGVAR}/openclaw.json"
OPENCLAW_TEMPLATE_CONFIG="${SYNOPKG_PKGDEST}/app/openclaw/config/openclaw.template.json"
LOG_FILE="${SYNOPKG_PKGVAR}/openclaw2.log"
PID_FILE="${SYNOPKG_PKGVAR}/openclaw2.pid"

resolve_state_dir_from_workspace() {
    local ws="$1"
    case "${ws}" in
        */.openclaw) echo "${ws}" ;;
        *) echo "${ws}/.openclaw" ;;
    esac
}

resolve_home_dir_from_workspace() {
    local ws="$1"
    case "${ws}" in
        */.openclaw) dirname "${ws}" ;;
        *) echo "${ws}" ;;
    esac
}

sync_skills_to_workspace() {
    OPENCLAW_BUNDLED_SKILLS_DIR="${OPENCLAW_STATE_DIR}/skills/_bundled"
    mkdir -p "${OPENCLAW_BUNDLED_SKILLS_DIR}"

    # Sync built-in extension skills from OpenClaw core bundle.
    if [ -d "${OPENCLAW_APP_DIR}/dist/extensions" ]; then
        find "${OPENCLAW_APP_DIR}/dist/extensions" -mindepth 2 -maxdepth 2 -type d -name skills | while read -r skills_dir; do
            plugin_id="$(basename "$(dirname "${skills_dir}")")"
            target_dir="${OPENCLAW_BUNDLED_SKILLS_DIR}/${plugin_id}"
            rm -rf "${target_dir}"
            mkdir -p "${target_dir}"
            cp -a "${skills_dir}/." "${target_dir}/"
        done
    fi

    # Sync plugin skills from bundled npm plugins.
    if [ -d "${OPENCLAW_APP_DIR}/node_modules" ]; then
        find "${OPENCLAW_APP_DIR}/node_modules" -mindepth 2 -maxdepth 4 -type d -name skills | while read -r skills_dir; do
            rel_pkg="${skills_dir#${OPENCLAW_APP_DIR}/node_modules/}"
            rel_pkg="${rel_pkg%/skills}"
            plugin_id="$(echo "${rel_pkg}" | tr '/' '_')"
            target_dir="${OPENCLAW_BUNDLED_SKILLS_DIR}/${plugin_id}"
            rm -rf "${target_dir}"
            mkdir -p "${target_dir}"
            cp -a "${skills_dir}/." "${target_dir}/"
        done
    fi
}

sync_bundled_channel_plugins_to_extensions() {
    local ext_dir="${OPENCLAW_STATE_DIR}/extensions"
    mkdir -p "${ext_dir}"

    # Let extensions resolve bundled runtime deps from app/node_modules.
    rm -f "${ext_dir}/node_modules"
    ln -s "${OPENCLAW_APP_DIR}/node_modules" "${ext_dir}/node_modules"

    # Keep channel plugins discoverable under workspace/extensions while preserving
    # Node module resolution from app/node_modules via symlink (avoids missing hoisted deps).
    for src in \
        "${OPENCLAW_APP_DIR}/node_modules/@larksuiteoapi/feishu-openclaw-plugin" \
        "${OPENCLAW_APP_DIR}/node_modules/@soimy/dingtalk" \
        "${OPENCLAW_APP_DIR}/node_modules/@sunnoy/wecom" \
        "${OPENCLAW_APP_DIR}/node_modules/@tencent-connect/openclaw-qqbot"
    do
        [ -d "${src}" ] || continue
        [ -f "${src}/openclaw.plugin.json" ] || continue

        local pkg_name
        pkg_name="$(basename "${src}")"
        local target_dir="${ext_dir}/${pkg_name}"

        rm -rf "${target_dir}"
        mkdir -p "${target_dir}"
        cp -a "${src}/." "${target_dir}/"
    done
}

harden_extension_permissions() {
    local ext_dir="${OPENCLAW_STATE_DIR}/extensions"
    [ -d "${ext_dir}" ] || return 0

    # Ownership policy: keep extensions owner consistent with workspace (.openclaw).
    # Do not force root ownership here.

    # OpenClaw blocks plugins under writable paths. Normalize perms conservatively.
    find "${ext_dir}" -type d -exec chmod 755 {} \; 2>/dev/null || true
    find "${ext_dir}" -type f -exec chmod 644 {} \; 2>/dev/null || true
    # Ensure no world-writable bits remain.
    find "${ext_dir}" -perm -0002 -exec chmod o-w {} \; 2>/dev/null || true
    [ -f "${OPENCLAW_CONFIG_FILE}" ] && chmod 600 "${OPENCLAW_CONFIG_FILE}" 2>/dev/null || true
}

validate_or_rollback_config() {
    local lkg="${OPENCLAW_STATE_DIR}/openclaw.last-known-good.json"

    # Lightweight guard only: avoid running `doctor --fix` on every start (too slow, may perform network checks).
    if "${OPENCLAW_NODE}" -e 'const fs=require("fs"); const p=process.argv[1]; JSON.parse(fs.readFileSync(p,"utf8"));' "${OPENCLAW_CONFIG_FILE}" >/dev/null 2>&1; then
        cp -f "${OPENCLAW_CONFIG_FILE}" "${lkg}"
        return 0
    fi

    if [ -f "${lkg}" ]; then
        cp -f "${lkg}" "${OPENCLAW_CONFIG_FILE}"
    fi
}

ensure_session_store_dir() {
    local agents_dir="${OPENCLAW_STATE_DIR}/agents"
    local main_dir="${agents_dir}/main"
    local sessions_dir="${main_dir}/sessions"

    mkdir -p "${sessions_dir}" 2>/dev/null || true
    chmod 775 "${agents_dir}" "${main_dir}" "${sessions_dir}" 2>/dev/null || true
}

ensure_openclaw_in_path() {
    local target_cli="/var/packages/openclaw2/target/bin/openclaw"
    [ -x "${target_cli}" ] || target_cli="/var/packages/openclaw/target/bin/openclaw"
    local link_cli="/usr/local/bin/openclaw"

    mkdir -p /usr/local/bin 2>/dev/null || true

    if [ -x "${target_cli}" ]; then
        if ! ln -sfn "${target_cli}" "${link_cli}" 2>/dev/null; then
            # Fallback for package runtime users: use passwordless sudo when available.
            if command -v sudo >/dev/null 2>&1; then
                if ! sudo -n ln -sfn "${target_cli}" "${link_cli}" 2>/dev/null; then
                    echo "[openclaw] WARN: cannot create ${link_cli}. Grant sudo NOPASSWD for ln, then rerun start/restart." 1>&2
                    echo "[openclaw]       sudo -n ln -sfn ${target_cli} ${link_cli}" 1>&2
                fi
            else
                echo "[openclaw] WARN: cannot create ${link_cli} (permission denied). Run as root:" 1>&2
                echo "[openclaw]       ln -sfn ${target_cli} ${link_cli}" 1>&2
            fi
        fi
    fi

    # Drop deprecated compatibility command.
    rm -f /usr/local/bin/openclaw-spk 2>/dev/null || true
    rm -f /var/packages/openclaw/target/bin/openclaw-spk 2>/dev/null || true
}

sync_provider_models_from_upstream() {
    "${OPENCLAW_NODE}" -e '
const fs = require("fs");

const configPath = process.argv[1];
const SUPPORTED_APIS = new Set(["openai-completions", "openai-responses"]);

const trim = (v) => (typeof v === "string" ? v.trim() : "");
const modelRef = (providerName, modelId) => `${providerName}/${modelId}`;

function getPrimaryRef(defaultsObj) {
  const modelObj = defaultsObj?.model;
  if (typeof modelObj === "string") return modelObj;
  if (modelObj && typeof modelObj === "object" && typeof modelObj.primary === "string") return modelObj.primary;
  return null;
}

function setPrimaryRef(defaultsObj, newRef) {
  const modelObj = defaultsObj?.model;
  if (typeof modelObj === "string") {
    defaultsObj.model = newRef;
    return;
  }
  if (modelObj && typeof modelObj === "object") {
    modelObj.primary = newRef;
    return;
  }
  defaultsObj.model = { primary: newRef };
}

function collectAvailableRefs(providersObj, excludeProvider) {
  const refs = [];
  for (const [pname, p] of Object.entries(providersObj || {})) {
    if (!p || typeof p !== "object") continue;
    if (excludeProvider && pname === excludeProvider) continue;
    const models = Array.isArray(p.models) ? p.models : [];
    for (const m of models) {
      if (m && typeof m === "object" && m.id) refs.push(modelRef(pname, String(m.id)));
    }
  }
  return refs;
}

async function fetchRemoteModels(baseUrl, apiKey, retries = 3) {
  let lastErr = null;
  for (let i = 1; i <= retries; i += 1) {
    try {
      const res = await fetch(baseUrl.replace(/\/$/, "") + "/models", {
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "User-Agent": "openclaw-model-sync/1.0"
        }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, attempts: i, error: null };
    } catch (e) {
      lastErr = e;
      if (i < retries) await new Promise((r) => setTimeout(r, 1000));
    }
  }
  return { data: null, attempts: retries, error: lastErr };
}

(async () => {
  if (!fs.existsSync(configPath)) return;

  const raw = fs.readFileSync(configPath, "utf8");
  const cfg = JSON.parse(raw);

  const providers = cfg?.models?.providers;
  if (!providers || typeof providers !== "object") return;

  cfg.agents = cfg.agents || {};
  cfg.agents.defaults = cfg.agents.defaults || {};
  const defaults = cfg.agents.defaults;

  let defaultsModels = defaults.models;
  if (Array.isArray(defaultsModels)) {
    defaultsModels = Object.fromEntries(defaultsModels.filter((x) => typeof x === "string").map((x) => [x, {}]));
  } else if (!defaultsModels || typeof defaultsModels !== "object") {
    defaultsModels = {};
  }
  defaults.models = defaultsModels;

  let changed = false;
  const summary = [];

  for (const [name, provider] of Object.entries(providers)) {
    if (!provider || typeof provider !== "object") continue;

    const api = trim(provider.api);
    const baseUrl = trim(provider.baseUrl);
    const apiKey = trim(provider.apiKey);
    const modelList = Array.isArray(provider.models) ? provider.models : [];

    if (!baseUrl || !apiKey || !modelList.length) continue;
    if (!SUPPORTED_APIS.has(api)) continue;

    const { data, attempts, error } = await fetchRemoteModels(baseUrl, apiKey, 3);
    if (error) {
      summary.push(`⚠️ ${name}: /models 探测失败，保留本地模型 (${error.message || error})`);
      continue;
    }
    if (!data || !Array.isArray(data.data)) {
      summary.push(`⚠️ ${name}: /models 返回结构不可识别，保留本地模型`);
      continue;
    }

    const remoteIds = data.data
      .filter((item) => item && typeof item === "object" && item.id)
      .map((item) => String(item.id));
    const remoteSet = new Set(remoteIds);

    if (!remoteSet.size) {
      summary.push(`⚠️ ${name}: /models 为空，保留本地模型`);
      continue;
    }

    const localModels = modelList.filter((m) => m && typeof m === "object" && m.id);
    if (!localModels.length) continue;

    const localIds = localModels.map((m) => String(m.id));
    const localSet = new Set(localIds);
    const template = JSON.parse(JSON.stringify(localModels[0]));

    const removedIds = localIds.filter((id) => !remoteSet.has(id));
    const addedIds = remoteIds.filter((id) => !localSet.has(id));

    const keptModels = localModels.filter((m) => remoteSet.has(String(m.id))).map((m) => JSON.parse(JSON.stringify(m)));
    const newModels = [...keptModels];

    for (const mid of addedIds) {
      const nm = JSON.parse(JSON.stringify(template));
      nm.id = mid;
      if (typeof nm.name === "string") nm.name = `${name} / ${mid}`;
      newModels.push(nm);
    }

    if (!newModels.length) {
      summary.push(`⚠️ ${name}: 同步结果为空，保留本地模型`);
      continue;
    }

    const expectedRefs = new Set(newModels.filter((m) => m && m.id).map((m) => modelRef(name, String(m.id))));
    const localRefs = new Set(localIds.map((id) => modelRef(name, id)));
    const firstRef = modelRef(name, String(newModels[0].id));

    const primaryRef = getPrimaryRef(defaults);
    if (typeof primaryRef === "string" && localRefs.has(primaryRef) && !expectedRefs.has(primaryRef)) {
      setPrimaryRef(defaults, firstRef);
      changed = true;
      summary.push(`🔁 ${name}: 默认主模型兜底 ${primaryRef} -> ${firstRef}`);
    }

    for (const fk of ["modelFallback", "imageModelFallback"]) {
      const v = defaults[fk];
      if (typeof v === "string" && localRefs.has(v) && !expectedRefs.has(v)) {
        defaults[fk] = firstRef;
        changed = true;
        summary.push(`🔁 ${name}: ${fk} 兜底 ${v} -> ${firstRef}`);
      }
    }

    for (const key of Object.keys(defaultsModels)) {
      if (key.startsWith(name + "/") && !expectedRefs.has(key)) {
        delete defaultsModels[key];
        changed = true;
      }
    }

    for (const ref of expectedRefs) {
      if (!(ref in defaultsModels)) {
        defaultsModels[ref] = {};
        changed = true;
      }
    }

    const changedModels = removedIds.length || addedIds.length || localModels.length !== newModels.length;
    if (changedModels) {
      provider.models = newModels;
      changed = true;
      summary.push(`✅ ${name}: 新增 ${addedIds.length}，删除 ${removedIds.length}，当前 ${newModels.length}（重试 ${attempts} 次）`);
    }
  }

  if (changed) {
    fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2) + "\n", "utf8");
  }

  if (summary.length) {
    for (const line of summary) console.error(`[model-sync] ${line}`);
    if (changed) console.error("[model-sync] 已写入 openclaw.json");
  }
})().catch((e) => {
  console.error(`[model-sync] 同步失败（忽略，不阻塞启动）: ${e && e.message ? e.message : e}`);
});
' "${OPENCLAW_CONFIG_FILE}" >/dev/null 2>&1 || true
}

service_postinst() {
    ensure_openclaw_in_path

    # Install DSM nginx alias for bundled terminal entry (root context during postinst/upgrade).
    mkdir -p "${SYNOPKG_PKGDEST}/var" 2>/dev/null || true
    cat > "${SYNOPKG_PKGDEST}/var/alias.openclaw2-terminal.conf" <<'NGINX_EOF'
location ~ ^/openclaw2-terminal(.*)$ {
    # 必须是 DSM 登录会话
    if ($http_cookie !~* "(^|;\\s*)id=") {
        return 403;
    }

    # 仅拦截“入口页”直链；放行 token/ws 等子路径，避免终端握手被误伤
    set $oc2_block 0;
    if ($request_uri ~ "^/openclaw2-terminal/?$") {
        set $oc2_block 1;
    }
    if ($http_referer != "") {
        set $oc2_block 0;
    }
    if ($http_sec_fetch_dest = "iframe") {
        set $oc2_block 0;
    }
    if ($oc2_block = 1) {
        return 404;
    }

    proxy_http_version      1.1;
    proxy_set_header        Host $host;
    proxy_set_header        Upgrade $http_upgrade;
    proxy_set_header        Connection "upgrade";
    proxy_set_header        X-Real-IP $remote_addr;
    proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header        X-Forwarded-Proto $scheme;
    proxy_set_header        X-Forwarded-Host $host;
    proxy_set_header        Cookie $http_cookie;
    proxy_read_timeout      3600s;
    proxy_send_timeout      3600s;
    proxy_connect_timeout   60s;

    add_header              'Access-Control-Allow-Origin' $scheme://$http_host always;
    add_header              'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
    add_header              'Access-Control-Allow-Headers' 'Authorization,Content-Type,Accept,Origin,User-Agent,DNT,Cache-Control,X-Mx-ReqToken,Keep-Alive,X-Requested-With,If-Modified-Since';
    add_header              'Access-Control-Allow-Credentials' 'true';
    add_header              'Cross-Origin-Embedder-Policy' 'require-corp';
    add_header              'Cross-Origin-Opener-Policy' 'same-origin';
    add_header              'Cross-Origin-Resource-Policy' 'same-site';

    proxy_pass              http://127.0.0.1:17682;
    proxy_buffering         off;
}
NGINX_EOF
    ln -sf "${SYNOPKG_PKGDEST}/var/alias.openclaw2-terminal.conf" /etc/nginx/conf.d/alias.openclaw2-terminal.conf
    if nginx -t >/dev/null 2>&1; then
        systemctl reload nginx >/dev/null 2>&1 || true
    fi
    if [ "${SYNOPKG_PKG_STATUS}" = "INSTALL" ] || [ "${SYNOPKG_PKG_STATUS}" = "UPGRADE" ]; then
        mkdir -p "${OPENCLAW_STATE_DIR_BASE}"

        if [ ! -f "${OPENCLAW_CONFIG_FILE_BASE}" ]; then
            if [ -f "${OPENCLAW_TEMPLATE_CONFIG}" ]; then
                cp -f "${OPENCLAW_TEMPLATE_CONFIG}" "${OPENCLAW_CONFIG_FILE_BASE}"
            elif [ -f "${OPENCLAW_LEGACY_CONFIG_FILE}" ]; then
                cp -f "${OPENCLAW_LEGACY_CONFIG_FILE}" "${OPENCLAW_CONFIG_FILE_BASE}"
            else
                echo "{}" > "${OPENCLAW_CONFIG_FILE_BASE}"
            fi
        fi

        # Wizard defaults
        if [ "${SYNOPKG_PKG_STATUS}" = "UPGRADE" ]; then
            export WIZARD_WORKSPACE_DIR="${wizard_workspace_dir}"
            export WIZARD_MODEL_ID="${wizard_model_id}"
            export WIZARD_BASE_URL="${wizard_base_url}"
            export WIZARD_API_KEY="${wizard_api_key}"
        else
            export WIZARD_WORKSPACE_DIR="${wizard_workspace_dir:-/volume1/docker/openclaw}"
            export WIZARD_MODEL_ID="${wizard_model_id:-Pro/MiniMaxAI/MiniMax-M2.5}"
            export WIZARD_BASE_URL="${wizard_base_url:-http://127.0.0.1:8317/v1}"
            export WIZARD_API_KEY="${wizard_api_key:-sk-V5zPkG6MJrIpxgmDw}"
        fi

        export WIZARD_FEISHU_APP_ID="${wizard_feishu_app_id}"
        export WIZARD_FEISHU_APP_SECRET="${wizard_feishu_app_secret}"
        export WIZARD_DINGTALK_CLIENT_ID="${wizard_dingtalk_client_id}"
        export WIZARD_DINGTALK_CLIENT_SECRET="${wizard_dingtalk_client_secret}"
        export WIZARD_QQBOT_APP_ID="${wizard_qqbot_app_id}"
        export WIZARD_QQBOT_CLIENT_SECRET="${wizard_qqbot_client_secret}"
        export WIZARD_WECOM_BOT_ID="${wizard_wecom_bot_id}"
        export WIZARD_WECOM_SECRET="${wizard_wecom_secret}"

        "${OPENCLAW_NODE}" -e '
const fs = require("fs");
const path = require("path");
const p = process.argv[1];
const appDir = process.argv[2] || "";
const cfg = JSON.parse(fs.readFileSync(p, "utf8"));
const trim = (v) => (typeof v === "string" ? v.trim() : "");

function safeReadJson(fp) {
  try { return JSON.parse(fs.readFileSync(fp, "utf8")); } catch { return null; }
}

function walkForPluginManifests(root, maxDepth = 6) {
  const out = [];
  if (!root || !fs.existsSync(root)) return out;
  const stack = [{ p: root, d: 0 }];
  while (stack.length) {
    const cur = stack.pop();
    let ents = [];
    try { ents = fs.readdirSync(cur.p, { withFileTypes: true }); } catch { continue; }
    for (const ent of ents) {
      const full = path.join(cur.p, ent.name);
      if (ent.isFile() && ent.name === "openclaw.plugin.json") out.push(full);
      if (ent.isDirectory() && cur.d < maxDepth) stack.push({ p: full, d: cur.d + 1 });
    }
  }
  return out;
}

function collectAvailablePluginIds(appDirPath) {
  const ids = new Set(["browser"]);
  for (const root of [path.join(appDirPath, "dist", "extensions"), path.join(appDirPath, "node_modules")]) {
    for (const manifest of walkForPluginManifests(root, 6)) {
      const j = safeReadJson(manifest);
      if (j && typeof j.id === "string" && j.id.trim()) ids.add(j.id.trim());
    }
  }
  return ids;
}

const availablePluginIds = collectAvailablePluginIds(appDir);
const pickPluginId = (candidates) => candidates.find((id) => availablePluginIds.has(id)) || null;
const selectedPluginIds = {
  feishu: pickPluginId(["feishu", "feishu-openclaw-plugin"]),
  dingtalk: pickPluginId(["dingtalk", "openclaw-dingtalk"]),
  wecom: pickPluginId(["wecom", "wecom-openclaw-plugin", "openclaw-wecom"]),
  qqbot: pickPluginId(["qqbot", "openclaw-qqbot"])
};

const workspaceInput = trim(process.env.WIZARD_WORKSPACE_DIR);
const modelIdInput = trim(process.env.WIZARD_MODEL_ID);
const baseUrlInput = trim(process.env.WIZARD_BASE_URL);
const apiKeyInput = trim(process.env.WIZARD_API_KEY);
const workspace = workspaceInput ? (workspaceInput.endsWith("/.openclaw") ? workspaceInput : `${workspaceInput}/.openclaw`) : "";

cfg.models = cfg.models || {};
cfg.models.providers = cfg.models.providers || {};
cfg.models.providers.default = cfg.models.providers.default || {};
cfg.models.providers.default.models = cfg.models.providers.default.models || [];
if (!cfg.models.providers.default.models.length) cfg.models.providers.default.models.push({});
if (modelIdInput) {
  cfg.models.providers.default.models[0].id = modelIdInput;
  cfg.models.providers.default.models[0].name = modelIdInput;
}
if (baseUrlInput) cfg.models.providers.default.baseUrl = baseUrlInput;
if (apiKeyInput) cfg.models.providers.default.apiKey = apiKeyInput;

cfg.agents = cfg.agents || {};
cfg.agents.defaults = cfg.agents.defaults || {};
if (workspace) cfg.agents.defaults.workspace = workspace;
cfg.agents.defaults.model = cfg.agents.defaults.model || {};
cfg.agents.defaults.imageModel = cfg.agents.defaults.imageModel || {};
if (modelIdInput) {
  cfg.agents.defaults.model.primary = `default/${modelIdInput}`;
  cfg.agents.defaults.imageModel.primary = `default/${modelIdInput}`;
}

cfg.memory = cfg.memory || {};
cfg.memory.qmd = cfg.memory.qmd || {};
cfg.memory.qmd.paths = Array.isArray(cfg.memory.qmd.paths) ? cfg.memory.qmd.paths : [];
if (workspace) {
  if (!cfg.memory.qmd.paths.length) {
    cfg.memory.qmd.paths.push({ path: workspace, name: "workspace", pattern: "**/*.md" });
  } else {
    cfg.memory.qmd.paths[0].path = workspace;
  }
}

cfg.channels = cfg.channels || {};
cfg.plugins = cfg.plugins || {};
cfg.plugins.entries = cfg.plugins.entries || {};
cfg.plugins.allow = Array.isArray(cfg.plugins.allow) ? cfg.plugins.allow : [];

cfg.channels = cfg.channels || {};

const browserEntry = cfg.plugins.entries.browser || {};
cfg.plugins.entries = {
  browser: {
    enabled: browserEntry.enabled !== false
  }
};
cfg.plugins.allow = Array.from(new Set([
  ...cfg.plugins.allow.filter((id) => id === "browser"),
  "browser"
]));

const enablePlugin = (pluginId) => {
  if (!pluginId) return;
  cfg.plugins.entries[pluginId] = cfg.plugins.entries[pluginId] || {};
  cfg.plugins.entries[pluginId].enabled = true;
  if (!cfg.plugins.allow.includes(pluginId)) cfg.plugins.allow.push(pluginId);
};

const feishuAppId = trim(process.env.WIZARD_FEISHU_APP_ID);
const feishuAppSecret = trim(process.env.WIZARD_FEISHU_APP_SECRET);
if (feishuAppId && feishuAppSecret && selectedPluginIds.feishu) {
  cfg.channels.feishu = cfg.channels.feishu || {};
  // Feishu schema expects credentials under accounts.<id>, not top-level appId/appSecret.
  const defaultAccountId = trim(cfg.channels.feishu.defaultAccount) || "default";
  cfg.channels.feishu.defaultAccount = defaultAccountId;
  cfg.channels.feishu.accounts = cfg.channels.feishu.accounts || {};
  cfg.channels.feishu.accounts[defaultAccountId] = cfg.channels.feishu.accounts[defaultAccountId] || {};
  cfg.channels.feishu.accounts[defaultAccountId].appId = feishuAppId;
  cfg.channels.feishu.accounts[defaultAccountId].appSecret = feishuAppSecret;
  // Clean deprecated top-level fields to avoid strict-schema "additionalProperties" failures.
  delete cfg.channels.feishu.appId;
  delete cfg.channels.feishu.appSecret;
  // Disable pairing gate by default for wizard provisioned Feishu credentials.
  cfg.channels.feishu.dmPolicy = "open";
  cfg.channels.feishu.groupPolicy = "open";
  cfg.channels.feishu.allowFrom = ["*"];
  enablePlugin(selectedPluginIds.feishu);
}

const dingtalkClientId = trim(process.env.WIZARD_DINGTALK_CLIENT_ID);
const dingtalkClientSecret = trim(process.env.WIZARD_DINGTALK_CLIENT_SECRET);
if (dingtalkClientId && dingtalkClientSecret && selectedPluginIds.dingtalk) {
  cfg.channels.dingtalk = cfg.channels.dingtalk || {};
  cfg.channels.dingtalk.clientId = dingtalkClientId;
  cfg.channels.dingtalk.clientSecret = dingtalkClientSecret;
  // Disable pairing gate by default: credentials are enough to communicate.
  cfg.channels.dingtalk.dmPolicy = "open";
  cfg.channels.dingtalk.groupPolicy = "open";
  cfg.channels.dingtalk.allowFrom = ["*"];
  enablePlugin(selectedPluginIds.dingtalk);
}

const qqbotAppId = trim(process.env.WIZARD_QQBOT_APP_ID);
const qqbotClientSecret = trim(process.env.WIZARD_QQBOT_CLIENT_SECRET);
if (qqbotAppId && qqbotClientSecret && selectedPluginIds.qqbot) {
  cfg.channels.qqbot = cfg.channels.qqbot || {};
  cfg.channels.qqbot.appId = qqbotAppId;
  cfg.channels.qqbot.clientSecret = qqbotClientSecret;
  cfg.channels.qqbot.dmPolicy = "open";
  cfg.channels.qqbot.groupPolicy = "open";
  cfg.channels.qqbot.allowFrom = ["*"];
  enablePlugin(selectedPluginIds.qqbot);
}

const wecomBotId = trim(process.env.WIZARD_WECOM_BOT_ID);
const wecomSecret = trim(process.env.WIZARD_WECOM_SECRET);
if (wecomBotId && wecomSecret && selectedPluginIds.wecom) {
  cfg.channels.wecom = cfg.channels.wecom || {};
  cfg.channels.wecom.botId = wecomBotId;
  cfg.channels.wecom.secret = wecomSecret;
  // Disable pairing gate by default: credentials are enough to communicate.
  cfg.channels.wecom.dmPolicy = "open";
  cfg.channels.wecom.groupPolicy = "open";
  cfg.channels.wecom.allowFrom = ["*"];
  // SPK default: keep all channels on main agent to avoid dynamic agent/config churn.
  cfg.channels.wecom.dynamicAgents = cfg.channels.wecom.dynamicAgents || {};
  cfg.channels.wecom.dynamicAgents.enabled = false;
  cfg.channels.wecom.dm = cfg.channels.wecom.dm || {};
  cfg.channels.wecom.dm.createAgentOnFirstMessage = false;
  enablePlugin(selectedPluginIds.wecom);
}

fs.writeFileSync(p, JSON.stringify(cfg, null, 2) + "\n", "utf8");
' "${OPENCLAW_CONFIG_FILE_BASE}" "${OPENCLAW_APP_DIR}"

        OPENCLAW_WORKSPACE="$(${OPENCLAW_NODE} -e 'const fs=require("fs"); const p=process.argv[1]; const c=JSON.parse(fs.readFileSync(p,"utf8")); const w=(c&&c.agents&&c.agents.defaults&&typeof c.agents.defaults.workspace==="string")?c.agents.defaults.workspace.trim():""; process.stdout.write(w);' "${OPENCLAW_CONFIG_FILE_BASE}")"
        if [ -z "${OPENCLAW_WORKSPACE}" ]; then
            OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE_DEFAULT}"
        fi
        OPENCLAW_STATE_DIR="$(resolve_state_dir_from_workspace "${OPENCLAW_WORKSPACE}")"
        OPENCLAW_CONFIG_FILE="${OPENCLAW_STATE_DIR}/openclaw.json"

        mkdir -p "${OPENCLAW_STATE_DIR}" "${OPENCLAW_WORKSPACE}"
        ensure_session_store_dir
        if [ ! -f "${OPENCLAW_CONFIG_FILE}" ]; then
            cp -f "${OPENCLAW_CONFIG_FILE_BASE}" "${OPENCLAW_CONFIG_FILE}"
        fi

        sync_bundled_channel_plugins_to_extensions
        harden_extension_permissions
        sync_skills_to_workspace
    fi
}

service_prestart() {
    mkdir -p "${OPENCLAW_STATE_DIR_BASE}"

    # OpenClaw2 bundled terminal (ttyd) integration (no dependency on external terminal package).
    # nginx alias is prepared in service_postinst (root context); here we only ensure ttyd process.
    if [ -x "${SYNOPKG_PKGDEST}/bin/ttyd" ]; then
        if [ ! -f "${SYNOPKG_PKGDEST}/var/openclaw2-terminal.pid" ] || ! kill -0 "$(cat "${SYNOPKG_PKGDEST}/var/openclaw2-terminal.pid" 2>/dev/null)" 2>/dev/null; then
            local ttyd_bin="${SYNOPKG_PKGDEST}/bin/ttyd"
            local ttyd_args="-p 17682 -6 -a -W --base-path /openclaw2-terminal/ -t titleFixed=OpenClaw2 -t allow-clipboard-read=true -t allow-clipboard-write=true -t rendererType=canvas"
            local shell_cmd="/bin/sh"
            [ -x /bin/bash ] && shell_cmd="/bin/bash"
            local terminfo_root="${SYNOPKG_PKGDEST}/share/terminfo"
            [ -d "${terminfo_root}" ] || terminfo_root="/usr/share/terminfo"
            LD_LIBRARY_PATH="${SYNOPKG_PKGDEST}/lib:${LD_LIBRARY_PATH}" TERMINFO="${terminfo_root}" \
                nohup "${ttyd_bin}" ${ttyd_args} ${shell_cmd} -l >"${LOG_FILE}" 2>&1 &
            echo "[openclaw2] terminal proxy up via ${ttyd_bin} at /openclaw2-terminal/" >> "${LOG_FILE}"
            echo $! > "${SYNOPKG_PKGDEST}/var/openclaw2-terminal.pid"
        fi
    fi

    # Ensure bootstrap config exists at fixed base path.
    if [ ! -f "${OPENCLAW_CONFIG_FILE_BASE}" ]; then
        if [ -f "${OPENCLAW_TEMPLATE_CONFIG}" ]; then
            cp -f "${OPENCLAW_TEMPLATE_CONFIG}" "${OPENCLAW_CONFIG_FILE_BASE}"
        elif [ -f "${OPENCLAW_LEGACY_CONFIG_FILE}" ]; then
            cp -f "${OPENCLAW_LEGACY_CONFIG_FILE}" "${OPENCLAW_CONFIG_FILE_BASE}"
        else
            echo "{}" > "${OPENCLAW_CONFIG_FILE_BASE}"
        fi
    fi

    local selected_workspace=""
    local selected_source_config="${OPENCLAW_CONFIG_FILE_BASE}"

    # Resolve active config source only (do not mutate config on restart).
    IFS='|' read -r selected_workspace selected_source_config <<EOF
$(${OPENCLAW_NODE} -e '
const fs = require("fs");
const path = require("path");

const baseConfigPath = process.argv[1];
const trim = (v) => (typeof v === "string" ? v.trim() : "");

function safeReadJson(p) {
  try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return null; }
}

const baseCfg = safeReadJson(baseConfigPath) || {};
const wsFromBase = trim(baseCfg?.agents?.defaults?.workspace);
const wsConfigPath = wsFromBase ? path.join(wsFromBase, "openclaw.json") : "";

let sourcePath = baseConfigPath;
if (wsConfigPath && wsConfigPath !== baseConfigPath && fs.existsSync(wsConfigPath)) {
  if (safeReadJson(wsConfigPath)) sourcePath = wsConfigPath;
}

process.stdout.write(`${wsFromBase}|${sourcePath}`);
' "${OPENCLAW_CONFIG_FILE_BASE}")
EOF

    if [ -z "${selected_workspace}" ]; then
        selected_workspace="${OPENCLAW_WORKSPACE_DEFAULT}"
    fi
    if [ -z "${selected_source_config}" ]; then
        selected_source_config="${OPENCLAW_CONFIG_FILE_BASE}"
    fi

    OPENCLAW_WORKSPACE="${selected_workspace}"
    OPENCLAW_STATE_DIR="$(resolve_state_dir_from_workspace "${OPENCLAW_WORKSPACE}")"
    OPENCLAW_CONFIG_FILE="${OPENCLAW_STATE_DIR}/openclaw.json"

    mkdir -p "${OPENCLAW_STATE_DIR}" "${OPENCLAW_WORKSPACE}"
    ensure_session_store_dir

    # Keep runtime config under workspace path. If missing (e.g. workspace wiped), recover from selected source config.
    if [ ! -f "${OPENCLAW_CONFIG_FILE}" ]; then
        cp -f "${selected_source_config}" "${OPENCLAW_CONFIG_FILE}"
    fi

    local resolved_home_dir
    resolved_home_dir="$(resolve_home_dir_from_workspace "${OPENCLAW_WORKSPACE}")"
    # Safety guard: never let HOME end at .../.openclaw, otherwise components that
    # derive ~/.openclaw paths will create nested .openclaw/.openclaw trees.
    case "${resolved_home_dir}" in
        */.openclaw) resolved_home_dir="$(dirname "${resolved_home_dir}")" ;;
    esac

    export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR}"
    export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_FILE}"
    export HOME="${resolved_home_dir}"

    sync_bundled_channel_plugins_to_extensions
    harden_extension_permissions

    # Safety: if a channel config exists but its plugin is unavailable in current runtime,
    # drop that channel config and stale plugin refs to avoid "unknown channel id" startup failures.
    "${OPENCLAW_NODE}" -e '
const fs = require("fs");
const path = require("path");

const cfgPath = process.argv[1];
const appDir = process.argv[2];
const stateDir = process.argv[3];

function safeReadJson(fp) {
  try { return JSON.parse(fs.readFileSync(fp, "utf8")); } catch { return null; }
}
function walkForPluginManifests(root, maxDepth = 6) {
  const out = [];
  if (!root || !fs.existsSync(root)) return out;
  const stack = [{ p: root, d: 0 }];
  while (stack.length) {
    const cur = stack.pop();
    let ents = [];
    try { ents = fs.readdirSync(cur.p, { withFileTypes: true }); } catch { continue; }
    for (const ent of ents) {
      const full = path.join(cur.p, ent.name);
      if (ent.isFile() && ent.name === "openclaw.plugin.json") out.push(full);
      if (ent.isDirectory() && cur.d < maxDepth) stack.push({ p: full, d: cur.d + 1 });
    }
  }
  return out;
}

const cfg = safeReadJson(cfgPath);
if (!cfg || typeof cfg !== "object") process.exit(0);

const availablePluginIds = new Set(["browser"]);
const pluginChannelMap = new Map();
for (const root of [
  path.join(appDir, "dist", "extensions"),
  path.join(appDir, "node_modules"),
  path.join(stateDir, "extensions"),
  path.join(stateDir, "node_modules")
]) {
  for (const manifest of walkForPluginManifests(root, 6)) {
    const j = safeReadJson(manifest);
    if (!j || typeof j.id !== "string" || !j.id.trim()) continue;
    const pluginId = j.id.trim();
    availablePluginIds.add(pluginId);
    const channels = Array.isArray(j.channels) ? j.channels.filter((x) => typeof x === "string" && x.trim()).map((x) => x.trim()) : [];
    pluginChannelMap.set(pluginId, channels);
  }
}

cfg.plugins = cfg.plugins || {};
cfg.plugins.entries = cfg.plugins.entries || {};
cfg.plugins.allow = Array.isArray(cfg.plugins.allow) ? cfg.plugins.allow : [];
cfg.channels = cfg.channels || {};

let changed = false;


const normalizePolicy = (obj, dmDefault = "open", groupDefault = "open") => {
  const norm = (v) => typeof v === "string" ? v.trim().toLowerCase() : "";
  const allowedDm = new Set(["open", "pairing", "allowlist"]);
  const allowedGroup = new Set(["open", "allowlist", "disabled"]);
  const dm = norm(obj.dmPolicy);
  const gp = norm(obj.groupPolicy);
  const mappedDm = dm === "allowall" ? "open" : dm;
  const mappedGp = gp === "allowall" ? "open" : gp;
  if (!allowedDm.has(mappedDm)) {
    obj.dmPolicy = dmDefault;
    changed = true;
  } else if (mappedDm !== obj.dmPolicy) {
    obj.dmPolicy = mappedDm;
    changed = true;
  }
  if (!allowedGroup.has(mappedGp)) {
    obj.groupPolicy = groupDefault;
    changed = true;
  } else if (mappedGp !== obj.groupPolicy) {
    obj.groupPolicy = mappedGp;
    changed = true;
  }
};

// Normalize Feishu credentials to schema-compatible location.
// Some UI surfaces may write clientId/clientSecret (or top-level appId/appSecret)
// which strict Feishu config schema rejects as additional properties.
if (cfg.channels.feishu && typeof cfg.channels.feishu === "object") {
  const f = cfg.channels.feishu;
  const norm = (v) => typeof v === "string" ? v.trim() : "";
  const migratedAppId = norm(f.clientId) || norm(f.appId);
  const migratedAppSecret = norm(f.clientSecret) || norm(f.appSecret);
  const defaultAccountId = norm(f.defaultAccount) || "default";
  f.defaultAccount = defaultAccountId;
  f.accounts = f.accounts && typeof f.accounts === "object" ? f.accounts : {};
  f.accounts[defaultAccountId] = f.accounts[defaultAccountId] && typeof f.accounts[defaultAccountId] === "object" ? f.accounts[defaultAccountId] : {};
  if (migratedAppId && !norm(f.accounts[defaultAccountId].appId)) {
    f.accounts[defaultAccountId].appId = migratedAppId;
    changed = true;
  }
  if (migratedAppSecret && !norm(f.accounts[defaultAccountId].appSecret)) {
    f.accounts[defaultAccountId].appSecret = migratedAppSecret;
    changed = true;
  }
  for (const k of ["clientId", "clientSecret", "appId", "appSecret", "agentId"]) {
    if (Object.prototype.hasOwnProperty.call(f, k)) {
      delete f[k];
      changed = true;
    }
  }
  normalizePolicy(f, "open", "open");
  if (f.dmPolicy !== "open") {
    f.dmPolicy = "open";
    changed = true;
  }
  if (f.groupPolicy !== "open") {
    f.groupPolicy = "open";
    changed = true;
  }
  const allowFrom = Array.isArray(f.allowFrom)
    ? f.allowFrom.filter((x) => typeof x === "string" && x.trim()).map((x) => x.trim())
    : [];
  if (!allowFrom.includes("*")) {
    f.allowFrom = ["*", ...allowFrom.filter((x) => x !== "*")];
    changed = true;
  }
}

// Normalize DingTalk config to schema-compatible values.
if (cfg.channels.dingtalk && typeof cfg.channels.dingtalk === "object") {
  const d = cfg.channels.dingtalk;
  const norm = (v) => typeof v === "string" ? v.trim() : "";
  if (!norm(d.clientId) && norm(d.appId)) {
    d.clientId = norm(d.appId);
    changed = true;
  }
  if (!norm(d.clientSecret) && norm(d.appSecret)) {
    d.clientSecret = norm(d.appSecret);
    changed = true;
  }
  for (const k of ["appId", "appSecret", "agentId"]) {
    if (Object.prototype.hasOwnProperty.call(d, k)) {
      delete d[k];
      changed = true;
    }
  }
  normalizePolicy(d, "open", "open");
  if (d.dmPolicy !== "open") {
    d.dmPolicy = "open";
    changed = true;
  }
  if (d.groupPolicy !== "open") {
    d.groupPolicy = "open";
    changed = true;
  }
  const allowFrom = Array.isArray(d.allowFrom)
    ? d.allowFrom.filter((x) => typeof x === "string" && x.trim()).map((x) => x.trim())
    : [];
  if (!allowFrom.includes("*")) {
    d.allowFrom = ["*", ...allowFrom.filter((x) => x !== "*")];
    changed = true;
  }
}

// Normalize WeCom config to schema-compatible values.
if (cfg.channels.wecom && typeof cfg.channels.wecom === "object") {
  const w = cfg.channels.wecom;
  const norm = (v) => typeof v === "string" ? v.trim() : "";
  if (!norm(w.botId) && norm(w.clientId)) {
    w.botId = norm(w.clientId);
    changed = true;
  }
  if (!norm(w.secret) && norm(w.clientSecret)) {
    w.secret = norm(w.clientSecret);
    changed = true;
  }
  for (const k of ["clientId", "clientSecret", "appId", "appSecret", "agentId"]) {
    if (Object.prototype.hasOwnProperty.call(w, k)) {
      delete w[k];
      changed = true;
    }
  }
  normalizePolicy(w, "open", "open");
  if (w.dmPolicy !== "open") {
    w.dmPolicy = "open";
    changed = true;
  }
  if (w.groupPolicy !== "open") {
    w.groupPolicy = "open";
    changed = true;
  }
  const allowFrom = Array.isArray(w.allowFrom)
    ? w.allowFrom.filter((x) => typeof x === "string" && x.trim()).map((x) => x.trim())
    : [];
  if (!allowFrom.includes("*")) {
    w.allowFrom = ["*", ...allowFrom.filter((x) => x !== "*")];
    changed = true;
  }
  // SPK default: disable dynamic agent creation to keep config stable.
  w.dynamicAgents = w.dynamicAgents && typeof w.dynamicAgents === "object" ? w.dynamicAgents : {};
  if (w.dynamicAgents.enabled !== false) {
    w.dynamicAgents.enabled = false;
    changed = true;
  }
  w.dm = w.dm && typeof w.dm === "object" ? w.dm : {};
  if (w.dm.createAgentOnFirstMessage !== false) {
    w.dm.createAgentOnFirstMessage = false;
    changed = true;
  }
}

// Normalize memory backend for SPK defaults: prefer builtin when qmd binary is unavailable.
cfg.memory = cfg.memory && typeof cfg.memory === "object" ? cfg.memory : {};
const memBackend = (typeof cfg.memory.backend === "string" ? cfg.memory.backend.trim().toLowerCase() : "") || "builtin";
if (!cfg.memory.backend) {
  cfg.memory.backend = "builtin";
  changed = true;
}
if (memBackend === "qmd") {
  const qmdCmd = cfg.memory?.qmd && typeof cfg.memory.qmd.command === "string" && cfg.memory.qmd.command.trim()
    ? cfg.memory.qmd.command.trim()
    : "/usr/local/bin/qmd";
  if (qmdCmd.startsWith("/") && !fs.existsSync(qmdCmd)) {
    cfg.memory.backend = "builtin";
    changed = true;
  }
}

// Normalize QQBot aliases + policy enums for schema safety.
if (cfg.channels.qqbot && typeof cfg.channels.qqbot === "object") {
  const q = cfg.channels.qqbot;
  const norm = (v) => typeof v === "string" ? v.trim() : "";
  if (!norm(q.appId) && norm(q.clientId)) {
    q.appId = norm(q.clientId);
    changed = true;
  }
  if (!norm(q.clientSecret) && norm(q.appSecret)) {
    q.clientSecret = norm(q.appSecret);
    changed = true;
  }
  for (const k of ["clientId", "appSecret", "agentId"]) {
    if (Object.prototype.hasOwnProperty.call(q, k)) {
      delete q[k];
      changed = true;
    }
  }
  normalizePolicy(q, "open", "open");
  if (q.dmPolicy !== "open") {
    q.dmPolicy = "open";
    changed = true;
  }
  if (q.groupPolicy !== "open") {
    q.groupPolicy = "open";
    changed = true;
  }
  const allowFrom = Array.isArray(q.allowFrom)
    ? q.allowFrom.filter((x) => typeof x === "string" && x.trim()).map((x) => x.trim())
    : [];
  if (!allowFrom.includes("*")) {
    q.allowFrom = ["*", ...allowFrom.filter((x) => x !== "*")];
    changed = true;
  }
}

// Ensure agents.list (object-array schema) contains on-disk agent dirs so doctor does not flag
// newly created per-channel agent dirs as stale/orphaned.
cfg.agents = cfg.agents && typeof cfg.agents === "object" ? cfg.agents : {};
let agentsList = [];
if (Array.isArray(cfg.agents.list)) {
  for (const item of cfg.agents.list) {
    if (typeof item === "string" && item.trim()) {
      agentsList.push({ id: item.trim() });
      changed = true;
      continue;
    }
    if (item && typeof item === "object" && typeof item.id === "string" && item.id.trim()) {
      const next = { ...item, id: item.id.trim() };
      agentsList.push(next);
      if (next.id !== item.id) changed = true;
    }
  }
} else if (cfg.agents.list != null) {
  changed = true;
}
const knownAgentIds = new Set(agentsList.map((x) => x.id));
if (!knownAgentIds.has("main")) {
  agentsList.unshift({ id: "main", heartbeat: {} });
  knownAgentIds.add("main");
  changed = true;
}
try {
  const agentsRoot = path.join(stateDir, "agents");
  if (fs.existsSync(agentsRoot)) {
    const diskAgentIds = fs.readdirSync(agentsRoot, { withFileTypes: true })
      .filter((ent) => ent.isDirectory())
      .map((ent) => ent.name)
      .filter((id) => typeof id === "string" && id.trim())
      .map((id) => id.trim());
    for (const agentId of diskAgentIds) {
      if (!knownAgentIds.has(agentId)) {
        knownAgentIds.add(agentId);
        agentsList.push({ id: agentId, heartbeat: {} });
        changed = true;
      }
    }
  }
} catch {}

const channelDefaultAgentId = {
  feishu: "main",
  dingtalk: "main",
  wecom: "main",
  qqbot: "main",
  "openclaw-weixin": "main"
};
for (const [channelId, defaultAgentId] of Object.entries(channelDefaultAgentId)) {
  const ch = cfg.channels[channelId];
  if (ch && typeof ch === "object") {
    if (defaultAgentId && !knownAgentIds.has(defaultAgentId)) {
      knownAgentIds.add(defaultAgentId);
      agentsList.push({ id: defaultAgentId, heartbeat: {} });
      changed = true;
    }
  }
}
cfg.agents.list = agentsList;

// Enforce per-channel fixed routing bindings (prevents cross-channel session bleed).
cfg.bindings = Array.isArray(cfg.bindings) ? cfg.bindings : [];
const upsertRouteBinding = (channelId, agentId) => {
  if (!channelId || !agentId) return;
  const idx = cfg.bindings.findIndex((b) => {
    if (!b || typeof b !== "object") return false;
    const type = typeof b.type === "string" ? b.type.trim().toLowerCase() : "route";
    const matchChannel = b.match && typeof b.match === "object" && typeof b.match.channel === "string"
      ? b.match.channel.trim().toLowerCase()
      : "";
    const hasAccountScope = Boolean(b.match && typeof b.match === "object" && b.match.accountId);
    return type === "route" && matchChannel === channelId && !hasAccountScope;
  });
  if (idx >= 0) {
    const existing = cfg.bindings[idx] || {};
    if (existing.agentId !== agentId) {
      existing.agentId = agentId;
      changed = true;
    }
    if (!existing.match || typeof existing.match !== "object") {
      existing.match = { channel: channelId };
      changed = true;
    }
    if (existing.type !== "route") {
      existing.type = "route";
      changed = true;
    }
    cfg.bindings[idx] = existing;
    return;
  }
  cfg.bindings.push({ type: "route", match: { channel: channelId }, agentId });
  changed = true;
};
for (const [channelId, defaultAgentId] of Object.entries(channelDefaultAgentId)) {
  const ch = cfg.channels[channelId];
  if (!ch || typeof ch !== "object") continue;
  upsertRouteBinding(channelId, defaultAgentId);
}

const legacyAliases = {
  feishu: ["feishu", "feishu-openclaw-plugin"],
  dingtalk: ["dingtalk", "openclaw-dingtalk"],
  wecom: ["wecom", "wecom-openclaw-plugin", "openclaw-wecom"],
  qqbot: ["qqbot", "openclaw-qqbot"],
  "openclaw-weixin": ["openclaw-weixin", "weixin"]
};

const resolvePluginsForChannel = (channelId) => {
  const ids = [];
  for (const [pluginId, channels] of pluginChannelMap.entries()) {
    if (pluginId === channelId || channels.includes(channelId)) ids.push(pluginId);
  }
  return ids;
};

for (const [channelId, channelCfg] of Object.entries(cfg.channels)) {
  if (!channelCfg || typeof channelCfg !== "object") continue;
  const available = resolvePluginsForChannel(channelId);
  const aliases = legacyAliases[channelId] || [channelId];

  // 微信渠道兜底保留：即使自动发现偶发失败，也不要把 openclaw-weixin 从配置里删掉。
  if (channelId === "openclaw-weixin") {
    const selectedId = "openclaw-weixin";
    cfg.plugins.entries[selectedId] = cfg.plugins.entries[selectedId] || {};
    if (cfg.plugins.entries[selectedId].enabled !== true) {
      cfg.plugins.entries[selectedId].enabled = true;
      changed = true;
    }
    if (!cfg.plugins.allow.includes(selectedId)) {
      cfg.plugins.allow.push(selectedId);
      changed = true;
    }
    continue;
  }

  if (!available.length) {
    delete cfg.channels[channelId];
    for (const id of aliases) delete cfg.plugins.entries[id];
    cfg.plugins.allow = cfg.plugins.allow.filter((id) => !aliases.includes(id));
    changed = true;
    continue;
  }

  const selectedId = available[0];
  cfg.plugins.entries[selectedId] = cfg.plugins.entries[selectedId] || {};
  if (cfg.plugins.entries[selectedId].enabled !== true) {
    cfg.plugins.entries[selectedId].enabled = true;
    changed = true;
  }
  if (!cfg.plugins.allow.includes(selectedId)) {
    cfg.plugins.allow.push(selectedId);
    changed = true;
  }
  // Clean stale legacy aliases if they differ from selected plugin id.
  for (const id of aliases) {
    if (id !== selectedId) {
      if (cfg.plugins.entries[id]) {
        delete cfg.plugins.entries[id];
        changed = true;
      }
      const before = cfg.plugins.allow.length;
      cfg.plugins.allow = cfg.plugins.allow.filter((x) => x !== id);
      if (cfg.plugins.allow.length !== before) changed = true;
    }
  }
}

if (changed) fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2) + "\n", "utf8");
' "${OPENCLAW_CONFIG_FILE}" "${OPENCLAW_APP_DIR}" "${OPENCLAW_STATE_DIR}" || true

    ensure_openclaw_in_path
    sync_provider_models_from_upstream
    sync_skills_to_workspace
    validate_or_rollback_config

    # Clear stale pid marker before a fresh start.
    [ -n "${PID_FILE}" ] && rm -f "${PID_FILE}" 2>/dev/null || true

    # fn-port monitor runtime dirs (ported from trim.openclaw)
    local fn_home_dir="${SYNOPKG_PKGVAR}/data/home"
    local fn_cfg_dir="${fn_home_dir}/.openclaw"
    local fn_cfg_file="${fn_cfg_dir}/openclaw.json"
    mkdir -p "${fn_cfg_dir}" "${SYNOPKG_PKGVAR}/data/runtime" "${SYNOPKG_PKGVAR}/data/workspace" "${SYNOPKG_PKGVAR}/data/monitor" 2>/dev/null || true

    # Ensure service user can write panel/runtime data.
    if [ -n "${EFF_USER}" ]; then
        chown -R "${EFF_USER}:${EFF_USER}" "${SYNOPKG_PKGVAR}/data" 2>/dev/null || true
    fi

    # Keep fn-panel system-mode config path in sync with SPK runtime config.
    if [ -f "${OPENCLAW_CONFIG_FILE}" ] && [ ! -f "${fn_cfg_file}" ]; then
        cp -f "${OPENCLAW_CONFIG_FILE}" "${fn_cfg_file}" 2>/dev/null || true
    elif [ ! -f "${OPENCLAW_CONFIG_FILE}" ] && [ -f "${fn_cfg_file}" ]; then
        cp -f "${fn_cfg_file}" "${OPENCLAW_CONFIG_FILE}" 2>/dev/null || true
    fi
}

service_poststop() {
    # stop bundled ttyd if still alive
    if [ -f "${SYNOPKG_PKGDEST}/var/openclaw2-terminal.pid" ]; then
        local tpid
        tpid="$(cat "${SYNOPKG_PKGDEST}/var/openclaw2-terminal.pid" 2>/dev/null)"
        if [ -n "${tpid}" ]; then
            kill -TERM "${tpid}" >/dev/null 2>&1 || true
            sleep 1
            kill -KILL "${tpid}" >/dev/null 2>&1 || true
        fi
        rm -f "${SYNOPKG_PKGDEST}/var/openclaw2-terminal.pid" >/dev/null 2>&1 || true
    fi

    rm -f /etc/nginx/conf.d/alias.openclaw2-terminal.conf >/dev/null 2>&1 || true
    if nginx -t >/dev/null 2>&1; then
        systemctl reload nginx >/dev/null 2>&1 || true
    fi
}

# Default exports before prestart recalculates runtime paths.
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR_BASE}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_FILE_BASE}"
export HOME="${OPENCLAW_WORKSPACE_DEFAULT}"
# Keep restarts in-process under Synology service manager to avoid PID drift
# (full-process respawn can make synopkg status misreport as stopped).
export OPENCLAW_NO_RESPAWN=1

FN_MONITOR_ENTRY="${SYNOPKG_PKGDEST}/fn-port/server/index.cjs"
FN_STATIC_DIR="${SYNOPKG_PKGDEST}/fn-port/ui"
FN_SOUL_MD_SRC="${SYNOPKG_PKGDEST}/fn-port/prompts/SOUL.md"
FN_SOCKET_PATH="${SYNOPKG_PKGDEST}/trim.openclaw.sock"

if [ ! -f "${FN_MONITOR_ENTRY}" ]; then
    echo "[openclaw2] ERROR: fn monitor entry missing: ${FN_MONITOR_ENTRY}" 1>&2
fi

# 仅保留 DSM 套件后台 UI（index.cgi），不再启动 trim monitor 页面服务。
# 使用稳定的 sleep 前台进程维持套件 running 状态。
SERVICE_COMMAND="env PATH=${SYNOPKG_PKGDEST}/bin:/var/packages/nodejs_v22/target/bin:/var/packages/bunjs/target/bin:$PATH HOME=${SYNOPKG_PKGVAR}/data/home OPENCLAW_USE_SYSTEM_CONFIG=0 OPENCLAW_DATA_DIR=${SYNOPKG_PKGVAR}/data PORT=${SERVICE_PORT} BASE_PATH=/ FN_AUTH_ENABLED=0 FN_AUTH_REQUIRE_SAME_ORIGIN=0 STATIC_DIR=${FN_STATIC_DIR} SOUL_MD_SRC=${FN_SOUL_MD_SRC} MONITOR_SOCKET_PATH=${FN_SOCKET_PATH} MONITOR_ACCESS_MODE=public OPENCLAW_PATCHES_DIR=${SYNOPKG_PKGDEST}/fn-port/vendor/openclaw-patches/dist ${OPENCLAW_NODE} ${FN_MONITOR_ENTRY}"
SVC_CWD="${SYNOPKG_PKGDEST}/fn-port/server"
SVC_BACKGROUND=yes
SVC_WRITE_PID=yes
