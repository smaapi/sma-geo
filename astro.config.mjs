import { defineConfig } from 'astro/config';
import { readFileSync } from 'node:fs';

// O1(REVIEW r7 §4):站点基址单一真源 = src/data/pages.json 的 site 字段;
// astro.config/生成器/组件全部从它读取,杜绝"产物对、配置错"的隐性分叉。
const { site } = JSON.parse(readFileSync(new URL('./src/data/pages.json', import.meta.url), 'utf8'));

export default defineConfig({
  site,
  trailingSlash: 'ignore',
  // 全站 CSS 内联(站点原本即全内联;改版后首页样式增大触发 auto 外链,显式锁定以保持
  // 单文件自包含——评审快照可独立查看,且去除渲染阻塞请求利于 LCP。不涉任何 GEO 标签)。
  build: { inlineStylesheets: 'always' },
});
