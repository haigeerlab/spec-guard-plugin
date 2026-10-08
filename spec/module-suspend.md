# Spec: module-suspend

## Objective

一个模块的代码已经做完，只剩一个要等的条件：某个日期的复核、发版后的观察、外部结果。这时它完成不了，却一直占着
当前模块：阶段判定取 Build order 里第一个没做完的模块，所以它永远被选中，项目到不了 DONE，`add-module` 也会因为
"上一个模块做到一半"拒绝插入新模块。现有的插队（`module-interrupt`）解决的是"临时插一件急事、做完自动回去"，
不适合"要等一段时间、多久不确定"。

本模块提供挂起：模块让出当前位置、留在原来的 Build order 位置、阶段提示照实报告它挂起中，直到用户明确恢复。
插件只提供机制，不判断该什么时候回来；需要提醒时由宿主的提醒能力完成。

登记：2026-10-08 经 `/spec-guard:add-module` 插入能力图。同批：`project-config`（已合并）、`runtime-state-layout`。

## Assumptions

用户已于 2026-10-08 确认：

1. **职责划分。** 插件只做挂起、跳过、报告、恢复；不记录原因、日期或条件，不判断该不该回来，不会自动恢复。
   提醒由宿主完成，时间和内容由用户说；AI 在挂起的检查点问一句要不要设提醒，不从上下文推断日期。
2. **挂起标记** 写在该模块的 `tasks/<id>/todo.md`：独占一行 `<!-- spec-guard: suspended -->`（与 plan.md 的
   `<!-- spec-guard: no-todo -->` 同一写法）。入库，团队和两边宿主都看得到。不改能力图结构，不写 `.agent/state.json`。
3. **位置不变。** 挂起的模块保留在 Build order 原位；"排到后面"靠跳过实现，"回轨"就是去掉标记。
4. **前提。** 只能挂起已开工的模块：有 Plan 和 todo，且至少一项未勾选。可以同时挂起多个模块。
5. **与插队独立。** 插队是插进来的模块做完后自动回去；挂起永不自动回来。挂起的模块不算"做到一半"，挂起后加新模块
   不需要 `--interrupt`。
6. **恢复只去掉标记**，不改 `activeModule`（`state.json` 由构建流程管）。
7. **hook 不提醒、不判断时间**，只报告"挂起中"这个事实。

## Measured host reminder capabilities (2026-10-08, read-only checks, no reminder created)

| 宿主 | 能力 | 本模块的用法 |
|---|---|---|
| Claude Code 桌面版 | 持久定时任务，`fireAt` 一次性触发，到点运行一次后自动停用；app 关闭时下次启动补跑 | 用户同意时按其给出的时间和内容创建，创建后读回确认 |
| Claude Code 会话内 Cron | 随会话结束失效 | 不用 |
| Codex 桌面版 | 有"自动化"（本机已有一个 hourly 实例）；协议里定义的周期只有每小时／每天／工作日／每周，未见一次性触发，agent 能否自行创建未确认 | 命令文本只写"宿主有提醒能力就用，否则请用户自己设"，不替它假设 |

## Contract

### 标记与状态

- `module_stage.module_state` 增加 `suspended`：标记行存在（去首尾空白后完全相等）且至少一项未勾选。
  标记存在但没有未勾选项时 `suspended` 为假，模块照常算完成（verify-artifacts 报"标记过期"）。
- `project_stage`：`pending` 取 Build order 中第一个**既未完成也未挂起**的模块；`activeModule` 指向挂起的模块时
  不采用它，按 Build order 取，并加一行说明。只剩挂起的模块未完成时，项目阶段为 `DONE`。
- `paused_modules` 不含挂起的模块；`module-insert` 的"做到一半"判断因此也不会被挂起的模块挡住。

### 阶段提示

