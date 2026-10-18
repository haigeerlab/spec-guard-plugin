# Spec: map-progress-facts

<!-- spec-guard: review approved a0ee8eda99d3 -->

## Objective

`map-view` 的勾选时间只读已提交的历史（`stall-signals` 有意如此）。一个真实的前端项目里，进行中的模块工作区 todo 已勾到
8/9，但这些勾选都没提交：`firstTickAt`、`lastTickAt` 为空，`tickCommits` 为 0，进度表看不出任何异常。进度（读工作区）与
勾选历史（读提交）对不上，map 却不说。

另一处缺口：读取方（module-crew）要知道项目的 `reviewCadence` 生效值，现在只能自己打开 `.agent/config.json`，绕过了
spec-guard 的对外接口。

本模块给 `/map --json` 只增三项事实，并在进度表里把"勾了没提交"说出来：

- 每个模块的**未提交勾选数**与**开工时间**；
- 当前 checkout **最后一次提交的时间**；
- **`reviewCadence` 的生效值与来源**。

只给事实，不设阈值、不判断"停滞"。多久算卡住、要不要问用户，由读取方（decision-inbox、module-crew）决定。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `map-view`、`stall-signals`、`project-config`、`plugin-interface`。
需求来自接入协调人转述的用户决定 53（S1、S4），用户在本会话审过取舍：不读文件修改时间、不设阈值、不改 `bottlenecks`。

## Assumptions

1. **未提交勾选数（`uncommittedTicks`）**：当前 checkout 工作区里 `tasks/<id>/todo.md` 的已勾选项数，减去 HEAD 里同一文件的
   已勾选项数；小于 0 时记 0（取消勾选不是本字段要报的事）。todo 没被 git 跟踪时，HEAD 里按 0 项算。读不出 git 时为 `null`。
2. **开工时间（`startedAt`）**：HEAD 历史里第一次加入 `spec/<id>.md` 的提交时间（`%cI`）。Spec 还没提交过时为 `null`。
   用 Spec 而不用 todo，是因为模块从写 Spec 起就算开工。
3. **最后一次提交时间（`head.committedAt`）**：当前 checkout HEAD 的提交时间。是整个 checkout 的，不按模块分：代码提交
   不一定碰模块文件，按模块分会低估进展。
4. **`reviewCadence`**：顶层新增 `{"value", "source"}`，取自 `project_config.summary()` 的同一份结果，与 `/spec-guard:config`
   显示一致；`source` 是 `.agent/config.json`、`default` 或 `default (config invalid)`。`moduleConcurrency` 已有出口（开关 on 时的
   顶层字段，缺省即 off），不重复给。
5. **只看当前 checkout**：开关 on 时其他 worktree 里的模块，已有 `worktree.dirty` 与 `worktree.progress`，本模块不再去那些
   worktree 算未提交勾选。
6. **git 调用只加三次**：一次 `git diff HEAD -U0` 比对 `tasks/*/todo.md`，一次 `git ls-files --others` 找未跟踪的 todo，一次
   `git log --diff-filter=A` 找 Spec 的首次提交；加上 HEAD 时间那一次，都不逐模块调用。
7. **JSON 只增字段**：`schemaVersion` 仍为 1，原有字段与取值不变，`bottlenecks` 仍只列挂起的模块；`interface.json` 升到 1.2，
   只加说明。
8. 每轮注入（`phase-guard.sh`）不变；发版 0.73.0。

## Contract

### JSON（`schemaVersion` 仍为 1，只增）

```json
{
  "head": {"sha": "…", "committedAt": "2026-10-16T21:04:11+08:00"},
  "reviewCadence": {"value": "separate", "source": "default"},
  "modules": [
    {"id": "…", "uncommittedTicks": 8, "startedAt": "2026-10-14T10:02:55+08:00"}
  ]
}
```

- `uncommittedTicks`：整数，≥ 0；`history` 为 `unavailable` 时为 `null`。
- `startedAt`：提交时间原样（`%cI`），不换算时区；Spec 没提交过、或 `history` 为 `unavailable` 时为 `null`。浅克隆时可能取到
  的是浅克隆边界后的第一次，`history` 已是 `shallow`，不另加说明字段。
