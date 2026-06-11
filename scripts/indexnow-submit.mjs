// 部署后向 IndexNow 推送全量 URL(增补件 F2;Bing 索引是 ChatGPT Search/Copilot 的检索底座之一)。
// key 文件随站点部署在根目录(IndexNow 协议要求,公开内容,非密钥)。
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { key, host } = JSON.parse(readFileSync(resolve(root, 'config/indexnow.json'), 'utf8'));
const { site, pages } = JSON.parse(readFileSync(resolve(root, 'src/data/pages.json'), 'utf8'));

const body = {
  host,
  key,
  keyLocation: `${site}/${key}.txt`,
  urlList: pages.map((p) => site + p.route),
};

const res = await fetch('https://api.indexnow.org/indexnow', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json; charset=utf-8' },
  body: JSON.stringify(body),
});
console.log(`IndexNow: ${res.status} ${res.statusText} (${body.urlList.length} urls)`);
if (!res.ok) process.exit(1);
