# Plan: checkpoint-default-report

<!-- spec-guard: review approved -->

依据 [`spec/checkpoint-default-report.md`](../../spec/checkpoint-default-report.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan
单独交审。分支 `claude/checkpoint-default-report`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `dea4d5a`（#379 合并）
开出。本模块一个 PR，不改版本号；0.79.0 的版本号与 CHANGELOG 由下一个模块 `align-upstream-rules` 的 PR 写。

所需工具：无 UI 改动；只用仓库已有的 `python3`、`git` 与检查脚本。

## Overview

先用测试固定新判据（先红），再改判据函数与两处调用方，再改接口说明，最后同步规则、模板与文档。

## Architecture Decisions

- **`gate_checkpoints(text) -> list[(title, checked)]` 取代 line 级 `gate_checkpoint(line)`**：先收集所有 `Checkpoint` 行（识别与级别正则
  不变），再按「显式 gate 算、显式 report 不算、未标级别只有最后一个算」筛出 gate。`next_gate` 取其中第一个未勾的；`_open_gate` 改为
  「这一行是否在未勾的 gate 集合里」，`at_final_gate` 的语义不变；`map_view._gates()` 直接数这份列表。
- **`interface.json` 1.4 只改说明**：`progressFacts.fields.gates` 的文字与 `appearsWhen`；`check-interface.py` 的字段核对不受影响。
- **原有回归里依赖旧判据的期望**：逐条改并在 todo 记下改了哪几条、为什么（未标级别的中间检查点从 gate 变为 report）。

## Task List

### Task 1：新判据的测试（先红）

`test_map_view.py` 的 `GateCountTest` 按 Spec Testing strategy 加用例并改原有一例（原 `TODO` 里中间未标的检查点不再算）；
`test-phase-guard.sh` 加「下一个 gate 跳过未标的中间检查点」与「最终 gate 判定」两类用例；`test_workflow_checkpoints.py` 加新判据关键句
与「不再出现未标注按 gate」的断言。

- 验收：新用例在旧判据上失败；记下哪些原有期望因判据变化而改。
- 验证：三个测试文件各自运行。
- 文件：`hooks/test_map_view.py`、`hooks/test-phase-guard.sh`、`hooks/test_workflow_checkpoints.py`。

### Task 2：判据函数与调用方

`module_stage.py` 加 `gate_checkpoints`，改 `next_gate`、`_open_gate`／`at_final_gate`；`map_view.py` 的 `_gates()` 改用它，删掉
不再使用的 `gate_checkpoint`。

- 验收：Task 1 的 map 与阶段提示用例转绿；一处变异（未标的中间检查点也算 gate）有用例变红。
- 验证：`python3 -B plugins/spec-guard/hooks/test_map_view.py`、`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`。
- 文件：`hooks/module_stage.py`、`hooks/map_view.py`。

### Task 3：接口说明、规则、模板与文档

`interface.json` 升到 1.4；共享检查点规则「Plan 检查点分级」按 Spec 第 3 条改；两份模板、`docs/convention-block.md`、`AGENTS.md`、
`docs/workflow.md`、`spec-guard-ops` 的 SKILL.md、`commands/map.md` 同步。

- 验收：`test_workflow_checkpoints.py` 转绿；`check-interface.py`、`check-readme-sync.py` 通过；`git grep` 确认产品文字里不再有
  「未标注的检查点按 `gate`」「未标注按 `gate`」。
- 验证：`verify-and-commit.sh` 全档（与 Task 1–2 一并提交：断言要三者都完成才全绿）。
- 文件：`interface.json`、`references/workflow-checkpoints.md`、两份模板、`docs/convention-block.md`、`AGENTS.md`、`docs/workflow.md`、
  `skills/spec-guard-ops/SKILL.md`、`commands/map.md`。

### Checkpoint 1（report）：判据、接口与规则的回归全绿

### Task 4：本仓库与临时项目实跑

在本仓库跑 `/map --json` 对比改动前后各模块的 `gates.total`（列出变化的模块数），在临时项目验证一份「中间未标＋最后未标」的 todo：
阶段提示的「下一个 gate」指向最后一个检查点，`gates` 为 `{1, 0}`。结果记进 todo。

- 验收与验证：实跑命令与输出写入 todo；`verify-and-commit.sh`。
- 文件：`tasks/checkpoint-default-report/todo.md`。

### Checkpoint 2（gate）：最终验收

按 AC1–AC5 逐条给证据（测试名与结果、改动的原有期望清单、实跑输出），展示未验证项、实际改动的文件清单（新增依赖与锁文件：应为
「无」）与文档建议。推送与开 PR 在此由用户确认，合并由用户进行；本模块不发版，完成后接着插入 `align-upstream-rules`。

## Risks

- **最后一个检查点之后另有检查点被误当作中间检查点**：判据按文件里最后一个 `Checkpoint` 行算，Task 1 有「最后检查点之后还有普通任务」用例。
- **原有阶段提示用例大量依赖「未标即 gate」**：逐条按新判据改，并记录；不为了过测试改判据。
- **decision-inbox 读到变小的 `gates.total`**：接口 1.4 写明，发版后单独通知。
