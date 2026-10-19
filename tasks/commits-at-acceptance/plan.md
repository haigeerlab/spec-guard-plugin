# Plan: commits-at-acceptance

<!-- spec-guard: review approved -->

依据 [`spec/commits-at-acceptance.md`](../../spec/commits-at-acceptance.md)。合并审：Spec 与本 Plan 一起评审、一次批准。
分支 `claude/commits-at-acceptance`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `9b40e3f`（v0.79.0 发版证据合并）
开出。本模块一个 PR，不含版本号（阶段丙版本冻结，排到下一版）。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：规则与摘要补一句（先红）

`test_workflow_checkpoints.py` 加断言并确认失败；在 `references/workflow-checkpoints.md` 补那一句；两份 `templates/*-block-local.md`
与 `docs/convention-block.md` 的摘要行同步。

- 验收：新断言先失败后通过。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。
- 文件：`references/workflow-checkpoints.md`、`templates/claude-block-local.md`、`templates/codex-block-local.md`、
  `docs/convention-block.md`、`hooks/test_workflow_checkpoints.py`。

### Task 2：CHANGELOG

`CHANGELOG.md` 顶部新增 `## [未发布]` 段，写这一条；版本号不改。

- 验收：`validate.sh` 通过，清单一致性不报错。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`CHANGELOG.md`。

### Checkpoint 1（gate）：模块最终验收

展示验证结果、未验证项、实际改动的文件清单、本模块的提交清单与文档建议。推送与开 PR 在此由用户确认，合并由用户进行；
PR 号抄送接入协调会话。

## Risks

- 无明显风险：只多一句规则文字。
