# Plan: user-docs-fixes

<!-- spec-guard: review approved -->

依据 [`spec/user-docs-fixes.md`](../../spec/user-docs-fixes.md)（2026-10-28 用户在本会话批准：「Spec 批准；Q1 A；Q2 A」）。批准节奏为分开审，
本 Plan 单独交审。分支 `claude/docs-fixes`（从 `origin/main` `462dbe05` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
只改文档，不改版本号、不发版。

## Overview

先改两处事实错误，再按文件改 README、workflow.md、上手文档；每个 task 先核对再改，核对位置记进 todo；每个 task 单独提交，
提交前另跑一次完整 `validate.sh`（快档不跑文档回归）。

## Architecture Decisions

1. **按文件分 task**，同一文件的几处改动一次提交；todo 里写明每个 task 覆盖哪些 AC。
2. **外部事实走官方源。** agent-skills 的安装方法与 Codex 入口用 `gh api` 读 `addyosmani/agent-skills` 默认分支的 README 与目录（只读），
   读不到再查 context7；两处都拿不到就照实写「见 agent-skills README」并链过去，不凭记忆写命令。
3. **规则原文为准。** 「什么算批准」取共享检查点规则「批准标记」一节；`gate` 清单取停点规则「Plan 交审」里「不可逆或高风险」那一串，
   文档里照列并链到原处。
4. **AC8 写在可选能力的账本一节**（那里讲账本是什么），README 功能一览的 `ticket` 一行只补一句并链过去。
5. **AC10 交审消息样例**照停点规则「Spec 交审」的小项与顺序手写，开头一行写明「示意，不是实跑输出」。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：两处事实错误（AC1、AC2）

- 文件：`docs/workflow.md`、`docs/troubleshooting.md`。
- 核对：`module_stage.brief_line` 对例子格式实际生成一行，逐字对照；activeModule 一句对照上手文档对照表与 workflow-checkpoints「验收后接着写下一份 Spec」。

### Task 2：README 中英与账本说明（AC3、AC8）

- 文件：`README.md`、`README.en.md`、`docs/optional-features.md`。
- 核对：agent-skills 官方 README（决定 2）；`commands/ticket.md` 与 ticket skill 在账本未启用时的分支。

### Task 3：`docs/workflow.md` 的批准与 gate（AC4、AC5）

- 核对：workflow-checkpoints「批准标记」、node-rules「Plan 交审」的停下清单。

### Task 4：上手文档（AC6、AC7、AC9、AC10）

- 文件：`docs/getting-started.md`。
- 核对：阶段名为结构关键字（config 说明「结构关键字不变」与 `module_stage.py` 阶段常量）；map 图例链到 `docs/commands.md` map 一节、`--all`；
  Codex 对应按决定 2 的查询结果；交审样例按 node-rules「Spec 交审」。

### Checkpoint 1（report）：整体检查

- `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全过；改过的文档无断链；`git diff --stat origin/main -- plugins/spec-guard` 为空；记入 todo。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC1～AC11 逐条证据、文档改动表与提交表、Spec 中途改动（如有）。通过后推送并开本模块 PR（批准本 Plan 即授权推送与开 PR），
  合并由用户进行。

## Files likely touched

- 文档：`README.md`、`README.en.md`、`docs/workflow.md`、`docs/troubleshooting.md`、`docs/getting-started.md`、`docs/optional-features.md`
- 记录：`spec/CAPABILITY-MAP.md`（已写入新行与变更记录）、`spec/user-docs-fixes.md`、`tasks/user-docs-fixes/plan.md`、`tasks/user-docs-fixes/todo.md`
- 不碰：`plugins/spec-guard/`、CHANGELOG、历史记录目录、维护者文档。新增依赖、锁文件改动：无。

## 风险

- **外部安装命令写错或过时。** 只照官方源写并链到它（决定 2）；读不到时不写命令。
- **规则摘录走样。** 照原文摘并链到原处（决定 3）。
- **README 中英结构检查。** 两版同时改，`check-readme-sync.py` 与逐段对照。
