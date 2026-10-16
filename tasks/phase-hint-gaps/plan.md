# Plan: phase-hint-gaps

<!-- spec-guard: review approved -->

依据 [`spec/phase-hint-gaps.md`](../../spec/phase-hint-gaps.md)。本仓库评审节奏为分开审：Spec 已单独批准，本 Plan 单独交审。
分支 `claude/phase-hint-gaps`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `06a0643`（#323 docs-refresh 合并）
开出。本模块一个 PR，含 0.63.2 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。Task 4 的 `/reload-plugins` 实测在发版后的真实 Claude Code 会话里做。

## Overview

三处钩子判断各一个任务（先红后绿），一个文档与版本任务。全部改动在 `phase-guard.sh`、`module_stage.py` 与它们的回归里；
`session_context.py` 不改（它对 `compact_boundary` 的处理没错，错在 SessionStart 时这条记录还没写入）。

## Architecture Decisions

- **D6 在 `phase-guard.sh` 处理。** 它已经知道事件（`EVENT=SessionStart`），在那里把传给 `module_stage.py` 的大小设为 0，
  比让 `session_context.py` 猜“是不是刚压缩”简单，也不影响 UserPromptSubmit。
- **D5 复用 `boundary_line`。** `NEEDS_SPEC` 达到边界档时调用同一个函数，文字与 `MODULE_DONE` 完全一样；只改出行的条件。
- **D1 用 `module_stage.py` 新增的只读入口取配置行。** 例如 `module_stage.py --config-lines`，内部就是现有的 `config_lines`；
  shell 不解析 JSON、不复制判断。取不到（非零退出或空）时什么都不加。

## Task List

### Task 0：提交已批准的产物

能力图新行、已批准的 Spec、本 Plan 与 todo 一次提交。

- 验收：`verify-and-commit.sh` 快档通过并提交。

### Task 1：D6 压缩后那一次不报大小（先红）

`test-phase-guard.sh` 加例：记录文件末尾是一条 900k 的用量（没有 `compact_boundary`），以 `SessionStart` 运行 → 输出没有
`Session context:`、没有 `Module boundary:`，有 `Context was just compacted`；同一记录以 UserPromptSubmit 运行 → 照旧有上下文行。
Claude 与 Codex（带窗口）各一组。先跑红，再在 `phase-guard.sh` 中 SessionStart 时把大小设为 0。

- 验收：新例全绿；现有压缩相关用例（`compact_boundary`、Codex `compacted`）逐字不变；变异（去掉置 0）新例变红。

### Task 2：D5 没开工的当前模块也给边界行（先红）

`test-phase-guard.sh` 加例（Claude 默认窗口与 Codex 窗口各一组）：`NEEDS_SPEC` + 600k → 只有带大小的边界行、没有上下文行；
`NEEDS_SPEC` + 100k → 都没有；`NEEDS_SPEC` 读不到大小 → 都没有（现有“NEEDS_SPEC 没有模块完成行”保持）；`NEEDS_PLAN`、
`BUILDING` + 600k → 都没有；`BUILDING` + 850k → 上下文行照旧；无人值守 `NEEDS_SPEC` + 600k → 都没有。先跑红，再改
`module_stage.py` 出行条件。

- 验收：新例全绿；`MODULE_DONE`／`DONE` 现有用例逐字不变；变异（条件改回只认 `MODULE_DONE`）新例变红。

### Task 3：D1 IDLE 与 MAP_ONLY 带配置行（先红）

`test-phase-guard.sh` 加例：IDLE、MAP_ONLY 各一例设 `artifactLanguage`（有那一行）、一例 `combined`（有节奏行）、一例无效配置
（有 invalid 行）、一例无配置（与现有用例逐字相同）。先跑红，再给 `module_stage.py` 加只读入口、在 `phase-guard.sh` 两处输出前
接上；入口失败时不加行。

- 验收：新例全绿；现有 IDLE、MAP_ONLY 用例逐字不变；变异（入口返回空）新例变红；ShellCheck 无警告。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告

随 Task 3 的提交跑 `verify-and-commit.sh` 全档。

### Task 4：文档、能力图文字、CHANGELOG 与版本号

- README 中英「更新与卸载」与 `docs/troubleshooting.md`：Claude Code 升级插件后新开会话才会用新版本（`/reload-plugins` 待发版后实测，
  先写“新开会话”；实测结论在发版验证里补）。
- 能力图 `docs-refresh` 行改为“去掉会过时的命令总数”，能力图「变更记录」追加一行（来源：用户本人）。
- `docs/design.md` 写明 SessionStart 时不读用量、`NEEDS_SPEC` 的边界行、IDLE／MAP_ONLY 的配置行。
- CHANGELOG `[0.63.2] - 2026-10-16`；两份 `plugin.json` 改为 0.63.2；README 中英 `--ref` 改为 v0.63.2。

- 验收：`validate.sh` 通过。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

列出实际改动的文件（取自版本库）、验证结果、未验证项、文档建议与拟回告（对象：会话「Spec/Guard 插件使用观测」
`local_3b05d344-963e-4750-8edb-83b08ad9d0ca`；渠道：宿主会话消息；时机：0.63.2 发布并装上之后）。

- 验收：用户确认推送与开 PR。

### 发版后的验证

两边宿主升级到 0.63.2，各在真实会话里手动压缩一次，看注入不再报旧大小；Claude Code 测 `/reload-plugins` 后命令是否改用新版本，
按结果补文档；按批准的内容回告观测会话，结果记在本项。

## 影响面

`plugins/spec-guard/hooks/phase-guard.sh`、`module_stage.py`、`test-phase-guard.sh`；README 中英、`docs/troubleshooting.md`、
`docs/design.md`、CHANGELOG、两份 `plugin.json`、`spec/CAPABILITY-MAP.md`，以及本模块的 Spec、Plan、todo。

## Risks and Mitigations

- **NEEDS_SPEC 边界行每轮重复。** Spec 假设 3 已接受；与 `MODULE_DONE` 现状一致。
- **SessionStart 置 0 掩盖真实的大上下文。** 压缩刚发生，大小必然已降；下一轮 UserPromptSubmit 照常读取，最多晚一轮。
- **新入口让 IDLE／MAP_ONLY 多一次 python 调用。** 只在已激活项目运行，失败即降级，不影响阶段输出。

## Open Questions

- 无。
