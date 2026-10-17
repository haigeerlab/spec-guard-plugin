# Spec: module-concurrency-switch

<!-- spec-guard: review approved 9912de088ff9 -->

## Objective

多模块并行开发分两层：spec-guard 管规划层（评估、并行边界、可开工列表、角色标记），新插件 module-crew 管运行时。规划层的
六个模块都只在项目明确打开并行时才生效，不需要并行的项目一切照旧。本模块提供这个开关：`.agent/config.json` 新增
`moduleConcurrency`，取值 `off` 或 `on`，默认 `off`；用 `/spec-guard:config` 预览、确认后设置，汇总里显示当前值和来源；
同时给后续模块一个唯一的读取入口。

本模块自己**不改任何行为**：开关打开后，第一个有可见效果的是下一个模块 `concurrency-assessment`。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图（同批 7 个模块）。来源：用户本人，经多模块并行需求讨论（2026-10-17～18），
需求记录由 module-crew 的需求会话转来，用户在本会话确认模块划分并批准写入能力图。发版后回告 module-crew 负责人会话。

## Assumptions

1. **键名是 `moduleConcurrency`，取值是字符串 `off`／`on`。** 不用布尔值，与 `reviewCadence` 的写法一致；名字避开 `parallel`，
   `scripts/check-no-parallel-surface.py` 不用改。
2. **未设置等于 `off`。** 显式写 `off` 也接受（和 `reviewCadence` 可以显式写 `separate` 一样），行为与未设置完全相同。
3. **配置文件无效时按 `off` 处理。** 沿用现有规则：文件里任何一处无效，整份配置都不生效，所有项回到默认值。
4. **「off 时逐字不变」的范围**：阶段提示注入、verify-artifacts、`/map`（文本与 JSON）、约定块与共享规则的效果在 off 和未设置时
   与 0.67.0 逐字相同，各有回归测试证明。唯一的例外是 `/spec-guard:config` 的汇总：它的职责就是列出所有可配置项，所以会多出
   `moduleConcurrency` 这一行（JSON 是 `items` 里多一项，只增不改）。
5. **`on` 时本模块也不往阶段提示里加行。** 现有规则是「设置了的项各注入一行」，但这一行现在没有可指向的规则，只会白占上下文。
   需要提示时，由后续模块按各自的停点加，不做每轮提醒（需求记录 A1）。
6. **后续模块只通过一个函数读开关。** `project_config.module_concurrency(root) -> bool`，只有在配置有效且值为 `on` 时返回 True。
   其他地方不自己解析这个键，不变量和 `spec-digest.py` 唯一指纹算法同理。
7. **旧版本插件兼容风险。** 0.67.0 及更早的 spec-guard 不认识这个键，会把整份配置判为 `unknown-key` 并全部回退默认值，包括
   `artifactLanguage`。插件这边无法补救，只在 `/spec-guard:config` 说明里写明：团队成员都升级到包含本模块的版本后再设置。
8. **版本号**：按用户确认的发版节奏，7 个模块合成一批，最后统一升到 0.68.0。本模块不改版本号，只在 CHANGELOG 顶部的未发布小节
   记一条。

## Contract

### `hooks/project_config.py`

- `VALIDATORS` 新增 `"moduleConcurrency": lambda value: value in ("off", "on")`；`DEFAULTS` 新增 `"moduleConcurrency": "off"`。
  `load`、`summary`、`render`、`set`／`unset` 的现有逻辑不变，自动覆盖这个键。
- 新增 `module_concurrency(root: Path) -> bool`：`load` 没有问题且值为 `"on"` 时返回 True，其余（未设置、`off`、文件无效、
  读不到）一律返回 False。
- 无效值的报错沿用现有固定代码：`moduleConcurrency-invalid`；文件里的值不回显。

### `hooks/module_stage.py`

`config_lines` 不变：`moduleConcurrency` 不论取什么值都不产生注入行。

### 命令与文档

- `commands/config.md`：description 加上「多模块并行开关」；「可配置项」表加一行，写明取值、默认值、作用（打开规划层并行规则，
  本身不开会话、不建 worktree）、旧版本兼容提醒（假设 7）；「设置了的项会在每轮阶段提示里各出现一行」一句改为写明这个键是例外。
- `skills/spec-guard-ops/SKILL.md` 的配置说明同步一行（Codex 侧）。
- `docs/design.md` 的 `project_config.py` 一行、`docs/commands.md` 的 config 条目同步；CHANGELOG 未发布小节记一条「新增」。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_project_config.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- **`test_project_config.py` 先写失败的测试：**
  - `on`、`off` 通过校验；`true`、`"ON"`、`1`、`""` 报 `moduleConcurrency-invalid`，整份配置不生效；
  - `module_concurrency`：未设置、`off`、文件无效（例如同时有一个未知键）、文件不存在时都是 False，只有有效的 `on` 是 True；
  - `summary` 列出 `moduleConcurrency`：未设置时值为 `off`、来源 `default`；设置后来源为 `.agent/config.json`；
  - `set` 预览只给 diff 不写文件，`--confirm` 写入后读回一致；`unset` 后回到默认。
- **off 时逐字不变（`test-phase-guard.sh` 的 project-config 段）：** 同一夹具分别用无配置文件、`{"version": 1}`、
  `{"version": 1, "moduleConcurrency": "off"}`、`{"version": 1, "moduleConcurrency": "on"}` 跑阶段提示，四份输出逐字节相同。
  和 `artifactLanguage` 同时设置时，只多出语言那一行。
- **verify-artifacts：** 含 `moduleConcurrency: on` 的有效配置不报问题；值无效时报 `moduleConcurrency-invalid`（正反各一例）。
- **改坏验证：** 把 `module_concurrency` 改成未设置也返回 True，确认「未设置为 False」一例变红；让 `config_lines` 在 `on` 时
  多出一行，确认逐字相同那例变红。两处都复原。

## Boundaries

- Always：只通过 `module_concurrency()` 读开关；off、未设置、文件无效时任何输出都与 0.67.0 相同；文件里的值不进注入。
- Ask first：给这个开关增加第三种取值；让 `on` 本身改变注入；在本模块里实现任何并行规则。
- Never：开关自动打开；因为开关打开而开会话、建 worktree、发消息或合并；用 `parallel` 命名新内容。

## Success criteria

1. `/spec-guard:config` 能预览、确认后设置和取消 `moduleConcurrency`，汇总显示当前值与来源；无效值按固定代码报错。
2. `module_concurrency()` 只在有效配置值为 `on` 时返回 True，后续模块都用它。
3. 无配置、`off`、`on` 三种情况下阶段提示逐字节相同；verify-artifacts 对有效配置不报问题。

<!-- spec-guard: external-review declined -->
