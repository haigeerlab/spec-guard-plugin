# Plan: ui-verify-by-change

<!-- spec-guard: review approved -->

依据 [`spec/ui-verify-by-change.md`](../../spec/ui-verify-by-change.md)。合并审：Spec 与本 Plan 一起评审、一次批准。
分支 `claude/ui-verify-by-change`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `9f9642d`（#309 合并）开出。
本模块一个 PR，含 0.60.3 版本号；合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：本模块不改界面，不需要浏览器或电脑操作。发版后的真实会话会用到临时项目里的静态页面。

## Task List

### Task 1：改写「UI 自验」与模板一行（先红）

`test_workflow_checkpoints.py` 加断言并确认失败；改写 `references/workflow-checkpoints.md` 的「UI 自验」一节；两份模板与
`docs/convention-block.md` 各新增一行；`docs/workflow.md` 改那一句；本仓库 `AGENTS.md` 的约定块用工作区源码更新（先预览）。

- 验收：新断言先失败后通过，原有关键词仍在；预览只新增这一行、无删除；`test-setup-teardown.sh` 通过。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh`。
- 文件：`references/workflow-checkpoints.md`、两份 `templates/*-block-local.md`、`docs/convention-block.md`、`docs/workflow.md`、
  `AGENTS.md`、`hooks/test_workflow_checkpoints.py`。

### Task 2：CHANGELOG 与版本号

`CHANGELOG.md` 顶部的 `[未发布]` 改为 `[0.60.3] - 2026-10-15` 并加本模块一条；两份 `plugin.json` 改为 0.60.3，中英 README 的
`--ref` 改为 v0.60.3。

- 验收与验证：`verify-and-commit.sh` 全档（`validate.sh`、阶段钩子回归、`verify-artifacts` 回归）。
- 文件：`CHANGELOG.md`、两份 `plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 1（gate）：模块评审

展示验证结果、未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 改界面的任务多一步验证，耗时增加。形式交给 agent 按改动判断，改一个文案看一眼即可。
- 无人值守运行多半拿不到浏览器，只能记“UI 未验证”。这是如实报告，不是失败。
- 规则无法确认 agent 真的看了，靠报告里写清看了什么来让用户判断。
