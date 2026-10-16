# Plan: acceptance-review-streamline

<!-- spec-guard: review approved -->

依据 [`spec/acceptance-review-streamline.md`](../../spec/acceptance-review-streamline.md)。本仓库评审节奏为分开审：Spec 已单独批准，
本 Plan 单独交审。分支 `claude/acceptance-review-streamline`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `0fbd896`
（v0.63.2 发版证据合并）开出。本模块一个 PR，含 0.63.3 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

规则文件三处新增文字（先写断言跑红，再补文字转绿），两份文档同步，CHANGELOG 与版本号。不改命令、钩子、检查与约定块模板。

## Architecture Decisions

- **规则只有一处出处。** 三条都只写在 `references/workflow-checkpoints.md`；`docs/workflow.md` 用面向用户的话说明，不复制规则细则。
- **O2 以“差异已原样呈现”为前提。** 规则写明没附差异就不算复审，避免被读成“验收时顺便把 Spec 也批了”。
- **O4 不点按钮名。** 写“任何会结束本轮的确认框”，括号里举宿主的“下一步”框为例，两个宿主都适用。

## Task List

### Task 0：提交已批准的产物

能力图新行、已批准的 Spec、本 Plan 与 todo 一次提交。

- 验收：`verify-and-commit.sh` 快档通过并提交。

### Task 1：三处规则文字（先红）

`test_workflow_checkpoints.py` 新增 3 例：
- 「Plan 检查点分级」里有验收附 Spec 差异的关键词（如“Spec 的改动差异”“同时批准修订后的 Spec”“先用 `review-mark`”“不算 Spec 复审”）；
- 「阶段交接」里有验收后接着写下一份 Spec 的关键词（如“接着写”“已在能力图里”“/compact”“新插入能力图”）；
- 「评审状态标记」里有确认框的关键词（如“结束本轮的确认框”“确认框摘要”）。

先跑红，再按 Spec 的 Contract 在规则文件三处加文字，转绿。

- 验收：新增 3 例全绿；现有断言不改；`validate.sh --quick` 通过；变异（删掉任一处新文字）对应断言变红。

### Checkpoint 1（report）：规则测试与 `validate.sh` 全绿

随 Task 1 的提交跑 `verify-and-commit.sh`。

### Task 2：文档、CHANGELOG 与版本号

- `docs/workflow.md` 的「交审时你应该看到内容」一段补：要点在正文里、确认框摘要不算；最终验收附 Spec 差异可一次批准；验收后接着
  写下一份 Spec 并提示 `/compact`。
- `docs/design.md:120` 的挂起说法改为：可用 `--reason` 记一行原因；挂起时长不另存，由进度表从 git 历史读出。
- CHANGELOG `[0.63.3] - 2026-10-16`；两份 `plugin.json` 改为 0.63.3；README 中英 `--ref` 改为 v0.63.3。

- 验收：`validate.sh` 通过。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

在正文里列出实际改动的文件（取自版本库）、三处新增规则的原文、验证结果、未验证项、文档建议与拟回告（对象：会话
「Spec/Guard 插件使用观测」`local_3b05d344-963e-4750-8edb-83b08ad9d0ca`；渠道：宿主会话消息；时机：0.63.3 装上之后）。

- 验收：用户确认推送与开 PR。

### 发版后的验证

两边宿主升级到 0.63.3；各在临时项目里跑一次多轮真实会话：一个已批准 Spec 的模块，构建中补改 Spec 后到最终 gate，观察验收消息是否
附 Spec 差异并说明一次批准、批准后是否接着写下一份已在能力图里的 Spec；交审时要点是否在正文里。如实记录，回告观测会话，结果记在本项。

## 影响面

`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`docs/workflow.md`、
`docs/design.md`、CHANGELOG、两份 `plugin.json`、README 中英，以及本模块的 Spec、Plan、todo 与能力图。

## Risks and Mitigations

- **O2 被读宽，变成“验收时顺手批 Spec”。** 规则写明没附差异不算复审、途中会影响后续任务的修改照旧当场停。
- **O2b 让用户错过压缩时机。** 验收消息预告并提示 `/compact`；0.63.2 起 NEEDS_SPEC 达到边界档也会出边界提示。
- **规则只靠 agent 遵守。** 与其他检查点规则一样不加机械检查；发版后真实会话观察，效果不好再议。

## Open Questions

- 无。
