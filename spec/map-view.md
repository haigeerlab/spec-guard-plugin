# Spec: map-view

<!-- spec-guard: review approved a06d38293b2c -->

## Objective

一个项目的模块多了以后，用户只能从每轮的阶段提示里看到"当前模块"，看不到整体：哪些做完了、哪个挂起了、挂起
挡住了下游几个模块、哪些可以开始、哪些 Spec 或 Plan 在等自己审核。实地出现过：一个模块因上游漏洞挂起，它挡住的
下游模块只在下游那一行写了原因，看不出卡点的分量；用户只能一遍遍问"开发顺不顺"。用户手工整理过一张按开发顺序
排、带"作用""状态（含原因）"的进度表，认为这样已经清楚。

本模块把这张表做成只读命令：数据全部来自 spec-guard 自己管的文件（能力图、各模块 Spec／Plan／todo、状态记录、
本地 git 引用），不新增数据源。同一份结果另给 JSON，供其他插件读取（decision-inbox 的跨项目汇总直接调用它，
不再自己解析能力图，保证能力图只有一份解析逻辑）。

挂起目前只记一个标记，不记原因；表里"挂起（原因）"需要原因，所以 `module-suspend` 加一个可选的原因行。

登记：2026-10-16 经 `/spec-guard:add-module` 插入能力图。下一个模块 `stall-signals`（停滞时长、反复返工、挂起
时长的原始数据）另开，不在本模块。

## Assumptions

用户已于 2026-10-16 确认方向与以下前提（JSON 字段按 decision-inbox 会话 2026-10-16 提的要求调整）：

1. **只读、离线。** 只读能力图、`spec/<id>.md`、`tasks/<id>/plan.md`、`tasks/<id>/todo.md`、`.agent/state.json` 与
   本地 git 引用；不读会话记录，不联网，不 fetch，不交互，可以无人值守运行。除第 9 条的挂起原因外不写任何文件。
2. **状态互斥，一个模块只取一个**，按下列顺序判定，取第一个成立的：
   - `done`：阶段判定为 DONE（有 Plan，todo 全部勾完；或 Plan 声明不建 todo）。
   - `suspended`：todo 有挂起标记且还有未勾选项（与阶段判定同一口径）。
   - `in_progress`：已经开工——有 Spec 或 Plan，或者它就是当前模块。另给它卡在哪一步（Spec／Plan／构建）。
   - `blocked`：没开工，且它的依赖链（直接或间接）上有挂起的模块。
   - `ready`：没开工，且直接依赖全部 `done`（没有依赖也算）。
   - `not_ready`：没开工，直接依赖里有没做完的，且依赖链上没有挂起的模块。
3. **`blocked` 只覆盖"被挂起的模块挡住"。** spec-guard 读不到外部等待（等某人交付、等审查结论）；这类阻塞由读取
   方叠加，本模块不推断。
4. **"挡住 N 个"按依赖链全算**：一个模块的 `blocks` 是所有直接或间接依赖它、且还没 `done` 的模块。
5. **关键卡点 = 挂起的模块**，按挡住的个数从多到少排；没有挂起的模块时写"无"。
6. **"作用"直接取能力图职责列。** 表格里截短，JSON 给全文。不另造短编号。
7. **审查列只显示 spec-guard 自己的评审标记**：Spec、Plan 各自的原值（`none`／`pending`／`approved`／`revised`／
   `invalid`，`revised` 只出现在 Spec）。别的插件或流程里的审查（例如负责人的架构审查）不读、不显示。
8. **待审核（`awaitingReview`）**：评审标记为 `pending`、`revised` 或 `invalid` 的 Spec 和 Plan。用户在别处待答的
   事项不归这里。当前模块的下一个 `gate` 另放 `nextGate`。
