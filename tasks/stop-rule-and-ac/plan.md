# Plan: stop-rule-and-ac

<!-- spec-guard: review approved -->

依据 [`spec/stop-rule-and-ac.md`](../../spec/stop-rule-and-ac.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan 单独交审。
分支 `claude/stop-rule-and-ac`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `claude/map-progress-facts` 的 `e88e81a`
开出（叠在 #367 上）；#367 合并后把基点换到 main。本模块一个 PR，含 0.74.0 版本号；合并后的 tag、Release、两边宿主同步与验证
记录按 `docs/release-process.md` 另走。本分支同时带着模块 ④ `boundary-hint-unknown-size` 插入能力图的那一行。

所需工具：无 UI 改动。

## Overview

先改规则文字（测试先行，关键词断言），再加 verify-artifacts 的提示（回归先行），最后接 CHANGELOG 与版本号。规则文字有五处
副本：共享检查点规则、两份约定块模板、`docs/convention-block.md`、本仓库 `AGENTS.md` 的约定块，`validate.sh` 核对约定块一致。

## Architecture Decisions

- **改写现有那一条，不并存两套说法。** 「同一个 gate 因外部原因再次挡住」整句换掉，测试断言旧说法不再出现。
- **约定块只放一行摘要、细则指向共享规则**，与已有各行同一写法；新增 AC 一行，检查点那一行只补半句。
- **verify-artifacts 的检查写在脚本里内嵌的 `python3 -B -c` 段**，与挂起标记、评审标记那几段同一结构；阶段用
  `module_stage.module_state` 判定，围栏代码块按已有的去围栏方式排除。
- **不加 `ok` 行**，全部编号或没有该节时不输出，避免每个项目多一行通过记录。

## Task List

### Task 1：规则文字的断言（先红）

`test_workflow_checkpoints.py`：改写 `test_an_external_blocker_goes_back_to_the_user` 为新说法（同一模块、同一目标；第二次因外部
原因过不去；第二次报批；自己能修的不算；挂起并先开可开工模块、`/spec-guard:map`、没有就照实说），并断言旧说法不再出现；新增两例：
`report` 提示（写 Plan、交审 Plan 两处，未标注仍按 `gate`）、验收标准编号（AC 写法、编号稳定、最终验收按编号给证据）。三例都覆盖
共享规则、两份模板、`docs/convention-block.md` 与 `AGENTS.md`。

- 验收：新断言在旧文字上失败。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。
- 文件：`hooks/test_workflow_checkpoints.py`。

### Task 2：改规则文字与约定块

`references/workflow-checkpoints.md` 按 Spec Contract 改写停点、加 `report` 提示、加「验收标准编号」一条；两份模板、
`docs/convention-block.md`、`AGENTS.md` 的约定块同步三行。

- 验收：Task 1 全绿；`validate.sh --quick` 的约定块一致性通过；一处变异（只改共享规则、漏改一份模板）有断言变红。
- 验证：`verify-and-commit.sh`（只动文档类路径时走快档）。
- 文件：上述规则、模板、文档、`AGENTS.md`。

### Checkpoint 1（report）：规则文字断言全绿

### Task 3：verify-artifacts 的 AC 编号提示

先在 `test-verify-artifacts.sh` 加用例（Spec Testing strategy 各项：未编号出提示且不失败、全部编号含 `**AC1**` 与 `1. AC1` 不出、
`验收标准`／`Acceptance criteria` 标题识别、没有该节不出、已完成模块不出、围栏示例不算），再在 `verify-artifacts.sh` 实现。

- 验收：新用例先红后绿；两处变异各有用例变红：不跳过已完成模块、不认 `**AC1**`；本仓库跑 `verify-artifacts.sh` 仍是 0 警告。
- 验证：`verify-and-commit.sh` 全档（暂存了 `.sh`，加 ShellCheck）。
- 文件：`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`。

### Task 4：CHANGELOG 与版本号

CHANGELOG 新增 `[0.74.0]`；两份 `plugin.json` 改为 0.74.0，中英 README 的 `--ref` 改为 v0.74.0。

- 验收与验证：`verify-and-commit.sh` 全档。
- 文件：`CHANGELOG.md`、两份 `plugin.json`、两份 README。

### Checkpoint 2（gate）：最终验收

按 AC1–AC5 逐条给证据，展示未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- **约定块一致性检查对行宽或标点敏感**：先跑 `validate.sh --quick` 看它比对什么，五处一起改。
- **规则改宽后 agent 停得更多**：已在 Spec 限定只算外部原因与报批，自己能修的失败不算。
- **已有项目里大量进行中模块的 Spec 没编号**：只是 ⚠️ 提示，不失败；提示里写明要按编号对证据，不要求回填已完成模块。
