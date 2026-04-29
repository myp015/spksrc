#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function fail(msg) {
  console.error(`[patch-startup-sidecars] ${msg}`);
  process.exit(1);
}

const root = process.argv[2];
if (!root) {
  fail('usage: node patch-startup-sidecars.mjs <openclaw-bundle-dir>');
}

const distDir = path.join(root, 'dist');
if (!fs.existsSync(distDir)) {
  fail(`dist dir not found: ${distDir}`);
}

const targets = fs.readdirSync(distDir).filter((name) => /^server\.impl-.*\.js$/.test(name));
if (targets.length === 0) {
  fail(`no server.impl-*.js found under ${distDir}`);
}

let patched = 0;
for (const name of targets) {
  const file = path.join(distDir, name);
  const src = fs.readFileSync(file, 'utf8');
  const reSidecars = /let startupSidecarsReady = minimalTestGateway;|let startupSidecarsReady = minimalTestGateway \|\| opts\.deferStartupSidecars !== false;/;
  const reUnavailable = /const unavailableGatewayMethods = new Set\(minimalTestGateway \? \[\] : STARTUP_UNAVAILABLE_GATEWAY_METHODS\);|const unavailableGatewayMethods = new Set\(minimalTestGateway \|\| opts\.deferStartupSidecars !== false \? \[\] : STARTUP_UNAVAILABLE_GATEWAY_METHODS\);/;
  if (!reSidecars.test(src) || !reUnavailable.test(src)) {
    fail(`target text not found in ${file}`);
  }
  let out = src.replace(
    /let startupSidecarsReady = minimalTestGateway(?: \|\| opts\.deferStartupSidecars !== false)?;/,
    'let startupSidecarsReady = minimalTestGateway || opts.deferStartupSidecars !== false;'
  );
  out = out.replace(
    /const unavailableGatewayMethods = new Set\(minimalTestGateway(?: \|\| opts\.deferStartupSidecars !== false)? \? \[\] : STARTUP_UNAVAILABLE_GATEWAY_METHODS\);/,
    'const unavailableGatewayMethods = new Set(minimalTestGateway || opts.deferStartupSidecars !== false ? [] : STARTUP_UNAVAILABLE_GATEWAY_METHODS);'
  );
  if (out === src) continue;
  fs.writeFileSync(file, out, 'utf8');
  patched += 1;
  console.log(`[patch-startup-sidecars] patched ${file}`);
}

if (patched === 0) {
  fail('no file patched');
}

console.log(`[patch-startup-sidecars] done, patched ${patched} file(s)`);
