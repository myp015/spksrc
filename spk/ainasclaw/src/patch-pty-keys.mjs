#!/usr/bin/env node
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

function listFiles(rootDir) {
  const out = [];
  const stack = [rootDir];
  while (stack.length > 0) {
    const dir = stack.pop();
    let entries = [];
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      const p = join(dir, ent.name);
      // Never follow symlinks (can form loops in node_modules/.bin).
      if (ent.isSymbolicLink()) continue;
      if (ent.isDirectory()) stack.push(p);
      else if (ent.isFile()) out.push(p);
    }
  }
  return out;
}

function patchContent(input) {
  let s = input;

  // 1) Backspace/Rubout constants
  s = s.replace(/const BACKSPACE = "(?:\\x7f|\u007f|\x7f)";/, 'const BACKSPACE = "\\x08";\nconst RUBOUT = "\\x7f";');

  // 2) Named key aliases: bs + rubout
  s = s.replace(
    '["bspace", BACKSPACE],\n\t["backspace", BACKSPACE],',
    '["bspace", BACKSPACE],\n\t["backspace", BACKSPACE],\n\t["bs", BACKSPACE],\n\t["rubout", RUBOUT],',
  );

  // 3) Numpad Enter should behave like Enter
  s = s.replace('["kpenter", `${ESC}OM`]', '["kpenter", CR],\n\t["numpadenter", CR]');

  // 4) parseModifiers supports long names and + separator
  s = s.replace(
    /function parseModifiers\(token\) \{[\s\S]*?return \{\n\t\tmods,\n\t\tbase: rest,\n\t\thasModifiers: sawModifiers\n\t\};\n\}/,
    `function parseModifiers(token) {
\tconst mods = {
\t\tctrl: false,
\t\talt: false,
\t\tshift: false
\t};
\tlet rest = token;
\tlet sawModifiers = false;
\twhile (rest.length > 2) {
\t\tconst plusIndex = rest.indexOf("+");
\t\tconst dashIndex = rest.indexOf("-");
\t\tconst sepIndex = plusIndex < 0 ? dashIndex : dashIndex < 0 ? plusIndex : Math.min(plusIndex, dashIndex);
\t\tif (sepIndex <= 0) break;
\t\tconst modToken = normalizeLowercaseStringOrEmpty(rest.slice(0, sepIndex));
\t\tconst consumed = sepIndex + 1;
\t\tif (modToken === "c" || modToken === "ctrl" || modToken === "control") mods.ctrl = true;
\t\telse if (modToken === "m" || modToken === "alt" || modToken === "meta") mods.alt = true;
\t\telse if (modToken === "s" || modToken === "shift") mods.shift = true;
\t\telse break;
\t\tsawModifiers = true;
\t\trest = rest.slice(consumed);
\t}
\treturn {
\t\tmods,
\t\tbase: rest,
\t\thasModifiers: sawModifiers
\t};
}`,
  );

  return s;
}

function main() {
  const bundleDir = process.argv[2];
  if (!bundleDir) {
    console.error("Usage: node patch-pty-keys.mjs <openclaw-bundle-dir>");
    process.exit(2);
  }

  const distDir = join(bundleDir, "dist");
  const files = listFiles(distDir).filter((p) => /\/bash-tools-.*\.js$/.test(p));
  if (files.length === 0) {
    console.error(`[patch-pty-keys] no bash-tools files found under ${distDir}`);
    process.exit(3);
  }

  let patchedCount = 0;
  for (const file of files) {
    const before = readFileSync(file, "utf8");
    if (!before.includes("function parseModifiers(token)")) continue;

    const after = patchContent(before);
    const ok =
      after.includes('const BACKSPACE = "\\x08";') &&
      after.includes('const RUBOUT = "\\x7f";') &&
      after.includes('["numpadenter", CR]') &&
      after.includes('["rubout", RUBOUT]') &&
      after.includes('modToken === "ctrl"') &&
      after.includes('rest.indexOf("+")');

    if (!ok) {
      console.error(`[patch-pty-keys] verification failed for ${file}`);
      process.exit(4);
    }

    if (after !== before) {
      writeFileSync(file, after, "utf8");
      patchedCount += 1;
      console.log(`[patch-pty-keys] patched ${file}`);
    }
  }

  if (patchedCount === 0) {
    console.error("[patch-pty-keys] no target file patched (pattern mismatch?)");
    process.exit(5);
  }

  console.log(`[patch-pty-keys] done, patched ${patchedCount} file(s)`);
}

main();
