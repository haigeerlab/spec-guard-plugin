# Plan: map-gate-count

<!-- spec-guard: review approved -->

依据 [`spec/map-gate-count.md`](../../spec/map-gate-count.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan 单独交审。
分支 `claude/map-gate-count`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `550ab7c7`（#372 合并）开出。
本模块一个 PR，含 0.77.0 版本号；合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动；Task 4 在本仓库与临时项目实跑。

需要的外部条件：无（不装依赖、不联网；只用仓库已有的 `python3`、`git` 与检查脚本）。

## Overview

先把 gate 判据抽成共用函数并用现有回归证明行为不变，再用测试固定 `gates` 的取值，再实现，再改接口说明，最后接文档与版本号。

## Architecture Decisions

- **共用判据**：`module_stage.py` 加 `checkpoint_tier(line) -> (is_checkpoint, is_gate, checked)` 一类的小函数（名字以实现为准），
  识别 `[ ]` 与 `[x]／[X]` 两种勾选状态；`_open_gate` 与 `next_gate` 改为调用它，`map_view.py` 的 `gates` 也调用它。
  现有 `OPEN_CHECKPOINT` 只匹配未勾项，新函数用同一个 `Checkpoint(?![A-Za-z])` 与 `CHECKPOINT_TIER`，不新写第二套正则。
- **`gates` 在构造模块记录时算**：`map_view.py` 已经为每个模块读一次 `todo.md`（`_read`），直接在同一份文本上数；todo 不存在
  （`path.is_file()` 为假）时为 `null`。不增加文件读取与 git 调用。
- **`PROGRESS_FIELDS` 加 `gates`**：`check-interface.py` 的 `_progress_facts()` 已按这个常量核对 `interface.json`，加进去后缺说明
  即报错，无需改检查器逻辑。

## Task List

### Task 1：抽出共用判据（行为不变）

把 gate 判据抽成 `module_stage.py` 的共用函数，`_open_gate`、`next_gate` 改为调用它。

- 验收：`test-phase-guard.sh`、`test_map_view.py`、阶段提示相关回归全绿，期望值一个不改；一处变异（让共用函数把 report 也算
  gate）有现有断言变红，证明判据被测到。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/module_stage.py`。

### Task 2：`gates` 的测试（先红）

在 `test_map_view.py` 新增 `GateCountTest`，覆盖 Spec Testing strategy 各项：标 gate＋未标级别＋report、勾掉一个 gate →
`{2, 1}`；全勾；无检查点 → `{0, 0}`；无 todo → `null`；大写 `[X]`；非 git 仓库仍有值；`Checkpointing` 不算；各处键集合加 `gates`。

- 验收：新用例在旧代码上失败；原有用例期望值除键集合外不改。
- 验证：`python3 -B plugins/spec-guard/hooks/test_map_view.py`。
- 文件：`hooks/test_map_view.py`。

### Task 3：实现与接口说明

`map_view.py` 在模块记录里加 `gates`，`PROGRESS_FIELDS` 加 `gates`；`interface.json` 升到 1.3，`progressFacts.fields` 加 `gates`
的说明（含义、`null` 的情形、判据、「最终验收通常是最后一个 gate，已在 total 里，基准不要再单独加」），`appearsWhen` 写 1.3；
`test-checkers.sh` 加一条缺 `gates` 说明即报错的反例。

- 验收：Task 2 全绿；先只改代码常量、不改 `interface.json` 时检查器报错，补上说明后通过；一处变异（`done` 不认大写 `X`）有断言变红；
  进度表输出与改动前逐字相同（现有表格用例不改即证明）。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/map_view.py`、`interface.json`、`scripts/test-checkers.sh`。

### Checkpoint 1（report）：map 与接口回归全绿

### Task 4：文档、实跑、CHANGELOG 与版本号

`commands/map.md`、`spec-guard-ops` 的 map 一节、`docs/commands.md` 写明 `gates`；在本仓库与一个临时项目（两个 gate、一个
report、勾一个 gate）实跑 JSON，结果与本仓库耗时记入 todo；CHANGELOG 新增 `[0.77.0]`；两份 `plugin.json` 改为 0.77.0，中英
README 的 `--ref` 改为 v0.77.0。

- 验收与验证：`verify-and-commit.sh` 全档；实跑命令写入 todo。
- 文件：上述文档、CHANGELOG、两份 `plugin.json`、两份 README。

### Checkpoint 2（gate）：最终验收

按 AC1–AC5 逐条给证据（测试名与结果、实跑输出），展示未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，
合并由用户进行；发版后通知 decision-inbox 整改会话改读、抄送接入协调人（含「最终验收已算在 total 里」），也在此由用户确认后再发。

## Risks

- **抽函数时改了 `next_gate` 的边界行为**（比如不带冒号的检查点、全角括号）：Task 1 要求现有回归一个不改，并做一处变异确认
  判据确实被测到；没有被测到的边界照旧沿用原正则，不扩大识别范围。
- **todo 存在但读不出**：沿用 `_read` 抛 `Unreadable` → 退出码 `4`，不为 `gates` 单独降级。
- **读取方把最终验收重复计入基准**：只能靠说明提醒；接口说明与发版通知里都写明。
