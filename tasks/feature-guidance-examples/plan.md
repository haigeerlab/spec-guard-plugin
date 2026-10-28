# Plan: feature-guidance-examples

<!-- spec-guard: review approved -->

依据 [`spec/feature-guidance-examples.md`](../../spec/feature-guidance-examples.md)（2026-10-28 用户在本会话批准：「Spec 批准」）。批准节奏为分开审，
本 Plan 单独交审。分支 `claude/feature-guidance-examples`（从 `origin/main` `8737c3a1` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
只改文档，不改版本号（版本号在「0.85.1 文档收尾」的第二个模块 `config-text-fixes` 里改）。

## Overview

先把两行要用的说法逐条对到现有文档的出处，再改表；一次提交（只改文档，走快档，快档已含读仓库文档的回归）。

## Architecture Decisions

1. **只改表里两行的「该开」「别开」两格**，场景写进格子里；格子放不下时在表下面紧跟一两句，标明对应哪一行。
2. **出处先行**：每个场景、每个判断方法写之前在 todo 里记下它出自哪份文档哪一节；找不到出处的不写（Spec「先问」）。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：改写两行（AC1～AC3）

- 文件：`docs/getting-started.md`「可选能力：什么时候开」表。
- 核对：`docs/workflow.md`「已有项目：加新需求」表与 Proposal 一节、`docs/optional-features.md`「文档治理」、`docs/concepts.md` 设计原则与术语。
- 验证：两行各有至少一个具体场景与判断方法；出处记进 todo；链接检查 0 处问题。

### Checkpoint 1（report）：整体检查（AC4）

- `/bin/bash scripts/validate.sh` 通过；`git diff --stat origin/main -- plugins/spec-guard` 为空；记入 todo。

### Checkpoint 2（gate）：最终验收

- 呈现改前改后的两行、AC1～AC4 证据、改动与提交表。通过后推送并开本模块 PR（批准本 Plan 即授权推送与开 PR），合并由用户进行；
  合并后接着交审第二个模块 `config-text-fixes` 的能力图新行与 Spec。

## Files likely touched

- 文档：`docs/getting-started.md`
- 记录：`spec/CAPABILITY-MAP.md`（已写入新行与变更记录）、`spec/feature-guidance-examples.md`、`tasks/feature-guidance-examples/plan.md`、`tasks/feature-guidance-examples/todo.md`
- 不碰：`plugins/spec-guard/`、`docs/optional-features.md`、`docs/workflow.md`、选用指引其他四行。新增依赖、锁文件改动：无。

## 风险

- **把场景写成新规则。** 出处先行（决定 2）；最终验收逐条列出处。
