# Spec: module-autonomy

<!-- spec-guard: review approved 55b8e3b31635 -->

## Objective

「项目定上限，需求定实际」：项目级 `autonomyTier` 之外，允许给单个模块另设实际自治档位（例如小修复用 `relaxed`、改判据的模块用
`strict`）。spec-guard 只存、读、报告每个模块的生效档位与来源；各档放开什么仍由 module-crew 定义，按项目上限截断由调用方
（module-crew、autopr）做。

给谁用：按 `/map --json` 派活的运行时（module-crew）与 GitHub 侧准入（autopr）；设置档位的用户。

登记：需求由 autopr-design 会话提出（bridge #21569 的 1a）。2026-11-19 用户在本会话确认需求「先做 1a」「说完了，第 3 条选甲」（档位名称
先沿用 strict／standard／relaxed），并确认插入能力图「确认插入」。账本 T1T36MR。

## Assumptions

1. **存在哪**：`.agent/config.json` 新增键 `moduleAutonomy`，值是对象：键为模块 id（kebab-case，同能力图的 id 规则），值为
   `strict`／`standard`／`relaxed`。不写进 Spec（会改变批准指纹）、不写进 todo（那是进度不是授权）。
2. **取值不合法**按 config-per-key：对象形状不对、某个 id 不合规或某个档位不在三档里，整个 `moduleAutonomy` 键失效（所有模块回到
   项目档位，来源报「config invalid」），verify-artifacts 判失败，其余键照常。粒度到键而不是到条目，和现有规矩一致。
3. **生效值**：模块在 `moduleAutonomy` 里有值就用它（来源 `moduleAutonomy`）；否则用 `autonomyTier` 的生效值（来源随它：
   `autonomyTier` 或 `default`）。
4. **宽于项目档位只提醒、不截断**：档位从严到宽为 `strict` < `standard` < `relaxed`。模块档位宽于项目生效档位时，`/map --json`
   该模块标 `widerThanProject: true`，`config set` 预览多一行提醒。spec-guard 不读 autopr 的 `readiness-conclusion.json`，也不替调用方
   取 min——项目上限在调用方那里。
5. **能力图上没有的 id**：不让键失效（模块可能稍后插入，或刚改名），verify-artifacts 对每个这样的 id 报一条警告；`/map` 忽略它们。
6. **怎么写**：`project_config.py set --key moduleAutonomy --module <id> --value <档位>`，只改这一个条目；`unset --key moduleAutonomy
   --module <id>` 去掉一个条目，最后一个条目去掉后整个键删除；`unset --key moduleAutonomy` 不带 `--module` 去掉整个键。都照现有流程
   预览、`--confirm` 写入并读回。`--module` 只对 `moduleAutonomy` 有效，其他键带它退出 2。写入要用户原话（同 `autonomyTier`，规则文字）。
7. **spec-guard 自己的行为不随它变**：阶段提示不注入、停点规则与底线不变（同 `autonomyTier`）。`show` 文本与 JSON 列出它（值为对象，
   未设时为 `{}`、来源 `default`）。
8. **接口 1.14**：`/map --json` 每个模块加 `autonomy: {"tier", "source", "widerThanProject"}`，任何开关下都出现；`interface.json`
   新增 `moduleAutonomy` 条目并在 `mapView` 写明新字段；其余字段不变。
9. **旧版本兼容**：0.68.0 起不认识的键只忽略（`unknown-key` 警告），0.67.1 及更早整份配置判无效；config 说明与 CHANGELOG 照
   `autonomyTier` 的写法提醒「团队都升级后再设置」。
10. **版本号 0.89.0**（新增配置项与接口字段，次版本号）。

## Contract

### C1 配置（`hooks/project_config.py`）

