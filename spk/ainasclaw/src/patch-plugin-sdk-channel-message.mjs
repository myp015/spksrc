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
const indexJsPath = path.join(distDir, 'index.js');
const indexDtsPath = path.join(distDir, 'src', 'plugin-sdk', 'index.d.ts');

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

// Compatibility bridge for legacy `openclaw/plugin-sdk/channel-message` imports.
// Upstream moved symbols across submodules; keep a union export surface here.
const bridgeSource = `export * from "./index.js";\nexport * from "./channel-plugin-common.js";\nexport * from "./command-auth.js";\nexport * from "./reply-reference.js";\nexport * from "./zalouser.js";\nexport { resolveSenderCommandAuthorization, resolveSenderCommandAuthorizationWithRuntime } from "./command-auth.js";\n`;

fs.writeFileSync(jsPath, bridgeSource, 'utf8');
fs.writeFileSync(dtsPath, bridgeSource, 'utf8');

const compatExportLine = 'export { resolveSenderCommandAuthorization, resolveSenderCommandAuthorizationWithRuntime } from "./command-auth.js";\n';
const compatWildcardLines = [
  'export * from "./command-auth.js";',
  'export * from "./allow-from.js";',
];
if (fs.existsSync(indexJsPath)) {
  const indexJs = fs.readFileSync(indexJsPath, 'utf8');
  let out = indexJs;
  if (!out.includes('resolveSenderCommandAuthorization')) out = `${out}${out.endsWith('\n') ? '' : '\n'}${compatExportLine}`;
  for (const line of compatWildcardLines) {
    if (!out.includes(line)) out = `${out}${out.endsWith('\n') ? '' : '\n'}${line}\n`;
  }
  if (out !== indexJs) fs.writeFileSync(indexJsPath, out, 'utf8');
}

if (fs.existsSync(indexDtsPath)) {
  const indexDts = fs.readFileSync(indexDtsPath, 'utf8');
  let out = indexDts;
  if (!out.includes('resolveSenderCommandAuthorization')) out = `${out}${out.endsWith('\n') ? '' : '\n'}${compatExportLine}`;
  for (const line of compatWildcardLines) {
    if (!out.includes(line)) out = `${out}${out.endsWith('\n') ? '' : '\n'}${line}\n`;
  }
  if (out !== indexDts) fs.writeFileSync(indexDtsPath, out, 'utf8');
}

fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n', 'utf8');

console.log('[patch-plugin-sdk-channel-message] ensured channel-message bridge + plugin-sdk compat command-auth exports');
