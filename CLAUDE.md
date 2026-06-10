# CLAUDE.md — sma_geo 工作区约定

## 分工
- 本仓库:SMA GEO 内容站 + 监测脚本,按 docs/internal/sma-geo-implementation-spec.md 执行(该目录不入库)。
- 评审流程:阶段完成即 push;外部评审 clone 当前 HEAD 对照 spec 验收,意见以 REVIEW-*.md 回传,按编号逐项修复。

## 硬性规则
1. 本仓库唯一写入方为 Claude Code;人工终端只读。禁止 force push(2026-06-10 基线修复除外)。
2. 一切对外可见文本(页面文案、README、代码注释、commit message)统一使用"企业级 AI 网关 / 模型接入平台"称谓。禁用的历史旧称及自查命令见 docs/internal/terminology.md,每次提交前执行该自查。
3. 密钥只走 .env;提交前自查 `git diff --cached | grep -iE "sk-|secret|token|api_key"`。
4. commit message 格式:`P0-1.1 robots.txt: 简述`,章节号对应 spec。
5. data/、docs/internal/、.env 永不入库。
6. 每完成一个 spec 小节即 commit,阶段完成即 push。