9. **挂起原因。** `module-suspend` 加可选 `--reason "<一行文字>"`，在原挂起标记的下一行写
   `<!-- spec-guard: suspended-reason: <原因> -->`。原挂起标记一个字不改，所以旧版本照常识别挂起、忽略原因行。
   恢复时两行一起去掉。这有意放开了 `module-suspend` 当初"不记原因"的取舍：只记用户说的原因，仍不记日期和条件，
   不据此做任何判断。
10. **JSON 给全量、不折叠**，带 `schemaVersion` 与稳定性承诺；折叠只在表格输出里做。
11. **调用方式**：Claude Code `/spec-guard:map`，Codex `spec-guard-ops` 的 map 一节；脚本支持 `--project <路径>` 从
    项目外调用。不进每轮注入，`phase-guard` 的输出不变。
12. **发版**：0.62.0。

## Contract

### 脚本 `hooks/map_view.py`

```
python3 -B map_view.py [--project <路径>] [--json] [--all]
```

- `--project` 缺省时按其他命令的同一顺序取项目根（`CLAUDE_PROJECT_DIR`，否则 git 顶层，否则当前目录）；给了就只用它，
  不跟随会话登记的指向。
- 退出码：`0` 成功；`2` 参数错误；`3` 没有能力图（`spec/CAPABILITY-MAP.md` 不存在），不算错误，stderr 一句说明，
  `--json` 时 stdout 仍给 `{"schemaVersion": 1, "error": "no-capability-map"}`；`--project` 指向的路径不存在或不是目录
  时走 `2`；`4` 能力图不能按严格规则解析，或
  某个模块文件读不出（权限、编码），stderr 给原因，`--json` 时 stdout 给 `{"schemaVersion": 1, "error":
  "unreadable", "detail": "<原因>"}`。不输出半张图。
- `--json` 时 stdout 只有一个 JSON 对象（成功或上面的错误对象），警告与说明一律走 stderr。
- 只用 `capability_map.parse_map` 与 `module_stage` 现有判定，不另写解析。

