# Spec: takeover-config

<!-- spec-guard: review approved e4e87436357e -->

## Objective

给项目和单个模块设「接管档位」：Spec 批准、Plan 批准、合并、发布四项，各自由人做还是交给 AI。spec-guard 只存、读、报告每个模块的
生效值与来源；按档位放行（记 Codex 批准、自动合并、自动发布）由后续模块和 autopilot、module-crew 做。同时退役 `autonomyTier` 与
`moduleAutonomy`。

给谁用：设档位的用户；按 `/map --json` 读档位的 autopilot（合并、发布）与 module-crew（交审消息里写清每项谁批）。

对外接口与用法草案一致吗：一致。对应 `spec/usage/auto-takeover.md` 入口「`/spec-guard:config` 设 `takeover`／`moduleTakeover`」与
「`/spec-guard:map --json` 的 `takeover` 字段」，典型用法 U1。

登记：S101 自动接管，合并方案 r2、r3 经用户批准（总账 `bfce091`、`1d5fd45`、`c7c0d48`；autopr-design #21876，ecosystem-lead #21841、
#21864、#21883 转述）。用户在本会话确认需求「说完了」、确认插入能力图「确认插入；Q1 B」。账本 T1T36MR。

**返工（2026-11-26，0.97.0）**：假设 8 说好的「下一版删」一直没做。功能盘点核对过三家调用方（autopilot、module-crew、decision-inbox）的代码，已经没有谁读 `/map` 的 `autonomy` 字段、
`interface.json` 的 `autonomyTier`／`moduleAutonomy` 条目。用户经 ecosystem-lead 转达「按你的建议做」（#23169），在本会话回「两件都做，Claude 写码」；返工 Spec 2026-11-26 用户回「批准；Q1 A；Q2 A」。
本次只删死代码与退役接口，见假设 11～13；module-crew 那边自己的读取代码由 ecosystem-lead 另请它删。

## Assumptions

1. **存在哪**：`.agent/config.json` 新增两个键。
   - `takeover`（项目）：预设名 `none`／`plan`／`merge`，或自定义对象 `{"spec", "plan", "merge", "release"}`。
   - `moduleTakeover`（模块）：模块 id → 同样的值（预设名或对象）。
   不写进 Spec、todo（同 `moduleAutonomy`，避免改批准指纹）。
2. **四项的取值**：`spec`、`plan` 为 `human`／`codex`；`merge` 为 `human`／`auto`；`release` 为 `human`／`prepare`／`auto-confirm`／`auto`。
   自定义对象里没写的项按 `human`；有不认识的项或取值，整个键失效（config-per-key）。
3. **预设展开**（每项从严到宽）：
   | 预设 | spec | plan | merge | release |
   |---|---|---|---|---|
   | `none`（默认） | human | human | human | human |
   | `plan` | human | codex | human | human |
   | `merge` | codex | codex | auto | human |
   发布只能用自定义对象打开，三个预设都是 `human`（方向文档把自动发布列为单独勾选项，试点保持 `human`）。
4. **生效值**：模块在 `moduleTakeover` 里有值就用它（来源 `moduleTakeover`）；否则用 `takeover` 的生效值（来源 `takeover` 或 `default`）；
   键不合法时回到下一层，来源写 `default (config invalid)`（同 `moduleAutonomy`）。
5. **宽于项目只提醒、不截断**：任一项比项目生效值宽（顺序见假设 2、3），`/map --json` 标 `widerThanProject: true`，`config set` 预览多一行
   note。截断与执行在调用方。
6. **发布的两条限制只提示**：`config set` 写出 `release` 为 `auto-confirm` 或 `auto` 时，预览多两行提示——流水线自用的四个插件
   （spec-guard、module-crew、delegate、agent-relay）最高 `prepare`；`auto` 只给能快速回滚的项目。真正的拦截在 autopilot 内核（合并方案 8.4，
   总账 `c7c0d48`）。spec-guard 照存。
7. **怎么写**：`project_config.py set --key takeover --value <预设名|JSON 对象>`；`set --key moduleTakeover --module <id> --value ...`；
   `unset` 同 `moduleAutonomy` 的做法。都先预览、`--confirm` 写入并读回；写入要用户原话（规则文字）。预览写明四项各由谁做、和写入前比改了哪几项。
   「放宽一次一档」不在这里限：首次设置可以一步到 `merge`；出事收窄之后的恢复按一次一档，由 `takeover-narrow` 管（它记收窄记录）。
