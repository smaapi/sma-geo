// 死链 + JSON-LD 结构校验(r8 批次 C):
// ① dist 内站内链接必须能解析到构建产物;② 每个 ld+json 块必须可解析且关键字段齐备。
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { resolve, relative, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = resolve(root, 'dist');
const site = JSON.parse(readFileSync(resolve(root, 'src/data/pages.json'), 'utf8')).site;

const htmls = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full);
    else if (name.endsWith('.html')) htmls.push(full);
  }
})(dist);

const routeExists = (path) => {
  const clean = path.replace(/[#?].*$/, '').replace(/\/$/, '');
  if (clean === '') return existsSync(join(dist, 'index.html'));
  return existsSync(join(dist, clean.slice(1), 'index.html')) || existsSync(join(dist, clean.slice(1)));
};

const errors = [];
for (const f of htmls) {
  const rel = relative(root, f);
  const text = readFileSync(f, 'utf8');
  // ① 站内链接(含锚定到自己站点的绝对链接)
  for (const m of text.matchAll(/href="([^"]+)"/g)) {
    let href = m[1];
    if (href.startsWith(site)) href = href.slice(site.length) || '/';
    if (!href.startsWith('/')) continue; // 外链交人工/月检
    if (!routeExists(href)) errors.push(`${rel}: 死链 ${m[1]}`);
  }
  // ② JSON-LD 块
  for (const m of text.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)) {
    let data;
    try {
      data = JSON.parse(m[1]);
    } catch {
      errors.push(`${rel}: JSON-LD 解析失败`);
      continue;
    }
    const type = data['@type'];
    if (!data['@context'] || !type) errors.push(`${rel}: JSON-LD 缺 @context/@type`);
    if (type === 'Organization' && !(data.name && data.url && data['@id'])) errors.push(`${rel}: Organization 缺 name/url/@id`);
    if (type === 'TechArticle' && !(data.datePublished && data.dateModified)) errors.push(`${rel}: TechArticle 缺日期`);
    if (type === 'FAQPage' && !(Array.isArray(data.mainEntity) && data.mainEntity.length)) errors.push(`${rel}: FAQPage mainEntity 空`);
    if (type === 'SoftwareApplication' && !(data.url && data.provider)) errors.push(`${rel}: SoftwareApplication 缺 url/provider`);
  }
}

if (errors.length) {
  console.error(`死链/JSON-LD 校验失败(${errors.length}):`);
  for (const e of errors.slice(0, 12)) console.error(`  - ${e}`);
  process.exit(1);
}
console.log(`死链/JSON-LD 校验通过: ${htmls.length} 页,站内链接全可达,结构化数据字段齐备`);
