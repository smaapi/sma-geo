// 百度主动推送 DNS 前置门测试（镜像 validate-indexnow-gate.mjs）：错误 DNS 期望值时须非零中止、不发请求。
import { spawnSync } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// 203.0.113.99 为 TEST-NET-3 保留地址，真实解析结果不可能等于它 → 必然触发门
const r = spawnSync('node', [resolve(root, 'scripts/baidu-push.mjs')], {
  env: { ...process.env, BAIDU_EXPECT_IP: '203.0.113.99' },
  encoding: 'utf8',
  timeout: 30000,
});

const out = (r.stdout || '') + (r.stderr || '');
const errors = [];
if (r.status === 0) errors.push(`错误 DNS 期望下脚本应非零退出，实为 ${r.status}`);
if (!/推送取消/.test(out)) errors.push(`应打印"推送取消"，实际输出: ${out.slice(0, 120)}`);
if (/HTTP 2\d\d/.test(out)) errors.push('门未生效：请求已发出');

if (errors.length) {
  console.error(`百度推送 DNS 门测试失败（${errors.length}）：`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log('百度推送 DNS 门测试通过: 错误期望值下非零中止，未发出请求');
