#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-openclaw-lark-bundled-entry] usage: node patch-openclaw-lark-bundled-entry.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const targets = [
  path.join(root, 'node_modules', '@larksuite', 'openclaw-lark'),
  path.join(root, 'dist', 'extensions', 'openclaw-lark'),
  path.join(root, 'dist', 'extensions', 'feishu'),
];

const write = (f, c) => fs.writeFileSync(f, c, 'utf8');
const patchJson = (file, fn) => {
  if (!fs.existsSync(file)) return false;
  const j = JSON.parse(fs.readFileSync(file, 'utf8'));
  const before = JSON.stringify(j);
  fn(j);
  const after = JSON.stringify(j);
  if (before === after) return false;
  write(file, JSON.stringify(j, null, 2) + '\n');
  return true;
};

let patched = 0;
for (const dir of targets) {
  if (!fs.existsSync(dir)) continue;

  write(path.join(dir, 'channel-plugin-api.cjs'),
`const root = require("./index.js");
const feishuPlugin = root && root.feishuPlugin;
if (!feishuPlugin) throw new Error("openclaw-lark adapter: feishuPlugin export not found from ./index.js");
module.exports = { feishuPlugin };
`);

  write(path.join(dir, 'runtime-api.cjs'),
`const fs = require("node:fs");
const path = require("node:path");

function loadLarkClient() {
  const candidates = [
    "./dist/src/core/lark-client.js",
    "./src/core/lark-client.js",
  ];
  for (const rel of candidates) {
    const abs = path.join(__dirname, rel);
    if (!fs.existsSync(abs)) continue;
    const mod = require(abs);
    if (mod && mod.LarkClient && typeof mod.LarkClient.setRuntime === "function") return mod.LarkClient;
  }
  throw new Error("openclaw-lark adapter: LarkClient.setRuntime not found");
}

module.exports.setFeishuRuntime = (runtime) => {
  const LarkClient = loadLarkClient();
  LarkClient.setRuntime(runtime);
};
`);

  write(path.join(dir, 'index.cjs'),
`const { defineBundledChannelEntry } = require("openclaw/plugin-sdk/channel-entry-contract");
const { pathToFileURL } = require("node:url");

const feishuEntry = defineBundledChannelEntry({
  id: "openclaw-lark",
  name: "Feishu",
  description: "OpenClaw Lark/Feishu plugin adapter",
  importMetaUrl: pathToFileURL(__filename).href,
  plugin: { specifier: "./channel-plugin-api.cjs", exportName: "feishuPlugin" },
  runtime: { specifier: "./runtime-api.cjs", exportName: "setFeishuRuntime" }
});

module.exports = feishuEntry;
module.exports.default = feishuEntry;
`);

  patchJson(path.join(dir, 'openclaw.plugin.json'), (j) => {
    j.id = 'openclaw-lark';
    j.channels = ['feishu'];
    j.extensions = ['./index.cjs'];
  });

  patchJson(path.join(dir, 'package.json'), (j) => {
    j.openclaw = j.openclaw && typeof j.openclaw === 'object' ? j.openclaw : {};
    j.openclaw.id = 'openclaw-lark';
    j.openclaw.channel = j.openclaw.channel && typeof j.openclaw.channel === 'object' ? j.openclaw.channel : {};
    j.openclaw.channel.id = 'feishu';
    j.openclaw.extensions = ['./index.cjs'];
    j.openclaw.runtimeExtensions = ['./index.cjs'];
  });

  patched += 1;
}

console.log(`[patch-openclaw-lark-bundled-entry] patched targets=${patched}`);