8. **autonomyTier、moduleAutonomy 退役，不映射**（Q8）：
   - 文件里还有这两个键时：`show` 列出并标「已退役，不生效」，提示改设 `takeover`；`check` 与 verify-artifacts 只警告、不判失败；不自动改文件。
   - `set` 这两个键退出 2 并说明已退役；`unset` 仍可用（让用户清掉）。
   - `/map --json` 里旧的 `autonomy` 字段本版保留、照旧按这两个键计算，`interface.json` 标 deprecated，下一版删；给调用方一个版本的切换窗口
     （合并方案第 6 节第 7 步）。
9. **spec-guard 自己的行为本模块不变**：阶段提示、停点规则、批准判定都不读 `takeover`；按档位放行由 `codex-approval`、
   `codex-final-acceptance` 等后续模块接上。workflow-checkpoints「自治档位与底线」一节本模块只把 autonomyTier 改为已退役的说明，
   底线按勾选项重写放在 `codex-approval`。
10. **接口 1.15**：`/map --json` 每个模块加 `takeover: {"spec", "plan", "merge", "release", "source", "widerThanProject"}`，任何开关下都出现；
    `interface.json` 新增 `takeover`、`moduleTakeover` 条目，`autonomyTier`、`moduleAutonomy` 与 `mapView.autonomy` 标 retired／deprecated。
11. **旧版本兼容**：0.68.0 起不认识的键只忽略；说明与 CHANGELOG 提醒「团队都升级后再设置」。版本号不在本模块改（0.91.0 在 `codex-final-acceptance`）。

11. **删掉什么**（返工）：
    - `/map --json` 每个模块的 `autonomy` 字段（`map_view.AUTONOMY_FIELDS` 与计算它的代码）；
    - `project_config` 里只为它服务的 `module_tier`、`project_tier`（读 `autonomyTier`／`moduleAutonomy` 算档位）；
    - `interface.json` 的 `autonomyTier`、`moduleAutonomy` 两个条目与 `mapView.autonomy`；`check-interface.py`、`scripts/test-checkers.sh` 夹具里对应的比对；
    - 文档里描述这两个键「还在 `/map` 里算」的句子。
12. **文件里还留着这两个键怎么办**（返工，Q1 A）：照旧认作 `retired-key`——不生效、`show` 标「已退役」、`check` 与 verify-artifacts 只警告、
    `set` 拒绝、`unset` 可用。只删「拿它们算档位」的代码，留下识别与清理的入口。
13. **接口 1.25**（返工，Q2 A）：删的是 1.15 起就标了 deprecated、没人读的字段，按次版本升；不升 2.0，因为 module-crew 读 spec-guard 接口时要求主版本一致，
    升 2.0 会让它整体不认。CHANGELOG 与发版通知写明「移除了 `mapView.autonomy`、`autonomyTier`、`moduleAutonomy` 三个接口条目」。版本号沿用同批的 0.97.0，本返工不再改。

## Contract

### C1 配置（`hooks/project_config.py`）

- `VALIDATORS` 加 `takeover`、`moduleTakeover`（假设 1、2）；`DEFAULTS` 加 `"takeover": "none"`、`"moduleTakeover": {}`。
- 新函数 `module_takeover(root, module_id) -> (items, source)`（`items` 为展开后的四项）与批量版 `module_takeovers(root, ids)`，是生效值的唯一判据。
- `set`／`unset` 接受这两个键；`--module` 对 `moduleTakeover` 有效；预览按假设 5、6、7 输出 note 与提示。
- `autonomyTier`、`moduleAutonomy`：`set` 退出 2 并说明已退役；`show`／`check` 按假设 8。原 `module_tier` 保留，只供 `/map` 的 deprecated 字段用。

### C2 `/map --json`（`hooks/map_view.py`）

- 每个模块加 `takeover`（假设 10）；文字版不加列；`autonomy` 字段照旧输出。

### C3 verify-artifacts

- `moduleTakeover` 里有能力图上没有的 id 时，每个 id 一条 ⚠️（同 `moduleAutonomy`）；文件里有已退役的两个键时一条 ⚠️；不合法的 `takeover`／`moduleTakeover` 判失败。

### C4 接口与说明

