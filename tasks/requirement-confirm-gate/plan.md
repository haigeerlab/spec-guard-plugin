# Plan: requirement-confirm-gate

<!-- spec-guard: review pending -->

Spec：[spec/requirement-confirm-gate.md](../../spec/requirement-confirm-gate.md)（2026-11-24 批准）。

## 架构决定

- **不能交接管的入口只有一处**：`module_stage.codex_route(root, module, "spec")` 在新流程模块上（`flow_marker(root, module)["v2"]`）返回新原因 `"requirement"`，
  排在 takeover 判断之前。`effective_review`、`codex_hint`、`map_view` 的待批清单都经它判定，Codex 的批准随之不算（AC3）。重要需求（`"important"`）在新流程模块上也落到 `"requirement"`
  之后的同一提示里：提示文字合成一句，重要时多写理由，不出两行。
- **没有标记也算待确认**：在 `describe` 取到 Spec 原始批准状态之后、交给 `review_hint` 之前，新流程模块的 `none` 改读为 `pending`（老模块不动）。只改提示与 `requirementConfirm`，
  `/map --json` 的 `review.spec` 仍报原始状态，不改已有字段的含义。
- **提示措辞**：新流程模块 Spec 待确认（`pending`，含上面改读的 `none`，以及 Codex 批准不算时）出「- 批准: 需求文档 `spec/<id>.md` 等用户确认。」；下一步：
  「在对话正文里复述需求（目标、给谁用、使用场景、业务规则和异常情形、不做什么、成功标准、待定问题，加上档位），问用户是否说完；给谁用、为什么做、怎样算做成、不做什么有一项写不出来、
  有你自己补的假设，或是重要需求（<理由>）时，先用 agent-skills 的 interview-me 一次问一个问题，问清再复述。用户在对话里确认后，用 <review-mark> 记下来；接管档位不能代替，Codex 的批准不算。」
  英文同义。`revised` 沿用现有提示，只把「Spec」改称「需求文档」。`combined` 节奏、`pre_build_batch` 等其余分支对新流程模块不改。
- **一个取值函数**：`module_stage.requirement_confirm(root, module) -> dict | None`：老模块 `None`；新流程模块按原始状态映射 `approved→confirmed`、`none／pending／codex-approved→pending`、
  `revised→revised`、`invalid`／`unreadable→invalid`；`by`、`at`、`sha256` 按 Spec 假设 3。`sha256` 用批准标记的同一函数（`review_digest`，内部走 spec-digest 的算法，不另写）。
  `at`：`git log -1 --format=%cI -S<当前批准标记行> -- spec/<id>.md`（用现有 `_git`），未提交、不在 git 仓库、git 失败时 `None`。只对新流程模块调用 git，老模块零开销。
- **verify-artifacts**：批准标记那段的 python 已经逐文件算状态；新流程需求文档原始状态为 `codex-approved` 时多输出一行警告类型，shell 侧报
  「⚠️ 新流程需求文档：`spec/<id>.md` 只有 Codex 的批准，需求要用户在对话里确认」（AC7）。不改判失败的条件。
- **接口**：`interface.json` 加 `mapView.requirementConfirm`（描述）与 `mapView.flow.requirementConfirmStatus` 取值表，版本 1.19；`check-interface._flow` 核对取值表与代码常量一致。

## 任务

编码由我在本会话完成，每个任务先写回归、确认失败再实现。

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**：路由与提示（C1 的前两项）。回归（`test_flow_v2.py` 新类 `RequirementConfirmHintTest`）：新流程模块在项目 `takeover` 为 `{"spec":"codex"}` 时 `codex-approved` 不算批准、提示写明 Codex 的批准不算，老模块同配置下照旧算（AC3）；
  新流程模块无标记、`pending` 时出「等用户确认」一行与复述各项、拷问三种情形、review-mark（中英，AC6）；`approved` 时这一行消失；`revised` 的提示称「需求文档」；
  老模块无标记时不出这一行（AC1）；几种情形下阶段值与改动前相同（AC2）。验证：`test_flow_v2`、`test-phase-guard.sh`。
- **Task 2**：`requirement_confirm` 与 `/map --json`（C1 第三项、C2、C5）。回归：`test_flow_v2.py` 新类覆盖四种 `status` 与 `by`（AC2）、`sha256` 等于 `spec-digest.py text`（AC5）、
  `at` 在已提交／未提交／非 git 目录三种情形（AC4，用现有 git 夹具模板）；`test_map_view.py` 的 `MODULE_KEYS` 加 `requirementConfirm`、老模块为 `null`；`interface.json` 1.19 与 `check-interface.py`。
  `docs/commands.md` 的 `/map --json` 一句补字段。验证：`test_flow_v2`、`test_map_view`、`check-interface.py`。
- **Task 3**：verify-artifacts 警告（C3）。回归：`test-verify-artifacts.sh` 加两例——新流程需求文档只有 `codex-approved` 时报警告、不判失败；老模块同样标记不出这条警告（AC7、AC1）。验证：`test-verify-artifacts.sh`。
- **Task 4**：规则文字（C4）。`references/workflow-checkpoints.md`「需求确认」一节的「新流程模块的写法」按 Spec 假设 5 改；`test_workflow_checkpoints.py` 若对这一节有逐字断言同步更新。验证：`validate.sh`。

## 会改哪些文件

- 新增：`tasks/requirement-confirm-gate/{plan,todo}.md`。
- 修改：`plugins/spec-guard/hooks/{module_stage,map_view}.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/{test_flow_v2,test_map_view}.py`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、
  `plugins/spec-guard/hooks/test-phase-guard.sh`（仅当已有用例受影响）、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`plugins/spec-guard/references/workflow-checkpoints.md`、`docs/commands.md`。
- 新增依赖、锁文件：无。

## 风险

- **老模块的提示被误改**：所有新分支都以 `flow_marker(...)["v2"]` 为前提。缓解：AC1 的现有回归全绿；Checkpoint 1 用本仓库（全是老模块）新旧输出逐字比对阶段提示、`/map --json`（只多 `requirementConfirm: null`）、verify-artifacts。
- **`/map` 变慢**：`at` 要跑 git。缓解：只对新流程模块、且只在 `confirmed` 时跑一次 `git log -S`；本仓库没有新流程模块，开销为零。
- **递归**：`codex_route` 调 `important`，`important` 不调 `codex_route`；新原因只读 `flow_marker`（不调 `important`），不引入新递归。

## 检查点

- Checkpoint 1（report）：逐项给出 AC9 的证据（`/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 的退出码与末行，`check-interface.py`）；
  AC8 变异（让 Codex 批准对新流程也算、`revised` 当 `confirmed`）各让哪条回归变红；临时项目实跑：新流程模块在 `takeover` spec=codex 下写 `codex-approved` 看提示与 verify-artifacts、无标记看提示、批准后看 `/map --json` 的 `requirementConfirm`；
  本仓库阶段提示、`/map --json`、verify-artifacts 与改动前比对。证据记在 todo 的「证据」一节。
- Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行。`requirementConfirm` 取值发给 autopr-design 核对。本模块不发版（M2 在 takeover-redefine 一次发）。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 未决问题

- 无。
