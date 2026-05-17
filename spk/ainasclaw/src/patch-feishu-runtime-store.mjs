#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-feishu-runtime-store] usage: node patch-feishu-runtime-store.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const targets = [
  path.join(root, 'node_modules', '@larksuite', 'openclaw-lark'),
  path.join(root, 'dist', 'extensions', 'feishu'),
  path.join(root, 'dist', 'extensions', 'openclaw-lark'),
];

const runtimeStorePatch = `"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.setLarkRuntime = setLarkRuntime;
exports.tryGetLarkRuntime = tryGetLarkRuntime;
exports.getLarkRuntime = getLarkRuntime;
const RUNTIME_NOT_INITIALIZED_ERROR = 'Feishu plugin runtime has not been initialised. Ensure LarkClient.setRuntime() is called during plugin activation.';
const RUNTIME_KEY = '__OPENCLAW_FEISHU_RUNTIME__';
function setLarkRuntime(nextRuntime) {
  globalThis[RUNTIME_KEY] = nextRuntime ?? null;
}
function tryGetLarkRuntime() {
  return globalThis[RUNTIME_KEY] ?? null;
}
function getLarkRuntime() {
  const runtime = tryGetLarkRuntime();
  if (!runtime) {
    throw new Error(RUNTIME_NOT_INITIALIZED_ERROR);
  }
  return runtime;
}
`;

let patched = 0;
for (const dir of targets) {
  if (!fs.existsSync(dir)) continue;
  const file = path.join(dir, 'src', 'core', 'runtime-store.js');
  if (!fs.existsSync(file)) continue;
  fs.writeFileSync(file, runtimeStorePatch, 'utf8');
  patched += 1;
}

console.log(`[patch-feishu-runtime-store] patched targets=${patched}`);
