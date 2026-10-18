# Plan: record-on-receipt

<!-- spec-guard: review approved -->

依据 [`spec/record-on-receipt.md`](../../spec/record-on-receipt.md)（已批准）。本仓库评审节奏为分开审：Spec 已批准，本 Plan 单独交审。
分支 `claude/record-on-receipt`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `712ed62`（0.70.0 合并）开出。

本模块与 `review-marker-blank-line` 合发 0.70.1。两个模块各一个 PR：本 PR 先开，带能力图两行、两份已批准的 Spec 与两份 Plan，以及本模块的
改动，不改版本号；`review-marker-blank-line` 的 PR 从本分支开出，带它的改动和 0.70.1 的版本号。两个 PR 按顺序合并。

所需工具：无 UI 改动；宿主实测用 tmux 驱动的交互 Claude 会话与 Codex 会话，消息走真实的会话通道。

## Overview

约定块两份模板各新增一行、共享检查点规则补两句（记账不是受理、调用要传 `repoRoot`）；`phase-guard.sh` 两处读回提醒补一句传 `repoRoot`
并写出项目根路径；更正 `docs/releases/v0.69.0-claude.json` 里不实的一句；文档与 CHANGELOG。

## Architecture Decisions

- **新增行，不改旧行。** 0.69.0 的两行模板一字不动，新行写在它们之后；`setup-convention --replace` 不需要 `--accept-removals`。
- **路径只在安全时写出。** fresh 提醒的 JSON 是手写的，路径里有 `"`、`\` 或控制字符就退回「项目根目录」的说法；压缩后的提醒经 python3
  生成 JSON，但为了两处说法一致，用同一个判断。
- **没有账本时一字不变。** 只有 `.epiq/project.json` 存在时才出现新句子，没有账本的输出与 0.70.0 逐字节相同。

## Task List

### Task 0：提交能力图、两份已批准的 Spec 与两份 Plan

- 验收：`verify-and-commit.sh` 快档通过并提交。
- 文件：`spec/CAPABILITY-MAP.md`、`spec/record-on-receipt.md`、`spec/review-marker-blank-line.md`、`tasks/record-on-receipt/`、
  `tasks/review-marker-blank-line/`。

### Task 1：规则与模板行（先红）

`test_workflow_checkpoints.py` 加断言（规则含「记账不是受理」「不需要用户批准」「传 `repoRoot`」；两份模板与 `docs/convention-block.md` 含
新增行）并确认失败；再改 `references/workflow-checkpoints.md`、两份模板与 `docs/convention-block.md`。

- 验收：规则测试通过；`git diff` 显示两份模板只有新增行。
- 文件：`references/workflow-checkpoints.md`、`templates/claude-block-local.md`、`templates/codex-block-local.md`、`docs/convention-block.md`、
  `hooks/test_workflow_checkpoints.py`。

### Task 2：读回提醒带 `repoRoot`（先红）

`test-phase-guard.sh` 第 19 段先改断言并确认失败：fresh 与压缩后的提醒（中英）以传 `repoRoot` 一句结尾、含项目根路径；跟随指向时是目标
项目根；项目路径含 `"` 时不写路径且 JSON 有效；没有账本时两处与 0.70.0 逐字节相同。再改 `phase-guard.sh`。

- 验收：phase-guard 回归全绿；ShellCheck 无告警。
- 文件：`hooks/phase-guard.sh`、`hooks/test-phase-guard.sh`。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警

### Task 3：更正 0.69.0 证据

把 `docs/releases/v0.69.0-claude.json` 里「(observed in the maintainer session)」那一句改为如实表述，其他字段不动。

- 验收：`validate.sh` 的证据校验通过；`git diff` 只改这一句。
- 文件：`docs/releases/v0.69.0-claude.json`。

### Task 4：文档与 CHANGELOG

`docs/workflow.md`「有人在等的事」一段补「记账不是受理」与传 `repoRoot`；CHANGELOG 新增 `[0.70.1]`（未发布前写 `Unreleased` 的标题下），
写本模块的修复与证据更正。版本号不在本 PR 改。

- 验收：`validate.sh` 通过。
- 文件：`docs/workflow.md`、`CHANGELOG.md`。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

列出实际改动、验证结果与未验证项；拟回告：无（本模块由本会话发现、用户本人确认）。

### 发版后的验证

0.70.1 发版后，两边宿主各跑 3 次：交互会话做手头的事时，用真实会话通道送来一条需求（Claude 用宿主的会话消息，Codex 用 agent-relay 信箱），
提示词不提账本；记录当场记账的次数、账本调用是否都带 `repoRoot`、是否没有自行受理或回复。结果写进 0.70.1 证据。