- `interface.json` 升 1.15（假设 10）；`scripts/check-interface.py` 核对 `mapView.takeover` 字段名与 `map_view` 一致，`test-checkers.sh` 加反例。
- `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`（config 与 `/map`）、`docs/concepts.md`（自治档位一行改为接管档位）、
  `references/workflow-checkpoints.md`「自治档位与底线」写明 autonomyTier 已退役（底线文字不在本模块改）。
- CHANGELOG 不在本模块写：仓库没有 `Unreleased` 小节的惯例，0.91.0 的 CHANGELOG 在 `codex-final-acceptance` 一次写全六个模块。

## Acceptance criteria

- **AC1** `test_project_config.py`：三个预设与自定义对象 `set` 各成功；自定义缺项按 `human`；不认识的项、取值、模块 id，非字符串非对象的值，
  `set` 退出 2 不写；文件里不合法时只这个键失效、`check` 失败、其余键照常；`--module` 用在 `takeover` 上退出 2；宽于项目时预览有 note；
  `release` 为 `auto-confirm`／`auto` 时预览有两行限制提示。
- **AC2** `module_takeover`：模块有值取模块；无值随 `takeover`（设了、未设、不合法三种来源）；`moduleTakeover` 不合法时回到项目；预设展开按假设 3。
- **AC3** 退役：文件里有 `autonomyTier`／`moduleAutonomy` 时 `show` 标已退役、`check` 不失败只警告；`set` 这两个键退出 2；`unset` 可用。
- **AC4** `test_map_view.py`：每个模块有 `takeover` 六个字段；设与未设、宽于项目各对；没有配置文件时全为 `human`、来源 `default`；`autonomy` 字段与改前相同；
  文字版输出不变。
- **AC5** 阶段提示：设了 `takeover`／`moduleTakeover` 与未设时输出逐字相同（`test-phase-guard.sh`）。
- **AC6** verify-artifacts：能力图上没有的 id、已退役的键各报警告不判失败；不合法值判失败（`test-verify-artifacts.sh`）。
- **AC7** `interface.json` 1.15，`check-interface.py` 通过，改掉字段名时变红；`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿。

- **AC9**（返工）`/map --json` 的模块对象里没有 `autonomy` 键，其余键与改前相同；`interface.json` 版本 1.25，没有 `autonomyTier`、`moduleAutonomy`、`mapView.autonomy`；`check-interface.py` 与 `test-checkers.sh` 通过。
- **AC10**（返工）文件里还有 `autonomyTier`／`moduleAutonomy` 时，`show`、`check`、verify-artifacts、`set`、`unset` 的结果与 0.96.2 相同（AC3 不变）；阶段提示不变。
- **AC11**（返工）仓库里除 CHANGELOG、`spec/`、`tasks/`、`docs/releases/` 的历史记录外，没有代码或文档再说 `/map` 会按这两个键计算。

## Open questions（返工）

- **Q1 文件里还留着这两个键怎么办？**（2026-11-26 用户选 A）
  - A（推荐）：照旧认作 `retired-key`，警告、`unset` 可清（假设 12）。不打扰还没清的项目，代码只多留一个识别分支。
  - B：当成不认识的键（`unknown-key`），只忽略。代价：提示里不再说它们是退役键、该改设 `takeover`；`unset` 能不能清要看不认识的键的规则。
- **Q2 接口版本怎么升？**（2026-11-26 用户选 A）
  - A（推荐）：1.24 → 1.25（假设 13）。
  - B：升 2.0。代价：module-crew 现在会因主版本不一致整体不认 spec-guard，要它同步改。

## Boundaries

- **会做**：C1～C4 及回归。
- **先问再做**：改阶段提示或停点规则的行为；改预设的展开；删掉 `autonomy` 字段（本版只标 deprecated；返工时用户已同意删，见假设 11）。
- **不做**：按档位放行任何事（后续模块）；收窄入口与恢复限档（`takeover-narrow`）；发布限制的拦截（autopilot）；改 module-crew、autopilot 的读取方；
  改版本号与发版。

## 并行边界

- 独占：`spec/takeover-config.md`、`tasks/takeover-config/`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/commands/config.md`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/concepts.md`、`docs/design.md`、`CHANGELOG.md`
- 公共：无

## 文档建议

改 `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/concepts.md`；CHANGELOG 与 README 本模块不改，
最后一个模块统一加「自动接管」一段。项目没有文档基线。
