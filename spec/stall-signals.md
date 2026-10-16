# Spec: stall-signals

<!-- spec-guard: review approved b9171b29f499 -->

## Objective

`map-view` 能看出"现在卡在哪"，看不出"卡了多久"。实地出现过：一个模块的最终 gate 因上游漏洞一直过不去，agent 按默认
推荐反复尝试很久，最后才挂起；挂起后下游被挡住多久，也只能靠人记。跨项目汇总一方（decision-inbox）要用"进度变慢"
"挂起挡住后面"两类信号，并要求拿原始时间自己和当前时间、项目历史基准比，不要 spec-guard 算好的结论。

本模块补两项原始时间：每个模块**最后一次勾选 todo 的时间**、当前**挂起标记写入的时间**，都取自已提交的 git 历史；
表格只为人加上"距今多久"。另在共享检查点规则补一条停点：同一个 gate 因外部原因再次挡住时，停下把选项交用户决定。

登记：2026-10-16 经 `/spec-guard:add-module` 插入能力图，依赖 `map-view`。decision-inbox 2026-10-16 撤回了"审查轮数"
（它的返工信号统计的是架构审查，spec-guard 没有这份数据），本模块不提供。

## Assumptions

用户已于 2026-10-16 确认：

1. **最后一次勾选的时间（`lastTickAt`）**：HEAD 历史里，最近一个让 `tasks/<id>/todo.md` 已勾选项变多的提交的提交时间
   （committer date，带时区的 ISO 8601）。只认已提交的改动；从没勾过或 todo 没提交过时为 `null`。
2. **挂起开始的时间（`suspendedAt`）**：只对当前 `suspended` 的模块给值，是 HEAD 历史里最近一次写入挂起标记那一行的
   提交时间。标记还没提交（最近一次碰到标记的提交是删除它，或从来没有提交过它）时为 `null`。
3. **一次 `git log`**：对 `tasks/*/todo.md` 只跑一次带补丁的 `git log`，从中分出每个模块，不逐模块调用。
4. **历史状况（`history`）**：顶层新增，取值 `complete`（完整历史）、`shallow`（浅克隆，较早的勾选可能看不到）、
   `unavailable`（不是 git 仓库、没有提交、找不到 git 或 `git log` 失败），让读取方分清"没有数据"与"从没勾过"。
   `unavailable` 时所有模块的两项都是 `null`。
5. **JSON 只增字段**：模块加 `lastTickAt`、`suspendedAt`，顶层加 `history`；`schemaVersion` 仍为 1，原有字段不变。
   2026-10-16 decision-inbox 核对后建议、用户同意再加两项：`firstTickAt`（第一次勾选的提交时间）与 `tickCommits`（勾选过
   的提交次数），供读取方自己算这个模块平时的节奏（平均间隔 =（lastTickAt − firstTickAt）÷（tickCommits − 1））。
6. **表格只为人加距今多久**：进行中写"…，上次勾选 3 天前"，挂起写"⏸ 挂起（原因，已挂 2 天）"；没有值时不写。
   不设阈值，不出现"停滞"之类的判断。
7. **检查点规则补一条停点**：同一个 gate 因外部原因（上游未修复、缺权限、要用户取舍）再次挡住时停下，把挂起、接受
   风险、换方案等选项与各自代价交用户决定，不按默认推荐继续试。不写死轮数。只改规则文字，不加机制。
8. 每轮注入与压缩后注入的阶段提示不变；发版 0.63.0。

## Contract

### `map_view.py` 新增

- 一次调用：`git -C <root> log --no-color --no-renames -U0 --format=<分隔符>%H%x00%cI -p -- ':(glob)tasks/*/todo.md'`，
  按提交从新到旧解析每个文件的增删行：
  - 增行里匹配 `- [x]`（`*`/`+` 列表符、`X` 同样认）的行数多于删行里匹配的行数 → 该提交是该模块的一次勾选；
    最新的一次给 `lastTickAt`，最早的一次给 `firstTickAt`，次数给 `tickCommits`。
  - 最新一个碰到挂起标记行的提交：增行是标记 → `suspendedAt` 取它的时间；删行是标记 → `null`。
- 浅克隆用 `git rev-parse --is-shallow-repository` 判断。
- 历史读取失败不影响其余输出，也不改变退出码；只把 `history` 置为 `unavailable`、两项置空，stderr 一句说明。

