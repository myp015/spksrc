#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-channel-bundled-js-entry] usage: node patch-channel-bundled-js-entry.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const exists = (p) => fs.existsSync(p);
const write = (p, c) => fs.writeFileSync(p, c, 'utf8');

function patchJsonFile(file, updater) {
  if (!exists(file)) return false;
  const obj = JSON.parse(fs.readFileSync(file, 'utf8'));
  const before = JSON.stringify(obj);
  updater(obj);
  const after = JSON.stringify(obj);
  if (before === after) return false;
  write(file, JSON.stringify(obj, null, 2) + '\n');
  return true;
}

function patchDingtalk(dir) {
  if (!exists(dir)) return 0;
  const distIndex = path.join(dir, 'dist', 'index.js');
  if (!exists(distIndex)) return 0;

  write(path.join(dir, 'channel-plugin-api.js'), 'export { dingtalkPlugin } from "./dist/index.js";\n');
  write(path.join(dir, 'runtime-api.js'), 'export { setDingTalkRuntime } from "./dist/index.js";\n');
  write(path.join(dir, 'full-api.js'),
`import dingtalkEntry from "./dist/index.js";

export function registerDingTalkPluginFull(api) {
  if (!dingtalkEntry || typeof dingtalkEntry.register !== "function") return;
  const proxy = Object.create(api);
  proxy.registerChannel = () => {};
  return dingtalkEntry.register(proxy);
}
`);
  write(path.join(dir, 'index.js'),
`import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";

const dingtalkEntry = defineBundledChannelEntry({
  id: "dingtalk",
  name: "DingTalk",
  description: "DingTalk channel plugin",
  importMetaUrl: import.meta.url,
  plugin: { specifier: "./channel-plugin-api.js", exportName: "dingtalkPlugin" },
  runtime: { specifier: "./runtime-api.js", exportName: "setDingTalkRuntime" },
  registerFull(api) { return import("./full-api.js").then((m) => m.registerDingTalkPluginFull(api)); }
});

export default dingtalkEntry;
`);

  let changed = 1;
  changed += patchJsonFile(path.join(dir, 'openclaw.plugin.json'), (j) => {
    j.id = 'dingtalk';
    j.channels = ['dingtalk'];
    j.extensions = ['./index.js'];
  }) ? 1 : 0;
  changed += patchJsonFile(path.join(dir, 'package.json'), (j) => {
    j.openclaw = j.openclaw && typeof j.openclaw === 'object' ? j.openclaw : {};
    j.openclaw.id = 'dingtalk';
    j.openclaw.channel = j.openclaw.channel && typeof j.openclaw.channel === 'object' ? j.openclaw.channel : {};
    j.openclaw.channel.id = 'dingtalk';
    j.openclaw.extensions = ['./index.js'];
    j.openclaw.runtimeExtensions = ['./index.js'];
  }) ? 1 : 0;
  return changed;
}

function patchWeixin(dir) {
  if (!exists(dir)) return 0;
  const distIndex = path.join(dir, 'dist', 'index.js');
  const channelSrc = path.join(dir, 'dist', 'src', 'channel.js');
  const runtimeSrc = path.join(dir, 'dist', 'src', 'runtime.js');
  if (!exists(distIndex) || !exists(channelSrc)) return 0;

  write(path.join(dir, 'channel-plugin-api.js'), 'export { weixinPlugin } from "./dist/src/channel.js";\n');
  write(path.join(dir, 'runtime-api.js'), exists(runtimeSrc)
    ? 'export { setWeixinRuntime } from "./dist/src/runtime.js";\n'
    : 'export const setWeixinRuntime = () => {};\n');
  write(path.join(dir, 'full-api.js'),
`import weixinEntry from "./dist/index.js";

export function registerWeixinPluginFull(api) {
  if (!weixinEntry || typeof weixinEntry.register !== "function") return;
  const proxy = Object.create(api);
  proxy.registerChannel = () => {};
  return weixinEntry.register(proxy);
}
`);
  write(path.join(dir, 'index.js'),
`import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";

const weixinEntry = defineBundledChannelEntry({
  id: "openclaw-weixin",
  name: "Weixin",
  description: "Weixin channel plugin",
  importMetaUrl: import.meta.url,
  plugin: { specifier: "./channel-plugin-api.js", exportName: "weixinPlugin" },
  runtime: { specifier: "./runtime-api.js", exportName: "setWeixinRuntime" },
  registerFull(api) { return import("./full-api.js").then((m) => m.registerWeixinPluginFull(api)); }
});

export default weixinEntry;
`);

  let changed = 1;
  changed += patchJsonFile(path.join(dir, 'openclaw.plugin.json'), (j) => {
    j.id = 'openclaw-weixin';
    j.channels = ['openclaw-weixin'];
    j.extensions = ['./index.js'];
  }) ? 1 : 0;
  changed += patchJsonFile(path.join(dir, 'package.json'), (j) => {
    j.openclaw = j.openclaw && typeof j.openclaw === 'object' ? j.openclaw : {};
    j.openclaw.id = 'openclaw-weixin';
    j.openclaw.channel = j.openclaw.channel && typeof j.openclaw.channel === 'object' ? j.openclaw.channel : {};
    j.openclaw.channel.id = 'openclaw-weixin';
    j.openclaw.extensions = ['./index.js'];
    j.openclaw.runtimeExtensions = ['./index.js'];
  }) ? 1 : 0;
  return changed;
}

const targets = [
  path.join(root, 'node_modules', '@soimy', 'dingtalk'),
  path.join(root, 'dist', 'extensions', 'dingtalk'),
  path.join(root, 'node_modules', '@tencent-weixin', 'openclaw-weixin'),
  path.join(root, 'dist', 'extensions', 'openclaw-weixin'),
];

let patched = 0;
for (const t of targets) {
  if (t.includes('dingtalk')) patched += patchDingtalk(t);
  if (t.includes('openclaw-weixin')) patched += patchWeixin(t);
}

console.log(`[patch-channel-bundled-js-entry] patched units=${patched}`);
