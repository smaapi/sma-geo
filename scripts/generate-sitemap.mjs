// 生成 dist/sitemap.xml,lastmod 取自页面注册表(主 spec §1.4)。
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { site, pages } = JSON.parse(readFileSync(resolve(root, 'src/data/pages.json'), 'utf8'));

const urls = pages
  .map(
    (p) => `  <url>
    <loc>${site + p.route}</loc>
    <lastmod>${p.dateModified}</lastmod>
  </url>`
  )
  .join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;

writeFileSync(resolve(root, 'dist/sitemap.xml'), xml);
console.log(`sitemap.xml generated: ${pages.length} urls`);
