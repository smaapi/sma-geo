// 锁文件 registry 守卫(REVIEW p0 D1):resolved URL 不得指向第三方镜像。
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const lock = readFileSync(resolve(root, 'package-lock.json'), 'utf8');

const hits = lock.match(/npmmirror/g) ?? [];
if (hits.length > 0) {
  console.error(`锁文件 registry 守卫失败: package-lock.json 含 npmmirror ${hits.length} 处(必须为 0)`);
  console.error('修复: rm package-lock.json && npm install --registry=https://registry.npmjs.org/');
  process.exit(1);
}
console.log('锁文件 registry 守卫通过: npmmirror 0 命中');
