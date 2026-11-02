# Plan: whitespace-only-preview

<!-- spec-guard: review approved -->

依据 [`spec/whitespace-only-preview.md`](../../spec/whitespace-only-preview.md)（2026-11-03 用户在本会话批准：「批准」，能力图新行同时确认写入）。
分支 `claude/whitespace-only-preview`（从 `origin/main` `07d38399` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.86.3。

## Overview

先在 `test-setup-teardown.sh` 写「只差空白」「逐字节相同」的预览用例，确认在 0.86.2 上失败；再在 `managed-block.py` 的 `replace --dry-run`
里加一行说明。随后补三处文档，改版本号与 CHANGELOG，交最终验收。

## Architecture Decisions

1. **`_units` 多返回一项原文**：每段返回 `(显示文字, 键, 原文)`，原文是该段各行去掉行尾换行后用 `\n` 拼接（保留行首缩进与行内空白）。
   `_keys`、`replace` 与 `remove` 里的解包随之改为三项；判定只用键，与 0.86.2 相同。
2. **计数**：旧块里键在模板里出现、但原文不在模板同键各段的原文里的段，计为「只差空白或折行」。个数大于 0 时，在 `will add:` 之后、
   `will adjust blank lines` 之前打印 `will adjust whitespace or line wrapping: N paragraph(s)`。只在 `--dry-run` 打印。
3. **其余不动**：`will remove:`／`will add:`、`[needs --accept-removals]`、`_refuse`、`--check`、写入路径、teardown 都不改；
   `block content unchanged` 的条件仍是 `inner == block`。
4. **文档**：`commands/setup-convention.md` 讲预览的那段、`skills/spec-guard-ops/SKILL.md` 的 setup-convention 一节、`docs/commands.md`
   的 setup-convention 条目，各补一句：只差空白或折行的段汇总成一行 `will adjust whitespace or line wrapping: N paragraph(s)`，不需要
   `--accept-removals`。
5. **发版**照 0.86.2：合并后核对、打 tag、打包、Release、两个宿主核对（Codex 先请你在 `/hooks` 重新批准，批完我先看一眼还有没有
   标 `[!]` 的再跑 smoke）、证据收尾 PR。需求来自你本人，没有要回告的会话。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：预览报告只差空白的段（成功标准 1–3）

- 文件：`hooks/managed-block.py`、`hooks/test-setup-teardown.sh`。
- 用例：两侧「折开再拼回」的块 `--replace --dry-run` 报这一行、N 等于改动的段数、不报 `block content unchanged`、没有 `will remove:`；
  有续行的旧块同样报；刚装好的块（逐字节相同）不报这一行、照旧报 `block content unchanged`。
- 验证：新用例在 0.86.2 上失败、改后通过；`test-setup-teardown.sh` 全部通过。

### Task 2：文档（成功标准 4）

- 文件：`commands/setup-convention.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`。
- 验证：`validate.sh --quick` 通过。

### Task 3：版本号与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、README 中英 `--ref`、`CHANGELOG.md`（0.86.3：修复、文档）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；ShellCheck；`evals/codex-plugin-smoke.sh --selftest`。
- 变异（草稿副本）：去掉这一行的打印、去掉「原文不同」的条件，两处都要让 `test-setup-teardown.sh` 变红。
- 用上次留在临时目录的真实块再跑一次 `--replace --dry-run`，确认报出这一行。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、成功标准证据、文档与改动表、提交表、Spec 中途改动（如有）。通过即同时授权：推送、开 PR；你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对合并、打 `v0.86.3`、打包、Release、比对 SHA-256；刷新并核对 Claude 与 Codex 安装副本；收尾扫描、证据收尾 PR。任一步失败就停下说明。

## Files likely touched

- 插件包：`hooks/managed-block.py`、`hooks/test-setup-teardown.sh`、`commands/setup-convention.md`、`skills/spec-guard-ops/SKILL.md`、两份 `plugin.json`
- 仓库：`docs/commands.md`、`README.md`、`README.en.md`（只改 `--ref`）、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.86.3-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/whitespace-only-preview.md`、本 Plan、`tasks/whitespace-only-preview/todo.md`
- 新增依赖、锁文件改动：无。不碰 `setup-convention.sh`、`teardown-convention.sh`、模板、阶段判定。

## 风险

- **同一个键在模板里出现多次**（比如两条相同的规则）：按「原文不在同键各段的原文集合里」计数，不会误报；模板目前没有重复规则。
- **既有用例依赖预览的确切行数**：先 grep 用到预览输出的断言；有用例因为多出这一行变红，就在 todo 里写明原因再改。
