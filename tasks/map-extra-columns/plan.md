# Plan: map-extra-columns

<!-- spec-guard: review approved -->

依据 [`spec/map-extra-columns.md`](../../spec/map-extra-columns.md)（2026-11-09 用户在本会话批准：「批准」，能力图新行同时确认写入）。
分支 `claude/map-extra-columns`（从 `origin/main` `5ae54858` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.86.7。

## Overview

先在 `test_module_insert.py` 写四列、五列、三列能力图的用例，确认在 0.86.6 上失败；再改 `module-insert.py` 的 `preview` 与
`format_report`。随后补三处说明，改版本号与 CHANGELOG，交最终验收。

## Architecture Decisions

1. **表头从 `_module_table_rows` 已找到的那一行取**：它已在去掉围栏的视图里定位模块表表头；把表头的格子一并返回（或在 `preview`
   里用同一行号读），额外列名 = 表头第 4 格起的各格。不另写一个找表头的函数。
2. **新行**：`"| %s | %s | %s |" % (...)` 后，每个额外列追加 `"  |"`，即 `| id | 职责 | 依赖 |  |`。三列时字符串与 0.86.6 相同。
3. **预览说明**：`preview` 结果多一个 `extra_columns`（列名列表）；`format_report` 在「新行」那一行之后、空行之前，列表非空时打印
   ``额外列 `本轮状态` 留空，需要时自己填``（多列用「、」连接）。写入（`write`）复用 `preview`，不另改。
4. **说明（S68）**：`commands/map.md` 状态图例那段、`docs/commands.md` 的 map 段落、`docs/concepts.md` 术语表各补一句。
5. **发版**照 0.86.6：合并后核对、打 tag（遇 500 改在你的终端推）、打包、Release、两个宿主核对（Codex 在新开 CLI 的提示里批 hook；
   会话窗口没开时直接给终端标签链接）、证据收尾 PR（用 REST 开 PR）、回告 ecosystem-lead（回复 #19453）。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：额外列补空格与预览说明（假设 1–3）

- 文件：`hooks/module-insert.py`、`hooks/test_module_insert.py`。
- 用例：四列（已有行有值）预览成功、新行第四格空、预览含说明，`--confirm` 后严格校验通过且已有行摘要不变；五列两列都留空、说明列出两列；
  三列新行与预览不含说明。
- 验证：新用例在 0.86.6 上失败、改后通过；`test_module_insert.py` 全部通过。

### Task 2：「可以开始」的说明（假设 4）

- 文件：`commands/map.md`、`docs/commands.md`、`docs/concepts.md`。
- 验证：`validate.sh --quick` 通过。

### Task 3：版本号与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、README 中英 `--ref`、`CHANGELOG.md`（0.86.7：修复、文档）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；`evals/codex-plugin-smoke.sh --selftest`。
- 变异（草稿副本）：去掉补齐、去掉说明行，两处都要让测试变红；临时项目用四列能力图从命令行跑一次预览与 `--confirm`。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、成功标准证据、改动表、提交表、Spec 中途改动（如有）、拟回告原文。通过即同时授权：推送、开 PR；你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对合并、打 `v0.86.7`、打包、Release、比对 SHA-256；刷新并核对 Claude 与 Codex 安装副本；收尾扫描、证据收尾 PR；回告 ecosystem-lead。任一步失败就停下说明。

## Files likely touched

- 插件包：`hooks/module-insert.py`、`hooks/test_module_insert.py`、`commands/map.md`、两份 `plugin.json`
- 仓库：`docs/commands.md`、`docs/concepts.md`、`README.md`、`README.en.md`（只改 `--ref`）、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.86.7-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/map-extra-columns.md`、本 Plan、`tasks/map-extra-columns/todo.md`
- 新增依赖、锁文件改动：无。不碰 `capability_map.py`、`spec-digest.py`、`map_view.py`、`interface.json`。

## 风险

- **行摘要**：新行带空格子，已有行不动；`preview` 现有的「已有行摘要不变」校验会兜住，四列用例再显式断言一次。
- **表头格子里有反引号或空格**：说明里原样用表头文字（去掉首尾空白）；列名来自仓库文件，只用于预览文字。
