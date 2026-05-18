#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function fail(message) {
  console.error(`[patch-qqbot-dispatch-visibility] ${message}`);
  process.exit(1);
}

const root = process.argv[2];
if (!root) fail('usage: node patch-qqbot-dispatch-visibility.mjs <openclaw-bundle-dir>');

const candidates = [
  path.join(root, 'node_modules', '@tencent-connect', 'openclaw-qqbot', 'dist', 'src', 'gateway.js'),
  path.join(root, 'dist', 'extensions', 'qqbot', 'dist', 'src', 'gateway.js'),
];

const dispatchNeedle = '                        const dispatchPromise = pluginRuntime.channel.reply.dispatchReplyWithBufferedBlockDispatcher({';
const dispatchReplacement = [
  '                        log?.info(`[qqbot:${account.accountId}] dispatch start: session=${route.sessionKey}, agent=${route.agentId}, c2c=${event.type === "c2c"}, patch=qq-dispatch-visibility-v1`);',
  dispatchNeedle,
].join('\n');

const finallyNeedle = [
  '                        finally {',
  '                            // 清理 tool-only 兜底定时器',
].join('\n');
const finallyReplacement = [
  '                        finally {',
  '                            log?.info(`[qqbot:${account.accountId}] dispatch promise settled: hasResponse=${hasResponse}, hasBlockResponse=${hasBlockResponse}, toolDeliverCount=${toolDeliverCount}`);',
  '                            if (event.type === "c2c" && !hasResponse && !hasBlockResponse && toolDeliverCount === 0) {',
  '                                log?.error(`[qqbot:${account.accountId}] Dispatch completed without any user-visible deliver; sending fallback (qq-dispatch-visibility-v1)`);',
  '                                try {',
  '                                    await sendErrorMessage("AI 已收到 QQ 消息，但本次没有产生可发送的最终回复。请再试一次。");',
  '                                }',
  '                                catch (sendErr) {',
  '                                    log?.error(`[qqbot:${account.accountId}] Failed to send no-deliver fallback: ${sendErr}`);',
  '                                }',
  '                            }',
  '                            // 清理 tool-only 兜底定时器',
].join('\n');

let patchedFiles = 0;
let alreadyPatched = 0;
let missingFiles = 0;

for (const file of candidates) {
  if (!fs.existsSync(file)) {
    missingFiles += 1;
    continue;
  }
  let source = fs.readFileSync(file, 'utf8');
  let changed = false;

  if (source.includes('qq-dispatch-visibility-v1')) {
    alreadyPatched += 1;
    console.log(`[patch-qqbot-dispatch-visibility] already patched ${file}`);
    continue;
  }

  if (!source.includes(dispatchNeedle)) {
    fail(`dispatch target not found in ${file}`);
  }
  source = source.replace(dispatchNeedle, dispatchReplacement);
  changed = true;

  if (!source.includes(finallyNeedle)) {
    fail(`finally target not found in ${file}`);
  }
  source = source.replace(finallyNeedle, finallyReplacement);
  changed = true;

  if (changed) {
    fs.writeFileSync(file, source, 'utf8');
    patchedFiles += 1;
    console.log(`[patch-qqbot-dispatch-visibility] patched ${file}`);
  }
}

if (patchedFiles === 0 && alreadyPatched === 0) {
  fail(`no qqbot gateway files patched (missing=${missingFiles})`);
}

console.log(`[patch-qqbot-dispatch-visibility] done, patched=${patchedFiles}, already=${alreadyPatched}, missing=${missingFiles}`);