### JSON（`schemaVersion` 仍为 1，只增）

```json
{
  "history": "complete",
  "modules": [
    {"id": "...", "lastTickAt": "2026-10-14T09:12:03+08:00", "firstTickAt": "2026-10-09T15:40:11+08:00",
     "tickCommits": 6, "suspendedAt": null}
  ]
}
```

- 时间都是提交时间原样（`%cI`），不换算时区。
- `tickCommits`：勾选过的提交次数，从没勾过为 `0`；`history` 为 `unavailable` 时为 `null`（与"从没勾过"区分）。
- 局限（写进说明）：todo 第一次提交时已有勾选项也算一次勾选，一次提交勾完整份 todo 的模块两个时间相同、次数为 1，
  算不出间隔，读取方应跳过次数小于 2 的模块；压缩合并（squash）会让次数偏少、间隔偏大。
- 稳定性承诺照旧；`history` 的三个取值在承诺之内。

### 表格

- `🔨 进行中 x/y` 后：`lastTickAt` 有值时加 `，上次勾选 <距今>`。
- `⏸ 挂起（原因）`：`suspendedAt` 有值时括号里加 `，已挂 <距今>`，例如 `⏸ 挂起（上游漏洞，已挂 2 天）`；没有原因时为
  `⏸ 挂起（未记原因，已挂 2 天）`。
- 关键卡点一行同样带 `，已挂 <距今>`。
- 距今写法：不到 1 小时写"不到 1 小时"，不到 1 天写"N 小时"，其余写"N 天"（向下取整）；"上次勾选"后面加"前"。
- `history` 为 `shallow` 时表头最后一行后加"（浅克隆：较早的勾选可能看不到）"；`unavailable` 时加"（没有 git 历史：
  不显示勾选与挂起时间）"。

### 检查点规则

`references/workflow-checkpoints.md`「Plan 检查点分级」的异常停点加一项："同一个 gate 因外部原因（上游未修复、缺权限、
要用户取舍）再次挡住"，并写明停下时给出挂起、接受风险、换方案等选项与代价，由用户决定；不按默认推荐继续重试。约定块
两份模板各加一行指向它（与已有的约定块行同一写法）。

### 文档

`docs/commands.md` 的 map 一节、`commands/map.md`、`spec-guard-ops` 的 map 一节写明两项时间与 `history`；`docs/design.md`
的 `map_view.py` 一行补一句；CHANGELOG `[0.63.0]`；版本号 0.63.0。

### 不变

- `phase-guard.sh` 与每轮注入逐字不变；`map-view` 已有字段与退出码不变；不写任何文件。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_map_view.py
python3 -B plugins/spec-guard/hooks/map_view.py --project . --json
```

## Testing strategy

在 `test_map_view.py` 用临时 git 仓库、固定提交时间（`GIT_COMMITTER_DATE`）构造历史，覆盖：勾选让 `lastTickAt` 前进；只改
文字不勾选、取消勾选不算；多个模块在同一提交里各自归属；`*`／`X` 写法；挂起标记提交后 `suspendedAt` 为该提交时间；标记
删掉后再在工作区加回（未提交）为 `null`；不是 git 仓库与没有提交时 `history` 为 `unavailable`；浅克隆为 `shallow`；JSON 键
集合（原有加三个）；表格的距今写法（测试用环境变量 `SPEC_GUARD_MAP_NOW` 注入固定的"当前时间"，不依赖真实时钟；这个变量只供测试，不写进命令说明）。本仓库实跑耗时 1 秒左右。
检查点规则与模板行用 `test_workflow_checkpoints.py` 的关键词断言。

## Boundaries

- **会做**：两项原始时间、`history`、表格距今、一条停点规则与模板行。
- **先问**：任何阈值、"停滞"判断、把时间放进每轮注入。
- **不做**：审查轮数；工作区未提交改动的时间；按项目历史算基准（读取方做）。

## Success criteria

1. 有挂起模块的仓库里，JSON 的 `suspendedAt` 等于写入标记那次提交的时间，表格显示"已挂 N 天"。
2. 进行中模块的 `lastTickAt` 等于最近一次勾选提交的时间；取消勾选、改文字不会让它前进。
3. 本仓库 93 个模块实跑在 1 秒左右；`map-view` 原有测试除键集合加上新字段外不改期望值。
4. decision-inbox 核对新增字段无异议。

## Open questions

- 无。
