# Plan: boundary-hint-unknown-size

<!-- spec-guard: review approved -->

依据 [`spec/boundary-hint-unknown-size.md`](../../spec/boundary-hint-unknown-size.md)。本项目按分开审：Spec 已于 2026-10-19 批准，
本 Plan 单独交审。分支 `claude/boundary-hint-unknown-size`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 main 的
`24a7e9e`（#369 合并）开出。本模块一个 PR，含 0.76.0 版本号；按用户决定，发版等这一批做完、冻结前一次发。

所需工具：无 UI 改动。

## Overview

代码只改 `module_stage.py` 的一个分支；工作量在回归：原来很多用例借"读不到大小"这一情形检查模块之间的边界行（判定在哪些阶段出、
文字是什么）。这些用例改为喂一份达到边界档的会话记录、断言带大小的那一行，覆盖不减；另加"读不到就不出"的用例。

## Architecture Decisions

- **`boundary()` 辅助函数改为喂会话记录**：用已有的 `transcript` 夹具写 700k（等于边界档）的记录，期望 `sized_boundary 700 …`
  那一行，9 个调用点（MODULE_DONE、DONE、有暂停模块、缺 todo、领先主线等）不用逐个改，继续验证"哪些阶段出边界行"。
- **新增 `no_boundary_when_unknown` 一组**：不给会话记录时断言没有 `Module boundary`／`模块边界` 行，也没有 `Session context` 行；
  覆盖 Claude、Codex、判断不了宿主、zh-CN。
- **文字检查改用带大小的行**：Codex 的 `/compact` 写法与斜杠命令说明（`test-phase-guard.sh` 约 1195–1203 行）、中文 DONE 那一例、
  无人值守对照（约 871 行）都改为喂会话记录，断言内容不变，只是从不带大小的那句换成带大小的那句。
- **不动 `BOUNDARY` 常量的其他用途**：第 698 行"每一行只出现一次"的循环里如果还用到它，按新行为改为只检查带大小的两行。

## Task List

### Task 1：回归先行

按上面的决定改 `test-phase-guard.sh`：`boundary()` 改喂记录、新增"读不到不出"一组、文字检查改用带大小的行、第 787 行
"DONE 读不到大小时保持现行 Module boundary 行"改为"……不出边界行"。

- 验收：在旧代码上只有"读不到不出"的新用例与第 787 行那一例失败；改喂记录的用例在旧代码上就是绿的（证明文字覆盖没丢）。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`。
- 文件：`hooks/test-phase-guard.sh`。

### Task 2：改分支

`module_stage.py`：`context_tokens is None` 时 `boundary_note_line = ""`，删掉这一分支里内联的中英两句。

- 验收：phase-guard 全绿；变异（恢复原分支）时 Task 1 的新用例变红。
- 验证：`verify-and-commit.sh` 全档（暂存了 `.sh`，加 ShellCheck）。
- 文件：`hooks/module_stage.py`、`hooks/test-phase-guard.sh`。

### Checkpoint 1（report）：phase-guard 全绿

### Task 3：CHANGELOG 与版本号

CHANGELOG 新增 `[0.76.0]`，写明行为变化与原因；两份 `plugin.json` 改为 0.76.0，中英 README 的 `--ref` 改为 v0.76.0。

- 验收与验证：`verify-and-commit.sh` 全档。
- 文件：`CHANGELOG.md`、两份 `plugin.json`、两份 README。

### Checkpoint 2（gate）：最终验收

按 AC1–AC4 逐条给证据，展示未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- **Task 1 与 Task 2 不能分开提交**：新用例在旧代码上是红的，提交脚本检查整个工作区，所以两者一个提交（与模块 ③ 同样的处理）。
- **改喂记录后某些用例意外出现模块中途的 `Session context` 行**：700k 低于 80% 的 800k，模块中途不会出；如有用例落在 BUILDING
  阶段，按断言实际结果调整夹具，不改产品代码。
- **真实宿主里第一轮以外也读不到**：Spec 已接受少提示一次的代价；发版后在两边宿主各开一个新会话核对第一轮不再出现这一行。
