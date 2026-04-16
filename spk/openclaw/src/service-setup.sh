OPENCLAW_NODE="${SYNOPKG_PKGDEST}/bin/node"
OPENCLAW_APP_DIR="${SYNOPKG_PKGDEST}/app/openclaw"
OPENCLAW_ENTRY="${OPENCLAW_APP_DIR}/dist/index.js"
OPENCLAW_STATE_DIR_BASE="/volume1/docker/openclaw"
OPENCLAW_WORKSPACE_DEFAULT="${OPENCLAW_STATE_DIR_BASE}"
OPENCLAW_CONFIG_FILE_BASE="${OPENCLAW_STATE_DIR_BASE}/openclaw.json"
OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE_DEFAULT}"
OPENCLAW_STATE_DIR="${OPENCLAW_WORKSPACE_DEFAULT}"
OPENCLAW_CONFIG_FILE="${OPENCLAW_CONFIG_FILE_BASE}"
OPENCLAW_LEGACY_CONFIG_FILE="${SYNOPKG_PKGVAR}/openclaw.json"
OPENCLAW_TEMPLATE_CONFIG="${SYNOPKG_PKGDEST}/app/openclaw/config/openclaw.template.json"

sync_skills_to_workspace() {
    OPENCLAW_BUNDLED_SKILLS_DIR="${OPENCLAW_WORKSPACE}/skills/_bundled"
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

    # Keep channel plugins in workspace/extensions so runtime discovery is stable
    # across restarts and independent from package-internal node_modules layout.
    for src in \
        "${OPENCLAW_APP_DIR}/node_modules/@larksuiteoapi/feishu-openclaw-plugin" \
        "${OPENCLAW_APP_DIR}/node_modules/openclaw-channel-dingtalk" \
        "${OPENCLAW_APP_DIR}/node_modules/@wecom/wecom-openclaw-plugin" \
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

    # Align ownership with runtime config owner when possible (prevents root-installed plugin files from breaking runtime).
    local owner_spec=""
    if [ -f "${OPENCLAW_CONFIG_FILE}" ]; then
        owner_spec="$(stat -c '%u:%g' "${OPENCLAW_CONFIG_FILE}" 2>/dev/null || true)"
    fi
    if [ -z "${owner_spec}" ]; then
        owner_spec="$(stat -c '%u:%g' "${OPENCLAW_STATE_DIR}" 2>/dev/null || true)"
    fi
    if [ -n "${owner_spec}" ]; then
        chown -R "${owner_spec}" "${ext_dir}" 2>/dev/null || true
        [ -f "${OPENCLAW_CONFIG_FILE}" ] && chown "${owner_spec}" "${OPENCLAW_CONFIG_FILE}" 2>/dev/null || true
    fi

    # OpenClaw blocks plugins under world-writable paths. Normalize perms to avoid plugin quarantine.
    find "${ext_dir}" -type d -exec chmod 775 {} \; 2>/dev/null || true
    find "${ext_dir}" -type f -exec chmod 664 {} \; 2>/dev/null || true
    # Ensure no world-writable bits remain.
    find "${ext_dir}" -perm -0002 -exec chmod o-w {} \; 2>/dev/null || true
    [ -f "${OPENCLAW_CONFIG_FILE}" ] && chmod 664 "${OPENCLAW_CONFIG_FILE}" 2>/dev/null || true
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
          "User-Agent": "openclaw-spk-model-sync/1.0"
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
    if [ "${SYNOPKG_PKG_STATUS}" = "INSTALL" ]; then
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
        export WIZARD_WORKSPACE_DIR="${wizard_workspace_dir:-/volume1/docker/openclaw}"
        export WIZARD_MODEL_ID="${wizard_model_id:-Pro/MiniMaxAI/MiniMax-M2.5}"
        export WIZARD_BASE_URL="${wizard_base_url:-http://127.0.0.1:8317/v1}"
        export WIZARD_API_KEY="${wizard_api_key:-sk-V5zPkG6MJrIpxgmDw}"
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

const workspace = trim(process.env.WIZARD_WORKSPACE_DIR) || "/volume1/docker/openclaw";
const modelId = trim(process.env.WIZARD_MODEL_ID) || "Pro/MiniMaxAI/MiniMax-M2.5";
const baseUrl = trim(process.env.WIZARD_BASE_URL) || "http://127.0.0.1:8317/v1";
const apiKey = trim(process.env.WIZARD_API_KEY) || "sk-V5zPkG6MJrIpxgmDw";

cfg.models = cfg.models || {};
cfg.models.providers = cfg.models.providers || {};
cfg.models.providers.default = cfg.models.providers.default || {};
cfg.models.providers.default.models = cfg.models.providers.default.models || [];
if (!cfg.models.providers.default.models.length) cfg.models.providers.default.models.push({});
cfg.models.providers.default.models[0].id = modelId;
cfg.models.providers.default.models[0].name = modelId;
cfg.models.providers.default.baseUrl = baseUrl;
cfg.models.providers.default.apiKey = apiKey;

cfg.agents = cfg.agents || {};
cfg.agents.defaults = cfg.agents.defaults || {};
cfg.agents.defaults.workspace = workspace;
cfg.agents.defaults.model = cfg.agents.defaults.model || {};
cfg.agents.defaults.imageModel = cfg.agents.defaults.imageModel || {};
cfg.agents.defaults.model.primary = `default/${modelId}`;
cfg.agents.defaults.imageModel.primary = `default/${modelId}`;

cfg.memory = cfg.memory || {};
cfg.memory.qmd = cfg.memory.qmd || {};
cfg.memory.qmd.paths = Array.isArray(cfg.memory.qmd.paths) ? cfg.memory.qmd.paths : [];
if (!cfg.memory.qmd.paths.length) {
  cfg.memory.qmd.paths.push({ path: workspace, name: "workspace", pattern: "**/*.md" });
} else {
  cfg.memory.qmd.paths[0].path = workspace;
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
  cfg.channels.feishu.appId = feishuAppId;
  cfg.channels.feishu.appSecret = feishuAppSecret;
  // Disable pairing gate by default: credentials are enough to communicate.
  cfg.channels.feishu.dmPolicy = "open";
  cfg.channels.feishu.groupPolicy = "open";
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
  enablePlugin(selectedPluginIds.dingtalk);
}

const qqbotAppId = trim(process.env.WIZARD_QQBOT_APP_ID);
const qqbotClientSecret = trim(process.env.WIZARD_QQBOT_CLIENT_SECRET);
if (qqbotAppId && qqbotClientSecret && selectedPluginIds.qqbot) {
  cfg.channels.qqbot = cfg.channels.qqbot || {};
  cfg.channels.qqbot.appId = qqbotAppId;
  cfg.channels.qqbot.clientSecret = qqbotClientSecret;
  // Disable pairing gate by default: credentials are enough to communicate.
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
  enablePlugin(selectedPluginIds.wecom);
}

fs.writeFileSync(p, JSON.stringify(cfg, null, 2) + "\n", "utf8");
' "${OPENCLAW_CONFIG_FILE_BASE}" "${OPENCLAW_APP_DIR}"

        OPENCLAW_WORKSPACE="$(${OPENCLAW_NODE} -e 'const fs=require("fs"); const p=process.argv[1]; const c=JSON.parse(fs.readFileSync(p,"utf8")); const w=(c&&c.agents&&c.agents.defaults&&typeof c.agents.defaults.workspace==="string")?c.agents.defaults.workspace.trim():""; process.stdout.write(w);' "${OPENCLAW_CONFIG_FILE_BASE}")"
        if [ -z "${OPENCLAW_WORKSPACE}" ]; then
            OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE_DEFAULT}"
        fi
        OPENCLAW_STATE_DIR="${OPENCLAW_WORKSPACE}"
        OPENCLAW_CONFIG_FILE="${OPENCLAW_STATE_DIR}/openclaw.json"

        mkdir -p "${OPENCLAW_STATE_DIR}" "${OPENCLAW_WORKSPACE}"
        if [ ! -f "${OPENCLAW_CONFIG_FILE}" ]; then
            cp -f "${OPENCLAW_CONFIG_FILE_BASE}" "${OPENCLAW_CONFIG_FILE}"
        fi

        sync_skills_to_workspace
    fi
}

