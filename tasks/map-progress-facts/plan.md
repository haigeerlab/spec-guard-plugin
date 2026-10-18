# Plan: map-progress-facts

<!-- spec-guard: review approved -->

依据 [`spec/map-progress-facts.md`](../../spec/map-progress-facts.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan 单独
交审。分支 `claude/map-progress-facts`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `d7026bc`（#366 合并）开出。
本模块一个 PR，含 0.73.0 版本号；合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动；Task 4 在本仓库与临时 git 仓库实跑。

## Overview

先用测试固定四项事实的判定（临时 git 仓库、固定提交时间），再实现，再改接口说明，最后接文档与版本号。新代码是
`map_view.py` 里与 `history()` 并列的一个函数，读不出 git 时只让这几项为 `null`，不影响其余输出与退出码。

## Architecture Decisions

- **未提交勾选用一次 `git diff HEAD -U0 -- ':(glob)tasks/*/todo.md'`**，沿用 `history()` 的 `DIFF_FILE`／`CHECKED_LINE` 计增删差；
  未跟踪的 todo 用一次 `git ls-files --others --exclude-standard -- tasks/` 找出，按工作区勾选数计。不逐模块调用 git。
- **`startedAt` 用一次 `git log --diff-filter=A --format=<分隔符>%cI --name-only -- ':(glob)spec/*.md'`**，每个文件取最早一次。
- **`head.committedAt`** 加在 `_head()` 里，一次 `git log -1 --format=%cI`。
- **`reviewCadence`** 直接取 `project_config.summary()` 里 `key == "reviewCadence"` 那一项的 `value` 与 `source`，不另写读配置的逻辑。
- **表格只改 `_status_cell` 的进行中分支**；为 0 或 `null` 时走原有分支，保证逐字不变。

## Task List

### Task 1：四项事实与表格的测试（先红）

在 `test_map_view.py` 新增 `ProgressFactsTest`，覆盖 Spec Testing strategy 各项：多勾 3 项未提交、全部提交后为 0 且表格逐字回到
原样、取消勾选为 0、未跟踪 todo、非 git 为 `null`、`startedAt` 已提交／未提交、`head.committedAt` 有提交／无提交、`reviewCadence`
三种配置；`test_key_sets_are_fixed` 与 `test_off_keeps_the_fixed_key_sets` 的键集合加上新字段。

- 验收：新用例在旧代码上失败；原有用例期望值除键集合外不改。
- 验证：`python3 -B plugins/spec-guard/hooks/test_map_view.py`。
- 文件：`hooks/test_map_view.py`。

### Task 2：实现

`map_view.py` 加未提交勾选与开工时间的读取、`head.committedAt`、顶层 `reviewCadence`、进行中状态格的那一句。

- 验收：Task 1 全绿；两处变异各有断言变红：不把负数记为 0、未跟踪 todo 按 0 计；本仓库实跑耗时与改动前同一量级。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/map_view.py`。

### Checkpoint 1（report）：map 回归全绿

### Task 3：接口说明

`interface.json` 升到 1.2，`mapView` 下加 `progressFacts` 一节（四项含义、`null` 的情形、"事实不含阈值"），改 concurrency 一节
"与 1.0 逐字相同"的说法；`scripts/check-interface.py` 加一条：`progressFacts` 列出的字段名与 `map_view.py` 输出的一致。

- 验收：新断言先红后绿；`scripts/test-checkers.sh` 通过。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`plugins/spec-guard/interface.json`、`scripts/check-interface.py`（及它的检查器回归，如需要）。

### Task 4：文档、实跑、CHANGELOG 与版本号

`commands/map.md`、`spec-guard-ops` 的 map 一节、`docs/commands.md`、`docs/design.md` 写明新字段；在本仓库与一个"勾了没提交"的
临时 git 仓库实跑表格与 JSON，结果记入 todo；CHANGELOG 新增 `[0.73.0]`；两份 `plugin.json` 改为 0.73.0，中英 README 的
`--ref` 改为 v0.73.0。

- 验收与验证：`verify-and-commit.sh` 全档；实跑命令写入 todo。
- 文件：上述文档、CHANGELOG、两份 `plugin.json`、两份 README。

### Checkpoint 2（gate）：最终验收

按 AC1–AC6 逐条给证据（测试名与结果、实跑输出），展示未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，
合并由用户进行；把新增字段发给 module-crew 与 decision-inbox 核对，也在此由用户确认后再发。

## Risks

- **工作区 todo 与 HEAD 都改了但勾选数相同**（比如勾一项、取消另一项）：记 0。只报净增，Spec 已写明。
- **`git diff HEAD` 在没有提交的仓库里失败**：归入 `history` 为 `unavailable` 的情形，几项为 `null`，不报错。
- **配置无效时 `reviewCadence` 的 source**：取 `summary()` 的原样输出（`default (config invalid)`），不另造取值。
