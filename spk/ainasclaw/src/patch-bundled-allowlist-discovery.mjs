#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function fail(message) {
  console.error(`[patch-bundled-allowlist-discovery] ${message}`);
  process.exit(1);
}

const root = process.argv[2];
if (!root) {
  fail('usage: node patch-bundled-allowlist-discovery.mjs <openclaw-bundle-dir>');
}

const distDir = path.join(root, 'dist');
if (!fs.existsSync(distDir)) {
  fail(`dist dir not found: ${distDir}`);
}

const targets = fs
  .readdirSync(distDir)
  .filter((name) => /^discovery-.*\.js$/.test(name))
  .map((name) => path.join(distDir, name));

if (targets.length === 0) {
  fail(`no discovery-*.js found under ${distDir}`);
}

const needle = [
  '\t\tif (entryType !== "directory") continue;',
  '\t\tif (params.skipDirectories?.has(entry.name)) continue;',
  '\t\tif (shouldIgnoreScannedDirectory(entry.name)) continue;',
].join('\n');

const replacement = [
  '\t\tif (entryType !== "directory") continue;',
  '\t\tconst bundledAllowlistRaw = params.origin === "bundled" ? (params.env?.OPENCLAW_BUNDLED_PLUGIN_DIR_ALLOWLIST ?? process.env.OPENCLAW_BUNDLED_PLUGIN_DIR_ALLOWLIST ?? "") : "";',
  '\t\tif (bundledAllowlistRaw) {',
  '\t\t\tconst bundledAllowlist = new Set(bundledAllowlistRaw.split(",").map((value) => value.trim()).filter(Boolean));',
  '\t\t\tif (bundledAllowlist.size > 0 && !bundledAllowlist.has(entry.name)) continue;',
  '\t\t}',
  '\t\tif (params.skipDirectories?.has(entry.name)) continue;',
  '\t\tif (shouldIgnoreScannedDirectory(entry.name)) continue;',
].join('\n');

let patched = 0;
let alreadyPatched = 0;
let skipped = 0;
for (const file of targets) {
  const source = fs.readFileSync(file, 'utf8');
  if (source.includes(replacement)) {
    alreadyPatched += 1;
    continue;
  }
  if (!source.includes(needle)) {
    skipped += 1;
    continue;
  }
  fs.writeFileSync(file, source.replace(needle, replacement), 'utf8');
  patched += 1;
  console.log(`[patch-bundled-allowlist-discovery] patched ${file}`);
}

if (patched === 0 && alreadyPatched === 0) {
  fail(`target text not found in any discovery file (scanned=${targets.length}, skipped=${skipped})`);
}

console.log(`[patch-bundled-allowlist-discovery] done, patched ${patched} file(s), already=${alreadyPatched}, skipped=${skipped}`);
