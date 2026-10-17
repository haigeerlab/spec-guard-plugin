# Spec: map-startable

<!-- spec-guard: review approved 982ac79902f1 -->

## Objective

协调会话（module-crew）要决定「这一波开哪几个模块」，需要三样事实：Build order 里哪些模块被写成可并列的逗号组、每个模块声明的并行边界、
现在哪些模块可以开工且边界互不冲突。这些都在 spec-guard 管的文件里，`/map` 已经是读它们的唯一入口。本模块在开关 `moduleConcurrency`
为 `on` 时，给 `/map --json` 只增字段，并在表格里给可开工的模块加一句说明、在表格上方列出并行边界的重叠。

开关为 `off`、未设置或配置无效时，`/map` 的表格与 JSON 都与现在逐字节相同（`generatedAt` 这类本来就随时间变的字段除外）。选当前模块和阶段
计算不变。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图（同批 7 个模块）。来源：用户本人，经多模块并行需求讨论（2026-10-17～18），需求记录
第 5 节 A5 与 C1；字段形状按 module-crew 负责人会话 2026-10-18 的询问调整（顶层加开关值，见假设 2）。

## Assumptions

1. **只增不改，`schemaVersion` 仍为 1。** 已有字段的名字、取值、含义都不动。新字段只在开关为 `on` 时出现。
2. **顶层 `moduleConcurrency: "on"`。** module-crew 约定只读 `interface.json` 与 `/map --json`，不读 `.agent/config.json`，所以把开关值放进 JSON。
   只在 `on` 时出现；读取方把「没有这个字段」当作 off。这是需求清单之外加的一项。
3. **新字段的形状：**
   - 顶层 `buildOrderGroups`：按 Build order 排的二维数组，逗号组放在同一个子数组里，例如 `[["a"], ["b", "c"], ["d"]]`。取自能力图解析器
     现成的 `order_groups`，不另写解析。
   - 每个模块 `scope`：Spec 没有并行边界一节（或还没写 Spec）时为 `null`；格式正确时为 `{"exclusive": [...], "shared": [...]}`；格式错误时为
     `{"error": "<code>"}`。判据只用 `module_scope.parse`。
   - 顶层 `startable`：`{"modules": [...], "conflicts": [...]}`，见假设 4、5。
4. **「可开工」怎么判断。** 就绪沿用 `/map` 现有判定（`status == "ready"`：没开工、直接依赖全部完成、上游没有挂起）；先后**只按 Build order**
   （需求记录 A5）。`startable.modules` 按 Build order 列出**全部**就绪的模块。
   - 按现有判定，模块一有 Spec 就算进行中，所以就绪的模块一定还没有 Spec，也就没有并行边界，`scope` 为 `null`，不按冲突排除。冲突检查发生在
     协调会话让这些模块写完 Spec、批量审过之后：那时它们已是进行中，重叠出现在 `conflicts` 里，由协调会话决定谁先开始构建。
   - 取前几个（上限）由 module-crew 决定，spec-guard 不截断。
5. **冲突的定义。** 两个未完成模块（进行中或就绪）都有格式正确的并行边界，且独占路径重叠：相同，或一个是目录、另一个在它下面。`conflicts` 每项为
   `{"modules": [a, b], "paths": [...]}`，`a` 在 Build order 里排在 `b` 前面，`paths` 是重叠的路径（取较具体的那一个）。挂起与已完成的模块不参与。
6. **表格改两处，只在开关为 `on` 时。**
   - 就绪模块的状态格从「🟢 可以开始」改为「🟢 可以开始 · 可同时开工」；
   - `conflicts` 不为空时，在表头上方「待审核」（有「下一个 gate」时在它之后）、「未合入主线」之前加一行
     「并行边界重叠：billing 与 report（apps/shared/）；…」，每个冲突一项；没有冲突时不加这一行。
   其他行都不变。表格不显示 `scope` 和 `buildOrderGroups`。
7. **`worktree` 字段不在本模块。** 它要读本机其他 worktree，归下一个模块 `checkout-role`。
8. **`interface.json` 在本模块不改。** 新字段的含义写在本 Spec 的 Contract；到 `crew-interface` 统一把接口升到 1.1，并在接口说明里指向这里。

## Contract

### `hooks/map_view.py`

