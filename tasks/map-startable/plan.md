# Plan: map-startable

<!-- spec-guard: review approved -->

依据 [`spec/map-startable.md`](../../spec/map-startable.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-18 单独批准（`45f2c69`，用户决定不做外部
审查），按用户定的顺序在 `concurrency-rule-wording` 验收后写本 Plan，单独交审。分支 `claude/module-concurrency`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`。按批量发版约定不改版本号、不推送、不开 PR；验收后进入 `checkout-role`，字段定稿后通知 module-crew。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先用测试锁住「开关不是 on 时与没有开关一样」，再加 JSON 的四个新字段，然后改表格里就绪模块那一格，最后用一次整份比对证明 off 时与改动前的实现逐字节相同。

## Architecture Decisions

- **「off 逐字节不变」和上个模块一样分两层，请留意与 Spec 写法的出入。** Spec 写的是「改代码之前先用现有实现生成输出，存成测试里的期望值」。存成长期夹具，
  以后任何合规改动 `/map` 的模块（下一个 `checkout-role` 就会改它）都得连夹具一起改，测试就失去了意义。所以：
  - **长期断言**（留在 `test_map_view.py`）：同一个夹具（Spec 带并行边界、Build order 带逗号组）在开关 off、未设置、配置无效三种情况下，JSON（去掉
    `generatedAt`）和表格都与「删掉 `.agent/config.json`」时逐字节相同；JSON 的顶层与模块字段集合仍等于现有的 `TOP_KEYS`、`MODULE_KEYS`。
  - **一次性整份比对**（Checkpoint 1）：用改动前提交里的 `map_view.py` 与改动后的版本，对同一组夹具（含无配置、off、未设置、无效配置）各跑一次，
    JSON（去掉 `generatedAt`）与表格逐字节相同。结果记进 todo。
- **新字段集中在 `build()` 末尾一处加。** `module_concurrency(root)` 为假时直接返回原来的 dict，不经过任何新代码；为真时再读并行边界、算 `startable`。
- **并行边界只经 `module_scope.parse` 读；重叠判断写成 `_overlap(a, b)`，按路径段比较**（`apps/bill/` 与 `apps/billing/` 不算重叠）。
- **`buildOrderGroups` 取自 `parse_map(...).order_groups`**，不另写解析。
- **表格改两处**：`_status_cell` 里 `ready` 那一支在开关为真时加后缀；`render` 在开关为真且有冲突时，在「未合入主线」一行前插一行。开关为假时都走原来的代码路径。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：off 等同于没有开关的长期断言（预期直接绿）

在 `test_map_view.py` 新增 `ConcurrencyOff` 测试：夹具里 Spec 带并行边界、Build order 带逗号组；开关 off、未设置（只有 `version`）、配置无效三种情况下，
JSON（去掉 `generatedAt`）与表格都和删掉配置文件时逐字节相同，字段集合等于 `TOP_KEYS`／`MODULE_KEYS`。现在还没有新代码，预期直接绿；先在夹具里临时
把一个字段改掉，确认比较真的会报差异。

- 验收：新用例绿，原有用例不变。

### Task 2：开关 on 时的 JSON 新字段（先红后绿）

先写失败的用例（Spec 测试策略第二、三组）：
- `moduleConcurrency == "on"`；`buildOrderGroups` 按 Build order，逗号组在同一子数组；
- `scope` 三种情况：没有 Spec 或没有这一节为 `null`，正常为 `{"exclusive", "shared"}`，格式错误为 `{"error": "<code>"}`；
- `startable`：全部就绪模块按 Build order 列入；两个进行中模块重叠时进 `conflicts`；挂起、已完成模块不参与；目录与子路径算重叠，
  `apps/bill/` 与 `apps/billing/` 不算；`conflicts` 里 `a` 排在 `b` 前、`paths` 取较具体的路径；
- `schemaVersion` 仍为 1。

再实现 `_scope`、`_overlap` 与 `build()` 末尾的新字段。

- 验收：新旧用例全绿。

### Task 3：表格里就绪模块的说明与冲突一行（先红后绿）

先写失败的用例：开关 on 时，就绪模块状态格是「🟢 可以开始 · 可同时开工」；有冲突时，表头上方多一行「并行边界重叠：a 与 b（路径）」，位置在
「未合入主线」那一行之前，没有冲突时不出现；其他行不变；off 时都没有。再改 `_status_cell` 与 `render`。

- 验收：用例全绿。

### Checkpoint 1（report）：一次性整份比对、三套核心回归与改坏验证

- 一次性整份比对（见 Architecture Decisions），对象是改动前提交里的 `map_view.py`；
- 改坏验证：让 `_overlap` 用字符串前缀判断，确认「同名前缀不算重叠」变红；让新字段在开关 off 时也加上，确认 `ConcurrencyOff` 变红。都复原；
- 三套核心回归全绿。

结果记进 todo。

### Task 4：设计文档与 CHANGELOG

`docs/design.md` 的 `map_view.py` 一行补「开关为 on 时只增字段（`spec/map-startable.md`）」；CHANGELOG「未发布」小节「新增」加一条。

- 验收：`verify-and-commit.sh` 通过。

### Checkpoint 2（gate）：模块验收

在正文列出：实际改动的文件（标出超出预计的）；一个演示项目在开关 on 时的 `/map` 表格与 JSON 新字段原文；整份比对结果；验证结果与未验证项；文档建议；
拟回告：把实现与定稿一致（或有出入之处）告诉 module-crew。

用户验收后勾选并提交，进入 `checkout-role`。

- 验收：用户验收通过。

## 影响面

- 修改：`hooks/map_view.py`、`hooks/test_map_view.py`、`docs/design.md`、CHANGELOG；
- 本模块的 Plan 与 todo。不改 `module_scope.py`、`capability_map.py`、阶段提示与 `interface.json`。

## Risks and Mitigations

- **`/map` 是 decision-inbox 与 module-crew 都在读的接口。** 只增字段、只在 on 时出现，长期断言锁住 off 等同于没有开关，一次性比对证明与改动前逐字节相同。
- **读并行边界让 `/map` 变慢。** 只在开关 on 时读，每个未完成模块的 Spec 读一次。
- **长期断言比整份比对弱。** 和上个模块相同的取舍，整份比对的结果记在 todo 里可复查。

## Open Questions

- 无。

## 变更记录

- 2026-10-18：Task 2 去掉「就绪且与进行中模块重叠的被排除」的用例，Task 3 改为「就绪格统一写可同时开工＋表格上方冲突一行」，架构决定同步。原因：随 Spec 修订（就绪模块一定没有并行边界，原排除规则永远不会触发）。来源：本会话实现前自查发现，用户本人决定按建议修订（2026-10-18）。
