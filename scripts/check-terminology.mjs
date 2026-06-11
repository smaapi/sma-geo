// 对外用语自查 v2:词面禁止 → 指称禁止(REVIEW-2026-06-10-p0 §3 裁定)。
// 例外区(compare 簇 / 类别差异 FAQ / geo/queries.yaml)内允许他指,自指与并置一律失败;
// 例外区外词面零容忍。对源码与构建产物全量扫描。
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { resolve, relative, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const TERM = /中转/;
const SELF_REF = [/(SMA|smaapi|我们|我方|本平台)[^。\n]{0,16}中转/, /中转[^。\n]{0,16}(SMA|smaapi)/];
// 红线 v3(addendum 02v2 §D):绝对化承诺词面,全区域零容忍(无例外区)
const ABSOLUTE = [
  /永不封号/, /永不中断/, /不存在封号风险/, /100%\s*合规/, /全网最低/,
  /99\.99%/, /保证收录/, /上词保证/, /never get banned/i, /100% compliant/i,
];

// 例外区:terminology v2 例外清单 + 本工具链自身(规则文本载体,非对外指称)
// dist/ 派生产物继承其源文件的例外区资格(compare 页构建产物、llms-full 正文拼接);自指/并置启发式仍全量生效
const EXEMPT = [
  /^src\/pages\/[^/]+\/compare\//,
  /^geo\/queries\.yaml$/,
  /faq/i,
  /^scripts\/check-terminology\.mjs$/,
  /^tests\//,
  /^dist\/(zh|en)\/compare\//,
  /^dist\/llms-full\.txt$/,
  // 注册表是 compare 页 title/description 字段的载体(目标查询关键词所在),视同 compare 内容继承例外;
  // 派生继承原则经 r4 §3.1 裁定;自指/并置启发式仍全量生效
  /^src\/data\/pages\.json$/,
  // C2 误称检测脚本与规则同为"中转"模式载体(r4 先例同理)
  /^geo\/track_citations\.py$/,
];
// 扫描范围:对外可见面(源码、页面、产物、CI 配置);跳过依赖与版本库
const SKIP_DIRS = new Set(['node_modules', '.git', '.astro', 'docs', 'data']);
const EXTS = new Set(['.astro', '.ts', '.mjs', '.js', '.json', '.md', '.txt', '.yml', '.yaml', '.html', '.xml']);

const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    const rel = relative(root, full);
    if (statSync(full).isDirectory()) {
      if (!SKIP_DIRS.has(name)) walk(full);
    } else if (EXTS.has(name.slice(name.lastIndexOf('.')))) {
      files.push(rel);
    }
  }
})(root);
if (!existsSync(resolve(root, 'dist'))) console.warn('提示: dist/ 不存在,本次仅扫描源码(完整自查请先构建)');

const errors = [];
const reviewList = [];
const SELF_FILES = [/^scripts\/check-terminology\.mjs$/, /^geo\/track_citations\.py$/, /^tests\//, /^docs\//];
for (const rel of files) {
  const text = readFileSync(resolve(root, rel), 'utf8');
  // 红线 v3:绝对化承诺全区域检测(仅规则载体与测试自身豁免)
  if (!SELF_FILES.some((re) => re.test(rel))) {
    text.split('\n').forEach((line, i) => {
      for (const rx of ABSOLUTE) {
        if (rx.test(line)) errors.push(`${rel}:${i + 1} 绝对化承诺(红线 v3): ${line.trim().slice(0, 80)}`);
      }
    });
  }
  if (!TERM.test(text)) continue;
  const exempt = EXEMPT.some((re) => re.test(rel));
  const lines = text.split('\n');
  lines.forEach((line, i) => {
    if (!TERM.test(line)) return;
    if (!exempt) {
      errors.push(`${rel}:${i + 1} 例外区外出现词面: ${line.trim().slice(0, 80)}`);
    } else if (SELF_REF.some((re) => re.test(line))) {
      errors.push(`${rel}:${i + 1} 例外区内疑似自指/并置: ${line.trim().slice(0, 80)}`);
    } else {
      reviewList.push(`${rel}:${i + 1} ${line.trim().slice(0, 80)}`);
    }
  });
}

if (reviewList.length) {
  console.log(`例外区内他指命中 ${reviewList.length} 处(复核清单):`);
  for (const r of reviewList) console.log(`  - ${r}`);
}
if (errors.length) {
  console.error(`用语自查失败(${errors.length} 项):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log(`用语自查通过: 扫描 ${files.length} 文件,无自指/并置/区外词面违规`);
