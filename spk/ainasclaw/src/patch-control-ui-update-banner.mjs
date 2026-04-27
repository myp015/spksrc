#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

function fail(msg) {
  console.error(msg);
  process.exit(1);
}

const bundleRoot = process.argv[2];
if (!bundleRoot) {
  fail("Usage: node src/patch-control-ui-update-banner.mjs <openclaw-bundle-root>");
}

const assetsDir = path.join(bundleRoot, "dist", "control-ui", "assets");
if (!fs.existsSync(assetsDir)) {
  fail(`Control UI assets dir not found: ${assetsDir}`);
}

const files = fs
  .readdirSync(assetsDir)
  .filter((name) => /^index-.*\.js$/.test(name))
  .map((name) => path.join(assetsDir, name));

if (!files.length) {
  fail(`No control-ui index assets found under: ${assetsDir}`);
}

const markerRegex =
  /e\.updateAvailable&&e\.updateAvailable\.latestVersion!==e\.updateAvailable\.currentVersion&&!([A-Za-z_$][A-Za-z0-9_$]*)\(e\.updateAvailable\)/g;

let patched = 0;
for (const file of files) {
  const original = fs.readFileSync(file, "utf8");
  let replacedCount = 0;
  const updated = original.replace(markerRegex, (_m, fnName) => {
    replacedCount += 1;
    return `false&&e.updateAvailable&&e.updateAvailable.latestVersion!==e.updateAvailable.currentVersion&&!${fnName}(e.updateAvailable)`;
  });
  if (replacedCount > 0 && updated !== original) {
    fs.writeFileSync(file, updated, "utf8");
    patched += 1;
    console.log(
      `[patch-control-ui-update-banner] patched: ${path.basename(file)} (replacements: ${replacedCount})`,
    );
  }
}

if (patched === 0) {
  fail(
    `[patch-control-ui-update-banner] update banner marker not found in any control-ui index asset under ${assetsDir}`,
  );
}

console.log(`[patch-control-ui-update-banner] done, patched files: ${patched}`);
