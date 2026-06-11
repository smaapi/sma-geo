// O1 单一真源断言(REVIEW r7 §4):dist 产物中所有 smaapi.com 系 URL 的主机必须等于注册表 site 主机。
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, relative, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const site = JSON.parse(readFileSync(resolve(root, 'src/data/pages.json'), 'utf8')).site;
const expectedHost = new URL(site).host;

const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full);
    else if (/\.(html|txt|xml)$/.test(name)) files.push(full);
  }
})(resolve(root, 'dist'));

const URL_RE = /https?:\/\/[a-z0-9.-]*smaapi\.com[^\s"'<)\]]*/gi;
const errors = [];
for (const f of files) {
  const text = readFileSync(f, 'utf8');
  for (const m of text.match(URL_RE) ?? []) {
    const host = new URL(m).host;
    if (host !== expectedHost) {
      errors.push(`${relative(root, f)}: ${m.slice(0, 80)} (host=${host},期望 ${expectedHost})`);
    }
  }
}

if (errors.length) {
  console.error(`单一主机断言失败(${errors.length}):`);
  for (const e of errors.slice(0, 10)) console.error(`  - ${e}`);
  process.exit(1);
}
console.log(`单一主机断言通过: ${files.length} 个产物文件,smaapi.com 系 URL 全部为 ${expectedHost}`);
