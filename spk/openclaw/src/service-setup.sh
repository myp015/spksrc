OPENCLAW_NODE="${SYNOPKG_PKGDEST}/bin/node"
OPENCLAW_APP_DIR="${SYNOPKG_PKGDEST}/app/openclaw"
OPENCLAW_ENTRY="${OPENCLAW_APP_DIR}/dist/index.js"
OPENCLAW_STATE_DIR_DEFAULT="/volume1/docker/openclaw/.openclaw"
OPENCLAW_WORKSPACE="${OPENCLAW_STATE_DIR_DEFAULT}"
OPENCLAW_CONFIG_FILE="${OPENCLAW_STATE_DIR_DEFAULT}/openclaw.json"
OPENCLAW_LEGACY_CONFIG_FILE="${SYNOPKG_PKGVAR}/openclaw.json"
OPENCLAW_DEFAULT_CONFIG="${SYNOPKG_PKGDEST}/var/openclaw.json"

service_postinst() {
    if [ "${SYNOPKG_PKG_STATUS}" = "INSTALL" ]; then
        mkdir -p "${OPENCLAW_STATE_DIR_DEFAULT}"

        if [ ! -f "${OPENCLAW_CONFIG_FILE}" ]; then
            if [ -f "${OPENCLAW_LEGACY_CONFIG_FILE}" ]; then
                cp -f "${OPENCLAW_LEGACY_CONFIG_FILE}" "${OPENCLAW_CONFIG_FILE}"
            else
                cp -f "${OPENCLAW_DEFAULT_CONFIG}" "${OPENCLAW_CONFIG_FILE}"
            fi
        fi

        # Wizard defaults
        export WIZARD_WORKSPACE_DIR="${wizard_workspace_dir:-/volume1/docker/openclaw/.openclaw}"
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
const p = process.argv[1];
const cfg = JSON.parse(fs.readFileSync(p, "utf8"));
const trim = (v) => (typeof v === "string" ? v.trim() : "");

const workspace = trim(process.env.WIZARD_WORKSPACE_DIR) || "/volume1/docker/openclaw/.openclaw";
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

const feishuAppId = trim(process.env.WIZARD_FEISHU_APP_ID);
const feishuAppSecret = trim(process.env.WIZARD_FEISHU_APP_SECRET);
if (feishuAppId && feishuAppSecret) {
  cfg.channels.feishu = cfg.channels.feishu || {};
  cfg.channels.feishu.appId = feishuAppId;
  cfg.channels.feishu.appSecret = feishuAppSecret;
  cfg.plugins.entries.feishu = cfg.plugins.entries.feishu || {};
  cfg.plugins.entries.feishu.enabled = true;
}

const dingtalkClientId = trim(process.env.WIZARD_DINGTALK_CLIENT_ID);
const dingtalkClientSecret = trim(process.env.WIZARD_DINGTALK_CLIENT_SECRET);
if (dingtalkClientId && dingtalkClientSecret) {
  cfg.channels.dingtalk = cfg.channels.dingtalk || {};
  cfg.channels.dingtalk.clientId = dingtalkClientId;
  cfg.channels.dingtalk.clientSecret = dingtalkClientSecret;
  cfg.plugins.entries["openclaw-dingtalk"] = cfg.plugins.entries["openclaw-dingtalk"] || {};
  cfg.plugins.entries["openclaw-dingtalk"].enabled = true;
}

const qqbotAppId = trim(process.env.WIZARD_QQBOT_APP_ID);
const qqbotClientSecret = trim(process.env.WIZARD_QQBOT_CLIENT_SECRET);
if (qqbotAppId && qqbotClientSecret) {
  cfg.channels.qqbot = cfg.channels.qqbot || {};
  cfg.channels.qqbot.appId = qqbotAppId;
  cfg.channels.qqbot.clientSecret = qqbotClientSecret;
  cfg.plugins.entries.qqbot = cfg.plugins.entries.qqbot || {};
  cfg.plugins.entries.qqbot.enabled = true;
}

const wecomBotId = trim(process.env.WIZARD_WECOM_BOT_ID);
const wecomSecret = trim(process.env.WIZARD_WECOM_SECRET);
if (wecomBotId && wecomSecret) {
  cfg.channels.wecom = cfg.channels.wecom || {};
  cfg.channels.wecom.botId = wecomBotId;
  cfg.channels.wecom.secret = wecomSecret;
  cfg.plugins.entries["openclaw-wecom"] = cfg.plugins.entries["openclaw-wecom"] || {};
  cfg.plugins.entries["openclaw-wecom"].enabled = true;
}

fs.writeFileSync(p, JSON.stringify(cfg, null, 2) + "\n", "utf8");
' "${OPENCLAW_CONFIG_FILE}"
    fi
}

service_prestart() {
    mkdir -p "${OPENCLAW_STATE_DIR_DEFAULT}"
    mkdir -p "${OPENCLAW_WORKSPACE}"

    if [ ! -f "${OPENCLAW_CONFIG_FILE}" ]; then
        if [ -f "${OPENCLAW_LEGACY_CONFIG_FILE}" ]; then
            cp -f "${OPENCLAW_LEGACY_CONFIG_FILE}" "${OPENCLAW_CONFIG_FILE}"
        else
            cp -f "${OPENCLAW_DEFAULT_CONFIG}" "${OPENCLAW_CONFIG_FILE}"
        fi
    fi
}

# Keep config + runtime state/workspace under docker-style path.
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR_DEFAULT}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_FILE}"
export HOME="${OPENCLAW_STATE_DIR_DEFAULT}"

SERVICE_COMMAND="${OPENCLAW_NODE} ${OPENCLAW_ENTRY} gateway run --allow-unconfigured --bind lan --port ${SERVICE_PORT}"
SVC_BACKGROUND=yes
SVC_WRITE_PID=yes
SVC_CWD="${OPENCLAW_APP_DIR}"
