# Plan: compact-next-step

<!-- spec-guard: review approved -->

依据 [`spec/compact-next-step.md`](../../spec/compact-next-step.md)。本仓库评审节奏为分开审：Spec 已单独批准，本 Plan 单独交审。
分支 `claude/compact-next-step`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `17734eb`（v0.64.1 发版证据合并）开出。
本模块一个 PR，含 0.64.2 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

一句钩子文案（先红后绿），设计文档同步、CHANGELOG 与版本号。

## Architecture Decisions

- **只动常量本身**：`COMPACT_NOTE` 的追加方式（`emit` 在 `SessionStart` 时拼到末尾）不变，测试也只改期望常量，不加新用例——现有
  两例已覆盖「末尾是这句」与「除末尾外逐字相同」。

## Task List

### Task 0：提交已批准的产物

能力图新行、已批准的 Spec、本 Plan 与 todo 一次提交。

- 验收：`verify-and-commit.sh` 快档通过并提交。

### Task 1：压缩后提醒补半句（先红）

先把 `test-phase-guard.sh` 第 15 段的 `REMIND` 改为新措辞，跑 phase-guard 回归，看到「带 SessionStart 参数时末尾有压缩后的核对提醒」
一例变红；再改 `phase-guard.sh` 的 `COMPACT_NOTE`，转绿。`docs/design.md` 对这句的中文转述补「核对后接着做建议的下一步，不就此
结束这一轮」。

- 验收：phase-guard 回归全绿，用例数不变；「除末尾一句外逐字相同」一例保持通过；`git diff` 中钩子只改这一行。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告

随 Task 1 的提交跑 `verify-and-commit.sh` 全档（暂存了 `.sh`，带 ShellCheck）。

### Task 2：CHANGELOG 与版本号

CHANGELOG `[0.64.2] - <合并日>`「修复」一条；两份 `plugin.json` 改为 0.64.2；README 中英 `--ref` 改为 v0.64.2。

- 验收：`validate.sh` 通过。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

在正文列出实际改动的文件（取自版本库）、新旧两句原文、验证结果、未验证项、文档建议（只同步 `docs/design.md`）与拟回告（对象：
spec-guard-monitor，经会话「Codex LIVE-SAAS 前端基础架构监测」`local_4f410de8-418e-440c-90d8-436a73edcc6b` 转达；渠道：宿主会话
消息；时机：0.64.2 装上之后）。

- 验收：用户确认推送与开 PR。

### 发版后的验证

两边升级到 0.64.2；以 `SessionStart` 参数调用两个安装副本的 `phase-guard.sh`，确认末尾是新措辞、每轮注入不变。能在临时项目里制造
一次真实压缩时，再看 agent 核对后是否接着做建议的下一步；做不到如实记为未验证。回告来源，结果记在本项。

## 影响面

`plugins/spec-guard/hooks/phase-guard.sh`、`hooks/test-phase-guard.sh`、`docs/design.md`、CHANGELOG、两份 `plugin.json`、README 中英，
以及本模块的 Spec、Plan、todo 与能力图。

## Risks and Mitigations

- **模型仍然在核对后停下。** 文案是建议不是机制；发版后如实记录，再出现时把证据交用户决定是否加更强的手段。
- **没有建议下一步的两种诊断输出。** 措辞带「if there is one」，不会让 agent 去找不存在的行。

## Open Questions

- 无。
