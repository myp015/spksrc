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

const runtimeRootCandidates = fs
  .readdirSync(distDir)
  .filter((n) => /^bundled-runtime-root-.*\.js$/.test(n))
  .map((n) => path.join(distDir, n));

const doctorCandidates = fs
  .readdirSync(distDir)
  .filter((n) => /^doctor-bundled-plugin-runtime-deps-.*\.js$/.test(n))
  .map((n) => path.join(distDir, n));

if (runtimeRootCandidates.length === 0 && doctorCandidates.length === 0) {
  console.warn('[patch-bundled-runtime-deps] no bundled-runtime-root-* or doctor-bundled-plugin-runtime-deps-* files found; skipping patch');
  process.exit(0);
}

let patched = 0;
for (const file of runtimeRootCandidates) {
  const src = fs.readFileSync(file, 'utf8');

  const oldPackagePlanFn = `function resolveBundledRuntimeDependencyPackageInstallRootPlan(packageRoot, options = {}) {\n\tconst env = options.env ?? process.env;\n\tconst externalRoots = resolveExternalBundledRuntimeDepsInstallRoots({\n\t\tpluginRoot: path.join(packageRoot, "dist", "extensions", "__package__"),\n\t\tenv\n\t});\n\tif (options.forceExternal || env.OPENCLAW_PLUGIN_STAGE_DIR?.trim() || env.STATE_DIRECTORY?.trim() || !isSourceCheckoutRoot(packageRoot)) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot: path.join(packageRoot, "dist", "extensions", "__package__"),\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n\tif (isWritableDirectory(packageRoot)) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: packageRoot,\n\t\tsearchRoots: [packageRoot],\n\t\texternal: false\n\t});\n\treturn createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot: path.join(packageRoot, "dist", "extensions", "__package__"),\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n}`;

  const newPackagePlanFn = `function resolveBundledRuntimeDependencyPackageInstallRootPlan(packageRoot, options = {}) {\n\tconst env = options.env ?? process.env;\n\tconst externalRoots = resolveExternalBundledRuntimeDepsInstallRoots({\n\t\tpluginRoot: path.join(packageRoot, "dist", "extensions", "__package__"),\n\t\tenv\n\t});\n\tif (options.forceExternal || env.OPENCLAW_PLUGIN_STAGE_DIR?.trim()) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot: path.join(packageRoot, "dist", "extensions", "__package__"),\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n\tif (fs.existsSync(path.join(packageRoot, "node_modules"))) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: packageRoot,\n\t\tsearchRoots: [packageRoot],\n\t\texternal: false\n\t});\n\tif (isSourceCheckoutRoot(packageRoot) && isWritableDirectory(packageRoot)) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: packageRoot,\n\t\tsearchRoots: [packageRoot],\n\t\texternal: false\n\t});\n\treturn createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot: path.join(packageRoot, "dist", "extensions", "__package__"),\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n}`;

  const oldPluginPlanFn = `function resolveBundledRuntimeDependencyInstallRootPlan(pluginRoot, options = {}) {\n\tconst env = options.env ?? process.env;\n\tconst externalRoots = resolveExternalBundledRuntimeDepsInstallRoots({\n\t\tpluginRoot,\n\t\tenv\n\t});\n\tif (options.forceExternal || env.OPENCLAW_PLUGIN_STAGE_DIR?.trim() || env.STATE_DIRECTORY?.trim() || isPackagedBundledPluginRoot(pluginRoot)) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot,\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n\tif (isWritableDirectory(pluginRoot)) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: pluginRoot,\n\t\tsearchRoots: [pluginRoot],\n\t\texternal: false\n\t});\n\treturn createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot,\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n}`;

  const newPluginPlanFn = `function resolveBundledRuntimeDependencyInstallRootPlan(pluginRoot, options = {}) {\n\tconst env = options.env ?? process.env;\n\tconst externalRoots = resolveExternalBundledRuntimeDepsInstallRoots({\n\t\tpluginRoot,\n\t\tenv\n\t});\n\tif (options.forceExternal || env.OPENCLAW_PLUGIN_STAGE_DIR?.trim()) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot,\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n\tconst resolvedPackageRoot = resolveBundledPluginPackageRoot(pluginRoot);\n\tif (resolvedPackageRoot && fs.existsSync(path.join(resolvedPackageRoot, "node_modules"))) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: resolvedPackageRoot,\n\t\tsearchRoots: [resolvedPackageRoot],\n\t\texternal: false\n\t});\n\tconst guessedPackageRoot = path.resolve(pluginRoot, "..", "..", "..");\n\tif (fs.existsSync(path.join(guessedPackageRoot, "package.json")) && fs.existsSync(path.join(guessedPackageRoot, "node_modules"))) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: guessedPackageRoot,\n\t\tsearchRoots: [guessedPackageRoot],\n\t\texternal: false\n\t});\n\tif (isPackagedBundledPluginRoot(pluginRoot)) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot,\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n\tif (env.STATE_DIRECTORY?.trim()) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot,\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n\tif (isWritableDirectory(pluginRoot)) return createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: pluginRoot,\n\t\tsearchRoots: [pluginRoot],\n\t\texternal: false\n\t});\n\treturn createBundledRuntimeDepsInstallRootPlan({\n\t\tinstallRoot: externalRoots.at(-1) ?? resolveExternalBundledRuntimeDepsInstallRoot({\n\t\t\tpluginRoot,\n\t\t\tenv\n\t\t}),\n\t\tsearchRoots: externalRoots,\n\t\texternal: true\n\t});\n}`;

  let out = src;
  out = out.replace(oldPackagePlanFn, newPackagePlanFn);
  out = out.replace(oldPluginPlanFn, newPluginPlanFn);

  if (out !== src) {
    fs.writeFileSync(file, out, 'utf8');
    patched += 1;
    console.log(`[patch-bundled-runtime-deps] patched ${file}`);
  }
}

for (const file of doctorCandidates) {
  const src = fs.readFileSync(file, 'utf8');
  const oldMissingLine = `const missing = deps.filter((dep) => !fs.existsSync(path.join(params.packageRoot, dependencySentinelPath(dep.name))));`;
  const newMissingLine = `const packagedAppRoot = path.join(params.packageRoot, "app", "openclaw");
	const missing = deps.filter((dep) => {
		const sentinel = dependencySentinelPath(dep.name);
		if (fs.existsSync(path.join(params.packageRoot, sentinel))) return false;
		if (fs.existsSync(path.join(packagedAppRoot, sentinel))) return false;
		return true;
	});`;

  let out = src;
  out = out.replace(oldMissingLine, newMissingLine);

  if (out !== src) {
    fs.writeFileSync(file, out, 'utf8');
    patched += 1;
    console.log(`[patch-bundled-runtime-deps] patched ${file}`);
  }
}

if (patched === 0) {
  console.warn('[patch-bundled-runtime-deps] no target blocks matched; upstream file shape may have changed (skip, non-fatal)');
  process.exit(0);
}

console.log(`[patch-bundled-runtime-deps] done, patched ${patched} file(s)`);
