# Spec: config-per-key

<!-- spec-guard: review approved bb9d7a7df926 -->

## Objective

`.agent/config.json` 现在是「一处不对、整份作废」：`project_config.load` 只要发现一个未知键或一个非法取值，
就把所有值清空，产物语言、批准节奏、多模块并行开关一起退回默认（`hooks/project_config.py:63-73`）。

真实后果出在版本错位上：一个团队里有人先升级、设了新版才认识的键（`moduleConcurrency` 就是这样加进来的），
还没升级的成员那边整份配置失效，连早就设好的 `artifactLanguage` 也不生效了；`commands/config.md` 与 README
只能靠一句「团队都升级后再设置」提醒。2026-10-22 多维度审查把它记为 F9（中），修复分组 G3「配置逐键容错」。

本模块改为逐键判定：某个键未知或取值非法，只让这个键失效并报告；其余合法的键照常生效。
只有文件本身坏了（读不了、不是 JSON、顶层不是对象、`version` 不对）才整体失效，这一部分与现在相同。

登记：2026-10-22 修复批次 12 个模块之一，经用户批准事项 C1 开模块会话；能力图依赖 `project-config`。

## Assumptions

以下是写 Spec 时定下的前提，请在批准时一并确认：

1. **结构问题仍然整体失效。** `unreadable`、`not-json`、`not-an-object`、`version-invalid` 四种照旧清空所有值。
   `version` 算结构问题：版本号不同意味着键的含义可能不同，逐键套用旧含义不安全。
2. **未知键：忽略这个键，报 `unknown-key`。** 不回显键名——配置文件是仓库内容，问题代码会进 agent 上下文，
   固定词表这条不变量保留；有几个未知键都只报一次 `unknown-key`。
3. **已知键取值非法：这个键按未设置处理，报 `<键>-invalid`。** 例如 `reviewCadence` 写成 `"both"`，
   批准节奏按默认 `separate`，产物语言等其他键照常生效。
4. **所有读取方只看自己那个键是否有效。** `module_concurrency`、`hint_language`、批准节奏行与 combined 下的
   下一步提示，都不再因为别的键有问题而失效。
5. **`check` 与 verify-artifacts 分两档。** 结构问题或已知键非法：仍判失败（这是本版本自己的键写错了，要修）。
   只有未知键：判通过并给警告（多半来自更新版本的 spec-guard，不该让旧版的检查变红）。
6. **`set`／`unset` 在只有逐键问题时允许写，只改目标键。** 其余键原样保留——包括未知键和非法值，不顺手删掉别人
   （可能是更新的版本）写的键；对目标键设一个合法值，就修好了它原来的非法值。结构问题时仍拒绝写入。
7. **不改文件格式、不升 `version`、不加配置项。** 对外接口 `interface.json` 不改：`/map` 的 `reviewCadence.source`
   仍只有 `.agent/config.json`、`default`、`default (config invalid)` 三种取值，后者现在表示「整份无效，
   或这个键自己的值无效」。
8. **旧版本改不了。** 0.83.1 及更早的 spec-guard 读到它不认识的键仍会整份失效；README 与 config 说明里「团队都升级后
   再设新键」的提醒保留，并补一句：从本版起，新版本遇到不认识的键只忽略那个键。
9. **`spec/project-config.md` 不重写。** 它的 Contract 里「出现未知键……都算配置无效」与「配置无效：追加一行……
   其余配置项一律不注入」两处被本 Spec 取代；只在那两处后面各加一句指向本 Spec 的说明，正文原样保留。

## Contract

### 问题代码分两类

| 类别 | 代码 | 效果 |
|---|---|---|
| 结构 | `unreadable`、`not-json`、`not-an-object`、`version-invalid` | 所有值清空，与现在相同 |
| 逐键 | `unknown-key`、`artifactLanguage-invalid`、`reviewCadence-invalid`、`moduleConcurrency-invalid` | 只有涉及的键失效，其余合法键照常返回 |

`project_config.py` 导出结构类代码的集合（例如 `STRUCTURAL`），调用方用它区分，不各自写死。

### `load(root)`

- 返回值形状不变：`(values, problems)`。
- 结构问题：`({}, [结构代码])`。
- 否则：`values` 是所有合法的已知键，`problems` 是逐键代码（顺序固定：`unknown-key` 在前，其余按 `VALIDATORS` 顺序）。
- 没有文件：`({}, [])`，不变。

### 阶段注入（`module_stage.py`）

- 结构问题：只出现现有那一行 `- Project config: invalid (<代码>) — run <config 命令>.`，逐字节不变。
- 逐键问题：合法键的行照常输出，后面再加一行：
  - 英文：`- Project config: ignored (<代码>) — the other settings apply; run <config 命令>.`
  - 中文（提示语言按 `hint-language-follow` 的判据，即有效的 `artifactLanguage` 恰为 `zh-CN`）：
    `- 项目配置: 已忽略 (<代码>)——其余设置照常生效；用 <config 命令> 查看。`
