# Plan: stall-signals

<!-- spec-guard: review approved -->

依据 [`spec/stall-signals.md`](../../spec/stall-signals.md)。本模块按合并审：Spec 与本 Plan 一起交用户审。分支
`claude/stall-signals`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `3982efe`（#318 合并）开出。本模块一个
PR，含 0.63.0 版本号；合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动；Task 3 在本仓库与临时 git 仓库实跑。

## Overview

先固定历史解析的判定（测试先行，用固定提交时间），再实现，再接表格、规则与文档。历史解析是 `map_view.py` 里独立的一个
函数，失败只影响两项时间与 `history`，不影响其余输出。

## Architecture Decisions

- **一次 `git log -p -U0`**，按提交从新到旧扫描，每个模块取第一个命中的提交；不逐模块调用 git。
- **只看增删行计数**判断是否勾选，不还原整份 todo；挂起看最新一个碰到标记行的提交是增还是删。
- **测试用 `SPEC_GUARD_MAP_NOW`** 固定"当前时间"，只影响表格的距今写法；JSON 不含"距今"。
- **规则与模板行**沿用已有写法：异常停点列表加一项；模板加一行"细则见 …"。

## Task List

### Task 1：历史解析的测试（先红）

在 `test_map_view.py` 新增一组用例：临时 git 仓库、`GIT_COMMITTER_DATE` 固定时间，覆盖 Spec Testing strategy 的各项（勾选
前进、改文字与取消勾选不算、同一提交多个模块、`*`／`X` 写法、挂起提交时间、删后未提交加回为 null、非 git 与无提交为
`unavailable`、浅克隆为 `shallow`、表格距今写法、键集合）。键集合断言加上三个新字段。

- 验收：新用例在旧代码上失败；原有用例期望值不改（键集合除外）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_map_view.py`。
- 文件：`hooks/test_map_view.py`。

### Task 2：实现

`map_view.py` 加历史解析、`lastTickAt`／`suspendedAt`／`history` 与表格距今写法。

- 验收：Task 1 全绿；两处变异（取消勾选也算勾选、挂起取最早一次写入）各有断言变红；本仓库实跑 1 秒左右。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/map_view.py`。

### Checkpoint 1（report）：历史解析回归全绿

### Task 3：检查点规则与约定块模板

`references/workflow-checkpoints.md` 的异常停点加"同一个 gate 因外部原因再次挡住"及处理方式；两份约定块模板
（`templates/claude-block-local.md`、`templates/codex-block-local.md`）与 `docs/convention-block.md`、本仓库 `AGENTS.md` 的
约定块各加一行指向它；`test_workflow_checkpoints.py` 加关键词断言。

- 验收：断言先红后绿；`validate.sh` 的约定块一致性检查通过。
- 验证：`verify-and-commit.sh` 全档。
- 文件：上述规则、模板、文档与测试。

### Task 4：文档、实跑、CHANGELOG 与版本号

`commands/map.md`、`spec-guard-ops` 的 map 一节、`docs/commands.md`、`docs/design.md` 写明两项时间与 `history`；在本仓库
与一个带挂起模块的临时 git 仓库实跑表格与 JSON，结果记入 todo；CHANGELOG 新增 `[0.63.0]`；两份 `plugin.json` 改为
0.63.0，中英 README 的 `--ref` 改为 v0.63.0。

- 验收与验证：`verify-and-commit.sh` 全档；实跑命令写入 todo。
- 文件：上述文档、CHANGELOG、两份 `plugin.json`、两份 README。

### Checkpoint 2（gate）：模块评审

展示验证结果、未验证项、实际改动的文件清单与文档建议；把新增字段发给 decision-inbox 核对。推送与开 PR 在此由用户确认，
合并由用户进行。

## 追加：首次勾选时间与勾选次数（2026-10-16）

decision-inbox 核对字段后建议加 `firstTickAt` 与 `tickCommits`，用户同意。出自同一次 `git log`，扫描时多记最早一次与次数，
不增加 git 调用；只给原始数据，节奏由读取方算。追加 Task 5，完成后回到 Checkpoint 2。

### Task 5：`firstTickAt` 与 `tickCommits`

先补测试（次数、最早时间、没勾过为 0、没有历史为 null，键集合加两项），再实现；Spec、命令与技能说明、CHANGELOG 同步。

- 验收：新增断言先红后绿；一处变异（不更新最早时间）变红。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/map_view.py`、`hooks/test_map_view.py`、`spec/stall-signals.md`、`commands/map.md`、`spec-guard-ops`、
  `docs/commands.md`、`CHANGELOG.md`。

## Risks

- **历史很长时变慢**：`-U0` 且只限 todo 文件；本仓库实测超出 1 秒较多时记入 todo 交检查点。
- **压缩合并（squash）改写了提交时间**：取到的是合并时间，比实际勾选晚；在说明里写明"取的是提交时间"。
- **约定块多一行**：用户可在评审时删掉 Task 3 的模板部分，只保留规则文字。
