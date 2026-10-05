# Spec: plan-without-todo

## Objective

`module_stage.module_state` 把"有 `tasks/<id>/plan.md`、没有未勾选项"的模块判为完成；没有 `todo.md` 时未勾选项为 0，
所以只有 Plan 的模块一律算完成。

2026-09-29 在一个消费者项目中实际撞上：插队插入的新模块有 Spec 与 Plan（任务写成标题、没有勾选项），没有 `todo.md`。
即使把 `activeModule` 设为它，阶段也报 `MODULE_DONE`，并提示回到被暂停的模块——新模块被当成已经做完。补一份 `todo.md` 才解决。

但"只有 Plan"在现有项目里很常见，而且绝大多数是早已交付的模块：本仓库 21 个模块中有 15 个，另外抽查的两个消费者项目里
分别过半和全部如此。原因见下方"修订"：它们来自已退役的远端 tracker 模式。

因此不能改完成判据，也不能对每个这样的模块都警告；只在会误导的地方提醒。

登记：2026-09-29 按用户决定经 `/spec-guard:add-module` 快速插入能力图。

## Assumptions

用户已于 2026-09-29 确认：

1. 完成判据不变：有 Plan 且没有未勾选项即完成，缺 `todo.md` 仍算完成。
2. 只加警告，不改任何阶段标签或计数。

以下为本 Spec 提出、待评审确认的范围：

3. 阶段提示只在一种情况下提醒：`activeModule` 明确指向的模块"因为缺 `todo.md` 而被判为完成"。这正是上面那个消费者项目的场景
   （用户显式要做它，它却显示已完成）；没有设置 `activeModule`、或它指向的模块有 `todo.md` 时，输出与现在逐字相同。
4. `verify-artifacts` 汇总成一条警告，列出所有"有 Plan 无 todo"的模块（按 Build order，最多列 10 个，其余只给数量），
   说明它们按已完成计；它按需运行，不会每轮出现。
5. 不改 `/plan` 或 agent-skills 的模板；新模块仍按约定由 `/plan` 同时生成 plan 与 todo。

## 修订：已退役的远端 tracker 模式（2026-09-29，用户决定）

2026-09-15 之前，spec-guard 支持 `tracker: github` / `gitlab`：`/plan` 只写 `plan.md`，任务同步成远端 Issue，进度记在 Issue 上，
因此这类模块**按设计就没有 `todo.md`**。该模式已退役（`docs/retirements/spec-github-bridge-retirement.md`），但仍有项目保留
`.agent/state.json` 中的 `tracker` 值。对这类项目，缺 `todo.md` 不是遗漏，T1 的提醒与 T2 的汇总都是误报。

因此：`.agent/state.json` 的 `tracker` 为 `github` 或 `gitlab` 时，T1 不加提醒行，T2 不发缺 todo 汇总（这类项目已经会收到
`verify-artifacts` 的"检测到历史状态文件"警告）。`tracker` 为 `none`、没有 `tracker` 字段或没有 `state.json` 时（本地模式），
行为不变：本地模式下 `todo.md` 是 `/build` 取任务与阶段判断的依据，必须存在。

### 再修订：抑制逻辑已删除（2026-10-04，用户决定）

上一条修订已失效。`tracker` 字段本身随 2026-10-04 的决定一并退役，见
[`docs/retirements/state-tracker-field.md`](../docs/retirements/state-tracker-field.md)：没有任何代码再读它，
因此也没有可供抑制的条件。`module_stage.retired_tracker()` 与 `verify-artifacts` 里对应的抑制分支都已删除，
T1 的提醒与 T2 的汇总现在只看文件是否存在，与 `state.json` 的内容无关。

**本节的完成判据不受影响**：Objective 与 Assumptions 第 1 条所述「有 Plan 且没有未勾选项即完成，缺
`todo.md` 仍算完成」逐字有效。删除的是警告抑制，不是判据；本仓库 13 个有 Plan 无 todo 的历史模块状态不变。
证据：删除前后在本仓库运行两个版本的 hook，阶段注入与 `verify-artifacts` 输出逐字相同。

## 修订：有意不建 todo 的模块可以声明（2026-10-05，用户决定）

本仓库 13 个有 Plan 无 todo 的模块都在 `plan.md` 开头写了登记说明，说明它们登记时已交付、没有 todo 是有意的。
但 T1 计数行与 T2 汇总仍然每次把它们全部列出，真正漏建 todo 的模块会被淹没在里面。

用户已确认：

