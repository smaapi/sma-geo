// 从 ai-robots-txt/ai.robots.txt 拉取 pinned commit 的 robots.json,vendor 进 config/。
// 仅取 UA 数据用于生成 Allow 规则(增补件 A1);更新流程:改 PINNED_COMMIT → 重跑 → diff 审查。
import { writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const PINNED_COMMIT = 'f420408eee6c6a8c4eaf3536d6f9c926c9b01fa4'; // 2026-06-04
const SOURCE_REPO = 'ai-robots-txt/ai.robots.txt';
const url = `https://raw.githubusercontent.com/${SOURCE_REPO}/${PINNED_COMMIT}/robots.json`;

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const res = await fetch(url);
if (!res.ok) {
  console.error(`fetch failed: ${res.status} ${url}`);
  process.exit(1);
}
const data = await res.json();
const uaCount = Object.keys(data).length;

writeFileSync(resolve(root, 'config/robots.json'), JSON.stringify(data, null, 2) + '\n');
writeFileSync(
  resolve(root, 'config/robots-source.json'),
  JSON.stringify({ repo: SOURCE_REPO, commit: PINNED_COMMIT, file: 'robots.json', uaCount }, null, 2) + '\n'
);
console.log(`vendored ${uaCount} UAs from ${SOURCE_REPO}@${PINNED_COMMIT.slice(0, 7)}`);
