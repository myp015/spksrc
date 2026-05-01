#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-gateway-warmup-cache] usage: node patch-gateway-warmup-cache.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const distDir = path.join(root, 'dist');
if (!fs.existsSync(distDir)) {
  console.warn('[patch-gateway-warmup-cache] dist dir not found; skipping');
  process.exit(0);
}

function patchServerMethods(file) {
  const src = fs.readFileSync(file, 'utf8');
  let out = src;

  out = out.replace(
    /const modelsAuthStatusHandlers = \{ "models\.authStatus": async \(\{ params, respond, context \}\) => \{[\s\S]*?\n\} \};/,
    `let contextForModelAuthWarmup;
async function warmModelAuthStatusCache(){
\tconst now = Date.now();
\tif (cached && now - cached.ts < CACHE_TTL_MS) return cached.result;
\tconst cfg = contextForModelAuthWarmup?.getRuntimeConfig?.() ?? loadConfig();
\tconst agentDir = resolveOpenClawAgentDir();
\tconst store = ensureAuthProfileStore(agentDir);
\tconst configured = resolveConfiguredProviders(cfg);
\tconst authHealth = buildAuthHealthSummary({
\t\tstore,
\t\tcfg,
\t\tproviders: configured.providers.length > 0 ? configured.providers : void 0
\t});
\tconst usageProviderIds = [...new Set(authHealth.profiles.filter((p) => p.type === "oauth" || p.type === "token").map((p) => resolveUsageProviderId(p.provider)).filter((id) => Boolean(id)))];
\tconst usageByProvider = /* @__PURE__ */ new Map();
\tif (usageProviderIds.length > 0) try {
\t\tconst usage = await loadProviderUsageSummary({ providers: usageProviderIds, agentDir, timeoutMs: 3500 });
\t\tfor (const snap of usage.providers) usageByProvider.set(snap.provider, { windows: snap.windows, plan: snap.plan });
\t} catch (err) {
\t\tlog.debug(\`usage enrichment failed (warm auth status still returned): providers=\${usageProviderIds.join(",")} error=\${formatForLog(err)}\`);
\t}
\tconst result = { ts: now, providers: authHealth.providers.map((prov) => mapProvider(prov, usageByProvider, configured.expectsOAuth)) };
\tcached = { ts: now, result };
\treturn result;
}
setTimeout(() => { void warmModelAuthStatusCache().catch(() => {}); }, 3e3);
const modelsAuthStatusHandlers = { "models.authStatus": async ({ params, respond, context }) => {
\tcontextForModelAuthWarmup = context;
\tconst now = Date.now();
\tif (!Boolean(params?.refresh) && cached && now - cached.ts < CACHE_TTL_MS) {
\t\trespond(true, cached.result, void 0, { cached: true });
\t\treturn;
\t}
\ttry {
\t\tconst result = await warmModelAuthStatusCache();
\t\trespond(true, result, void 0);
\t} catch (err) {
\t\trespond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, formatForLog(err)));
\t}
} };`,
  );

  out = out.replace(
    /const toolsCatalogHandlers = \{ "tools\.catalog": \(\{ params, respond, context \}\) => \{[\s\S]*?\n\} \};/,
    `const TOOLS_CATALOG_CACHE_TTL_MS = 3e5;
const toolsCatalogCache = /* @__PURE__ */ new Map();
let contextForToolsCatalogWarmup;
function buildToolsCatalogCacheKey(agentId, includePlugins) { return \`${'${agentId}'}::plugins=${'${includePlugins ? "1" : "0"}'}\`; }
async function loadToolsCatalogCached(cfg, agentId, includePlugins) {
\tconst key = buildToolsCatalogCacheKey(agentId, includePlugins);
\tconst now = Date.now();
\tconst cachedEntry = toolsCatalogCache.get(key);
\tif (cachedEntry && now - cachedEntry.ts < TOOLS_CATALOG_CACHE_TTL_MS && cachedEntry.result) return cachedEntry.result;
\tif (cachedEntry?.inFlight) return await cachedEntry.inFlight;
\tconst inFlight = Promise.resolve().then(() => buildToolsCatalogResult({ cfg, agentId, includePlugins }));
\ttoolsCatalogCache.set(key, { ts: cachedEntry?.ts ?? 0, result: cachedEntry?.result, inFlight });
\ttry {
\t\tconst result = await inFlight;
\t\ttoolsCatalogCache.set(key, { ts: Date.now(), result });
\t\treturn result;
\t} catch (err) {
\t\ttoolsCatalogCache.delete(key);
\t\tthrow err;
\t}
}
setTimeout(() => {
\ttry {
\t\tconst cfg = contextForToolsCatalogWarmup?.getRuntimeConfig?.() ?? loadConfig();
\t\tconst agentId = resolveDefaultAgentId(cfg);
\t\tvoid loadToolsCatalogCached(cfg, agentId, true).catch(() => {});
\t} catch {}
}, 5e3);
const toolsCatalogHandlers = { "tools.catalog": async ({ params, respond, context }) => {
\tcontextForToolsCatalogWarmup = context;
\tif (!validateToolsCatalogParams(params)) {
\t\trespond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, \`invalid tools.catalog params: \${formatValidationErrors(validateToolsCatalogParams.errors)}\`));
\t\treturn;
\t}
\tconst resolved = resolveAgentIdOrRespondError(params.agentId, respond, context.getRuntimeConfig());
\tif (!resolved) return;
\ttry {
\t\tconst result = await loadToolsCatalogCached(resolved.cfg, resolved.agentId, params.includePlugins !== false);
\t\trespond(true, result, void 0);
\t} catch (err) {
\t\trespond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, String(err)));
\t}
} };`,
  );

  if (out !== src) {
    fs.writeFileSync(file, out, 'utf8');
    console.log(`[patch-gateway-warmup-cache] patched ${file}`);
    return 1;
  }
  return 0;
}

let patched = 0;
for (const name of fs.readdirSync(distDir)) {
  const file = path.join(distDir, name);
  if (!fs.statSync(file).isFile() || !name.endsWith('.js')) continue;
  if (/^server-methods-.*\.js$/.test(name)) patched += patchServerMethods(file);
}

if (patched === 0) {
  console.warn('[patch-gateway-warmup-cache] no target blocks matched; skipping');
  process.exit(0);
}

console.log(`[patch-gateway-warmup-cache] done, patched ${patched} file(s)`);
