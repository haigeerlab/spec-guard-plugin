# Plan: convention-block-blank-lines

<!-- spec-guard: review approved -->

依据 [`spec/convention-block-blank-lines.md`](../../spec/convention-block-blank-lines.md)（已批准）。本仓库评审节奏为分开审：Spec 已批准，本 Plan 单独交审。
分支 `claude/convention-block-blank-lines`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `3f4e54f`（0.71.0 发版收尾）开出。
本模块一个 PR，含 0.71.1 版本号；发版后另开一个收尾 PR 放证据。

所需工具：无 UI 改动；oxfmt 人工核对用使用方项目已装的可执行文件，只在临时目录里跑，不碰那个项目。

## Overview

只改 `hooks/managed-block.py` 的 `replace`、`hooks/setup-convention.sh` 的新建块拼接、两份派活规则段模板与 `hooks/test-setup-teardown.sh`。
新建与替换都按 Spec 的 Contract 写出「每条标记前后一个空行」的块；`--dry-run` 报空行变化；teardown 不改。

## Architecture Decisions

- **只在一处组装块正文。** `managed-block.py` 增加一个 `compose` 动作：输入模板正文文件与（可选）本地段，输出按 Contract 拼好的块内正文；
  `replace` 用它组装，`setup-convention.sh` 新建块时也调用它，两处写法不会分叉。
- **模板首尾空行一律去掉再组装**，所以模板本身多一行少一行空行不影响结果；派活规则段的注释行后加空行，是为了模板单独查看时也符合规则。
- **teardown 不动。** 新写法的块整个在 BEGIN…END 之间，卸载时连同内侧空行一起删掉；块外的空行处理与现在相同，往返仍逐字节还原。

## Task List

### Task 0：提交已批准的 Plan 与 todo

- 验收：`verify-and-commit.sh` 快档通过并提交。
- 文件：`tasks/convention-block-blank-lines/plan.md`、`todo.md`。

### Task 1：回归先红

在 `test-setup-teardown.sh` 里（Claude 与 Codex 两边各一遍）：

- 新建块（派活关／开；空文件与已有内容的文件）：每条标记前后各一个空行；块正文等于按 Contract 拼出的内容；
- 旧写法（无空行，用当前代码写出的块）`--replace --dry-run` 输出 `will adjust blank lines: add N, remove 0`，没有 `needs --accept-removals`；写入后与新建块逐字节相同；
- 新写法再 `--replace --dry-run` 输出 `block content unchanged`，写入后逐字节不变；
- 带本地段：本地段内部原样、前后各一个空行；本地段内部已有空行时再 `--replace` 逐字节不变；
- 原有 setup→teardown 往返（派活关／开、有本地段）继续逐字节还原。

现有按「模板原样拼接」断言块正文的用例（`block_is` 一组）按新写法改写期望值。先确认新断言失败。

- 验收：新断言在当前代码上失败，原有其余用例通过。
- 文件：`hooks/test-setup-teardown.sh`。

### Task 2：实现

- `managed-block.py`：新增 `compose`；`replace` 用它组装，`--dry-run` 比较新旧块空行数并输出 `will adjust blank lines: add N, remove M`，逐字节相同才输出 `block content unchanged`；
- `setup-convention.sh`：新建块与 `--replace` 都经 `compose`；
- 两份 `*-dispatch-rule.md`：注释行后加一个空行。

- 验收：`test-setup-teardown.sh` 全绿；`validate.sh` 通过。
- 文件：`hooks/managed-block.py`、`hooks/setup-convention.sh`、`templates/claude-dispatch-rule.md`、`templates/codex-dispatch-rule.md`。

### Task 3：oxfmt 人工核对

在临时目录用工作区版本 `setup-convention local`（Claude 与 `--host=codex`，派活关／开，带一个本地段）建块，再用使用方项目已装的 oxfmt 跑 `--check`：
退出码 0。再用 0.71.0（`git archive v0.71.0`）建一个旧写法的块，跑工作区版本 `--replace --dry-run` 与实际写入，确认预览与写入一致、写入后 `--check` 通过。结果记进 todo，临时目录跑完即删。

- 验收：上述都符合预期。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警

### Task 4：CHANGELOG 与 0.71.1 版本号

CHANGELOG `[0.71.1]`（本版 1 个模块，修复）；两份 `plugin.json` 改为 0.71.1，中英 README 的 `--ref` 改为 v0.71.1。如有说明 `--replace` 预览输出的文档（`commands/setup-convention.md`），补一句空行变化的那一行。

- 验收：`validate.sh` 通过。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

列出实际改动、验证结果与未验证项；拟回告：发版后告诉接入协调人版本号（原生会话消息，草稿先给用户看）。

### 发版后的验证

PR 合并后按 `docs/release-process.md` 发 0.71.1：tag、发布包、Release、两边宿主升级与 Codex smoke、证据 JSON；用安装版 `setup-convention` 在临时项目建块并跑一次 `oxfmt --check`。
然后在账本里关闭 8AB0R0B，按批准的草稿回告接入协调人。
