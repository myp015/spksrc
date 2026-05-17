#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-jiti-loader-try-native] usage: node patch-jiti-loader-try-native.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const targets = [
  path.join(root, 'node_modules', '@earendil-works', 'pi-coding-agent', 'dist', 'core', 'extensions', 'loader.js'),
  path.join(root, 'dist', 'node_modules', '@earendil-works', 'pi-coding-agent', 'dist', 'core', 'extensions', 'loader.js'),
];

let patched = 0;
for (const file of targets) {
  if (!fs.existsSync(file)) continue;
  let next = fs.readFileSync(file, 'utf8');
  next = next.replace(
    '...(isBunBinary ? { virtualModules: VIRTUAL_MODULES, tryNative: false } : { alias: getAliases() }),',
    '...(isBunBinary ? { virtualModules: VIRTUAL_MODULES, tryNative: false } : { alias: getAliases(), tryNative: false }),',
  );
  if (!next.includes('let __jitiImportQueue = Promise.resolve();') && next.includes('async function loadExtensionModule(extensionPath) {')) {
    next = next.replace(
      'async function loadExtensionModule(extensionPath) {',
      'let __jitiImportQueue = Promise.resolve();\nasync function loadExtensionModule(extensionPath) {',
    );
  }
  if (next.includes('const module = await jiti.import(extensionPath, { default: true });')) {
    next = next.replace(
      'const module = await jiti.import(extensionPath, { default: true });',
      'const module = await (__jitiImportQueue = __jitiImportQueue.then(() => jiti.import(extensionPath, { default: true })));',
    );
  }
  fs.writeFileSync(file, next, 'utf8');
  patched += 1;
}

console.log(`[patch-jiti-loader-try-native] patched files=${patched}`);