- `head.committedAt`：没有提交时为 `null`；`head` 原有字段不变。
- `reviewCadence`：总在输出里，与开关无关。

### 进度表

- 进行中模块 `uncommittedTicks` 大于 0 时，状态格在原文后加 `，N 项勾选未提交`；`head.committedAt` 有值时再加
  `（最后一次提交 <距今>前）`。距今写法沿用 `stall-signals`。例：`🔨 进行中 8/9，8 项勾选未提交（最后一次提交 3 天前）`。
- 为 0 或 `null` 时表格逐字不变。不出现"停滞""太久"等判断，没有阈值。
- 不在表格里显示 `startedAt` 与 `reviewCadence`（`/spec-guard:config` 已经显示后者）。

### `interface.json`（1.1 → 1.2，只加说明）

在 `mapView` 下加 `progressFacts` 一节，说明 `uncommittedTicks`、`startedAt`、`head.committedAt`、`reviewCadence` 的含义、
`null` 的情形，并写明"这些是事实，阈值与判断由读取方做"。concurrency 一节"与 1.0 逐字相同"的说法改为"不出现这些
并行字段"，因为 1.2 起关着开关时也有新字段。

### 文档

`commands/map.md`、`docs/commands.md` 的 map 一节、`spec-guard-ops` 的 map 一节写明新字段；`docs/design.md` 的 `map_view.py`
一行补一句；CHANGELOG `[0.73.0]`；版本号 0.73.0（两份清单同步）。

### 不变

- `phase-guard.sh` 与每轮注入逐字不变；`map-view` 已有字段、取值与退出码不变；不写任何文件；不读文件修改时间。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_map_view.py
python3 -B plugins/spec-guard/hooks/map_view.py --project . --json
```

## Testing strategy

在 `test_map_view.py` 用临时 git 仓库与固定提交时间构造：工作区多勾 3 项未提交 → `uncommittedTicks` 为 3、表格出现那句；
勾选全部提交后为 0、表格逐字回到原样；取消勾选未提交 → 0；todo 未被跟踪 → 等于工作区勾选数；不是 git 仓库 → `null`；
`startedAt` 等于加入 Spec 那次提交的时间、Spec 未提交为 `null`；`head.committedAt` 等于 HEAD 时间、没有提交为 `null`；
`reviewCadence` 在未设置、设为 combined、配置无效三种情况下的 value 与 source 与 `project_config.summary()` 一致；JSON 键
集合（原有加四项）。距今写法用已有的 `SPEC_GUARD_MAP_NOW` 注入。`interface.json` 的版本与新说明由现有的接口校验断言。

## Boundaries

- **会做**：四项事实、表格一句、接口说明与文档。
- **先问**：任何阈值或"停滞"判断、把这些放进每轮注入、去其他 worktree 算未提交勾选。
- **不做**：读文件修改时间；改 `bottlenecks` 的含义；按模块拆分最后一次提交时间。

## Success criteria

- AC1：工作区比 HEAD 多勾 N 项时，JSON 的 `uncommittedTicks` 为 N，进度表该模块状态格显示"N 项勾选未提交（最后一次提交 … 前）"。
- AC2：勾选全部提交后 `uncommittedTicks` 为 0，进度表输出与改动前逐字相同。
- AC3：`startedAt` 等于第一次提交 Spec 的时间，`head.committedAt` 等于 HEAD 的提交时间；读不出 git 时三项都是 `null`，退出码不变。
- AC4：`reviewCadence` 的 value 与 source 和 `/spec-guard:config` 显示的一致（未设置、已设置、配置无效三种）。
- AC5：原有 JSON 字段与取值不变（`test_map_view.py` 原有期望值除键集合外不改）；`interface.json` 为 1.2 且说明了四项。
- AC6：本仓库实跑 `map_view.py --json` 耗时与改动前同一量级（1 秒左右）。

## Open questions

- 无。
