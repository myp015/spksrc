#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-bundled-channel-entries] usage: node patch-wecom-bundled-entry.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const ensureFile = (file, content) => {
  fs.writeFileSync(file, content, 'utf8');
};

const copyIfMissing = (from, to) => {
  if (!fs.existsSync(from) || fs.existsSync(to)) return;
  fs.copyFileSync(from, to);
};

const patchPluginManifestId = (file, nextId) => {
  if (!fs.existsSync(file)) return false;
  const json = JSON.parse(fs.readFileSync(file, 'utf8'));
  const prev = JSON.stringify(json);
  json.id = nextId;
  if (JSON.stringify(json) === prev) return false;
  fs.writeFileSync(file, JSON.stringify(json, null, 2) + '\n', 'utf8');
  return true;
};

const patchPluginManifestContract = (file, { id, channels, extensions }) => {
  if (!fs.existsSync(file)) return false;
  const json = JSON.parse(fs.readFileSync(file, 'utf8'));
  const prev = JSON.stringify(json);
  json.id = id;
  if (Array.isArray(channels) && channels.length) json.channels = channels;
  if (Array.isArray(extensions) && extensions.length) json.extensions = extensions;
  // These plugins expose a bundled-channel-entry contract (index.js via
  // defineBundledChannelEntry), not the legacy "channel" kind. A leftover
  // "kind": "channel" makes the gateway emit
  //   plugin kind mismatch (manifest uses "channel", export uses
  //   "bundled-channel-entry")
  // and can cause a second registration of the WS plugin. Drop it.
  delete json.kind;
  if (JSON.stringify(json) === prev) return false;
  fs.writeFileSync(file, JSON.stringify(json, null, 2) + '\n', 'utf8');
  return true;
};

const patchPackageOpenClawMeta = (file, nextPluginId, nextChannelId, nextExtensions) => {
  if (!fs.existsSync(file)) return false;
  const json = JSON.parse(fs.readFileSync(file, 'utf8'));
  let changed = false;
  json.openclaw = json.openclaw && typeof json.openclaw === 'object' ? json.openclaw : {};
  if (nextPluginId) {
    if (json.openclaw.id !== nextPluginId) {
      json.openclaw.id = nextPluginId;
      changed = true;
    }
  }
  json.openclaw.channel = json.openclaw.channel && typeof json.openclaw.channel === 'object' ? json.openclaw.channel : {};
  if (nextChannelId && json.openclaw.channel.id !== nextChannelId) {
    json.openclaw.channel.id = nextChannelId;
    changed = true;
  }
  if (Array.isArray(nextExtensions) && nextExtensions.length > 0) {
    const cur = Array.isArray(json.openclaw.extensions) ? json.openclaw.extensions : [];
    if (JSON.stringify(cur) !== JSON.stringify(nextExtensions)) {
      json.openclaw.extensions = nextExtensions;
      changed = true;
    }
  }
  if (changed) fs.writeFileSync(file, JSON.stringify(json, null, 2) + '\n', 'utf8');
  return changed;
};

const writeRegisterFullProxy = ({ file, importPath, exportName = 'default', registerName }) => {
  ensureFile(
    file,
    `import pluginModule from ${JSON.stringify(importPath)};
import * as allExports from ${JSON.stringify(importPath)};

// Idempotency guard: the gateway may invoke a bundled channel plugin's
// registerFull more than once per process (e.g. discovery + real register),
// and wecom's plugin-api register() logs 'Registering WeCom WS plugin' on
// every call, which shows up as a duplicated line in doctor output. Run it
// exactly once.
let __${registerName}Done = false;
export function ${registerName}(api) {
  if (__${registerName}Done) return;
  __${registerName}Done = true;
  const target = ${exportName === 'default' ? 'pluginModule' : `allExports[${JSON.stringify(exportName)}]`} ?? allExports?.default ?? allExports;
  if (!target || typeof target.register !== 'function') return;
  const proxy = Object.create(api);
  proxy.registerChannel = () => {};
  return target.register(proxy);
}
`,
  );
};

