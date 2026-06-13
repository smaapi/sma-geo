import { defineConfig } from 'astro/config';
import { readFileSync } from 'node:fs';

// O1(REVIEW r7 §4):站点基址单一真源 = src/data/pages.json 的 site 字段;
// astro.config/生成器/组件全部从它读取,杜绝"产物对、配置错"的隐性分叉。
const { site } = JSON.parse(readFileSync(new URL('./src/data/pages.json', import.meta.url), 'utf8'));

export default defineConfig({
  site,
  trailingSlash: 'ignore',
  // CSS 外链化(inlineStylesheets:'auto'):大块样式拆为外部 .css,降低 HTML 噪声占比(首页内联
  // CSS 曾占 64%),利于 Kimi 等文本抽取型 AI 干净取正文。原 'always' 锁为改版评审期快照自包含,
  // 已正式上线故解锁。不涉任何 GEO 标签:canonical/hreflang/og/JSON-LD 不变,仅 head 多一条 stylesheet link。
  build: { inlineStylesheets: 'auto' },
});