- 每个挂起的模块一行：``- Suspended: `<id>` (<n> unchecked item(s)); resume with `/spec-guard:module-suspend --resume <id>` (Codex: spec-guard-ops module-suspend).``
- 计数行有挂起时在末尾追加 ` · Suspended <n>`；没有挂起时计数行逐字节不变。
- `DONE` 且有挂起模块时，下一步建议改为说明"未挂起的模块都已完成，<n> 个挂起中"，不说成"every mapped module …
  no open todo item"。
- 没有任何挂起标记时，所有现有输出逐字节不变。

### `hooks/module_suspend.py` 与命令

- `suspend <id>`／`resume <id>`，`--project`；默认只预览（显示 todo.md 改前改后、挂起后的当前模块），`--confirm`
  才原子写入 todo.md 并读回核对。
- `suspend` 拒绝：id 不是有效 module id 或不在能力图上、没有 Plan 或 todo、没有未勾选项、已挂起。
  `resume` 拒绝：未挂起。拒绝时退出码 2 且不写文件。
- `resume` 的预览写明恢复后它回到 Build order 原位；若另一个模块正做到一半，提示二者形成插队那样的暂停关系。
- Claude：新增 `commands/module-suspend.md`（规范引导段）。挂起确认后，命令文本要求 AI 问一句要不要设提醒；
  用户同意时时间和内容由用户给出，用宿主的持久提醒能力创建并读回；宿主没有该能力时请用户自己设。插件不保存提醒，
  提醒失败不影响挂起。
- Codex：`spec-guard-ops` 新增 `module-suspend` 一节，参数一致（command-parity 检查器覆盖）；提醒一句按上表处理。
- `docs/workflow.md` 命令对照表登记。

### 校验

- `verify-artifacts`：标记只在 `todo.md` 中计数；同一文件出现多于一行 → 失败；标记存在但没有未勾选项 → 警告"标记过期"。
- 同一判据在 phase-guard（跳过、报告）与 verify-artifacts 两边都有正反回归。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_module_suspend.py
python3 -B plugins/spec-guard/hooks/test_module_insert.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/test-checkers.sh
/bin/bash scripts/validate.sh
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh evals/*/*.sh
```

## Testing strategy

- 先写测试并确认在当前代码上失败，再实现。
- `test_module_suspend.py`：挂起和恢复的预览不写文件、`--confirm` 写入并读回；全部拒绝情况；挂起后当前模块跳到下一个；
  恢复后回到原位；做到一半时恢复的提示。
- `test-phase-guard.sh`：挂起中间模块后当前模块是下一个、提示有 Suspended 行与计数；只剩挂起模块时为 DONE 且建议文案
  说明挂起；`activeModule` 指向挂起模块时按 Build order 取并说明；标记存在但无未勾选项按完成计；无标记时逐字节不变。
- `test_module_insert.py`：唯一未完成的模块挂起时 `add-module` 允许插入，且不需要 `--interrupt`。
- `test-verify-artifacts.sh`：重复标记失败、过期标记警告、正常标记通过。
- 变异：标记匹配改为包含即可、跳过逻辑不排除挂起模块、`paused_modules` 包含挂起模块，三处都必须让测试变红。

## Boundaries

- Always：先红后绿；只有 `module_stage` 一处判定挂起；hook 只读；无标记时行为不变。
- Ask first：给挂起加原因或日期字段；让 hook 根据时间提示恢复；自动恢复。
- Never：插件保存或创建提醒；从上下文推断提醒时间；改 `activeModule`；在 Spec、代码、测试、提交信息或 PR 中写入
  消费者项目的名称、模块或编号。

## Success criteria

- 挂起一个做到一半的模块后，阶段提示的当前模块是下一个，挂起的模块单独列出；`add-module` 可以插入新模块。
- 恢复后它回到 Build order 原位，成为当前模块（除非另一个模块正做到一半）。
- 只剩挂起模块时阶段为 DONE，提示不说成"全部完成"。
- 没有挂起标记的项目所有既有回归逐字节通过。

## Open questions

- 无。
