#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-feishu-plugin-sdk-imports] usage: node patch-feishu-plugin-sdk-imports.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const targets = [
  path.join(root, 'node_modules', '@larksuiteoapi', 'feishu-openclaw-plugin', 'src', 'messaging', 'inbound', 'handler.js'),
  path.join(root, 'dist', 'extensions', 'feishu', 'src', 'messaging', 'inbound', 'handler.js'),
];

const importSplit = `import { recordPendingHistoryEntryIfEnabled, DEFAULT_GROUP_HISTORY_LIMIT, } from "openclaw/plugin-sdk";
import { resolveSenderCommandAuthorization } from "openclaw/plugin-sdk/command-auth";
import { isNormalizedSenderAllowed } from "openclaw/plugin-sdk/allow-from";`;

let patched = 0;
for (const file of targets) {
  if (!fs.existsSync(file)) continue;
  const src = fs.readFileSync(file, 'utf8');
  let out = src;

  const pluginSdkImportPattern = /import\s*\{[^}]*\}\s*from\s*"openclaw\/plugin-sdk";\n?/g;
  out = out.replace(pluginSdkImportPattern, '');
  const commandAuthImportPattern = /import\s*\{\s*resolveSenderCommandAuthorization\s*\}\s*from\s*"openclaw\/plugin-sdk\/command-auth";\n?/g;
  out = out.replace(commandAuthImportPattern, '');
  const allowFromImportPattern = /import\s*\{\s*isNormalizedSenderAllowed\s*\}\s*from\s*"openclaw\/plugin-sdk\/allow-from";\n?/g;
  out = out.replace(allowFromImportPattern, '');

  const marker = 'import { getLarkAccount } from "../../core/accounts.js";';
  if (out.includes(marker)) {
    out = out.replace(marker, `${importSplit}\n${marker}`);
  }

  if (out !== src) {
    fs.writeFileSync(file, out, 'utf8');
    patched += 1;
    console.log(`[patch-feishu-plugin-sdk-imports] patched ${file}`);
  }
}

if (patched === 0) {
  console.warn('[patch-feishu-plugin-sdk-imports] no target blocks matched; upstream file shape may have changed (skip, non-fatal)');
  process.exit(0);
}

console.log(`[patch-feishu-plugin-sdk-imports] done, patched ${patched} file(s)`);
