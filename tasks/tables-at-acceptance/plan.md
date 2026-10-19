# Plan: tables-at-acceptance

<!-- spec-guard: review approved -->

依据 [`spec/tables-at-acceptance.md`](../../spec/tables-at-acceptance.md)。合并审：Spec 与本 Plan 一起评审、一次批准。
分支 `claude/tables-at-acceptance`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `089d9c2`（#384 合并）开出。
本模块一个 PR，不含版本号（阶段丙版本冻结，排到下一版）。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：规则与摘要改成表格呈现（先红）

`test_workflow_checkpoints.py` 加断言并确认失败；按 Spec 的 Contract 改 `references/workflow-checkpoints.md` 那一条；两份
`templates/*-block-local.md` 与 `docs/convention-block.md` 的摘要行同步。

- 验收：新断言先失败后通过，已有断言不动且通过。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。
- 文件：`references/workflow-checkpoints.md`、`templates/claude-block-local.md`、`templates/codex-block-local.md`、
  `docs/convention-block.md`、`hooks/test_workflow_checkpoints.py`。

### Task 2：CHANGELOG

`CHANGELOG.md`「[未发布]」段加一条；版本号不改。

- 验收：`verify-and-commit.sh` 全档通过。
- 文件：`CHANGELOG.md`。

### Checkpoint 1（gate）：模块最终验收

按本模块的新规则呈现：验证结果、未验证项、文档改动表、其他改动表、新增依赖、本模块的提交表与文档建议。推送与开 PR
在此由用户确认，合并由用户进行。

## Risks

- 无明显风险：只改规则文字。