service_prestart() {
    mkdir -p "${OPENCLAW_STATE_DIR_BASE}"

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
    OPENCLAW_STATE_DIR="${OPENCLAW_WORKSPACE}"
    OPENCLAW_CONFIG_FILE="${OPENCLAW_STATE_DIR}/openclaw.json"

    mkdir -p "${OPENCLAW_STATE_DIR}" "${OPENCLAW_WORKSPACE}"

    # Keep runtime config under workspace path. If missing (e.g. workspace wiped), recover from selected source config.
    if [ ! -f "${OPENCLAW_CONFIG_FILE}" ]; then
        cp -f "${selected_source_config}" "${OPENCLAW_CONFIG_FILE}"
    fi

    export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR}"
    export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_FILE}"
    export HOME="${OPENCLAW_STATE_DIR}"

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
for (const root of [
  path.join(appDir, "dist", "extensions"),
  path.join(appDir, "node_modules"),
  path.join(stateDir, "extensions"),
  path.join(stateDir, "node_modules")
]) {
  for (const manifest of walkForPluginManifests(root, 6)) {
    const j = safeReadJson(manifest);
    if (j && typeof j.id === "string" && j.id.trim()) availablePluginIds.add(j.id.trim());
  }
}

cfg.plugins = cfg.plugins || {};
cfg.plugins.entries = cfg.plugins.entries || {};
cfg.plugins.allow = Array.isArray(cfg.plugins.allow) ? cfg.plugins.allow : [];
cfg.channels = cfg.channels || {};

const candidates = {
  feishu: ["feishu", "feishu-openclaw-plugin"],
  dingtalk: ["dingtalk", "openclaw-dingtalk"],
  wecom: ["wecom", "wecom-openclaw-plugin", "openclaw-wecom"],
  qqbot: ["qqbot", "openclaw-qqbot"]
};

let changed = false;
for (const [channelId, ids] of Object.entries(candidates)) {
  const channelConfigured = cfg.channels[channelId] && typeof cfg.channels[channelId] === "object";
  if (!channelConfigured) continue;
  const hasAnyPlugin = ids.some((id) => availablePluginIds.has(id));
  if (hasAnyPlugin) continue;

  delete cfg.channels[channelId];
  for (const id of ids) delete cfg.plugins.entries[id];
  cfg.plugins.allow = cfg.plugins.allow.filter((id) => !ids.includes(id));
  changed = true;
}

if (changed) fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2) + "\n", "utf8");
' "${OPENCLAW_CONFIG_FILE}" "${OPENCLAW_APP_DIR}" "${OPENCLAW_STATE_DIR}" || true

    sync_provider_models_from_upstream
    sync_skills_to_workspace
}

# Default exports before prestart recalculates runtime paths.
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR_BASE}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_FILE_BASE}"
export HOME="${OPENCLAW_STATE_DIR_BASE}"

SERVICE_COMMAND="${OPENCLAW_NODE} ${OPENCLAW_ENTRY} gateway run --allow-unconfigured --bind lan --port ${SERVICE_PORT}"
SVC_BACKGROUND=yes
SVC_WRITE_PID=yes
SVC_CWD="${OPENCLAW_APP_DIR}"
