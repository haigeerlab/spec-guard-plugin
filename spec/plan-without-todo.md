# Spec: plan-without-todo

## Objective

`module_stage.module_state` 把"有 `tasks/<id>/plan.md`、没有未勾选项"的模块判为完成；没有 `todo.md` 时未勾选项为 0，
所以只有 Plan 的模块一律算完成。

2026-09-29 在 `haigeerlab/pwa-platform` 实际撞上：插队插入的 `ai-onboarding` 有 Spec 与 Plan（任务写成 `### AO1`…`### AO16`
标题，没有勾选项）、没有 `todo.md`。即使把 `activeModule` 设为它，阶段也报 `MODULE_DONE`，并提示回到被暂停的模块——
新模块被当成已经做完。当时靠在 PR #88 里补一份 `todo.md` 才解决。

但"只有 Plan"在现有项目里是常见的历史写法，而且绝大多数是早已交付的模块：

| 项目 | 模块数 | 有 Plan 无 todo |
|---|---|---|
| spec-guard（本仓库） | 21 | 15 |
| pwa-platform | 27 | 15 |
| x9-live-player | 24 | 24 |

因此不能改完成判据，也不能对每个这样的模块都警告；只在会误导的地方提醒。

登记：2026-09-29 按用户决定经 `/spec-guard:add-module` 快速插入能力图。

## Assumptions

用户已于 2026-09-29 确认：

1. 完成判据不变：有 Plan 且没有未勾选项即完成，缺 `todo.md` 仍算完成。
2. 只加警告，不改任何阶段标签或计数。

以下为本 Spec 提出、待评审确认的范围：

3. 阶段提示只在一种情况下提醒：`activeModule` 明确指向的模块"因为缺 `todo.md` 而被判为完成"。这正是 pwa 的场景
   （用户显式要做它，它却显示已完成）；没有设置 `activeModule`、或它指向的模块有 `todo.md` 时，输出与现在逐字相同。
4. `verify-artifacts` 汇总成一条警告，列出所有"有 Plan 无 todo"的模块（按 Build order，最多列 10 个，其余只给数量），
   说明它们按已完成计；它按需运行，不会每轮出现。
5. 不改 `/plan` 或 agent-skills 的模板；新模块仍按约定由 `/plan` 同时生成 plan 与 todo。

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

- pwa-platform 的场景（`activeModule` 指向只有 Plan 的新模块）每轮都能看到提醒，知道要补 `todo.md`。
- 本仓库、pwa-platform、x9-live-player 在没有触发条件时阶段输出不变；`verify-artifacts` 只多一条汇总警告。
- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过。