### JSON（`schemaVersion: 1`）

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-10-16T14:05:00+08:00",
  "generator": {"name": "spec-guard", "version": "0.62.0"},
  "project": {"root": "/abs/path", "title": "<能力图一级标题，没有则 null>"},
  "head": {"sha": "<完整 sha 或 null>", "branch": "<分支名；分离头指针为 null>",
           "unmerged": {"count": 2, "base": "origin/main"},
           "unpushed": {"count": 1, "upstream": "origin/claude/map-view"}},
  "stage": "BUILDING",
  "activeModule": "<当前模块 id 或 null>",
  "nextGate": "<当前模块下一个未勾的 gate 标题，没有则 null>",
  "totals": {"done": 0, "in_progress": 0, "suspended": 0, "blocked": 0, "ready": 0, "not_ready": 0},
  "bottlenecks": [{"id": "<挂起模块>", "suspendedReason": "<原因或 null>", "blocks": ["<id>", "..."]}],
  "awaitingReview": [{"id": "<模块>", "kind": "spec|plan", "review": "pending|revised|invalid"}],
  "modules": [
    {
      "id": "<id>", "position": 1, "responsibility": "<全文>", "dependsOn": ["<id>"],
      "status": "done|in_progress|suspended|blocked|ready|not_ready",
      "step": "spec|plan|build|null",
      "progress": {"done": 3, "total": 7},
      "suspendedReason": null,
      "blockedOn": [],
      "missingDeps": [],
      "blocks": {"count": 0, "ids": []},
      "review": {"spec": "none|pending|approved|revised|invalid", "plan": "none|pending|approved|invalid"}
    }
  ]
}
```

- `head.unmerged`：HEAD 上还没进入本地已知远端默认分支的提交数（与阶段提示同一口径，只比本地引用，不 fetch）；
  判断不了（没有远端默认分支、不是 git 仓库）时为 `null`，与 `count: 0` 区分。`head` 在不是 git 仓库时各项都为 `null`。
- `head.unpushed`：HEAD 上还没推到当前分支上游的提交数（`@{upstream}..HEAD`，只比本地引用，不 fetch）；没有上游、
  分离头指针或判断不了时为 `null`。与 `unmerged` 回答的是两个问题：一个是"推了没有"，一个是"合进主线没有"。
- `generator.version`：生成这份 JSON 的已安装插件版本，取自插件自己的 `plugin.json`；读不到时为 `null`。
- `stage`：与阶段提示同一口径，取值只有 `NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MODULE_DONE`、`DONE`（能力图读不出时
  走退出码 4，不会出现 `MAP_INVALID`；剩下没做完的模块全部挂起时也是 `DONE`，与阶段提示一致）。取值集合在稳定性
  承诺之内。
- `position`：Build order 里从 1 开始的序号；能力图没有 Build order 时按表格行序。
- `step`：只对 `in_progress` 有值——没有 Spec 为 `spec`，有 Spec 没 Plan 为 `plan`，其余为 `build`；其他状态为 `null`。
- `progress`：todo 里已勾／全部的复选项数；没有 todo 时两者都是 0。
- `blockedOn`：只对 `blocked` 有值，是依赖链上挂起的模块 id（去重、按 Build order）。
- `missingDeps`：只对 `not_ready` 有值，是直接依赖里没 `done` 的模块 id。
- `blocks`：所有直接或间接依赖它、且没 `done` 的模块，按 Build order。
- **稳定性承诺**：`schemaVersion` 为 1 期间只增加字段，不删除、不改名、不改已有字段的含义和取值集合（含 `status`、`step`、
  `review`、`stage` 的取值）；需要做这些时
  `schemaVersion` 加一，并在 CHANGELOG 写明。读取方应忽略不认识的字段。

### 表格输出（默认）

```
<标题> · 92 个模块 · ✅ 89 🔨 1 ⏸ 1 ⛔ 1 🟢 0 ○ 0 · 2026-10-16 14:05
关键卡点：quality-gates 挂起（上游漏洞）→ 挡住 1 个：pwa-lifecycle
待审核：map-view Plan（待审核）
下一个 gate：Checkpoint 2（gate）：模块评审
未合入主线：2 个提交（相对 origin/main）；未推送：1 个提交

| 位 | 模块 | 作用 | 状态 | 审查 |
|---|---|---|---|---|
| 1–88 | 其余 88 个已完成 | | ✅ | |
| 89 | ... | ... | ✅ 已完成 | Spec ✔ Plan ✔ |
| 90 | ... | ... | ⏸ 挂起（上游漏洞），挡住 1 个 | Spec ✔ Plan ✔ |
| 91 | ... | ... | ⛔ 阻塞：等 quality-gates | — |
| 92 | map-view | ... | 🔨 进行中 3/7 | Spec ✔ Plan 待审核 |
```

- 折叠：默认展开 `in_progress`、`suspended`、`blocked`、`ready` 与最后一个完成的模块；其余 `done` 合并成一行
  "其余 N 个已完成"，`not_ready` 合并成一行"N 个未就绪"（合并行按连续区段标"位"的范围）。`--all` 全部展开。
- "作用"截到 40 个字符，多出的以"…"结尾；职责、原因等来自项目文件的文字去掉控制字符和表格竖线。
- 状态写法：`✅ 已完成`、`🔨 进行中 x/y`（`step` 为 spec／plan 时写 `🔨 写 Spec`／`🔨 写 Plan`）、
  `⏸ 挂起（<原因>）`（没有原因写"未记原因"），挡住非零时加"，挡住 N 个"、`⛔ 阻塞：等 <id>[、<id>]`、`🟢 可以开始`、
  `○ 未就绪：缺 <id>[、<id>]`。
- 审查：`Spec ✔`（approved）、`Spec 待审核`（pending）、`Spec 改过待重审`（revised）、`Spec 标记无效`（invalid）、
  `Spec 无标记`（none）；Plan 同理。两个都没有文件时写 `—`。
- 没有关键卡点、待审核、下一个 gate 或判断不了未合入时，对应那一行写"无"或省略（"未合入主线"判断不了时写
  "判断不了"）。

### `module-suspend` 的原因行

- `module_suspend.py ... --reason "<文字>"`：只在挂起时有效，恢复时给了报参数错误。原因是一行，去掉首尾空白，
  不能为空，不能包含换行、`-->`，最长 120 个字符；不符合时拒绝并说明，不改文件。
- 写入位置：挂起标记的下一行。已挂起的模块再带 `--reason` 运行，只替换原因行（预览给 diff）。不带 `--reason` 挂起，
  不写原因行。
- 恢复：删掉挂起标记和紧跟其后的原因行。
- `module_stage` 的挂起判定不变（仍只认挂起标记那一行）；原因行在没有挂起标记时没有任何作用。
- `/spec-guard:module-suspend` 命令与 `spec-guard-ops` 对应一节说明 `--reason`，并写明：原因只按用户说的写，不从
  上下文推断。

### 文档

- 新命令 `commands/map.md`；`skills/spec-guard-ops/SKILL.md` 加 map 一节。
- `docs/commands.md` 加 map 一节；`docs/design.md` 部件表加 `map_view.py` 与 JSON 接口；CHANGELOG 新增 `[0.62.0]`；
  两份 `plugin.json` 改为 0.62.0，README 的 `--ref` 改为 v0.62.0。

### 不变

- `phase-guard.sh` 与每轮注入的输出逐字不变；`verify-artifacts` 判据不变；能力图格式不变。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_map_view.py
python3 -B plugins/spec-guard/hooks/test_module_suspend.py
python3 -B plugins/spec-guard/hooks/map_view.py --project . --json
```

