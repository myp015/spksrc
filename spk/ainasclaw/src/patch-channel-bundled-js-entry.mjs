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

  // Keep the built runtime under a non-shadowing name so OpenClaw's bundled
  // channel discovery loads the ESM *source* contract (index.js) instead of
  // the old defineChannelPluginEntry runtime dist/index.js. Otherwise discovery
  // sees kind != bundled-channel-entry and logs a warning.
  if (exists(distIndex) && !exists(path.join(dir, 'dist', 'index.runtime.js'))) {
    fs.copyFileSync(distIndex, path.join(dir, 'dist', 'index.runtime.js'));
  }

  write(path.join(dir, 'channel-plugin-api.js'), 'export { dingtalkPlugin } from "./dist/index.runtime.js";\n');
  write(path.join(dir, 'runtime-api.js'), 'export { setDingTalkRuntime } from "./dist/index.runtime.js";\n');
  // OpenClaw 2026.8.2 removed the legacy text-runtime SDK facade. The
  // published DingTalk runtime still imports parseInlineDirectives from that
  // facade, so provide the small compatibility function locally and rewrite
  // the import to a package-local module. This keeps the plugin loadable while
  // preserving reply/audio directive parsing used by the inbound handler.
  write(path.join(dir, 'text-runtime-compat.js'), `
const REPLY_CURRENT = /^\\[\\[reply_to_current\\]\\]\\s*/i;
const REPLY_EXPLICIT = /^\\[\\[reply_to:([^\\]]+)\\]\\]\\s*/i;
const AUDIO = /^\\[\\[audio_as_voice\\]\\]\\s*/i;
export function parseInlineDirectives(input, options = {}) {
  let text = String(input ?? "");
  let replyToCurrent = false;
  let replyToExplicitId;
  let audioAsVoice = false;
  if (REPLY_CURRENT.test(text)) { replyToCurrent = true; text = text.replace(REPLY_CURRENT, ""); }
  const explicit = text.match(REPLY_EXPLICIT);
  if (explicit) { replyToExplicitId = explicit[1]; text = text.slice(explicit[0].length); }
  if (AUDIO.test(text)) { audioAsVoice = true; text = text.replace(AUDIO, ""); }
  return {
    text: options.stripReplyTags === false ? String(input ?? "") : text,
    replyToCurrent,
    replyToExplicitId,
    replyToId: replyToExplicitId,
    audioAsVoice,
    hasReplyTag: replyToCurrent || Boolean(replyToExplicitId),
    hasAudioTag: audioAsVoice
  };
}
`);
  write(path.join(dir, 'full-api.js'),
`import dingtalkEntry from "./dist/index.runtime.js";

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
  // Do NOT keep dist/index.js: if it exists, OpenClaw's bundled channel
  // discovery loads it as the entry (treating dist/ as plugin root) instead of
  // the real ESM contract ../index.js, producing a warning and path errors.
  // Removing it makes discovery fall back to the root index.js contract, the
  // same pattern as the qqbot/wecom plugins. The runtime stays under
  // dist/index.runtime.js, referenced by the api files above.
  fs.rmSync(distIndex, { force: true });
  for (const runtimeFile of [path.join(dir, 'dist', 'index.runtime.js')]) {
    if (exists(runtimeFile)) {
      const source = fs.readFileSync(runtimeFile, 'utf8');
      const patched = source.replaceAll('openclaw/plugin-sdk/text-runtime', '../text-runtime-compat.js');
      if (patched !== source) fs.writeFileSync(runtimeFile, patched, 'utf8');
    }
  }


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
  const distDir = path.join(dir, 'dist');
  const distIndex = path.join(distDir, 'index.js');
  const channelSrc = path.join(distDir, 'src', 'channel.js');
  const runtimeSrc = path.join(distDir, 'src', 'runtime.js');
  // The vendor package may ship without a built dist dir; create it so the
  // contract entry can be written.
  fs.mkdirSync(distDir, { recursive: true });

  write(path.join(dir, 'channel-plugin-api.js'), exists(channelSrc)
    ? 'export { weixinPlugin } from "./dist/src/channel.js";\n'
    : 'export const weixinPlugin = {};\n');
  write(path.join(dir, 'runtime-api.js'), exists(runtimeSrc)
    ? 'export { setWeixinRuntime } from "./dist/src/runtime.js";\n'
    : 'export const setWeixinRuntime = () => {};\n');
  write(path.join(dir, 'full-api.js'),
`import weixinEntry from "./dist/index.runtime.js";

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

  // Built entry: copy any real vendor runtime to a non-shadowing name and then
  // REMOVE dist/index.js. If dist/index.js stays, OpenClaw's bundled channel
  // discovery loads it (treating dist/ as plugin root) instead of the real
  // contract ../index.js, which triggers the warning and path errors. Removing
  // it makes discovery fall back to the root index.js contract (qqbot/wecom
  // pattern).
  const runtimeRel = path.join(dir, 'dist', 'index.runtime.js');
  if (exists(distIndex) && !exists(runtimeRel)) {
    fs.copyFileSync(distIndex, runtimeRel);
  }
  fs.rmSync(distIndex, { force: true });

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
