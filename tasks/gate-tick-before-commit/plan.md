# Plan: gate-tick-before-commit

<!-- spec-guard: review pending -->

依据 [`spec/gate-tick-before-commit.md`](../../spec/gate-tick-before-commit.md)。合并审：Spec 与本 Plan 一起评审、一次批准。
分支 `claude/gate-tick-before-commit`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `78ea9c9`（v0.60.3 验证记录合并）
开出。本模块一个 PR，含 0.60.4 版本号；合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：规则加一句（先红）

`test_workflow_checkpoints.py` 加断言并确认失败；在 `references/workflow-checkpoints.md` 加那一条；`CHANGELOG.md` 新增 `[0.60.4]`；
两份 `plugin.json` 改为 0.60.4，中英 README 的 `--ref` 改为 v0.60.4。

- 验收：新断言先失败后通过；清单一致性与 README 同步检查通过。
- 验证：`verify-and-commit.sh` 全档（`validate.sh`、阶段钩子回归、`verify-artifacts` 回归）。
- 文件：`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、`CHANGELOG.md`、两份 `plugin.json`、
  `README.md`、`README.en.md`。

### Checkpoint 1（gate）：模块评审

展示验证结果、未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 无明显风险：只多一条规则文字。
