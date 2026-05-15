#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-plugin-sdk-channel-message] usage: node patch-plugin-sdk-channel-message.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const pkgPath = path.join(root, 'package.json');
const distDir = path.join(root, 'dist', 'plugin-sdk');
const jsPath = path.join(distDir, 'channel-message.js');
const dtsPath = path.join(distDir, 'channel-message.d.ts');

if (!fs.existsSync(pkgPath)) {
  console.error(`[patch-plugin-sdk-channel-message] package.json not found: ${pkgPath}`);
  process.exit(1);
}
if (!fs.existsSync(distDir)) {
  console.error(`[patch-plugin-sdk-channel-message] dist plugin-sdk dir not found: ${distDir}`);
  process.exit(1);
}

const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
pkg.exports = pkg.exports && typeof pkg.exports === 'object' ? pkg.exports : {};

pkg.exports['./plugin-sdk/channel-message'] = {
  types: './dist/plugin-sdk/channel-message.d.ts',
  default: './dist/plugin-sdk/channel-message.js',
};

const bridgeSource = `export * from "./channel-plugin-common.js";\nexport * from "./command-auth.js";\nexport { createMessageReceiptFromOutboundResults } from "./reply-reference.js";\n`;

fs.writeFileSync(jsPath, bridgeSource, 'utf8');
fs.writeFileSync(dtsPath, bridgeSource, 'utf8');
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n', 'utf8');

console.log('[patch-plugin-sdk-channel-message] ensured ./plugin-sdk/channel-message export + bridge files');
