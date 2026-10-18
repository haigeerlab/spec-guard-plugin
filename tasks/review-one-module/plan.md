# Plan: review-one-module

<!-- spec-guard: review approved -->

依据 [`spec/review-one-module.md`](../../spec/review-one-module.md)（已批准）。本仓库评审节奏为分开审：Spec 已批准，本 Plan 单独交审。
分支 `claude/review-one-module`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `bd37cde` 开出，已合入 0.70.1 发版收尾后的 main（`0715b13`）。
能力图新行与 Spec 已在 `ecabea2` 提交。本模块一个 PR，含 0.70.2 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动；发版后的真实会话用 tmux 驱动的交互 Claude 会话与 `codex exec`。

## Overview

只改文字：共享检查点规则四处（新增「一次交审只放一个模块」一条、收紧「按需求批量前置审」、改「返工与小模块」一句、「协调会话的批准与合并」补一句），
两份约定块模板与 `docs/convention-block.md` 各新增一行，`docs/workflow.md` 补一句，CHANGELOG 与版本号。钩子、命令、阶段判定不动。

## Architecture Decisions

- **规则只有一个出处。** 分组写法只写在新增的那一条里，另外三处都指向它，不各写一遍。
- **模板只新增行。** 现有行一字不改，`setup-convention --replace` 不需要 `--accept-removals`。
- **现有断言不删。** 「按需求批量前置审」现有的断言（`activeModule`、`80%`、`不自行开新会话` 等）原样保留，收紧只改第一段。

## Task List

### Task 0：提交已批准的 Plan 与 todo

- 验收：`verify-and-commit.sh` 快档通过并提交。
- 文件：`tasks/review-one-module/plan.md`、`tasks/review-one-module/todo.md`。

### Task 1：规则与模板行（先红）

`test_workflow_checkpoints.py` 先加断言并确认失败：
- 新一条含「一次交审只放一个模块」「一起发版」「按模块分组」「Build order」「不按产物类型」「不主动提议」「能力图评审」；
- 「按需求批量前置审」含「只在用户明确要求时」；
- 「返工与小模块」含「用户也要求一次审完时」，并且不再出现「确需各自成模块时，用「按需求批量前置审」一次交审」；
- 「协调会话的批准与合并」含分组那一句；
- 两份模板与约定块文档含新增行。

再改 `references/workflow-checkpoints.md`、两份模板与 `docs/convention-block.md`。

- 验收：规则测试全绿；`git diff` 显示两份模板只有新增行。
- 文件：`references/workflow-checkpoints.md`、`templates/claude-block-local.md`、`templates/codex-block-local.md`、`docs/convention-block.md`、
  `hooks/test_workflow_checkpoints.py`。

### Checkpoint 1（report）：三套核心回归全绿

### Task 2：文档、CHANGELOG 与 0.70.2 版本号

`docs/workflow.md` 讲交审的地方补一句；CHANGELOG `[0.70.2]`；两份 `plugin.json` 改为 0.70.2，中英 README 的 `--ref` 改为 v0.70.2。
另核对：先装 0.70.1 的约定块，再用工作区版本 `setup-convention --replace`（Claude 与 `--host=codex` 各一次），退出码为 0、新行已写入。

- 验收：`validate.sh` 通过；两次 `--replace` 退出码 0。
- 文件：`docs/workflow.md`、`CHANGELOG.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、
  `README.md`、`README.en.md`。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

列出实际改动、验证结果与未验证项；拟回告：无（本模块由用户本人提出）。

### 发版后的验证

0.70.2 发版后两边宿主各跑一次：临时项目的能力图里有两个未开工的模块，提示词只说「把这两个模块做了」，不提怎么审；看 agent 是否只交第一个模块的
Spec，而不是把两份 Spec 一起交。结果如实写进 0.70.2 证据。
