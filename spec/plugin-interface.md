# Spec: plugin-interface

<!-- spec-guard: review approved bed3cb90fd07 -->

## Objective

同生态的其他插件（例如一个汇总多个项目进度的看板插件）会读 spec-guard 的进度和审查数据。`map_view.py --json` 已经有
`schemaVersion: 1`、稳定性承诺和含义明确的退出码（见 [map-view.md](map-view.md)），但这些只写在 spec-guard 的仓库里。
使用方得先从宿主的插件记录找到 spec-guard，再自己猜脚本路径和格式版本，没有一份随插件发布、可以按版本检查的说明。另外，
审查状态的取值只有名字，没有对外写明含义，使用方只能按字面去对照它自己的说法。

agent-relay 已经用 `interface.json` 加版本范围探测解决过同类问题，spec-guard 的 `agent_relay_probe.py` 就是按它读的。本模块
反过来，让 spec-guard 也随插件发布一份 `interface.json`，写明只读入口、格式版本、退出码含义和各取值的含义。同时把
delegate-review-hint 引入的「外部审查意见」状态，只增不改地加进 map-view 的 JSON，让使用方经接口就能读到，不用去翻 todo。

登记：2026-10-17 经 `/spec-guard:add-module` 插入能力图。来源是生态接缝建议的第 2、3 条，由监测会话转达；用户 2026-10-17 在
本会话确认：发布接口（第 2 条），取值只发布含义、不改名，对照关系由使用方维护（第 3 条），D2-A（加 `externalReview` 字段）。

## Assumptions

1. **只发布，不改名。** 现有字段名和取值（`review` 的 none/pending/approved/revised/invalid 等）一律不动，改了就要升
   `schemaVersion`。和其他插件说法之间的对照，由使用方自己维护；spec-guard 只负责把自己取值的含义写清楚。
2. **interface.json 不解决「怎么找到 spec-guard」。** 使用方仍要从宿主插件记录找到插件根目录，这一点和 spec-guard 读
   agent-relay 时相同。interface.json 解决的是「按版本确认能不能这样读」。
3. **接口版本独立于插件版本**，从 `1.0` 开始。只增加内容时升次版本号；删除、改名、改含义时升主版本号。`mapView.schemaVersion`
   跟随 map_view 的 `SCHEMA_VERSION`，两者由校验保证一致。
4. **`externalReview` 是只增字段，仍为 schemaVersion 1。** 取值和判定直接复用 delegate-review-hint 的函数，不另写解析。所以本
   模块排在 delegate-review-hint 之后。
5. **表格输出不加这一列。** 表格是给人看的视图，列已经不少；需要的话以后再提。
6. 版本 0.66.0（新增对外接口文件和 JSON 字段），一个 PR。

## Contract

### `plugins/spec-guard/interface.json`（新文件，随插件发布）

```json
{
  "interface": "1.0",
  "mapView": {
    "command": ["python3", "-B", "hooks/map_view.py", "--json", "--project", "<project-root>"],
    "schemaVersion": 1,
    "contract": "spec/map-view.md",
    "exitCodes": {
      "0": "ok",
      "2": "usage error, or --project is not a directory",
      "3": "no capability map (not an error); stdout is {\"schemaVersion\":1,\"error\":\"no-capability-map\"}",
      "4": "capability map or a module file unreadable; stdout is {\"schemaVersion\":1,\"error\":\"unreadable\",\"detail\":...}"
    },
    "values": {
      "review": {
        "none": "no review marker in the file (project may not use markers); says nothing about approval",
        "pending": "written and waiting for the user's review",
        "approved": "approved by the user; the file has not changed since",
        "revised": "Spec only: approved earlier, edited after approval, needs another review",
        "invalid": "the marker line is malformed; review state unknown"
      },
      "externalReview": {
        "none": "no external review recorded and not declined",
        "recorded": "an external review (for example from delegate) is recorded; advisory only, not an approval",
        "declined": "the user declined an external review for this module"
      }
    }
  }
}
```

- `command` 里的路径相对于插件根目录；`<project-root>` 由调用方替换。
- `contract` 指向 spec-guard 公开仓库里的完整格式说明，供人查阅；程序只认 `interface` 和 `schemaVersion`。
- 措辞用英文，与 JSON 的字段名保持同一种语言；它不属于给用户看的产物文本。

### map-view JSON

- `modules[]` 的每一项新增 `"externalReview": "none|recorded|declined"`，用 delegate-review-hint 的判定函数读 Spec 与 todo
  里的「外部审查意见」小节和拒绝标记：小节有非空内容为 `recorded`；否则有拒绝标记为 `declined`；两者都没有为 `none`。
- `spec/map-view.md` 的 JSON 示例和字段说明同步补上这一项；仍为 `schemaVersion: 1`。

### 一致性校验（`validate.sh` 调用一个新的小检查，或并入已有的清单一致性检查）

- `interface.json` 是合法 JSON，`interface` 的格式是 `<主>.<次>`；
- `mapView.schemaVersion` 等于 `map_view.SCHEMA_VERSION`；
- `values.review` 的键集合等于 `module_stage.review_state` 可能返回的取值集合（以模块里的常量为准，必要时把取值集合提成常量）；
- `values.externalReview` 的键集合等于外部审查判定函数的取值集合；
- `command` 引用的脚本存在。

### 文档

- `docs/design.md` 新增一小节「对外接口」：interface.json 管什么、版本规则、使用方怎么读，并点明 spec-guard 也是按同样的方式
  读 agent-relay 的。
- README 中英两版各加一句：对外只读接口见插件根目录的 `interface.json`，格式说明见 `docs/design.md`「对外接口」。
- CHANGELOG 记一条「新增」。

## Commands

```bash
python3 plugins/spec-guard/hooks/test_map_view.py
/bin/bash scripts/validate.sh
```

## Testing strategy

- **先写失败的测试：** `test_map_view.py` 断言每个模块都有 `externalReview`，三种取值各一个用例（Spec 里记录、todo 里记录、
  只有拒绝标记），外加小节标题在但内容为空时为 `none`；断言其余字段与改动前逐字一致。
- **一致性检查正反例：** 正常时通过；在草稿副本上把 `schemaVersion` 改成 2、删掉一个 `review` 取值、把 `command` 指向不存在的
  脚本，各自确认会报错，再复原。
- 发布包检查：确认 `interface.json` 在 git archive 出来的包里（发版证据里一并列出）。

## Boundaries

- Always：只增不改；interface.json 与代码由校验保证一致；没有能力图、读不出时的行为不变。
- Ask first：在表格输出里加外部审查一列；把阶段、进度之外的数据（成本报告、事项账本）也写进 interface.json；升 `schemaVersion`。
- Never：改名或删除现有字段和取值；替其他插件维护它们的取值对照；在仓库里写其他私有插件或消费者项目的名称和路径。

## Success criteria

1. 插件根目录有 `interface.json`，使用方按 `interface` 的主版本号和 `mapView.schemaVersion` 就能判断能不能读，不用读
   spec-guard 的内部文件。
2. map-view JSON 每个模块都带 `externalReview`，其余输出逐字不变，`schemaVersion` 仍为 1。
3. interface.json 和代码常量不一致时，`validate.sh` 会变红。
