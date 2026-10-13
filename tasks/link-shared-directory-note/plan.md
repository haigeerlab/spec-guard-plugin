# Plan: link-shared-directory-note

<!-- spec-guard: review approved -->

依据 [`spec/link-shared-directory-note.md`](../../spec/link-shared-directory-note.md)。本仓库评审节奏为合并审：Spec 与本 Plan
一起评审、一次批准（2026-10-13，内容先在对话里给出，用户批准后写成文件）。分支 `claude/link-shared-directory-note`，
worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `8b9ff2d`（v0.58.1 验证记录合并）开出。本模块一个 PR，含 0.58.2
版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

三处输出各加一句固定文字，文档同步。不新增命令、不改判定。

## Task List

### Task 1：`Linked project` 行、预览与 `show` 的说明（先红）

`test-phase-guard.sh` 更新 `Linked project` 行的逐字期望；`test_project_link.py` 加预览与 `show` 的断言。确认失败后改
`phase-guard.sh` 与 `project_link.py`。

- 验收：phase-guard 回归与单测全绿。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`；`python3 -B plugins/spec-guard/hooks/test_project_link.py`。
- 文件：`hooks/phase-guard.sh`、`hooks/project_link.py`、`hooks/test-phase-guard.sh`、`hooks/test_project_link.py`。

### Task 2：命令文件、技能、排障文档、CHANGELOG 与版本号

- 验收：`validate.sh` 通过。
- 验证：`/bin/bash scripts/validate.sh`。
- 文件：`commands/link-project.md`、`skills/spec-guard-ops/SKILL.md`、`docs/troubleshooting.md`、`CHANGELOG.md`、两份
  `plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 1（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`，一个任务做完并提交后再开始下一个。展示验证结果与未验证项。推送本分支与开 PR 在
这个检查点由用户确认；合并由用户进行。

## 影响面

`phase-guard.sh` 的一行文字、`project_link.py` 的两处输出、三份文档。既有项目无须任何操作。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| `Linked project` 行有逐字断言 | 同一个任务里先改期望、看它失败，再改实现 |

## Open Questions

- 无。
