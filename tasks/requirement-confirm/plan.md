# Plan: requirement-confirm

<!-- spec-guard: review approved -->

依据 [`spec/requirement-confirm.md`](../../spec/requirement-confirm.md)。分开审：Spec 已批准，本 Plan 单独审。
分支 `claude/requirement-confirm`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `be0ec57`（0.81.0 证据 #394 合并）开出。
本模块一个 PR，不含版本号（冻结期间不发版）。批准本 Plan 即授权推送分支并开本模块的 PR；合并由用户进行。

所需工具：没有 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：规则一节、模板与 add-module 说明（先红）

`test_workflow_checkpoints.py` 先加断言，确认失败：
- 「需求确认」一节有这些关键句：触发时机、「需求说完了吗？还有要补充的吗？」、只认明确确认、确认后停、转 `interview-me`、两种跳过；
- 两份约定块模板各有一行指向它；
- `add-module.md` 在提出四项之前有这一步。

然后在 `references/workflow-checkpoints.md`「阶段交接」之前写这一节，两份模板各加一行，`commands/add-module.md` 加一步。

- 验收：新断言先红后绿，已有断言不改且通过（AC1、AC2）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。
- 文件：`references/workflow-checkpoints.md`、`templates/claude-block-local.md`、`templates/codex-block-local.md`、`commands/add-module.md`、
  `hooks/test_workflow_checkpoints.py`。若别的检查器要求复述这条规则的镜像（例如 `spec-guard-ops`、`docs/workflow.md`），一并同步并在 todo 里写明。

### Task 2：三处建议下一步（先红）

`test-phase-guard.sh` 先改或加断言：
- DONE 的三种情形（普通、有挂起、有待推送提交）中英各一句，都先提确认需求；
- MAP_ONLY、IDLE 中英各一句，都先提确认需求；
- NEEDS_SPEC 的建议语照旧（反例）。

然后改 `hooks/module_stage.py` 的 DONE 文案，以及 `hooks/phase-guard.sh` 的 MAP_ONLY、IDLE 文案。

- 验收：新断言先红后绿。原有逐字断言（第 2018、2024、2051 行附近）按新措辞改，逐条记入 todo（AC3、AC4）。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`。
- 文件：`hooks/module_stage.py`、`hooks/phase-guard.sh`、`hooks/test-phase-guard.sh`。

### Task 3：CHANGELOG

`CHANGELOG.md` 新开「[未发布]」段加一条；两份 `plugin.json` 仍为 0.81.0。

- 验收：`verify-and-commit.sh` 全档通过，并跑 ShellCheck（改了 `.sh`）（AC4、AC5）。
- 文件：`CHANGELOG.md`。

### Checkpoint 1（report）：变异核对

在副本上分别删掉规则那一节、DONE 和 MAP_ONLY 提示里那一句，确认对应断言变红；结果记入 todo。

### Checkpoint 2（gate）：模块最终验收

按交审小项呈现验证结果、AC 逐条证据、改动文件与提交表。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 低：只改文字和提示；阶段判定不动。DONE 的提示每轮都会出现，措辞要短，不能把这一轮变长很多。
- 低：原有逐字断言要改 3 处左右，逐条列出，防止顺手改掉别的期望。

## 返工 1（2026-10-21）

最终验收后，向用户讲解工作流时发现两处没写明。#395 还没合并，补在同一个 PR 里，属于已批准范围内的补漏：

1. 用户主动说「已确定」、但还没看过总结时：先给总结，再确认。保证用户确认之前一定看过完整内容。
2. 确认后的下一轮，把能力图新行和 Spec 一起交审（一次批准），不为能力图新行单独停一次，少问用户一轮。

- Task 4：`test_workflow_checkpoints.py` 先加两条断言、确认失败，再改「需求确认」一节、`add-module.md` 与 `spec-guard-ops` 的 add-module 一节；
  Spec 第 2 条按此修订并记变更记录。验证：规则测试与全档校验。
- Checkpoint 3（gate）：返工验收，附 Spec 差异，一次批准同时批准修订后的 Spec；推送到 #395 在此由用户确认。
