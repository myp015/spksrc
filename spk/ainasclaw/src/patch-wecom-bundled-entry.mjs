#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-wecom-bundled-entry] usage: node patch-wecom-bundled-entry.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const targets = [
  path.join(root, 'dist', 'extensions', 'wecom'),
  path.join(root, 'node_modules', '@sunnoy', 'wecom'),
];

const ensureFile = (file, content) => {
  fs.writeFileSync(file, content, 'utf8');
};

let patched = 0;
for (const dir of targets) {
  if (!fs.existsSync(dir)) continue;
  const indexPath = path.join(dir, 'index.js');
  const pluginApiPath = path.join(dir, 'plugin-api.js');

  if (!fs.existsSync(indexPath)) continue;
  if (!fs.existsSync(pluginApiPath)) {
    fs.copyFileSync(indexPath, pluginApiPath);
  }

  ensureFile(
    path.join(dir, 'channel-plugin-api.js'),
    'export { wecomChannelPlugin } from "./wecom/channel-plugin.js";\n',
  );
  ensureFile(
    path.join(dir, 'runtime-api.js'),
    'export { setRuntime as setWecomRuntime } from "./wecom/state.js";\n',
  );
  ensureFile(
    path.join(dir, 'account-inspect-api.js'),
    'export { describeAccount as inspectWecomReadOnlyAccount } from "./wecom/accounts.js";\n',
  );
  ensureFile(
    path.join(dir, 'full-api.js'),
    'export { register as registerWecomPluginFull } from "./plugin-api.js";\n',
  );

  ensureFile(
    indexPath,
    `import { defineBundledChannelEntry, loadBundledEntryExportSync } from "openclaw/plugin-sdk/channel-entry-contract";

function registerWecomPluginFull(api) {
  loadBundledEntryExportSync(import.meta.url, {
    specifier: "./full-api.js",
    exportName: "registerWecomPluginFull"
  })(api);
}

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
  registerFull: registerWecomPluginFull
});

export default wecomEntry;
`,
  );

  patched += 1;
  console.log(`[patch-wecom-bundled-entry] patched ${dir}`);
}

if (patched === 0) {
  console.warn('[patch-wecom-bundled-entry] no wecom target found; skipping');
  process.exit(0);
}

console.log(`[patch-wecom-bundled-entry] done, patched ${patched} target(s)`);