## Testing strategy

- `test_map_view.py`（新）：在临时项目里搭能力图与模块文件，覆盖六种状态的判定与先后顺序；传递依赖的 `blocks`
  与 `blockedOn`；`missingDeps` 只算直接依赖；关键卡点排序；`awaitingReview` 的三种取值；`step` 与 `progress`；
  折叠与 `--all`；"作用"截断与控制字符清理；三种退出码与对应 JSON；不是 git 仓库时 `head` 为 null、`unmerged`
  为 null；`--project` 从项目外调用；JSON 顶层与模块字段的键集合固定（防止误删字段）。
- `test_module_suspend.py`：带原因挂起、替换原因、恢复删两行、原因不合法被拒且不改文件、恢复时给 `--reason` 报错；
  旧判定在有原因行时仍识别挂起（module_stage 不改的回归）。
- 本仓库实跑：`map_view.py --project .`，92 个模块的表与 JSON，耗时在 1 秒内。
- 发版后在一个消费者项目上实跑（有挂起模块和下游）对照用户手工表。

## Boundaries

- **会做**：只读汇总、表格与 JSON、挂起原因行。
- **先问**：JSON 字段的删除或改名（要升 `schemaVersion`）；把任何结果放进每轮注入。
- **不做**：外部等待与会话状态（归读取方）；停滞时长、返工轮数（`stall-signals`）；按时间或阈值下结论；跨项目汇总；
  写能力图、todo、状态记录（挂起原因除外）。

## Success criteria

1. 在有挂起模块的项目上，表头一行能看出合计、关键卡点挡住了谁、待审核什么。
2. 六种状态在测试中各有正反例，`blocked` 与 `not_ready` 能区分开。
3. JSON 键集合由测试固定；decision-inbox 会话核对字段后无异议。
4. 带原因挂起后，旧版本的阶段判定照常识别挂起（回归覆盖）。
5. `phase-guard` 回归逐字不变，全部现有回归通过。

## Open questions

- 无。decision-inbox 会话 2026-10-16 核对 JSON 后补的五处（`head.unpushed`、`generator`、`stage` 取值、stdout 只有
  JSON、`--project` 无效走 2）已写入，对方无其他异议。
