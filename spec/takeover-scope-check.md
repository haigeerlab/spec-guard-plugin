# Spec: takeover-scope-check

<!-- spec-guard: review approved 557739d8b122 -->

## Objective

接管模块的改动不能悄悄超出声明的范围。现在的只读越界检查（`module_scope.py check`）只在 `moduleConcurrency` 为 on 时运行，而且只在最终验收时
由 agent 手动跑一次。本模块让它对「接管模块」（接管档位里任一项不是 `human`）也生效：构建中改动超出 Spec「并行边界」与 Plan「预先声明」时，
阶段提示停下交用户；同时给 autopilot 一个只读结果，供它在自动合并前查。

给谁用：在接管档位下构建的 agent；读越界结果的 autopilot（合并前）与 module-crew；用户。

对外接口与用法草案一致吗：一致。对应 `spec/usage/auto-takeover.md` 入口「越界检查（阶段提示与只读结果）」，典型用法 U2、U4。

登记：S101 合并方案 r2 第 2 节（「越界检查对接管模块生效」，衔接 S32；用户「按推荐批准」）；方向文档第二节第 4 条「改动超出 Spec 声明范围」必停。
账本 T1T36MR。

## Assumptions

1. **谁要查**：`moduleConcurrency` 为 on 的项目照旧；另外，模块生效的接管档位（`module_takeover`）里任一项不是 `human` 的模块也查。其余模块不查，输出与改前相同。
2. **允许的范围**：本模块自己的 `spec/<id>.md` 与 `tasks/<id>/`；Spec「并行边界」的独占路径；Spec「并行边界」的公共类别只预告、不放行（与现在一样，改到公共文件
   记为越界：公共文件不归任何模块，要改先提出）；Plan「预先声明」的公共路径（该节由用户批过才算，沿用 `declaredScope` 的判定）。其余改动记为越界。
3. **跟谁比（基线）**：按 Q10。
4. **阶段提示**：接管模块在 BUILDING 阶段，有越界文件时加一行「越界：N 个文件（前几个）」，建议下一步换成「停下，把每个越界文件为什么要改交用户；
   用户同意就补进 Spec 并行边界或 Plan 预先声明并复审，不同意就撤回这些改动」，节点按 Spec 没覆盖的决定处理（中途 gate 规则）。没有并行边界时按 Q11。
   中英两套。没有越界时不加行。
5. **只读结果**：`module_scope.py check --module <id> [--base <commit>] --json` 对接管模块不再因开关没开而退出 3；`--base` 不给时按 Q10 自己算；结果加
   `declared`（预先声明放行的文件）与 `base`（实际用的基线）。autopilot 合并前读 `outside` 是否为 0。
6. **不变的**：越界只是停下交人，不自动撤回、不改文件；moduleConcurrency 为 on 的项目原有用法与输出不变（只多了 `declared` 字段）；最终验收「超出并行边界」那一列照旧。
7. **接口**：同在 1.15：`scopeCheck` 写明接管模块也运行、`--base` 可省、新增字段。版本号不在本模块改。

## Contract

### C1 `hooks/module_scope.py`

- `scope_applies(root, module)`：开关 on 或接管模块；`_check` 用它代替只看开关。
- `default_base(root, module)`：按 Q10；取不到返回 None，命令报 `base-unknown` 退出 2。
- 允许范围加上已批准 Plan 的预先声明公共路径，结果行 `scope` 增加取值 `declared`。

### C2 阶段提示（`hooks/module_stage.py`）

- 新函数 `scope_overreach(root, module)` 返回越界文件列表、`None`（不用查）或「未判定」；BUILDING 且接管模块时调用；行与建议下一步按假设 4。

### C3 规则与说明

- `references/workflow-checkpoints.md`「并行边界」一节写明接管模块也查、越界即停交用户；「自治档位与底线」必停里加「接管模块越界」。
- `interface.json` 的 `scopeCheck`、`check-interface.py`；`docs/commands.md`、`skills/spec-guard-ops/SKILL.md`。

## Acceptance criteria

- **AC1** `module_scope` 单测（临时 git 仓库）：接管模块在开关 off 时也运行；非接管模块开关 off 时照旧退出 3；独占内、自己的 Spec 与 tasks、
  已批准预先声明的公共路径都不算越界，其余算；Plan 未批准时预先声明不放行；`--base` 省略时按 Q10 取到基线，取不到退出 2。
- **AC2** 阶段提示（`test-phase-guard.sh` 新段）：接管模块越界时有越界行、建议下一步改为停下交用户（中英）；不越界、或不是接管模块时输出与改前逐字相同；
  没有并行边界时按 Q11。
- **AC3** JSON 结果有 `outside`、`declared`、`base`；`interface.json` 与 `check-interface.py` 一致。
- **AC4** 规则：「并行边界」「自治档位与底线」写进越界即停；字节上限内；`validate.sh`、phase-guard、verify-artifacts 全绿。

## Boundaries

- **会做**：C1～C3 及回归。
- **先问再做**：自动撤回越界改动；让越界拦截提交或推送；改最终验收的文件表。
- **不做**：判断「Spec 没覆盖的决定」（由 Codex 审查对照，见方向文档）；合并（autopilot）；版本号与发版。

## 未决问题

- **Q10 越界跟哪个提交比**（2026-11-22 用户选 A）：
  - **A（推荐）**：本模块 Spec 第一次提交的父提交（这个模块开工前的状态）；本地就能算，叠加分支也不会把前面模块的改动算进来。
  - **B**：与默认分支（`origin/main`）的分叉点。叠加分支时会把前面还没合并的模块的改动都算成越界。
- **Q11 接管模块没写并行边界时**（2026-11-22 用户选 A）：
  - **A（推荐）**：判为「无法检查越界」，同样停下交用户（与 important-requirement 的 Q7 A 一致：没有边界就不放行）。
  - **B**：只加一行提醒，不停。

## 并行边界

- 独占：`spec/takeover-scope-check.md`、`tasks/takeover-scope-check/`、`plugins/spec-guard/hooks/module_scope.py`、`plugins/spec-guard/hooks/test_module_scope.py`
- 公共：无

## 文档建议

改 `docs/commands.md`（越界检查一段）、`skills/spec-guard-ops/SKILL.md`；CHANGELOG 与 README 在最后一个模块统一写。项目没有文档基线。

## 变更记录

- 2026-11-22（构建中）：假设 2 原写「公共类别……与现在一样记为 shared，不算越界」，与现有越界检查不符——现有检查把改到公共文件记为越界（公共文件不归任何模块，要改先提出）。按「与现在一样」的本意改正措辞，行为不变。
- 2026-11-22（M3 返工，用户「批准；Q14 A」）：假设 2 的允许范围对接管模块再加 `.agent/config.json`（记为 `flow`，与能力图、用法草案相同）：它是项目设置，autopilot 收窄或用户调整档位都会改它，不属于模块的补丁。防止 PR 借此开自动合并的核对放在 codex-final-acceptance。
- 2026-11-22（M3 返工，用户「Q15 A」，autopr-design 沙盒演练 2 发现）：基线仍按 Q10 A；接管模块的 `flow` 再加 `.agent/state.json`（`activeModule` 在模块交接时就会改）。约定块所在的 `CLAUDE.md`／`AGENTS.md` 与 `.github/autopr/risk-paths.json` 照旧算越界，应在 Spec 之前单独提交。
