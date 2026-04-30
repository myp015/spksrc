#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
if (!root) {
  console.error('[patch-control-ui-preload] usage: node patch-control-ui-preload.mjs <openclaw-bundle-dir>');
  process.exit(2);
}

const assetsDir = path.join(root, 'dist', 'control-ui', 'assets');
if (!fs.existsSync(assetsDir)) {
  console.warn('[patch-control-ui-preload] control-ui assets dir not found; skipping');
  process.exit(0);
}

const candidates = fs.readdirSync(assetsDir).filter((n) => /^index-.*\.js$/.test(n));
if (candidates.length === 0) {
  console.warn('[patch-control-ui-preload] no control-ui index-*.js found; skipping');
  process.exit(0);
}

let patched = 0;
for (const name of candidates) {
  const file = path.join(assetsDir, name);
  const src = fs.readFileSync(file, 'utf8');
  let out = src;

  out = out.replace(
    /async function \w+\(e,t\)\{await Promise\.all\(\[\w+\(e\),\w+\(e,\{activeMinutes:0,limit:0,includeGlobal:!0,includeUnknown:!0\}\),\w+\(e\),\w+\(e\),\w+\(e\)\]\),t\?\.scheduleScroll!==!1&&\w+\(e\)\}/,
    (m) => {
      const parts = /async function (\w+)\(e,t\)\{await Promise\.all\(\[(\w+)\(e\),(\w+)\(e,\{activeMinutes:0,limit:0,includeGlobal:!0,includeUnknown:!0\}\),(\w+)\(e\),(\w+)\(e\),(\w+)\(e\)\]\),t\?\.scheduleScroll!==!1&&(\w+)\(e\)\}/.exec(m);
      if (!parts) return m;
      return `async function ${parts[1]}(e,t){await Promise.all([${parts[2]}(e),${parts[3]}(e,{activeMinutes:0,limit:0,includeGlobal:!0,includeUnknown:!0}),${parts[4]}(e),${parts[6]}(e)]),t?.scheduleScroll!==!1&&${parts[7]}(e),${parts[5]}(e)}`;
    },
  );

  out = out.replace(
    /async function \w+\(e,t\)\{let n=e;await Promise\.allSettled\(\[(\w+\(n,!1\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n,\{refresh:t\?\.refresh\}\))\]\),(\w+)\(n\)\}/,
    (m) => {
      const parts = /async function (\w+)\(e,t\)\{let n=e;await Promise\.allSettled\(\[(\w+\(n,!1\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n\)),(\w+\(n,\{refresh:t\?\.refresh\}\))\]\),(\w+)\(n\)\}/.exec(m);
      if (!parts) return m;
      return `async function ${parts[1]}(e,t){let n=e;await Promise.allSettled([${parts[2]},${parts[3]},${parts[4]},${parts[5]},${parts[9]},${parts[10]}]),${parts[12]}(n),Promise.allSettled([${parts[6]},${parts[7]},${parts[8]},${parts[11]}]).then(()=>{${parts[12]}(n)})}`;
    },
  );

  if (out !== src) {
    fs.writeFileSync(file, out, 'utf8');
    patched += 1;
    console.log(`[patch-control-ui-preload] patched ${file}`);
  }
}

if (patched === 0) {
  console.warn('[patch-control-ui-preload] no target blocks matched; skipping');
  process.exit(0);
}

console.log(`[patch-control-ui-preload] done, patched ${patched} file(s)`);
