# Plan: boundary-hint-70

<!-- spec-guard: review approved -->

依据 [`spec/boundary-hint-70.md`](../../spec/boundary-hint-70.md)。本仓库评审节奏为分开审：Spec 已单独批准，本 Plan 单独交审。
分支 `claude/boundary-hint-70`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `40a97fb`（v0.63.4 发版证据合并）开出。
本模块一个 PR，含 0.63.5 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先改测试跑红，再改一个常数与一处整数算式转绿；文档、CHANGELOG 与版本号。

## Architecture Decisions

- **只动边界那一档。** `BOUNDARY_SHARE` 0.5 → 0.7；`thresholds()` 有窗口时的 `-(-window * 5 // 10)` 改为 `* 7 // 10`，说明文字 50% → 70%。
  80% 一档、`boundary_line`、`context_line` 与阶段判定不碰。
- **用例就地改，不另起一段。** 现有 50% 用例所在的三处（DONE、MODULE_DONE、NEEDS_SPEC）各自改成 70% 的正反例，加“500k 不再出”一例。

## Task List

### Task 0：提交已批准的产物

能力图新行、已批准的 Spec、本 Plan 与 todo 一次提交。

- 验收：`verify-and-commit.sh` 快档通过并提交。

### Task 1：边界阈值改为 70%（先红）

`test-phase-guard.sh`：
- DONE（Claude）：800k 的说明改为 `at or over 700 k`；699,999 不出、700,000 出；新增 500,000 不出（原来出）；原“恰好 500k”“低于 500k”两例换成这几例。
- Codex DONE：180,880 出（`at or over 70% of the 258 k window`）、180,879 不出、129,200 不出；“压缩之后的新读数照常判断”改用 180,880。
- MODULE_DONE：700,000 出、600,000 不出（原 600k 出）。
- NEEDS_SPEC：700,000 出、600,000 不出；850k 只改说明；Codex 180,880 出；无人值守一例改用 700k 读数。
- 文件头注释的 50%（500k）改为 70%（700k）。

先跑红，再改 `module_stage.py` 转绿。

- 验收：phase-guard 全绿；BUILDING 80% 用例逐字未改；变异（`BOUNDARY_SHARE` 改回 0.5）后“500k 不出”“699,999 不出”变红，
  （有窗口的算式改回 5）后 Codex“129,200 不出”变红。

### Checkpoint 1（report）：三套核心回归全绿

随 Task 1 的提交跑 `verify-and-commit.sh` 全档。

### Task 2：文档、CHANGELOG 与版本号

`commands/phase.md`（两处 50%、一处 500k）、`references/workflow-checkpoints.md`（连续构建一段的 50%）、`docs/design.md`（第 73 行）
改为 70% / 700k；CHANGELOG `[0.63.5] - 2026-10-16`；两份 `plugin.json` 改为 0.63.5；README 中英 `--ref` 改为 v0.63.5。
完成后在仓库内 grep，确认除 CHANGELOG 历史条目与发版记录外不再把模块边界写成 50% / 500k。

- 验收：`validate.sh` 通过；grep 结果为空。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

在正文列出实际改动的文件（取自版本库）、阈值前后对比、验证结果、未验证项与文档建议。需求由用户直接提出，无需回告其他会话。

- 验收：用户确认推送与开 PR。

### 发版后的验证

两边升级到 0.63.5；用安装副本的 `phase-guard.sh` 对构造的会话记录跑一次：Claude DONE 600k 不出、700k 出；Codex 180,880 出。结果记在本项。

## 影响面

`plugins/spec-guard/hooks/module_stage.py`、`test-phase-guard.sh`、`commands/phase.md`、`references/workflow-checkpoints.md`、
`docs/design.md`、CHANGELOG、两份 `plugin.json`、README 中英，以及本模块的 Spec、Plan、todo 与能力图。

## Risks and Mitigations

- **漏改某处 50% 说法。** Task 2 末尾 grep 兜底。
- **Codex 窗口小（258k），70% 时离宿主自动压缩更近。** 模块进行中仍有 80% 一档；发版后观察，有问题再议。

## Open Questions

- 无。
