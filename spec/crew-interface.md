# Spec: crew-interface

<!-- spec-guard: review approved e9554b941354 -->

## Objective

多模块并行规划层的前六个模块已经做完：并行开关、并行评估、并行边界与越界检查、协调会话的批准与合并规则、`/map` 的可开工信息、checkout 角色。
运行时插件 module-crew 约定只通过 `interface.json` 和 `/map --json` 读 spec-guard，不读内部文件。本模块把这些能力登记进 `interface.json`
（接口版本从 1.0 升到 1.1，只加不改），收好对外说明，并把这一批合成 0.68.0 交给你决定推送、开 PR 与发版。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图（同批 7 个模块，本模块排最后）。来源：用户本人，经多模块并行需求讨论（2026-10-17～18），
需求记录第 5 节 C1。入口键名与命令形式在 2026-10-18 应 module-crew 负责人会话的询问先给了打算（`scopeCheck`、`reviewMark`、`checkoutRole`），
本 Spec 定稿。

## Assumptions

1. **只加不改，接口版本 1.1。** `interface` 从 `"1.0"` 改为 `"1.1"`；`mapView` 已有的字段名、取值、含义一字不改。按 plugin-interface 的约定，只增加
   内容升次版本，读 1.x 的使用方（decision-inbox、module-crew）不受影响。`interface.json` 是随插件发布的静态说明，不受开关控制。
2. **新增的顶层入口（键名定稿）：**
   - `moduleConcurrency`：开关说明——配置位置 `.agent/config.json` 的 `moduleConcurrency`、取值 `off`／`on`、默认 `off`；使用方读法：看 `/map --json`
     顶层有没有 `"moduleConcurrency": "on"`，没有就当作 off；契约 `spec/module-concurrency-switch.md`。
   - `scopeCheck`：越界检查。`command` 为 `python3 -B hooks/module_scope.py check --project <project-root> --module <module-id> --base <base-ref> --format json`，
     退出码 0／2／3／4 的含义，`values.scope` 为 `exclusive`／`own`／`outside` 的含义，契约 `spec/module-scope-boundary.md`。
   - `checkoutRole`：角色标记。`commands` 下分 `show`、`setModule`、`setCoordinator`、`clear` 四条命令（参数 `<checkout-root>`、`<module-id>`），
     写入类命令另附「不带 `--confirm` 只预览」；退出码 0／2／3／4；`values.role` 为 `module <id>`、`coordinator` 的含义；标记位置说明；契约 `spec/checkout-role.md`。
   - `reviewMark`：评审标记。`command` 为 `python3 -B hooks/review_mark.py --project <project-root> --module <module-id> --target <spec|plan|both> --state <pending|approved>`，
     附「不带 `--confirm` 只预览」与退出码 0／2；`notes` 写明：`approved` 只在用户明确批准后写，开关为 on 时由协调会话写（见共享规则「协调会话的批准与合并」）；
     契约 `spec/review-approval-marker.md`。
3. **`mapView` 里只增一项 `concurrency`**：列出开关为 on 时才出现的字段（顶层 `moduleConcurrency`、`buildOrderGroups`、`startable`，模块级 `scope`、`worktree`）、
   「开关不是 on 时都不出现、输出与 1.0 时逐字节相同」，以及契约 `spec/map-startable.md`、`spec/checkout-role.md`。`schemaVersion` 仍为 1。
4. **一致性检查跟着扩展。** `scripts/check-interface.py` 现在核对 `mapView` 与代码常量；本模块加：四个新入口的命令所引用的脚本都存在；`scopeCheck.values.scope`
   与 `module_scope` 的取值一致、`checkoutRole.values.role` 的种类与 `checkout_role` 一致、`moduleConcurrency.values` 与 `project_config` 一致。为此在
   `module_scope.py` 与 `checkout_role.py` 各加一个取值常量（`SCOPES`、`ROLE_KINDS`），代码里的字面量改为引用它，行为不变。
5. **对外说明。** `docs/design.md`「对外接口」一节列出新入口；README 中英文加一节「多模块并行（可选）」：开关怎么开、开了以后 spec-guard 提供什么、运行时由
   module-crew 负责、开关不开时一切照旧。这也是「能力图全部完成」停点要表态的 README 更新。
6. **版本与发版材料。** 两份 `plugin.json` 升到 `0.68.0`，README 中英文的 `--ref` 改为 `v0.68.0`，CHANGELOG 的「未发布」改为 `[0.68.0] - <发版日期>`，
   导语写明本版的 7 个模块。推送、开 PR、合并、打 tag 都在最终 gate 上问你，不在本模块里自行进行；发版后的步骤按 `docs/release-process.md` 另走。
7. **收尾核对。** 按 checkout-role 的约定，在本模块最后再跑一次 `evals/hint-english-diff.sh v0.67.1`（英文提示与 0.67.1 逐字节相同、中文无英文标签），确认这一批没有
   破坏 #345 的保证；另用改动前提交的 hooks 对开关不是 on 的夹具做最后一次整份比对。

