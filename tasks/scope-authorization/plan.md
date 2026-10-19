# Plan: scope-authorization

<!-- spec-guard: review approved -->

依据 [`spec/scope-authorization.md`](../../spec/scope-authorization.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan 单独交审。
分支 `claude/scope-authorization`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `0883717`（#374 合并）开出。
本模块一个 PR，不改版本号；0.78.0 的版本号与 CHANGELOG 由下一个模块 `dependency-check` 的 PR 写。

需要的外部条件：无（不装依赖、不联网；只用仓库已有的 `python3`、`git` 与检查脚本）。

## Overview

先用断言固定要出现的规则句子与 verify-artifacts 的提示（先红），再改共享检查点规则，再同步四处约定块，最后接 verify-artifacts。
规则文字的改动集中在 `references/workflow-checkpoints.md`，约定块只放短句并指向它。

## Architecture Decisions

- **规则断言放在 `test_workflow_checkpoints.py`**：沿用现有 `test_plan_checkpoints_are_gate_or_report`、`test_the_final_gate_lists_the_changed_files`
  的写法，断言关键句出现在共享检查点规则与两份模板里；不断言整段原文，便于以后改措辞。
- **约定块四处一致**：改两份模板，`docs/convention-block.md` 的 SYNC 段与本仓库 `AGENTS.md` 的约定块按模板同步；
  `check-readme-sync.py` 与 `validate.sh` 的一致性检查照旧把关。
- **verify-artifacts 新段落仿照 AC 编号检查**：同一种 python 内嵌写法、同样跳过代码块、同样「只 warn 不 ok」、读不出给「未验证」；
  未完成的判定用 `module_state(...)["stage"] != "DONE"`，再要求 `tasks/<id>/plan.md` 存在。

## Task List

### Task 1：规则与提示的测试（先红）

`test_workflow_checkpoints.py` 加 `test_plan_approval_authorizes_by_scope`（规则含：按范围不按次数、需要的外部条件、只问一次、
宿主确认不算报批、一次列全所需权限、新增依赖与锁文件；两份模板含新增两行与两处修改）。`test-verify-artifacts.sh` 加用例：
缺这一节提示；标题、行首「需要的外部条件：无」、英文标题不提示；只在代码块里出现仍提示；已完成与没有 Plan 不提示；退出码不变。

- 验收：新断言在旧文字、旧脚本上失败；原有断言不改。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`。
- 文件：`hooks/test_workflow_checkpoints.py`、`hooks/test-verify-artifacts.sh`。

### Task 2：共享检查点规则

按 Spec Contract 改 `references/workflow-checkpoints.md`：「Plan 检查点分级」加两条、「异常停点」改为完整清单并加「新依赖只问一次」、
第二次报批加第四个选项、最终验收清单加依赖一行、UI 自验的工具清单并入、「权限、未知结果与取消」加「宿主确认」。

- 验收：Task 1 的规则断言转绿；原有 `test_workflow_checkpoints.py` 断言保持绿。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。
- 文件：`references/workflow-checkpoints.md`。

### Task 3：四处约定块

两份模板加两行、改两行；`docs/convention-block.md` 与 `AGENTS.md` 同步。

- 验收：模板断言转绿；`check-readme-sync.py` 报一致；`validate.sh` 通过。
- 验证：`verify-and-commit.sh` 全档（与 Task 2 一并提交，因为 Task 1 的断言要两者都改完才全绿）。
- 文件：`templates/claude-block-local.md`、`templates/codex-block-local.md`、`docs/convention-block.md`、`AGENTS.md`。

### Task 4：verify-artifacts 提示

`verify-artifacts.sh` 加「需要的外部条件」一段。

- 验收：Task 1 的 verify-artifacts 用例全绿；一处变异（不跳过代码块）有用例变红；本仓库实跑不出新提示（已完成模块不追溯，
  本模块 Plan 已写这一节）。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/verify-artifacts.sh`。

### Checkpoint 1（report）：规则、约定块与提示的回归全绿

### Checkpoint 2（gate）：最终验收

按 AC1–AC8 逐条给证据（断言名与结果、规则改动前后对照、verify-artifacts 实跑），展示未验证项、实际改动的文件清单（含新增依赖与
锁文件：本模块应为「无」）与文档建议。推送与开 PR 在此由用户确认，合并由用户进行；本模块不发版，完成后接着插入 `dependency-check`。

## Risks

- **改写「异常停点」时漏掉原有停点**（如「测试改不红」「Spec 没覆盖的决策要问是否记 ADR」）：Task 1 的断言同时检查原有停点仍在。
- **约定块变长**：只加两行、改两行，完整清单留在共享检查点规则；`rules-in-context` 的上下文预算不受影响（不进每轮注入）。
- **已有项目升级后进行中模块出一条提示**：只提示、不失败，且只对未完成模块；在 CHANGELOG（由 `dependency-check` 写）里说明。