const makeWecomRegisterIdempotent = (file) => {
  if (!fs.existsSync(file)) return;
  let s = fs.readFileSync(file, 'utf8');
  if (s.includes('__wecomRegisterDone')) return; // already patched
  s = s.replace('const plugin = {', 'let __wecomRegisterDone = false;\n\nconst plugin = {', 1);
  const sig = '  register(api) {\n    logger.info("Registering WeCom WS plugin");';
  if (s.includes(sig)) {
    s = s.replace(
      sig,
      '  register(api) {\n    if (__wecomRegisterDone) return;\n    __wecomRegisterDone = true;\n    logger.info("Registering WeCom WS plugin");',
      1,
    );
    fs.writeFileSync(file, s, 'utf8');
  }
};

const patchFeishu = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  // Keep official openclaw-lark entry contract unchanged.
  return 0;
};

const patchQQBot = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  const indexPath = path.join(dir, 'index.ts');
  const builtEntryPath = path.join(dir, 'dist', 'index.cjs');
  if (!fs.existsSync(indexPath) || !fs.existsSync(builtEntryPath)) return 0;

  // OpenClaw resolves a bundled source extension (`index.ts`) to its built
  // artifact (`dist/index.cjs`). QQBot 2.x still emits `openclaw-qqbot` from
  // that CJS entry, while the bundled manifest/config use `qqbot`.
  // Patch the artifact that the runtime actually imports; changing index.ts
  // alone has no effect on the generated bundled-plugin load path.
  const normalizePluginId = (file) => {
    const source = fs.readFileSync(file, 'utf8');
    const normalized = source
      .replace("id: 'openclaw-qqbot'", "id: 'qqbot'")
      .replace('id: "openclaw-qqbot"', 'id: "qqbot"');
    if (normalized === source && !source.includes("id: 'qqbot'") && !source.includes('id: "qqbot"')) {
      throw new Error(`QQBot 2.x plugin ID not found in ${file}`);
    }
    fs.writeFileSync(file, normalized, 'utf8');
  };

  // Gateway startup loads dist/index.cjs while plugin validation/pre-warming
  // loads index.ts through Jiti. Both exports must use the bundled ID.
  normalizePluginId(indexPath);
  normalizePluginId(builtEntryPath);
  // The discovery scan picks package.json's built JS extension. Supply the
  // same contract entry for QQBot, rather than leaving it as a plain plugin.
  const channelApiPath = path.join(dir, 'channel-plugin-api.js');
  const runtimeApiPath = path.join(dir, 'runtime-api.js');
  const fullApiPath = path.join(dir, 'full-api.js');
  const bundledEntryPath = path.join(dir, 'index.js');
  ensureFile(channelApiPath, 'import pluginModule from "./dist/index.cjs";\nexport const qqbotPlugin = pluginModule.qqbotPlugin;\n');
  ensureFile(runtimeApiPath, 'export { setQQBotRuntime } from "./dist/index.cjs";\n');
  ensureFile(fullApiPath, 'import pluginModule from "./dist/index.cjs";\nexport function registerQQBotPluginFull(api) { if (!pluginModule || typeof pluginModule.register !== "function") return; const proxy = Object.create(api); proxy.registerChannel = () => {}; return pluginModule.register(proxy); }\n');
  ensureFile(bundledEntryPath, `import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";
export default defineBundledChannelEntry({ id: "qqbot", name: "QQ Bot", description: "QQ Bot channel plugin", importMetaUrl: import.meta.url, plugin: { specifier: "./channel-plugin-api.js", exportName: "qqbotPlugin" }, runtime: { specifier: "./runtime-api.js", exportName: "setQQBotRuntime" }, registerFull(api) { return import("./full-api.js").then((m) => m.registerQQBotPluginFull(api)); } });
`);
  copyIfMissing(indexPath, path.join(dir, 'plugin-api.ts'));
  ensureFile(indexPath, 'export { default } from \"./index.js\";\n');
  patchPluginManifestContract(path.join(dir, 'openclaw.plugin.json'), {
    id: 'qqbot',
    channels: ['qqbot'],
    extensions: ['./index.js']
  });
  patchPackageOpenClawMeta(path.join(dir, 'package.json'), 'qqbot', 'qqbot', ['./index.js']);
  return 1;
};

