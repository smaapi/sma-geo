// robots.txt 校验(自研,替代 npm 不在档的 robots-txt-audit;增补件 A2)。
// 验收点:每个数据源 UA 都有显式 Allow 组;无整站封禁;内部路径全员屏蔽;Sitemap 在位。
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(resolve(root, p), 'utf8');
const errors = [];

const txt = read('dist/robots.txt');
const upstream = Object.keys(JSON.parse(read('config/robots.json')));
const cn = JSON.parse(read('config/cn-bots.json')).bots.map((b) => b.ua);
// 与生成器同构:大小写不敏感去重后逐一核对
const merged = new Map();
for (const ua of [...upstream, ...cn]) {
  if (!merged.has(ua.toLowerCase())) merged.set(ua.toLowerCase(), ua);
}
const expected = [...merged.values()];

// 按 UA 组切分:组 = User-agent 行 + 后续指令行
const groups = new Map();
let current = null;
for (const line of txt.split('\n')) {
  const ua = line.match(/^User-agent:\s*(.+)\s*$/i);
  if (ua) {
    current = ua[1];
    if (!groups.has(current)) groups.set(current, []);
  } else if (current && line.trim() && !line.startsWith('#')) {
    groups.get(current).push(line.trim());
  }
}

for (const ua of expected) {
  const rules = groups.get(ua);
  if (!rules) errors.push(`缺少 UA 组: ${ua}`);
  else if (!rules.includes('Allow: /')) errors.push(`UA 组未显式放行: ${ua}`);
}

for (const [ua, rules] of groups) {
  if (rules.some((r) => /^Disallow:\s*\/\s*$/i.test(r))) errors.push(`整站封禁(违反 Allow 反转): ${ua}`);
  for (const path of ['/console/', '/admin/', '/api/internal/', '/_review/']) {
    if (!rules.includes(`Disallow: ${path}`)) errors.push(`UA 组 ${ua} 未屏蔽内部路径 ${path}`);
  }
}

if (!groups.has('*')) errors.push('缺少 User-agent: * 默认组');
const site = JSON.parse(read('src/data/pages.json')).site;
if (!txt.split('\n').includes(`Sitemap: ${site}/sitemap.xml`)) errors.push('缺少 Sitemap 行(应与注册表 site 基址一致)');

if (errors.length) {
  console.error(`robots.txt 校验失败(${errors.length} 项):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log(`robots.txt 校验通过: ${expected.length} 个数据源 UA 全部显式放行,内部路径全员屏蔽`);