- `build(root)` 末尾：`project_config.module_concurrency(root)` 为真时，才往结果里加 `moduleConcurrency`、`buildOrderGroups`、`startable`，并给每个
  模块加 `scope`；为假时返回值与现在完全相同。
- 新函数 `_scope(root, module) -> dict | None`：读 `spec/<id>.md`，调 `module_scope.parse`；读不了时为 `{"error": "unreadable"}`。
- 新函数 `_overlap(a: Scope, b: Scope) -> list`：两份独占路径重叠的部分，按路径排序。
- `render`：开关为 `on` 时按假设 6 改就绪模块的状态格、加冲突那一行；为 `off` 时走原来的代码路径。

### 例子（开关为 on）

```json
{
  "moduleConcurrency": "on",
  "buildOrderGroups": [["setup"], ["billing", "shop"], ["report"]],
  "startable": {
    "modules": ["shop"],
    "conflicts": [{"modules": ["billing", "report"], "paths": ["apps/shared/"]}]
  },
  "modules": [{"id": "billing", "status": "in_progress", "scope": {"exclusive": ["apps/billing/", "apps/shared/"], "shared": []}, "...": "..."}]
}
```

### 文档

`docs/design.md` 里讲 map-view 的地方补一句「开关为 on 时只增字段」；CHANGELOG 未发布小节加一条「新增」。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_map_view.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- **`test_map_view.py` 先写失败的测试：**
  - 开关 off、未设置、配置无效时：同一个夹具（模块 Spec 里带并行边界、Build order 带逗号组）的 JSON（去掉 `generatedAt`）与表格，和本模块改动前
    的输出逐字节相同。做法：改代码之前先用现有实现生成这份输出，存成测试里的期望值；
  - 开关 on：`moduleConcurrency`、`buildOrderGroups` 的值；`scope` 三种情况（null、正常、error）；
  - `startable`：全部就绪模块按 Build order 列入；两个进行中模块重叠时进 `conflicts`；挂起、已完成模块不参与；目录与子路径算重叠，
    `apps/bill/` 与 `apps/billing/` 不算；`a` 排在 `b` 前，`paths` 取较具体的路径；
  - 表格：开关 on 时就绪模块带「可同时开工」，有冲突时出现「并行边界重叠」一行且位置在「未合入主线」之前，没有冲突时不出现；off 时都没有。
- **阶段提示与 verify-artifacts：** 本模块不改它们；两套回归原样全绿。
- **改坏验证：** 让 `_overlap` 用字符串前缀判断，确认「同名前缀不算重叠」变红；让新字段在开关 off 时也加上，确认「off 逐字节相同」变红。

## Boundaries

- Always：开关不是 `on` 时 `/map` 输出逐字节不变；新字段只增不改；并行边界只经 `module_scope.parse` 读；先后只按 Build order。
- Ask first：按关键路径或挡住的下游数给可开工模块排序；在 spec-guard 里截取前 N 个；改变 `ready` 或「进行中」的判定；在表格里显示 `scope`。
- Never：改选当前模块的逻辑或阶段计算；`/map` 写任何文件；在开关 off 时输出新字段。

## Success criteria

1. 开关为 `on` 时，`/map --json` 多出 `moduleConcurrency`、`buildOrderGroups`、`startable` 与每个模块的 `scope`，形状如 Contract 所写；
   `schemaVersion` 仍为 1。
2. `startable.modules` 按 Build order 列出全部就绪模块；`conflicts` 列出所有已知的重叠。
3. 开关为 `on` 时，表格里就绪模块的状态格带上「可同时开工」，有重叠时表格上方多一行「并行边界重叠」。
4. 开关为 `off`、未设置或配置无效时，表格与 JSON 与改动前逐字节相同（`generatedAt` 除外）。

## 文档建议

无。接口说明到 `crew-interface` 统一写。

<!-- spec-guard: external-review declined -->

## 变更记录

- 2026-10-18：去掉「排除与进行中模块边界重叠的就绪模块」（假设 4），`startable.modules` 改为列出全部就绪模块；表格从「就绪格写与 X 重叠」改为在表格上方加一行「并行边界重叠」（假设 6），测试策略与成功标准同步。原因：开工实现时发现，按现有判定模块一有 Spec 就算进行中，就绪模块一定没有并行边界，原排除规则与那句说明永远不会触发。来源：本会话实现 Task 1 前自查发现，用户本人决定按建议修订（2026-10-18）。
