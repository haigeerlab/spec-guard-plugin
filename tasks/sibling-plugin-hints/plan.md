# Plan: sibling-plugin-hints

<!-- spec-guard: review approved -->

依据 [`spec/sibling-plugin-hints.md`](../../spec/sibling-plugin-hints.md)。本仓库评审节奏为分开审：Spec 已单独批准，本 Plan 单独交审。
分支 `claude/sibling-plugin-hints`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `707841a`（v0.64.0 发版证据合并）开出。
本模块一个 PR，含 0.64.1 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

一组模板行（先红后绿），文档同步、CHANGELOG 与版本号。不改钩子、阶段提示、判据与指纹。

## Architecture Decisions

- **两行紧跟各自相关的现有行**：delegate 一行放在「交审 Spec 或 Plan 时……」之后，agent-relay 一行放在「回告来源」之后；现有行
  一字不改，`git diff` 对模板只能出现新增行。
- **入口按宿主写，措辞其余一致**：Claude 写 `/delegate:review`，Codex 写 `$delegate-routing`、`$session-routing`（本机两边已装
  副本核实过的技能名）。

## Task List

### Task 0：提交已批准的产物

能力图新行、已批准的 Spec、本 Plan 与 todo 一次提交。

- 验收：`verify-and-commit.sh` 快档通过并提交。

### Task 1：约定块模板两行（先红）

`test_workflow_checkpoints.py` 新增 1 例：两份 `*-block-local.md` 与 `docs/convention-block.md` 含 `若装了 delegate 插件`、`只读审查`、
`不算用户批准`、`若装了 agent-relay 插件`；Claude 模板与约定块文档含 `/delegate:review`，Codex 模板含 `$delegate-routing` 与
`$session-routing`。先跑红，再在两份模板与约定块文档里各新增两行，转绿。变异：删掉 Codex 模板的 delegate 一行，断言变红后复原。
临时项目先用 0.64.0 装约定块，再用工作区版本 `setup-convention local --replace`（Claude 与 `--host=codex` 各一次），确认退出 0、
两行已写入、不需 `--accept-removals`。

- 验收：规则测试与 `test-setup-teardown.sh` 全绿；`--replace` 两边退出 0；模板 diff 只有新增行。

### Checkpoint 1（report）：三套核心回归、规则测试与 setup-teardown 回归全绿

随 Task 1 的提交跑 `verify-and-commit.sh` 全档加 `--suite setup-teardown`。

### Task 2：CHANGELOG 与版本号

CHANGELOG `[0.64.1] - <合并日>`「新增」一条（两行提示、只在装了插件时适用、已装项目跑一次 `setup-convention --replace` 拿到新行）；
两份 `plugin.json` 改为 0.64.1；README 中英 `--ref` 改为 v0.64.1。

- 验收：`validate.sh` 通过。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

在正文列出实际改动的文件（取自版本库）、新增两行原文（两边）、验证结果、未验证项、文档建议（无，README 不加，用户已定）。
需求来自用户本人，无需回告其他会话。

- 验收：用户确认推送与开 PR。

### 发版后的验证

两边升级到 0.64.1；Claude Code 与 Codex 各在装了 delegate 与 agent-relay、约定块用 0.64.1 装的临时项目里跑一轮到 Spec 交审，
看 agent 是否提议一次 delegate 只读审查、且没有自行发起。如实记录，结果记在本项。

## 影响面

`plugins/spec-guard/templates/claude-block-local.md`、`templates/codex-block-local.md`、`hooks/test_workflow_checkpoints.py`、
`docs/convention-block.md`、CHANGELOG、两份 `plugin.json`、README 中英，以及本模块的 Spec、Plan、todo 与能力图。

## Risks and Mitigations

- **agent 每次交审都提议，显得啰嗦。** 行内写明「值得另一个 agent 复核时」与「拒绝过就不再提」；发版后的真实会话看频率，太多再收紧。
- **技能名以后改了。** 只写入口名一处，断言会在改名后提醒同步；插件本身的技能描述仍会被用户措辞触发，不依赖这一行。
- **已装项目拿不到新行。** CHANGELOG 写明跑一次 `--replace`。

## Open Questions

- 无。
