# Plan: doc-suggestion-template-line

<!-- spec-guard: review pending -->

依据 [`spec/doc-suggestion-template-line.md`](../../spec/doc-suggestion-template-line.md)。合并审：Spec 与本 Plan 一起评审、一次批准。
分支 `claude/doc-suggestion-template-line`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `8177a35`（v0.60.2 验证记录合并）
开出。本模块一个 PR，不带版本号；0.60.3 的版本号与发版随下一个模块 `ui-verify-by-change`。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：模板新增一行（先红）

`test_workflow_checkpoints.py` 加断言并确认失败；两份模板与 `docs/convention-block.md` 各新增一行；本仓库 `AGENTS.md` 的约定块用工作区源码
`setup-convention.sh local --host=codex --replace` 更新（先预览）；`CHANGELOG.md` 的 `[未发布]` 记一条。

- 验收：断言先失败后通过；预览只新增这一行、无删除；`test-setup-teardown.sh` 通过。
- 验证：`verify-and-commit.sh` 全档。
- 文件：两份 `templates/*-block-local.md`、`docs/convention-block.md`、`AGENTS.md`、`CHANGELOG.md`、`hooks/test_workflow_checkpoints.py`。

### Checkpoint 1（gate）：模块评审

展示验证结果、未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 约定块又多一行，每个会话多读一行。只点出位置，不写细则。
