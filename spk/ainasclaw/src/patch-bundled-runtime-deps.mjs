#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-bundled-runtime-deps] usage: node patch-bundled-runtime-deps.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const distDir = path.join(root, 'dist');
if (!fs.existsSync(distDir)) {
  console.error(`[patch-bundled-runtime-deps] dist dir not found: ${distDir}`);
  process.exit(1);
}

const candidates = fs
  .readdirSync(distDir)
  .filter((n) => /^bundled-runtime-deps-.*\.js$/.test(n))
  .map((n) => path.join(distDir, n));

if (candidates.length === 0) {
  console.warn('[patch-bundled-runtime-deps] no bundled-runtime-deps-*.js found; skipping patch');
  process.exit(0);
}

let patched = 0;
for (const file of candidates) {
  const src = fs.readFileSync(file, 'utf8');

  const oldPackageFn = `function resolveBundledRuntimeDependencyPackageInstallRoot(packageRoot, options = {}) {\n\tconst env = options.env ?? process.env;\n\tconst externalRoot = resolveExternalBundledRuntimeDepsInstallRoot({\n\t\tpluginRoot: path.join(packageRoot, "dist", "extensions", "__package__"),\n\t\tenv\n\t});\n\tif (options.forceExternal || env.OPENCLAW_PLUGIN_STAGE_DIR?.trim() || env.STATE_DIRECTORY?.trim() || !isSourceCheckoutRoot(packageRoot)) return externalRoot;\n\treturn isWritableDirectory(packageRoot) ? packageRoot : externalRoot;\n}`;

  const newPackageFn = `function resolveBundledRuntimeDependencyPackageInstallRoot(packageRoot, options = {}) {\n\tconst env = options.env ?? process.env;\n\tconst externalRoot = resolveExternalBundledRuntimeDepsInstallRoot({\n\t\tpluginRoot: path.join(packageRoot, \"dist\", \"extensions\", \"__package__\"),\n\t\tenv\n\t});\n\tif (options.forceExternal || env.OPENCLAW_PLUGIN_STAGE_DIR?.trim() || env.STATE_DIRECTORY?.trim()) return externalRoot;\n\tif (isSourceCheckoutRoot(packageRoot)) return isWritableDirectory(packageRoot) ? packageRoot : externalRoot;\n\tif (fs.existsSync(path.join(packageRoot, \"node_modules\"))) return packageRoot;\n\treturn externalRoot;\n}`;

  const oldPluginFn = `function resolveBundledRuntimeDependencyInstallRoot(pluginRoot, options = {}) {\n\tconst env = options.env ?? process.env;\n\tconst externalRoot = resolveExternalBundledRuntimeDepsInstallRoot({\n\t\tpluginRoot,\n\t\tenv\n\t});\n\tif (options.forceExternal || env.OPENCLAW_PLUGIN_STAGE_DIR?.trim() || env.STATE_DIRECTORY?.trim() || isPackagedBundledPluginRoot(pluginRoot)) return externalRoot;\n\treturn isWritableDirectory(pluginRoot) ? pluginRoot : externalRoot;\n}`;

  const newPluginFn = `function resolveBundledRuntimeDependencyInstallRoot(pluginRoot, options = {}) {\n\tconst env = options.env ?? process.env;\n\tconst externalRoot = resolveExternalBundledRuntimeDepsInstallRoot({\n\t\tpluginRoot,\n\t\tenv\n\t});\n\tif (options.forceExternal || env.OPENCLAW_PLUGIN_STAGE_DIR?.trim() || env.STATE_DIRECTORY?.trim()) return externalRoot;\n\tconst resolvedPackageRoot = resolveBundledPluginPackageRoot(pluginRoot);\n\tif (resolvedPackageRoot && fs.existsSync(path.join(resolvedPackageRoot, \"node_modules\"))) return resolvedPackageRoot;\n\t// Heuristic fallback for bundled stock plugins under <packageRoot>/dist/extensions/<pluginId>.\n\tconst guessedPackageRoot = path.resolve(pluginRoot, \"..\", \"..\", \"..\");\n\tif (fs.existsSync(path.join(guessedPackageRoot, \"package.json\")) && fs.existsSync(path.join(guessedPackageRoot, \"node_modules\"))) return guessedPackageRoot;\n\tif (isPackagedBundledPluginRoot(pluginRoot)) return externalRoot;\n\treturn isWritableDirectory(pluginRoot) ? pluginRoot : externalRoot;\n}`;

  let out = src;
  out = out.replace(oldPackageFn, newPackageFn);
  out = out.replace(oldPluginFn, newPluginFn);

  if (out !== src) {
    fs.writeFileSync(file, out, 'utf8');
    patched += 1;
    console.log(`[patch-bundled-runtime-deps] patched ${file}`);
  }
}

if (patched === 0) {
  console.error('[patch-bundled-runtime-deps] no target blocks matched; upstream file shape may have changed');
  process.exit(1);
}

console.log(`[patch-bundled-runtime-deps] done, patched ${patched} file(s)`);