const patchDingTalk = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  const indexPath = path.join(dir, 'index.ts');
  const pluginApiPath = path.join(dir, 'plugin-api.ts');
  if (!fs.existsSync(indexPath)) return 0;
  copyIfMissing(indexPath, pluginApiPath);
  ensureFile(path.join(dir, 'channel-plugin-api.ts'), 'export { dingtalkPlugin } from "./src/channel";\n');
  ensureFile(path.join(dir, 'runtime-api.ts'), 'export { setDingTalkRuntime } from "./src/runtime";\n');
  writeRegisterFullProxy({
    file: path.join(dir, 'full-api.ts'),
    importPath: './plugin-api.ts',
    registerName: 'registerDingTalkPluginFull',
  });
  ensureFile(
    indexPath,
    `import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";

const dingtalkEntry = defineBundledChannelEntry({
  id: "dingtalk",
  name: "DingTalk",
  description: "DingTalk channel plugin",
  importMetaUrl: import.meta.url,
  plugin: {
    specifier: "./channel-plugin-api.ts",
    exportName: "dingtalkPlugin"
  },
  runtime: {
    specifier: "./runtime-api.ts",
    exportName: "setDingTalkRuntime"
  },
  registerFull(api) {
    return import("./full-api.ts").then((m) => m.registerDingTalkPluginFull(api));
  }
});

export default dingtalkEntry;
`,
  );
  ensureFile(indexPath, 'export { default } from \"./index.js\";\n');
  patchPluginManifestContract(path.join(dir, 'openclaw.plugin.json'), {
    id: 'dingtalk',
    channels: ['dingtalk'],
    extensions: ['./index.ts']
  });
  patchPackageOpenClawMeta(path.join(dir, 'package.json'), 'dingtalk', 'dingtalk', ['./index.ts']);
  return 1;
};

const patchWeCom = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  const indexPath = path.join(dir, 'index.js');
  const pluginApiPath = path.join(dir, 'plugin-api.js');
  if (!fs.existsSync(indexPath)) return 0;
  copyIfMissing(indexPath, pluginApiPath);
  // The gateway invokes a bundled channel plugin's register() more than once
  // per process (discovery + real register), and doctor also scans both the
  // dist/extensions and node_modules copies of wecom. Each call to wecom's
  // register() logs 'Registering WeCom WS plugin', so the line appears
  // duplicated in doctor output. Make register() idempotent.
  makeWecomRegisterIdempotent(pluginApiPath);
  ensureFile(path.join(dir, 'channel-plugin-api.js'), 'export { wecomChannelPlugin } from "./wecom/channel-plugin.js";\n');
  ensureFile(path.join(dir, 'runtime-api.js'), 'export { setRuntime as setWecomRuntime } from "./wecom/state.js";\n');
  ensureFile(path.join(dir, 'account-inspect-api.js'), 'export { describeAccount as inspectWecomReadOnlyAccount } from "./wecom/accounts.js";\n');
  writeRegisterFullProxy({
    file: path.join(dir, 'full-api.js'),
    importPath: './plugin-api.js',
    registerName: 'registerWecomPluginFull',
  });
  ensureFile(
    indexPath,
    `import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";

const wecomEntry = defineBundledChannelEntry({
  id: "wecom",
  name: "WeCom",
  description: "Enterprise WeChat (WeCom) channel plugin",
  importMetaUrl: import.meta.url,
  plugin: {
    specifier: "./channel-plugin-api.js",
    exportName: "wecomChannelPlugin"
  },
  runtime: {
    specifier: "./runtime-api.js",
    exportName: "setWecomRuntime"
  },
  accountInspect: {
    specifier: "./account-inspect-api.js",
    exportName: "inspectWecomReadOnlyAccount"
  },
  registerFull(api) {
    return import("./full-api.js").then((m) => m.registerWecomPluginFull(api));
  }
});

export default wecomEntry;
`,
  );
  patchPluginManifestContract(path.join(dir, 'openclaw.plugin.json'), {
    id: 'wecom',
    channels: ['wecom'],
    extensions: ['./index.js']
  });
  patchPackageOpenClawMeta(path.join(dir, 'package.json'), 'wecom', 'wecom', ['./index.js']);
  return 1;
};

