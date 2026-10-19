# Spec: map-gate-count

<!-- spec-guard: review approved f3e36a40dc9d -->

## Objective

下游要按模块算「问用户的基准次数」：Spec、Plan、最终验收，再加上 Plan 里约定要停下等确认的 `gate` 检查点。前三项人人都有，
gate 个数每个模块不同，现在只能自己去解析 `tasks/<id>/todo.md` 的检查点写法与级别，绕过了 spec-guard 的对外接口，也会和
spec-guard 自己的判据（未标级别按 gate）走偏。

本模块给 `/map --json` 每个模块只增一项事实：**gate 检查点的总数与已勾数**。只给事实，不算基准、不数问了用户几次、不判断
打转，这些归读取方。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `map-view`、`map-progress-facts`、`checkpoint-tiers`、
`plugin-interface`。需求来自接入协调人转达的 R21 条目 SG-7（用户决定 58–60）；用户在本会话确认了字段同时给总数与已勾数。

## Assumptions

1. **什么算 gate**：与「下一个 gate」（`module_stage.next_gate`）同一判据——`todo.md` 里以 `Checkpoint` 开头的勾选项，冒号前
   标了 `（report）` 的不算，标了 `（gate）` 或没标级别的都算。判据抽成 `module_stage.py` 里的一个函数，`next_gate` 与本字段
   共用，不在 `map_view.py` 里另写一份正则。
2. **总数与已勾数**：`gates: {"total": N, "done": M}`，`done` 是其中已勾（`[x]`／`[X]`）的个数。
3. **最终验收也是 gate**：本仓库和约定里，最终验收通常就是 Plan 的最后一个 `gate` 检查点，所以它已经算在 `total` 里。读取方
   算基准时不要再把「最终验收」单独加一次。这一点写进 `interface.json` 的说明。
4. **没有 todo 时为 `null`**：`tasks/<id>/todo.md` 不存在（还没写 Plan，或只有 plan.md）时 `gates` 为 `null`；文件存在但没有
   gate 检查点时为 `{"total": 0, "done": 0}`。读不出文件沿用现有的退出码 `4`。
5. **只看当前 checkout 的工作区**：与 `progress` 一样读工作区的 todo；不读 git 历史，所以 `history` 为 `unavailable` 时照常
   有值。开关 on 时其他 worktree 里的模块不去那边数。
6. **JSON 只增字段**：`schemaVersion` 仍为 1，原有字段与取值不变，`nextGate` 不变；`interface.json` 从 1.2 升到 1.3，只加说明。
7. 人看的进度表、每轮注入（`phase-guard.sh`）都不变；发版 0.77.0，发完通知 decision-inbox 整改会话改读。

## Contract

### JSON（`schemaVersion` 仍为 1，只增）

```json
{
  "modules": [
    {"id": "…", "gates": {"total": 2, "done": 1}},
    {"id": "…", "gates": null}
  ]
}
```

- `gates.total`、`gates.done`：整数，`0 ≤ done ≤ total`。
- `gates`：todo 不存在时为 `null`；总在每个模块的记录里出现，与开关无关。

### `interface.json`（1.2 → 1.3，只加说明）

在 `mapView.progressFacts.fields` 下加 `gates`：含义、`null` 的情形、gate 的判据（未标级别按 gate、report 不计）、
「最终验收通常是最后一个 gate，已在 total 里」。`progressFacts.appearsWhen` 的版本说明同步写 1.3。检查器
（`check-interface`）随之要求这一项存在。

### 文档

`commands/map.md`、`docs/commands.md` 的 map 一节、`spec-guard-ops` 的 map 一节写明新字段；CHANGELOG `[0.77.0]`；
版本号 0.77.0（两份清单同步）。

### 不变

- 进度表逐字不变；`phase-guard.sh` 与每轮注入逐字不变；`nextGate` 的取值不变；不写任何文件；不增加 git 调用。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_map_view.py
python3 -B plugins/spec-guard/hooks/map_view.py --project . --json
```

## Testing strategy

在 `test_map_view.py` 用临时项目构造：两个 gate（一个标 `（gate）`、一个不标级别）加一个 `（report）`、勾掉其中一个 gate
→ `{"total": 2, "done": 1}`；全勾 → `done == total`；没有检查点的 todo → `{0, 0}`；没有 todo → `null`；大写 `[X]` 算已勾；
不是 git 仓库时仍有值。反向：`（report）` 检查点不进总数；`Checkpointing` 这类词不算检查点（沿用现有判据）。原有用例的期望
值除键集合外不改。`next_gate` 改用共用函数后，现有阶段提示与 map 回归保持全绿，证明判据没变。`interface.json` 的新说明
由 `test-checkers.sh` 加一条缺 `gates` 即报错的反例断言。

## Boundaries

- **会做**：`gates` 一项事实、共用判据函数、接口说明与文档。
- **先问**：在进度表里显示 gate 个数；按 gate 算任何基准、阈值或「问了几次」；去其他 worktree 数。
- **不做**：数问用户的次数、判断打转；改 `nextGate` 或检查点级别的判据；改 Plan 的写法。

## Success criteria

- AC1：todo 里有两个 gate（一个标 gate、一个未标级别）和一个 report、勾掉一个 gate 时，JSON 的 `gates` 为 `{"total": 2, "done": 1}`。
- AC2：没有 todo 时 `gates` 为 `null`；有 todo 但没有 gate 检查点时为 `{"total": 0, "done": 0}`；`history` 为 `unavailable` 时照常有值。
- AC3：原有 JSON 字段与取值不变，进度表输出逐字不变，`nextGate` 与改动前一致。
- AC4：`interface.json` 为 1.3，`progressFacts.fields` 说明了 `gates`（含「最终验收已算在 total 里」），检查器缺这一项时报错。
- AC5：本仓库实跑 `map_view.py --json`，128 个模块都有 `gates` 键，耗时与改动前同一量级。

## Open questions

- 无。
