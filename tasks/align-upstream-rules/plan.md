# Plan: align-upstream-rules

<!-- spec-guard: review approved -->

依据 [`spec/align-upstream-rules.md`](../../spec/align-upstream-rules.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan 单独交审。
分支 `claude/align-upstream-rules`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `checkpoint-default-report` 的分支末端
开出；#381 已合并，开工前先把最新 `main` 合进来。本模块一个 PR，含 0.79.0 版本号；合并后在合并提交上打 tag，按
`docs/release-process.md` 发版，发版后通知 decision-inbox 整改会话（`gates` 含义变化、interface 1.4）并抄送接入协调人。

所需工具：无 UI 改动；只用仓库已有的 `python3`、`git` 与检查脚本。

## Overview

先同步 main，再用断言固定新规则与阶段提示的新建议语（先红），然后改共享检查点规则与四处约定块、改阶段提示、删 AC 提示，最后写
CHANGELOG 与版本号。

## Architecture Decisions

- **阶段提示只改一个分支**：`review_hint`／`review_hint_zh` 里「Spec 为 revised 且 stage 为 BUILDING、不在最终 gate」的建议语；
  `NEEDS_PLAN` 等阶段的 revised 分支与最终 gate 分支逐字不变。
- **规则断言沿用 `test_workflow_checkpoints.py`**：新关键句 assertIn，退役句子（「人做最后的兜底审查」「把 Plan 的批准标记改回 `pending`」
  「`verify-artifacts` 对未完成模块缺编号只提示」）assertNotIn；原有断言因新说法而改的，逐条记进 todo。
- **删 AC 提示整段**：verify-artifacts 那段与它的 7 个用例一起删，加一例反向。

## Task List

### Task 1：同步 main 与新断言（先红）

用宿主同步工具把最新 `main` 合进本分支；改 `test_workflow_checkpoints.py`（新关键句、退役句子、受影响的原有断言）、
`test-phase-guard.sh`（BUILDING 未到最终 gate 的 revised 建议语，中英各一；`NEEDS_PLAN` 照旧）、`test-verify-artifacts.sh`（删 AC 编号
7 例，加反向一例）。

- 验收：新断言在旧规则、旧提示、旧脚本上失败；记下改了哪些原有期望。
- 验证：三个测试文件各自运行。
- 文件：`hooks/test_workflow_checkpoints.py`、`hooks/test-phase-guard.sh`、`hooks/test-verify-artifacts.sh`。

### Task 2：共享检查点规则与四处约定块

按 Spec Contract 改 `references/workflow-checkpoints.md`（批准标记、检查点分级里最终验收一并复审的停下条件、批 Plan 授权的常规操作、
文档建议、返工与小模块、UI 自验、变更记录相关句）；两份模板、`docs/convention-block.md`、`AGENTS.md` 改对应各行。

- 验收：规则断言转绿；`check-readme-sync.py` 一致。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`python3 scripts/check-readme-sync.py`。
- 文件：`references/workflow-checkpoints.md`、两份模板、`docs/convention-block.md`、`AGENTS.md`。

### Task 3：阶段提示与 verify-artifacts

`module_stage.py` 中英两份 revised 建议语按 Spec 第 1 条改；`verify-artifacts.sh` 删「验收标准编号」一段。

- 验收：阶段提示与 verify-artifacts 用例转绿；`git grep` 确认 verify-artifacts 不再有 AC 编号相关代码；一处变异（BUILDING 未到最终 gate
  时仍输出旧建议语）有用例变红。
- 验证：`verify-and-commit.sh` 全档（与 Task 1–2 一并提交：断言要三者都改完才全绿）。
- 文件：`hooks/module_stage.py`、`hooks/verify-artifacts.sh`。

### Checkpoint 1（report）：规则、阶段提示与 verify-artifacts 的回归全绿

### Task 4：CHANGELOG 与版本号

CHANGELOG `[0.79.0] - 2026-10-19` 写 `checkpoint-default-report` 与本模块：停得更少的几处、`gates` 含义变化与 interface 1.4、
进行中的模块升级后的影响；两份 `plugin.json` 改为 0.79.0，中英 README 的 `--ref` 改为 v0.79.0。

- 验收与验证：`verify-and-commit.sh` 全档；`check-readme-sync.py` 通过。
- 文件：`CHANGELOG.md`、两份 `plugin.json`、两份 README。

### Checkpoint 2（gate）：最终验收

按 AC1–AC6 逐条给证据，展示改动的原有期望清单、未验证项、实际改动的文件清单（新增依赖与锁文件：应为「无」）与文档建议。推送与开
PR 在此由用户确认，合并由用户进行；合并后的 0.79.0 发版（tag、Release、两边宿主、证据 PR）与发版后通知 decision-inbox、抄送协调人，
也在此一并确认。

## Risks

- **改范围的判断交给 agent**：规则给例子（改验收标准的意思、加新能力、换实现方向算改范围；措辞、澄清、实现细节不算），不做自动判断。
- **四处约定块行数变化影响一致性检查**：改完跑 `check-readme-sync.py`。
- **与 `checkpoint-default-report` 改同一批文件**：本分支叠在它上面，先合 main 再改，避免冲突。
