# Plan: rules-in-context

<!-- spec-guard: review approved -->

依据 [`spec/rules-in-context.md`](../../spec/rules-in-context.md)。本仓库评审节奏为分开审：Spec 已单独批准，本 Plan 单独交审。
分支 `claude/rules-in-context`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `b3ae14e`（v0.63.3 发版证据合并）开出。
本模块一个 PR，含 0.63.4 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

一个钩子判断（先红后绿），一组模板行（先红后绿），文档、CHANGELOG 与版本号。

## Architecture Decisions

- **“已到最终验收”只在 `module_stage.py` 里判断一次**，复用 `next_gate` 的检查点识别（同一个 `OPEN_CHECKPOINT`、`CHECKPOINT_TIER`），
  不另写一套解析；读不了或认不出时返回“不是”，回到现行提示。
- **模板行与规则文件同义，不复制细则**：一行一条，说清要做什么；两份模板措辞一致，只有命令写法按宿主区分。

## Task List

### Task 0：提交已批准的产物

能力图新行、已批准的 Spec、本 Plan 与 todo 一次提交。

- 验收：`verify-and-commit.sh` 快档通过并提交。

### Task 1：最终验收时的修订提示（先红）

`test-phase-guard.sh` 新增一段 4 例：Spec 已修订 + 只剩最终 gate（其后有“发版后的验证”非检查点项）→ 新建议；已修订 + 还有未勾 task →
现行建议逐字不变；已修订 + 只剩一个 gate 但其后还有别的 gate → 现行建议；todo 不可读 → 现行建议。先跑红，再在 `module_stage.py`
加判断并改建议文字，转绿。

- 验收：新例全绿，现有 phase-guard 用例不改；变异（判断恒为假）新建议那例变红；ShellCheck 无警告（若改 `.sh`）。

### Task 2：约定块模板三行（先红）

`test_workflow_checkpoints.py` 新增断言：两份 `*-block-local.md` 与 `docs/convention-block.md` 含三行的关键词（“确认框之前”“附上 Spec
的改动差异”“直接写它的 Spec”）。先跑红，再在两份模板与约定块文档里各新增三行，现有行不改，转绿。在临时项目先用 0.63.3 装约定块，再用
工作区版本 `setup-convention local --replace`（Claude 与 `--host=codex` 各一次），确认退出 0、新行已写入、不需 `--accept-removals`。

- 验收：规则测试与 `test-setup-teardown.sh` 全绿；`--replace` 两边退出 0。

### Checkpoint 1（report）：三套核心回归、规则测试与 setup-teardown 回归全绿，ShellCheck 无警告

随 Task 2 的提交跑 `verify-and-commit.sh` 全档。

### Task 3：文档、CHANGELOG 与版本号

`docs/workflow.md` 一句话说明升级后已装项目跑一次 `setup-convention --replace` 才能拿到新行；CHANGELOG `[0.63.4] - 2026-10-16`；两份
`plugin.json` 改为 0.63.4；README 中英 `--ref` 改为 v0.63.4。

- 验收：`validate.sh` 通过。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

在正文列出实际改动的文件（取自版本库）、新增的模板三行与新建议原文、验证结果、未验证项、文档建议与拟回告（对象：会话
「Spec/Guard 插件使用观测」`local_3b05d344-963e-4750-8edb-83b08ad9d0ca`；渠道：宿主会话消息；时机：0.63.4 装上之后）。

- 验收：用户确认推送与开 PR。

### 发版后的验证

两边升级到 0.63.4；Claude Code 与 Codex 各在“Spec 已修订、只剩最终 gate”的临时项目（约定块用 0.63.4 装）跑一轮真实会话，看阶段提示
的新建议是否出现、验收消息是否附差异并说明一次批准。如实记录，回告观测会话，结果记在本项。

## 影响面

`plugins/spec-guard/hooks/module_stage.py`、`test-phase-guard.sh`、`test_workflow_checkpoints.py`、`templates/claude-block-local.md`、
`templates/codex-block-local.md`、`docs/convention-block.md`、`docs/workflow.md`、CHANGELOG、两份 `plugin.json`、README 中英，以及本模块的
Spec、Plan、todo 与能力图。

## Risks and Mitigations

- **“只剩最终 gate”判错。** 只认未勾的检查点与其前后项，认不出就回现行提示；4 例覆盖边界。
- **约定块变长。** 只加三行；之后若再加规则，考虑精简已有行（另议）。
- **已装项目拿不到新行。** 阶段提示那处修改不依赖模板，升级即生效；文档写明跑一次 `--replace`。

## Open Questions

- 无。