- `VALIDATORS` 加 `moduleAutonomy`：`dict`，每个键匹配 `capability_map.MODULE_ID`，每个值在 `TIERS` 里；空对象合法。
- `DEFAULTS` 加 `"moduleAutonomy": {}`；新函数 `module_tier(root, module_id) -> (tier, source)` 是生效档位的唯一判据（`/map`、调用方都用它）。
- `set`／`unset` 加 `--module`，行为见假设 6；预览在模块档位宽于项目档位时多一行 `note: <id> 的档位 <x> 宽于项目档位 <y>；spec-guard 不截断，按项目上限截断由调用方做`。
- `config_lines`（阶段提示）对它不输出任何行。

### C2 `/map --json`（`hooks/map_view.py`）

- 每个模块加 `autonomy`：`tier`、`source`（`moduleAutonomy`／`autonomyTier`／`default`／`default (config invalid)`）、`widerThanProject`（布尔）。
- 文字版不加列（避免表格变宽）；不改其他字段。

### C3 verify-artifacts

- 现有配置检查已覆盖不合法取值（经 `project_config.py check`）；新增：`moduleAutonomy` 里有能力图上没有的 id 时，每个 id 一条 ⚠️。

### C4 接口与说明

- `interface.json` 升 1.14：新增 `moduleAutonomy` 条目（`config`、`key`、`default: {}`、`values` 同 `autonomyTier`、`readFrom`、
  `notes`：生效规则、宽于项目只提醒不截断、上限由调用方做、不低于底线、写入要用户原话、旧版本兼容），`mapView` 写明 `autonomy` 字段。
- `scripts/check-interface.py` 核对 `mapView` 的新字段名与 `map_view` 常量一致，`test-checkers.sh` 加一个反例。
- `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md` 的 config 与 `/map` 两段、`docs/concepts.md` 自治档位一行同步。

### C5 发版准备

- 0.89.0：两份 `plugin.json`、README 中英 `--ref`、CHANGELOG `## [0.89.0]`（新增、接口 1.14、升级须知）。

## Acceptance criteria

- **AC1** `test_project_config.py`：给一个模块设三档各成功且只改该条目；`unset --module` 去掉条目，最后一个去掉后键消失；不合规 id、
  不合法档位、非对象值 `set` 退出 2 不写；文件里 `moduleAutonomy` 不合法时只这个键失效、`check` 失败、其余键照常；`--module` 用在
  其他键上退出 2；宽于项目档位时预览有 note 行。
- **AC2** `module_tier`：有条目取条目；无条目随 `autonomyTier`（设了／未设／不合法三种来源）；`moduleAutonomy` 不合法时回到项目档位。
- **AC3** `test_map_view.py`：每个模块有 `autonomy` 三个字段；设了模块档位与未设的模块各对；宽于项目时 `widerThanProject` 为真；
  没有配置文件的项目所有模块为 `strict`／`default`／`false`；文字版输出不变。
- **AC4** 阶段提示：设了 `moduleAutonomy` 与未设时输出逐字相同（`test-phase-guard.sh`）。
- **AC5** verify-artifacts：能力图上没有的 id 报警告、不判失败；不合法值判失败（`test-verify-artifacts.sh`）。
- **AC6** `interface.json` 1.14，`check-interface.py` 通过，改掉字段名时变红。
- **AC7** 版本 0.89.0（`check-manifests.py`、`check-readme-sync.py`）；`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿。

## Boundaries

- **会做**：C1～C5 及回归。
- **先问再做**：让 spec-guard 自己的任何行为随档位变；往阶段提示注入档位；读外部上限文件或替调用方截断；改档位名称或加档。
- **不做**：档位含义（module-crew）；项目上限与截断（autopr、module-crew）；普通 Issue 的档位（autopr 用标签）；1b（Spec 修订攒批，
  1a 之后另开模块）；打 tag 与发 Release（合并后按发布流程做）。

## 并行边界

- 独占：`spec/module-autonomy.md`、`tasks/module-autonomy/`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/test_map_view.py`
- 公共：无

## 文档建议

改 `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/concepts.md` 与 CHANGELOG；README 只改 `--ref`
（档位是给运行时用的配置，README 不讲 `autonomyTier`，这里也不加）。项目没有文档基线。