const patchWeixin = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  const indexPath = path.join(dir, 'index.ts');
  if (!fs.existsSync(indexPath)) return 0;
  ensureFile(path.join(dir, 'channel-plugin-api.ts'), 'export { weixinPlugin } from "./src/channel.js";\n');
  ensureFile(path.join(dir, 'runtime-api.ts'), 'export { setWeixinRuntime } from "./src/runtime.js";\n');
  writeRegisterFullProxy({
    file: path.join(dir, 'full-api.ts'),
    importPath: './index.ts',
    registerName: 'registerWeixinPluginFull',
  });
  ensureFile(
    indexPath,
    `import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";

const weixinEntry = defineBundledChannelEntry({
  id: "openclaw-weixin",
  name: "Weixin",
  description: "Weixin channel plugin",
  importMetaUrl: import.meta.url,
  plugin: {
    specifier: "./channel-plugin-api.ts",
    exportName: "weixinPlugin"
  },
  runtime: {
    specifier: "./runtime-api.ts",
    exportName: "setWeixinRuntime"
  },
  registerFull(api) {
    return import("./full-api.ts").then((m) => m.registerWeixinPluginFull(api));
  }
});

export default weixinEntry;
`,
  );
  ensureFile(indexPath, 'export { default } from \"./index.js\";\n');
  patchPluginManifestContract(path.join(dir, 'openclaw.plugin.json'), {
    id: 'openclaw-weixin',
    channels: ['openclaw-weixin'],
    extensions: ['./index.ts']
  });
  patchPackageOpenClawMeta(path.join(dir, 'package.json'), 'openclaw-weixin', 'openclaw-weixin', ['./index.ts']);
  return 1;
};

const targets = [
  // Patch node_modules source roots first. DSM service-setup stages channel dirs
  // from these package roots into dist/extensions at runtime.
  { name: 'node-feishu', dir: path.join(root, 'node_modules', '@larksuite', 'openclaw-lark'), patch: patchFeishu },
  { name: 'node-qqbot', dir: path.join(root, 'node_modules', '@tencent-connect', 'openclaw-qqbot'), patch: patchQQBot },
  { name: 'node-dingtalk', dir: path.join(root, 'node_modules', '@soimy', 'dingtalk'), patch: patchDingTalk },
  { name: 'node-wecom', dir: path.join(root, 'node_modules', '@sunnoy', 'wecom'), patch: patchWeCom },
  { name: 'node-weixin', dir: path.join(root, 'node_modules', '@tencent-weixin', 'openclaw-weixin'), patch: patchWeixin },

  // Also patch any already-staged dist/extensions copies when they exist.
  { name: 'feishu', dir: path.join(root, 'dist', 'extensions', 'feishu'), patch: patchFeishu },
  { name: 'qqbot', dir: path.join(root, 'dist', 'extensions', 'qqbot'), patch: patchQQBot },
  { name: 'dingtalk', dir: path.join(root, 'dist', 'extensions', 'dingtalk'), patch: patchDingTalk },
  { name: 'wecom', dir: path.join(root, 'dist', 'extensions', 'wecom'), patch: patchWeCom },
  { name: 'openclaw-weixin', dir: path.join(root, 'dist', 'extensions', 'openclaw-weixin'), patch: patchWeixin },
];

let patched = 0;
for (const target of targets) {
  patched += target.patch(target.dir);
}

if (patched === 0) {
  console.warn('[patch-bundled-channel-entries] no target found; skipping');
  process.exit(0);
}

console.log(`[patch-bundled-channel-entries] done, patched ${patched} target(s)`);
