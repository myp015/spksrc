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

export function ${registerName}(api) {
  const target = ${exportName === 'default' ? 'pluginModule' : `allExports[${JSON.stringify(exportName)}]`} ?? allExports?.default ?? allExports;
  if (!target || typeof target.register !== 'function') return;
  const proxy = Object.create(api);
  proxy.registerChannel = () => {};
  return target.register(proxy);
}
`,
  );
};

const patchFeishu = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  const indexPath = path.join(dir, 'index.js');
  const pluginApiPath = path.join(dir, 'plugin-api.js');
  if (!fs.existsSync(indexPath)) return 0;
  copyIfMissing(indexPath, pluginApiPath);
  ensureFile(path.join(dir, 'channel-plugin-api.js'), 'export { feishuPlugin } from "./plugin-api.js";\n');
  ensureFile(
    indexPath,
    `import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";

const feishuEntry = defineBundledChannelEntry({
  id: "feishu",
  name: "Feishu",
  description: "Feishu/Lark channel plugin",
  importMetaUrl: import.meta.url,
  plugin: {
    specifier: "./channel-plugin-api.js",
    exportName: "feishuPlugin"
  }
});

export default feishuEntry;
`,
  );
  patchPluginManifestContract(path.join(dir, 'openclaw.plugin.json'), {
    id: 'feishu',
    channels: ['feishu'],
    extensions: ['./index.js']
  });
  patchPackageOpenClawMeta(path.join(dir, 'package.json'), 'feishu', 'feishu', ['./index.js']);
  return 1;
};

const patchQQBot = (dir) => {
  if (!fs.existsSync(dir)) return 0;
  const indexPath = path.join(dir, 'index.ts');
  const pluginApiPath = path.join(dir, 'plugin-api.ts');
  if (!fs.existsSync(indexPath)) return 0;
  copyIfMissing(indexPath, pluginApiPath);
  ensureFile(path.join(dir, 'channel-plugin-api.ts'), 'export { qqbotPlugin } from "./plugin-api.ts";\n');
  ensureFile(path.join(dir, 'runtime-api.ts'), 'export { setQQBotRuntime } from "./plugin-api.ts";\n');
  writeRegisterFullProxy({
    file: path.join(dir, 'full-api.ts'),
    importPath: './plugin-api.ts',
    registerName: 'registerQQBotPluginFull',
  });
  ensureFile(
    indexPath,
    `import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";

const qqbotEntry = defineBundledChannelEntry({
  id: "qqbot",
  name: "QQ Bot",
  description: "QQ Bot channel plugin",
  importMetaUrl: import.meta.url,
  plugin: {
    specifier: "./channel-plugin-api.ts",
    exportName: "qqbotPlugin"
  },
  runtime: {
    specifier: "./runtime-api.ts",
    exportName: "setQQBotRuntime"
  },
  registerFull(api) {
    return import("./full-api.ts").then((m) => m.registerQQBotPluginFull(api));
  }
});

export default qqbotEntry;
`,
  );
  patchPluginManifestContract(path.join(dir, 'openclaw.plugin.json'), {
    id: 'qqbot',
    channels: ['qqbot'],
    extensions: ['./index.ts']
  });
  patchPackageOpenClawMeta(path.join(dir, 'package.json'), 'qqbot', 'qqbot', ['./index.ts']);
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
  { name: 'node-feishu', dir: path.join(root, 'node_modules', '@larksuiteoapi', 'feishu-openclaw-plugin'), patch: patchFeishu },
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