- `hint_language`、combined 节奏下 Spec 待审的下一步提示：只看 `artifactLanguage`／`reviewCadence` 自己是否有效。
- 没有配置文件、或配置完全合法时，所有现有输出逐字节不变。

### `module_concurrency(root)`

`moduleConcurrency` 自己有效且为 `on` 就是开；结构问题、未设、`off` 或它自己非法都是关。

### `summary`／`show`

- 结构问题：三项来源都是 `default (config invalid)`，与现在相同。
- 逐键问题：值非法的那个键来源为 `default (config invalid)`，其余键按实际来源（`.agent/config.json` 或 `default`）。
- 文本输出末尾的说明分两种：结构问题照旧「整份按默认」；逐键问题写「<代码> 已忽略，其余设置照常生效」。
- `--format json` 的字段不变（`items`、`problems`、`gitignored`）。

### `check`

| 情况 | 退出码 | 输出 |
|---|---|---|
| 合法 | 0 | `ok` |
| 只有 `unknown-key` | 0 | `ok (ignored: unknown-key)` |
| 结构问题或有已知键非法 | 1 | `.agent/config.json is invalid: <代码>`（与现在格式相同） |

### verify-artifacts

- 退出码 0 且输出带 `ignored`：警告「项目配置里有不认识的键，已忽略（可能来自更新版本的 spec-guard）」。
- 其余映射不变：0 通过、1 失败、其他为未验证。

### `set`／`unset`

- 结构问题：拒绝，退出码 2，与现在相同。
- 否则：只改目标键。写出时已知的合法键按固定顺序在前，其余原有键（未知键、值非法的已知键）按原文件顺序原样保留在后；
  预览差异如实显示。
- 读回核对：目标键读回为写入的值（`unset` 则不存在），其余原有键的原文不变。
- 键与取值的校验、`dispatch`／`trackerDefault` 的指引、预览不写、`--confirm` 原子写入，都不变。

### 说明文字

- `commands/config.md` 的「配置无效时」一节与 `moduleConcurrency` 一行、`skills/spec-guard-ops/SKILL.md` 的 config 一节、
  README 并行开关那一步：写明逐键容错、哪些仍整体失效、旧版本仍会整份失效。
- CHANGELOG 记一条（见 Open questions）。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_project_config.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_map_view.py
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先写测试并确认在当前代码上失败，再实现。
- `test_project_config.py`：一个未知键 + 合法 `artifactLanguage` → 语言生效、问题为 `unknown-key`；一个已知键非法 +
  其余合法 → 只有那个键缺席；多个逐键问题的代码顺序；四种结构问题仍清空；`module_concurrency` 在别的键非法时仍认 `on`；
  `summary` 的逐键来源；`check` 三档的退出码与输出；`set` 在有未知键时只改目标键、未知键与非法值原样保留、读回通过；
  用合法值修好非法键；结构问题时 `set` 仍拒绝。
- `test-phase-guard.sh`：未知键 + `zh-CN` → 中文提示照常且出现「已忽略」行；节奏非法 + 语言合法 → 语言行在、节奏行不在、
  出现 ignored 行；结构问题 → 只有原 invalid 行（逐字节同现在）；无配置与合法配置 → 逐字节同现在。
- `test-verify-artifacts.sh`：只有未知键 → 警告且不失败；已知键非法 → 失败；结构问题 → 失败。
- `test_map_view.py`：别的键有问题时 `reviewCadence` 的值与来源按它自己判定。
- 改坏验证（手工在草稿副本上做，结果记进 todo）：把逐键问题改回清空全部值、把 `unknown-key` 判为失败、
  `set` 时丢掉未知键，三处都必须让测试变红。

## Boundaries

- Always：先红后绿；只有 `project_config.py` 一处解析配置；问题代码是固定词表、不回显文件内容；hook 只读；
  无配置文件或配置合法时所有既有输出不变。
- Ask first：改 `interface.json`；增加配置项或改 `version`；改结构问题的判据。
- Never：把非法值当成合法值套用；`set`／`unset` 删掉不是目标的键；在 Spec、代码、测试、提交信息中写入使用者项目的
  名称、模块或编号。

## 并行边界

- 独占：`spec/config-per-key.md`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/commands/config.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、`README.md`、`spec/project-config.md`
- 公共：无

## Success criteria

- 配置里多一个不认识的键时，产物语言、批准节奏、并行开关照常生效，阶段提示多一行「已忽略」，`check` 通过并提示。
- 一个已知键取值非法时，只有它退回默认，其余照常；`check` 与 verify-artifacts 判失败并点名该键的代码。
- 文件结构损坏时，行为与现在逐字节相同。
- `set`／`unset` 不会删掉未知键或别的键的原值。
- 无配置文件与合法配置的所有既有回归逐字节通过；`interface.json` 不变。

## Open questions

1. **CHANGELOG 与版本号**：本批 12 个模块都会写 CHANGELOG。本模块按惯例在 `CHANGELOG.md` 顶部未发布段加一条，
   还是由模块协调在发版时统一汇总？未定前本模块不改 `CHANGELOG.md` 与版本号。
