# Plan: map-view

<!-- spec-guard: review approved -->

依据 [`spec/map-view.md`](../../spec/map-view.md)。本模块按分开审：Spec 先交用户审（2026-10-16 批准了初版；decision-inbox 核对
JSON 后补的五处与本 Plan 一起交审）。分支 `claude/map-view`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从
`a1d2796`（#316 合并）开出。本模块一个 PR，含 0.62.0 版本号；合并后的 tag、Release、两边宿主同步与验证记录按
`docs/release-process.md` 另走。

所需工具：无 UI 改动；输出在终端与对话里看，Task 4 用本仓库和临时项目实跑。

## Overview

先固定判定（测试先行），再写脚本，再接命令与文档。状态判定只组合 `module_stage` 与 `capability_map` 的现有结果，不另写
解析；挂起原因是 `module_suspend.py` 的一个小扩展，单独一个任务，便于确认旧判定不受影响。

## Architecture Decisions

- **一个脚本两种输出。** `map_view.py` 先算出 JSON 结构，表格由同一结构渲染，保证两者不会说法不一。
- **判定复用。** 每个模块的阶段、进度、挂起取自 `module_state`；项目阶段与当前模块取自 `project_stage`；下一个 gate 取自
  `next_gate`；未合入取自 `unmerged_commits`。新增的只有：六种状态的映射、依赖闭包（`blocks`、`blockedOn`）、`unpushed`、
  `step`、折叠。
- **依赖闭包按 Build order 算一次反向图**，93 个模块量级，不做缓存。
- **原因行与挂起标记分两行。** `module_stage` 的挂起判定只认原挂起标记那一行，一字不改，旧版本因此兼容。

## Task List

### Task 1：`map_view.py` 的测试（先红）

新建 `hooks/test_map_view.py`，按 Spec 的 Testing strategy 覆盖：六种状态与判定先后、传递依赖的 `blocks`／`blockedOn`、
`missingDeps` 只算直接依赖、关键卡点排序、`awaitingReview` 三种取值、`step` 与 `progress`、`stage` 取值、折叠与 `--all`、
截断与清理、三种退出码与错误 JSON、`--project` 无效走 2、`--json` 时 stdout 只有一个对象、非 git 仓库时 `head` 全为 null、
有上游与无上游时的 `unpushed`、`generator.version` 与 `plugin.json` 一致、JSON 键集合固定。在 `scripts/validate.sh` 登记。

- 验收：新测试在没有 `map_view.py` 时失败。
- 验证：`python3 -B plugins/spec-guard/hooks/test_map_view.py`。
- 文件：`hooks/test_map_view.py`、`scripts/validate.sh`。

### Task 2：实现 `map_view.py`

按 Contract 实现 JSON 与表格输出、退出码、`--project`／`--json`／`--all`。

- 验收：Task 1 全绿；两处变异（`blocked` 只看直接依赖、折叠时漏掉 `ready`）各有断言变红；本仓库实跑 1 秒内。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/map_view.py`。

### Task 3：挂起原因（`module_suspend.py --reason`）

先在 `test_module_suspend.py` 加用例（带原因挂起、替换原因、恢复删两行、原因不合法被拒且不改文件、恢复时给 `--reason`
报错、有原因行时 `module_state` 仍判为挂起），再实现；`map_view.py` 读原因行，补对应断言。

- 验收：新增用例先红后绿；现有 `test_module_suspend.py` 用例期望值不改。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/module_suspend.py`、`hooks/test_module_suspend.py`、`hooks/map_view.py`、`hooks/test_map_view.py`。

### Checkpoint 1（report）：脚本与挂起原因回归全绿

### Task 4：命令、技能与实跑

新建 `commands/map.md`（定位插件根目录的片段与其他命令相同；把表格原样给用户，不另行改写）；`spec-guard-ops` 加 map
一节；`commands/module-suspend.md` 与 `spec-guard-ops` 的挂起一节说明 `--reason`（只按用户说的写，不从上下文推断）。
在本仓库与一个临时项目（有挂起模块和下游）各实跑一次表格与 JSON，结果记入 todo。

- 验收：两处实跑的输出与 Spec 的表格示例结构一致；命令文件通过 `validate.sh` 的清单与命令检查。
- 验证：`verify-and-commit.sh` 全档；实跑命令写入 todo。
- 文件：`commands/map.md`、`skills/spec-guard-ops/SKILL.md`、`commands/module-suspend.md`。

### Task 5：文档、CHANGELOG 与版本号

`docs/commands.md` 加 map 一节；`docs/design.md` 部件表加 `map_view.py` 与 JSON 接口（指向 Spec 的 Contract）；CHANGELOG 新增
`[0.62.0]`；两份 `plugin.json` 改为 0.62.0，中英 README 的 `--ref` 改为 v0.62.0。

- 验收与验证：`verify-and-commit.sh` 全档。
- 文件：`docs/commands.md`、`docs/design.md`、`CHANGELOG.md`、两份 `plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 2（gate）：模块评审

展示验证结果、未验证项、实际改动的文件清单与文档建议；把 Spec 的 Contract 发给 decision-inbox 会话作为接入依据。推送与开
PR 在此由用户确认，合并由用户进行。

## Risks

- **依赖闭包算错导致"挡住 N 个"失真**：Task 1 用多层依赖与菱形依赖的夹具覆盖。
- **大项目耗时**：每个模块读三个文件，93 个模块实测在 1 秒内；超出时在 todo 记录并交检查点。
- **原因行被旧版本误判**：旧版本只认原标记那一行，原因行对它是普通注释；Task 3 的回归覆盖。
