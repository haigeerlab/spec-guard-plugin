# Plan: install-by-scope

<!-- spec-guard: review approved -->

依据 [`spec/install-by-scope.md`](../../spec/install-by-scope.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan 单独交审。
分支 `claude/install-by-scope`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `b3ff5e0`（#377 合并）开出。本模块一个
PR，含 0.78.1 版本号；合并后在合并提交上打 tag，按 `docs/release-process.md` 发版。

所需工具：无 UI 改动；只用仓库已有的 `python3`、`git` 与检查脚本，不装依赖、不联网。

## Overview

先把断言改成新说法并加反向断言（先红），再改共享检查点规则与四处约定块，再删掉检查与模块，最后接文档、CHANGELOG 与版本号。

## Architecture Decisions

- **断言沿用 `test_plan_approval_authorizes_by_scope`**：改写其中的关键句，并新增「不应出现」的短语列表（`只问一次`、`一条命令`、
  `verify-artifacts 会对照 Plan`），对共享检查点规则与两份模板都检查；「需要的外部条件」允许出现在「愿意写可以写」那一句，断言
  只查它不再是一条要求（不出现「Plan 开头写「需要的外部条件」」与 verify-artifacts 提示的说法）。
- **删除而不是停用**：`dependency_check.py` 与单测直接删除，verify-artifacts 两段直接删除；不留开关。能力图历史行不动。
- **`external_conditions` 随模块一起删**：0.78.0 时「需要的外部条件」检查改为调用它，两段一起删，没有别的调用方（实现前用 grep 复核）。

## Task List

### Task 1：断言改写与反向断言（先红）

改 `test_workflow_checkpoints.py` 的 `test_plan_approval_authorizes_by_scope`；`test-verify-artifacts.sh` 删掉「需要的外部条件」7 例与
「依赖改动」15 例，加一例反向（未完成模块的 Plan 没有这一节、package.json 新增包，不出提示）。

- 验收：改写后的断言在旧规则上失败；反向用例在旧脚本上失败。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`。
- 文件：`hooks/test_workflow_checkpoints.py`、`hooks/test-verify-artifacts.sh`。

### Task 2：共享检查点规则与四处约定块

按 Spec Contract 改 `references/workflow-checkpoints.md` 五处；两份模板、`docs/convention-block.md`、`AGENTS.md` 改两行。

- 验收：规则断言转绿；原有停点断言保持绿；`check-readme-sync.py` 报一致。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`python3 scripts/check-readme-sync.py`。
- 文件：`references/workflow-checkpoints.md`、两份模板、`docs/convention-block.md`、`AGENTS.md`。

### Task 3：删掉检查与模块

删 verify-artifacts 两段、`dependency_check.py`、`test_dependency_check.py` 与 `validate.sh` 里的登记；`commands/verify-artifacts.md`、
`docs/commands.md` 删对应说明。

- 验收：反向用例转绿；grep 确认仓库里不再引用 `dependency_check`（历史文件 `spec/`、`tasks/`、`CHANGELOG.md`、`docs/releases/` 除外）；
  本仓库实跑 verify-artifacts 结果与改动前一致。
- 验证：`verify-and-commit.sh` 全档（与 Task 1–2 一并提交：改写后的断言要规则与删除都完成才全绿）。
- 文件：`hooks/verify-artifacts.sh`、`hooks/dependency_check.py`（删）、`hooks/test_dependency_check.py`（删）、`scripts/validate.sh`、
  `commands/verify-artifacts.md`、`docs/commands.md`。

### Checkpoint 1（report）：规则、约定块与 verify-artifacts 回归全绿

### Task 4：CHANGELOG 与版本号

CHANGELOG `[0.78.1] - 2026-10-19`：写明放宽了什么、去掉了什么、原因（真实项目实跑的三类打扰）与已写这一节的 Plan 不受影响；
两份 `plugin.json` 改为 0.78.1，中英 README 的 `--ref` 改为 v0.78.1。

- 验收与验证：`verify-and-commit.sh` 全档；`check-readme-sync.py` 通过。
- 文件：`CHANGELOG.md`、两份 `plugin.json`、两份 README。

### Checkpoint 2（gate）：最终验收

按 AC1–AC7 逐条给证据，展示未验证项、实际改动的文件清单（含新增直接依赖与锁文件：应为「无」）与文档建议。推送与开 PR 在此由
用户确认，合并由用户进行；合并后的 0.78.1 发版（tag、Release、两边宿主、证据 PR）与发版后抄送协调人，也在此一并确认。

## Risks

- **删段时误伤相邻检查**：两段是最后加上的，删除后 verify-artifacts 回归里其他用例照旧要过；本仓库实跑结果与改动前比对。
- **断言写得过严**：「需要的外部条件」在「愿意写可以写」里合法出现；断言只查不再是要求，不查这个词本身。
- **CHANGELOG 已有未合并的 0.78.0 证据 PR #378**：它只改 `docs/releases/`，与本模块互不冲突。
