// 部署后向 IndexNow 推送全量 URL(增补件 F2;Bing 索引是 ChatGPT Search/Copilot 的检索底座之一)。
// key 文件随站点部署在根目录(IndexNow 协议要求,公开内容,非密钥)。
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import dns from 'node:dns';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { key, host } = JSON.parse(readFileSync(resolve(root, 'config/indexnow.json'), 'utf8'));
const { site, pages } = JSON.parse(readFileSync(resolve(root, 'src/data/pages.json'), 'utf8'));

// R1 DNS 前置门(REVIEW r6 §3):站点主机必须公网解析到目标服务器,否则推送的是他人现状。
// 200 = 已受理而非已验证 —— 会撒谎的成功信号,必须在源头设门。
const EXPECT_IP = process.env.INDEXNOW_EXPECT_IP || '47.93.39.204';
let resolved;
try {
  resolved = await dns.promises.resolve4(host);
} catch (err) {
  console.error(`DNS 解析失败(${host}): ${err.code ?? err.message} —— 推送取消`);
  process.exit(1);
}
if (!resolved.includes(EXPECT_IP)) {
  console.error(`DNS 未指向目标服务器(${host} -> ${resolved.join(', ')},期望 ${EXPECT_IP})—— 推送取消`);
  process.exit(1);
}
console.log(`DNS 门通过: ${host} -> ${EXPECT_IP}`);

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
