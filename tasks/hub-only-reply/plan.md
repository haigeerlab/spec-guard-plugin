# Plan: hub-only-reply

<!-- spec-guard: review approved -->

依据 [`spec/hub-only-reply.md`](../../spec/hub-only-reply.md)。分开审：Spec 已批准，本 Plan 单独审。
分支 `claude/hub-only-reply`，worktree `.claude/worktrees/distracted-morse-46ef70`，从 `0295c86`（0.80.0 证据 #388 合并）开出。
本模块一个 PR，不含版本号。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：让步规则与镜像（先红）

`test_workflow_checkpoints.py` 先补断言并确认失败：「交审时说明怎么批准」用例加让步规则的关键词，镜像用例加「去决策收件箱答」。
再按 Spec 的 Contract 在规则里加那一句，三处镜像各补半句。

- 验收：新断言先失败后通过；已有断言不改且通过（AC1～AC3）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。
- 文件：`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、`commands/review-mark.md`、
  `skills/spec-guard-ops/SKILL.md`、`docs/commands.md`。

### Task 2：CHANGELOG

`CHANGELOG.md` 加「[未发布]」段与一条；两份 `plugin.json` 仍为 0.80.0。

- 验收：`verify-and-commit.sh` 全档通过（AC4）。
- 文件：`CHANGELOG.md`。

### Checkpoint 1（report）：变异核对

在副本上删掉这句，确认断言变红；结果记入 todo。

### Checkpoint 2（gate）：模块最终验收

按交审小项呈现验证结果、AC 逐条证据、改动文件与提交表。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 低：只加一句规则文字；已有断言全部不改，作为回归。