## Contract

### `plugins/spec-guard/interface.json`

```json
{
  "interface": "1.1",
  "mapView": { "...": "1.0 的内容不变", "concurrency": { "appearsWhen": "moduleConcurrency is on", "fields": { "...": "..." }, "contracts": ["spec/map-startable.md", "spec/checkout-role.md"] } },
  "moduleConcurrency": { "config": ".agent/config.json", "key": "moduleConcurrency", "values": { "off": "...", "on": "..." }, "default": "off", "readFrom": "...", "contract": "spec/module-concurrency-switch.md" },
  "scopeCheck": { "command": [ "python3", "-B", "hooks/module_scope.py", "check", "--project", "<project-root>", "--module", "<module-id>", "--base", "<base-ref>", "--format", "json" ], "exitCodes": { "0": "...", "2": "...", "3": "...", "4": "..." }, "values": { "scope": { "exclusive": "...", "own": "...", "outside": "..." } }, "contract": "spec/module-scope-boundary.md" },
  "checkoutRole": { "commands": { "show": [ "..." ], "setModule": [ "..." ], "setCoordinator": [ "..." ], "clear": [ "..." ] }, "confirm": "...", "exitCodes": { "0": "...", "2": "...", "3": "...", "4": "..." }, "values": { "role": { "module <id>": "...", "coordinator": "..." } }, "marker": "...", "contract": "spec/checkout-role.md" },
  "reviewMark": { "command": [ "..." ], "confirm": "...", "exitCodes": { "0": "...", "2": "..." }, "notes": "...", "contract": "spec/review-approval-marker.md" }
}
```

各说明文字用英文（与 1.0 一致），写在实现里；上面的 `...` 由实现按假设 2、3 填写。

### `scripts/check-interface.py`、`module_scope.py`、`checkout_role.py`

见假设 4。

### 文档与版本

`docs/design.md`、README 中英文、CHANGELOG、两份 `plugin.json`，见假设 5、6。

## Commands

```bash
python3 scripts/check-interface.py
python3 -B plugins/spec-guard/hooks/test_module_scope.py
python3 -B plugins/spec-guard/hooks/test_checkout_role.py
/bin/bash scripts/validate.sh
/bin/bash evals/hint-english-diff.sh v0.67.1
```

## Testing strategy

- **`check-interface.py` 的正反用例（先红后绿）：** 现有的检查有夹具测试的话沿用；用临时 `interface.json` 验证：缺少新入口的脚本、`values.scope` 多一个或少一个取值、
  `checkoutRole.values.role` 种类不符、`moduleConcurrency.values` 不符时都报错；本仓库的 `interface.json` 通过。
- **常量重构不改行为：** `test_module_scope.py`、`test_checkout_role.py` 原样全绿。
- **只加不改：** 测试断言新 `interface.json` 去掉新增的键（四个顶层入口与 `mapView.concurrency`）并把 `interface` 还原为 `"1.0"` 后，与 v0.67.1 的 `interface.json`
  逐字节相同（一次性比对，记进 todo）；长期断言 `mapView` 的 1.0 字段仍在。
- **收尾核对：** 假设 7 的两项，结果记进 todo。
- **改坏验证：** 删掉 `scopeCheck` 引用的脚本路径中的一个字符，确认 `check-interface.py` 报错；把 `module_scope.SCOPES` 改掉一个值，确认一致性检查报错。

## Boundaries

- Always：`mapView` 的 1.0 内容一字不改；新入口的命令与代码实际参数一致；接口版本只升次版本；推送、开 PR、合并、打 tag 都先问用户。
- Ask first：升接口主版本；在 `interface.json` 里登记本批以外的命令；改 `/map --json` 的 `schemaVersion`。
- Never：让 `interface.json` 的内容随开关变化；在本模块里推送或合并；删除或改名 1.0 已有的键。

## Success criteria

1. `interface.json` 为 1.1，登记 `moduleConcurrency`、`scopeCheck`、`checkoutRole`、`reviewMark` 四个入口与 `mapView.concurrency`，1.0 内容逐字不变；`check-interface.py` 核对通过，
   且能拦下不一致。
2. 对外说明（设计文档、README 中英文）写明多模块并行的用法与边界；CHANGELOG 与版本号为 0.68.0。
3. 收尾核对通过：英文阶段提示与 0.67.1 逐字节相同、中文无英文标签；开关不是 on 时的整份比对逐字节相同。

## 文档建议

这是能力图全部完成的停点，按规则对 README 表态：**更新**——中英文各加一节「多模块并行（可选）」（假设 5）。另建议在 `docs/design.md` 的「对外接口」后加一小节，
把规划层与运行层（module-crew）的分工画清楚（谁读什么、谁写什么），已并入假设 5 的设计文档改动。没有其他收尾文档。

<!-- spec-guard: external-review declined -->