1. 声明用机读标记行：`tasks/<id>/plan.md` 中有一行去掉首尾空白后恰好是 `<!-- spec-guard: no-todo -->`。
   与语言无关；自由文本的登记说明不算声明。
2. 共享判据改为「有 Plan、无 `todo.md`、且 Plan 没有声明」，由 `module_stage.plan_without_todo` 唯一实现；
   T1 的提醒行、T1 的 `Plan without todo: N` 计数行、T2 的汇总三处都只看它。没有剩余模块时对应行不输出。
3. **完成判据不变**：声明只影响提醒，带声明与不带声明的缺 todo 模块都按已完成计，阶段标签与计数不变。
4. 本仓库 13 个模块的 `plan.md` 各加一行声明，紧接在登记说明之后。

## Contract

### T1 阶段提示（`hooks/module_stage.py`）

- `module_state` 增加字段 `todo`（`tasks/<id>/todo.md` 是否存在），供判定与提示使用；`stage` 的计算不变。
- `activeModule` 指向能力图中的模块、该模块 `stage` 为 `DONE` 且 `todo` 为假时，在计数行之后（`Paused` 行之前）加一行：
  `- activeModule \`<id>\` has a plan but no \`tasks/<id>/todo.md\`, so it counts as done; add the todo if work remains.`
  适用于该情况下的 `MODULE_DONE` 与 `DONE` 两种阶段。
- 其他情况（含没有 `activeModule`、`activeModule` 不在图中、有 `todo.md`）输出不变；已有全部回归逐字保持。

### T2 产物校验（`hooks/verify-artifacts.sh`）

- 能力图通过严格解析后，统计"有 `tasks/<id>/plan.md`、无 `tasks/<id>/todo.md`"的模块；数量大于 0 时发一条 `warn`：
  `N 个模块有 Plan 但没有 todo.md，按已完成计：a, b, c…`（按 Build order，最多 10 个，超过时以"等 N 个"结尾）。
- 数量为 0 时不输出；不产生 `bad`，不改变退出码。
- 判据与 T1 相同（同一个"plan 存在、todo 不存在"），不复制完成判据本身。

### T3 文档

- `commands/phase.md`、`docs/workflow.md`：说明缺 `todo.md` 的模块按已完成计，以及 T1 的提醒何时出现、如何处理（补 `todo.md`）。
- `commands/verify-artifacts.md`：新警告的含义。
- `CHANGELOG.md` Unreleased。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_module_insert.py
/bin/bash scripts/validate.sh
python3 scripts/check-command-parity.py
```

## Project structure

```text
plugins/spec-guard/hooks/module_stage.py        -> T1
plugins/spec-guard/hooks/test-phase-guard.sh    -> T1 回归
plugins/spec-guard/hooks/verify-artifacts.sh    -> T2
plugins/spec-guard/hooks/test-verify-artifacts.sh -> T2 回归
plugins/spec-guard/commands/phase.md, verify-artifacts.md, docs/workflow.md, CHANGELOG.md -> T3
```

## Testing strategy

- 每项先写测试并确认它在当前代码上失败，再修改。
- `test-phase-guard.sh`：
  - `activeModule` 指向"有 Plan 无 todo"的模块、仍有别的未完成模块 → `MODULE_DONE` 带提醒行；
  - 同上但全部完成 → `DONE` 带提醒行；
  - 反例：`activeModule` 指向有 `todo.md` 且全勾的模块、没有 `activeModule`、指向不在图中的模块 → 不出现提醒；
  - 已有 48 个用例全部保留。
- `test-verify-artifacts.sh`：有 0 个、1 个、超过 10 个"有 Plan 无 todo"模块时的输出与警告计数；退出码不变。
- 修改共享判据时同时更新 phase-guard 与 verify-artifacts 的正反回归（仓库不变量）。
- 两种 Python（默认 `python3` 3.10 与 `/usr/bin/python3` 3.9）下三条最小验证都通过。

## Boundaries

- Always：先红后绿；hook 只读、输出合法 JSON；没有触发条件时输出逐字不变。
- Ask first：改变完成判据；对每个缺 todo 的模块逐轮提醒；自动生成 `todo.md`。
- Never：写文件；把缺 `todo.md` 的历史模块报为失败；改变阶段标签或计数。

## Success criteria

- 本地模式下 `activeModule` 指向只有 Plan 的新模块时，每轮都能看到提醒，知道要补 `todo.md`。
- 本仓库与抽查的消费者项目在没有触发条件时阶段输出不变；`verify-artifacts` 只多一条汇总警告。
- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过。
