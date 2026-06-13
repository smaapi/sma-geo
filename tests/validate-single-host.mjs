// O1 单一真源断言(REVIEW r7 §4):dist 产物中所有 smaapi.com 系 URL 的主机必须等于注册表 site 主机。
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, relative, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const site = JSON.parse(readFileSync(resolve(root, 'src/data/pages.json'), 'utf8')).site;
const expectedHost = new URL(site).host;
// 首页导航「API 接口」链接的第一方 API 子域(业务侧指定,2026-06-12);
// 自指主机仍统一 www,此处仅放行该 API 端点主机。**待评审追认**(api.smaapi.com 现解析至 43.136.14.69)。
const ALLOWED_HOSTS = new Set([expectedHost, 'api.smaapi.com']);

const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full);
    else if (/\.(html|txt|xml)$/.test(name)) files.push(full);
  }
})(resolve(root, 'dist'));

const URL_RE = /https?:\/\/[a-z0-9.-]*smaapi\.com[^\s"'<)\]]*/gi;
// r9 §2:裸域 smaapi.com 已指向上游站点,产物自指必须用完整主机(例外区:讨论第三方/类别语境,目前无)
const BARE_RE = /(?<![\w.])smaapi\.com/g;
const BARE_EXEMPT = []; // 形如 /^zh\/compare\// 的相对路径正则,经评审确认后加入
const errors = [];
for (const f of files) {
  const text = readFileSync(f, 'utf8');
  const rel = relative(resolve(root, 'dist'), f);
  for (const m of text.match(URL_RE) ?? []) {
    const host = new URL(m).host;
    if (!ALLOWED_HOSTS.has(host)) {
      errors.push(`${relative(root, f)}: ${m.slice(0, 80)} (host=${host},期望 ${[...ALLOWED_HOSTS].join(' | ')})`);
    }
  }
  if (!BARE_EXEMPT.some((re) => re.test(rel))) {
    let bm;
    while ((bm = BARE_RE.exec(text)) !== null) {
      errors.push(`${relative(root, f)}: 裸域自指 "…${text.slice(Math.max(0, bm.index - 20), bm.index + 12).replace(/\n/g, ' ')}…"`);
    }
  }
}

if (errors.length) {
  console.error(`单一主机断言失败(${errors.length}):`);
  for (const e of errors.slice(0, 10)) console.error(`  - ${e}`);
  process.exit(1);
}
console.log(`单一主机断言通过: ${files.length} 个产物文件,smaapi.com 系 URL 主机 ∈ {${[...ALLOWED_HOSTS].join(', ')}}`);
