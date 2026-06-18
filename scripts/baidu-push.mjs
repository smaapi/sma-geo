// 向百度搜索资源平台「普通收录 → API提交(主动推送·实时)」提交全量 URL。
// token 走环境变量 BAIDU_PUSH_TOKEN（凭证级，永不入库）；沿用 indexnow-submit.mjs 的 DNS 前置门。
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import dns from 'node:dns';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { site, pages } = JSON.parse(readFileSync(resolve(root, 'src/data/pages.json'), 'utf8'));
const host = new URL(site).host;

// R1 DNS 前置门（同 indexnow-submit.mjs）：主机必须公网解析到目标服务器，否则推的是他人现状。
const DEFAULT_EXPECT_IP = '47.93.39.204';
const override = process.env.BAIDU_EXPECT_IP;
if (override && process.env.CI) {
  console.error('CI 环境禁用 BAIDU_EXPECT_IP 覆写 —— 推送取消');
  process.exit(1);
}
if (override) {
  console.warn(`⚠️⚠️⚠️ 警告: DNS 门期望值被覆写为 ${override}（默认 ${DEFAULT_EXPECT_IP}）——仅限本地测试 ⚠️⚠️⚠️`);
}
const EXPECT_IP = override || DEFAULT_EXPECT_IP;
let resolved;
try {
  resolved = await dns.promises.resolve4(host);
} catch (err) {
  console.error(`DNS 解析失败（${host}）: ${err.code ?? err.message} —— 推送取消`);
  process.exit(1);
}
if (!resolved.includes(EXPECT_IP)) {
  console.error(`DNS 未指向目标服务器（${host} -> ${resolved.join(', ')}，期望 ${EXPECT_IP}）—— 推送取消`);
  process.exit(1);
}
console.log(`DNS 门通过: ${host} -> ${EXPECT_IP}`);

// 便于一键运行：环境未注入时，自动从仓库根 .env 读取 BAIDU_PUSH_TOKEN（.env 永不入库）。
let token = process.env.BAIDU_PUSH_TOKEN;
if (!token) {
  try {
    const m = readFileSync(resolve(root, '.env'), 'utf8').match(/^\s*BAIDU_PUSH_TOKEN\s*=\s*(.+?)\s*$/m);
    if (m) token = m[1];
  } catch { /* 无 .env：走下方缺失校验 */ }
}
if (!token) {
  console.error('缺少 BAIDU_PUSH_TOKEN（环境变量或 .env 均无）—— 推送取消（在百度站长「普通收录 → API提交」页获取准入密钥）');
  process.exit(1);
}

const urls = pages.map((p) => site + p.route);
// 百度示例口径：site 用原样完整主机（不做 URL 编码），与控制台给出的调用地址一致。
const endpoint = `http://data.zz.baidu.com/urls?site=${site}&token=${token}`;
const res = await fetch(endpoint, {
  method: 'POST',
  headers: { 'Content-Type': 'text/plain' },
  body: urls.join('\n'),
});
const text = await res.text();
console.log(`百度主动推送: HTTP ${res.status}（提交 ${urls.length} 条）`);
console.log(text);

// 成功响应形如 {"remain":N,"success":M}；存在 error 字段或 success 非数字视为未成功。
let ok = res.ok;
try {
  const j = JSON.parse(text);
  if (j.error || typeof j.success !== 'number') ok = false;
  else if (j.success === 0) console.warn('注意: success=0 —— 多为今日配额(余额)耗尽或站点级别过低；token 有效，配额恢复后重跑即可。');
} catch {
  ok = false;
}
if (!ok) process.exit(1);
