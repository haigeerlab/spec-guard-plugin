# Plan: doc-suggestion-at-handoff

<!-- spec-guard: review pending -->

依据 [`spec/doc-suggestion-at-handoff.md`](../../spec/doc-suggestion-at-handoff.md)。合并审：Spec 与本 Plan 一起评审、一次批准。
分支 `claude/doc-suggestion-at-handoff`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `4900e1f`（v0.60.1 验证记录合并）
开出。本模块一个 PR，含 0.60.2 版本号；合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

只改文字：共享检查点规则两处、命令文件两份、技能一处、协议说明一处、文档与版本号。没有新命令，也没有会被检查器拦下的
新引用，按任务逐个提交。

## Architecture Decisions

- **规则只有一个出处。** 文档建议的写法写在共享检查点规则；命令文件与技能只列这一项并指向它。
- **说明跟着代码走。** 影响检查的说明以实跑结果为准，不凭阅读代码下结论。
- **静态测试不冒充行为验收。** agent 是否照做，由发版后的真实会话观察。

## Task List

### Task 1：文档建议与 ADR 询问（先红）

`test_workflow_checkpoints.py` 加一例并确认失败；再改 `references/workflow-checkpoints.md` 的 Spec 交审清单与说明、异常停点，
`commands/review-mark.md` 与 `spec-guard-ops` 的交审内容，`docs/workflow.md` 的停点。

- 验收：新断言先失败后通过；三处清单措辞一致。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`/bin/bash scripts/validate.sh --quick`。
- 文件：`references/workflow-checkpoints.md`、`commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`、
  `hooks/test_workflow_checkpoints.py`。

### Task 2：影响检查的 Spec 阶段说明（先红）

先在临时项目里实跑两种情况，确认说明要写的行为；再加断言并确认失败，然后改两处说明。

- 验收：断言先失败后通过；实跑结果与说明一致（有 `create` 且 Plan 不存在时报那句错误；只有 `follow`、`pending`、
  `not-applicable` 时得到 `valid`）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_documentation_impact.py`（或断言所在的测试文件）；实跑命令记入 todo。
- 文件：`references/documentation-impact.md`、`commands/documentation-impact.md`、一个测试文件。

### Task 3：CHANGELOG 与版本号

`CHANGELOG.md` 新增 `[0.60.2]`；两份 `plugin.json` 改为 0.60.2，中英 README 的 `--ref` 改为 v0.60.2。

- 验收与验证：`verify-and-commit.sh` 全档（`validate.sh`、阶段钩子回归、`verify-artifacts` 回归）。
- 文件：`CHANGELOG.md`、两份 `plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 1（gate）：模块评审

展示验证结果、未验证项与实际改动的文件清单。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 交审内容又多一项。允许写“无”、只挂在 Spec 交审一处，控制住噪音。
- 发版后的真实会话可能不给建议。那是规则文字的效果问题，如实记录，不靠加机制补。
