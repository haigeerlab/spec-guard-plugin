# Spec: plan-auto-approve

<!-- spec-guard: review approved 9bbc70fed280 -->

## Objective

开发流程改版（S110）M2 的第三个模块。用法草案 `spec/usage/dev-flow-v2.md` 定了：新流程模块的 Plan 只留任务列表，**写完即自动批准，不交人也不交 AI**；
越界、不可逆操作、碰 T4 路径照拦。现在新流程模块写完 Plan 仍停在「Plan 交审」，构建中还提示「Plan 没有批准标记：如果用户还没批准它，先等批准再构建」。
本模块去掉新流程模块的 Plan 审批，同时把「照拦」的三类情况落到构建中的阶段提示上，因为原来由 Plan 审批兜住的授权（预先声明的公共路径）现在没人审了。

给谁用：所有用 spec-guard 新流程的项目里写 Plan、做构建的 agent；读 `/map --json` 的 autopilot 与 module-crew。

对外接口与用法草案一致吗：一致。入口表「Plan」一行、A 节「Plan 不可配置、永远自动批准」。草案没有细说「越界」拿什么比、「照拦」后怎样放行，本 Spec 在假设 4～6 补上，见 Q1、Q2。

登记：用法草案 dev-flow-v2（用户 2026-11-24「确认插入，Q1–Q6 按推荐」），M2 里程碑。需求确认沿用草案的确认，本 Spec 交审即确认范围；2026-11-25 用户回「批准；Q1 A；Q2 A」。

## Assumptions

1. **只管新流程模块**：`spec/<id>.md` 有 `flow v2` 标记的模块，四个档位都算（bug、small 也有 Plan）。没有标记的老模块，Plan 的批准标记、`takeover` 的 `plan: codex`、预先声明、越界检查全部照旧。
2. **自动批准不写标记**：新流程模块的 `tasks/<id>/plan.md` 存在即视为已批准，生效状态 `approved`、批准人 `auto`。文件里的批准标记不起作用，verify-artifacts 遇到时警告「新流程 Plan 自动批准，标记不起作用」。
   `review-mark --target plan`（以及 `both`）对新流程模块拒绝，退出 2，拒绝码 `plan-auto`，什么都不写。
3. **阶段提示与停点**：新流程模块在 `NEEDS_PLAN` 不再是「Plan 交审」停点，下一步写 Plan 与 todo 后直接开始构建。构建中的「下一个 gate」一行写「Plan 已自动批准」，不再写「先等批准再构建」。
   需求确认（requirement-confirm-gate）与技术方案审查（design-review）照旧在 Plan 之前拦住。
4. **越界照拦**：新流程模块构建中，不论接管档位，阶段提示都检查自开工基线（需求文档首次提交的父提交）以来改动的文件；超出下面范围的就停下交用户（中途 gate），做法同现有越界检查：
   - 需求文档的「并行边界」一节（有就用）；
   - 技术方案「影响面」一节里反引号括起的路径（文件或目录，同 design-review 的读法）；
   - 本模块自己的文档（`spec/<id>.md`、`tasks/<id>/`）与流程文件（能力图、`.agent/` 配置与状态、用法草案）。
   新流程 Plan 没有「预先声明」一节；写了也不授权任何路径（没人审过）。用户同意越界的改动后，补进技术方案影响面或并行边界——技术方案因此变为「放行后又改过」，按 design-review 重新审或重新批。
   bug、small 没有技术方案：需求文档有并行边界就按它查；没有就不查越界，阶段提示写一行「越界：没有并行边界，未检查」，不停下（Q1 A）。
5. **碰 T4 路径照拦**：
   - 重要需求判定（important-requirement）的风险路径检查，路径来源加上技术方案影响面（现在只看并行边界与预先声明）：影响面列了 T3／T4 路径的需求按规则就是重要需求，技术方案交用户批。
   - 构建中改动的文件命中 `.github/autopr/risk-paths.json` 的 T4、而模块不是重要需求时，停下交用户（中途 gate）。用户同意后，把这个路径补进影响面或并行边界——模块随之成为重要需求，按重要需求的流程由用户批。
   - 没有可读的风险路径清单时不查，阶段提示写一行「T4 路径：没有可读的风险路径清单，未检查」，不停下（同现有 `risk-unknown` 只记不拦的做法）。
6. **不可逆操作照拦**：自动批准只代替「Plan 交审」这一次批准。共享检查点规则里「只在这几类情况停下问用户」的清单不变；推送、发布、删除工作区外的文件、改全局配置等照旧要用户同意。
   推送本分支与开 PR 算在自动批准的授权里（Q2 A）；合并照 F3 由用户在对话里决定，发布另要授权。
7. **`/map --json`**：新流程模块的 `reviewApprovedBy.plan` 为 `auto`；`codexRoute.plan` 为新取值 `auto`（review-mark 用同一判定拒绝，见假设 2）；`awaitingReview` 不列新流程模块的 Plan。`review.plan` 仍报文件里标记的原始状态（事实不改）。
   接口 1.20 → 1.21，`interface.json` 与 `scripts/check-interface.py` 同步。插件版本不改，M2 在 takeover-redefine 一次发版。
8. **规则文字**：共享检查点规则「批准标记」一节加「新流程 Plan 自动批准」一条（假设 2～6 的要点）；停点规则「Plan 交审」加一行「新流程模块的 Plan 不交审」，中途 gate 加越界与 T4 的放行办法。
9. **和接管档位的关系**：本模块不改 `takeover` 的取值与读法。老模块的 `plan: codex` 照旧；新流程模块不读 `plan` 这一项（草案 A 节「Plan 不可配置」）。档位重定义归 takeover-redefine。
10. **共享判据**：越界与 T4 的判定只写一处（`module_scope.flow_scope`、`module_stage.t4_hits`），构建中的检查由阶段提示、`module_scope.py check` 与最终验收的范围检查共用；verify-artifacts 和现在一样不查构建中的改动，它调同一个 `flow_scope` 查范围本身（并行边界写坏判失败，normal／important 没有范围给警告）。改判据时各入口的正反回归一起改（项目不变量）。（2026-11-25 写 Plan 时修订：原文「phase-guard 与 verify-artifacts 调同一个函数」与 verify-artifacts 的现状不符。）
11. **不做**：takeover 新取值与兼容（takeover-redefine）；回归文档检查（regression-doc-check）；合并前验证（verification-criteria）；技术方案审查本身（design-review 已做）；给老模块的 Plan 改规则或补标记。

## Contract

- **C1** `hooks/module_stage.py`：新流程 Plan 的生效批准（`effective_review`、`codex_route`、`stop_node`、阶段提示的下一步与 gate 一行，假设 2、3）；越界与 T4 检查（假设 4、5）；重要需求的风险路径加影响面（假设 5）。
- **C2** `hooks/module_scope.py`：越界范围加上技术方案影响面、新流程不认预先声明（假设 4）。
- **C3** `hooks/review_mark.py`：`plan-auto` 拒绝（假设 2）。
- **C4** `hooks/map_view.py`：`reviewApprovedBy.plan`、`codexRoute.plan`、`awaitingReview`（假设 7）。
- **C5** `hooks/verify-artifacts.sh`：新流程 Plan 带标记时警告（假设 2）。
- **C6** `references/workflow-checkpoints.md`、`references/node-rules.md`：规则文字（假设 8）。
- **C7** `interface.json` 1.21、`scripts/check-interface.py`、`docs/commands.md`（假设 7）。

## Acceptance criteria

- **AC1** 老模块：阶段提示、`/map --json`、review-mark、verify-artifacts 的输出与行为不变；现有回归全绿。
- **AC2** 新流程模块写完 Plan：不出「Plan 交审」停点，不出「先等批准再构建」，阶段提示直接给出构建的下一步；`/map --json` 的 `reviewApprovedBy.plan` 为 `auto`、`codexRoute.plan` 为 `auto`，`awaitingReview` 里没有它的 Plan。
- **AC3** `review-mark --target plan`／`both` 对新流程模块退出 2、拒绝码 `plan-auto`、文件不变；新流程 Plan 带批准标记时 verify-artifacts 警告、不判失败。
- **AC4** 越界：改了范围外的文件时停在中途 gate，列出文件；补进技术方案影响面后不再报越界，技术方案状态变为 `revised`。Plan 里写的「预先声明」不算授权。
- **AC5** bug、small 没有并行边界时出「未检查」一行、不停下；有并行边界时按它查。
- **AC6** T4：影响面列了 T4 路径的模块按规则是重要需求（`important.reasons` 含 `risk-path`）；不是重要需求的模块改到 T4 文件时停在中途 gate；风险路径清单读不了时出「未检查」一行、不停下。
- **AC7** 需求待确认、技术方案待审或待批时，Plan 之前照旧拦住（requirement-confirm-gate、design-review 的回归不变）。
- **AC8** 本机 `validate.sh`、phase-guard、verify-artifacts 全绿；`check-interface.py` 通过；PR 上 `CI required` 通过。

## Boundaries

- **会做**：C1～C7 及回归；写定后把 `reviewApprovedBy.plan=auto`、`codexRoute.plan=auto` 发给 autopr-design 核对（拟回告在验收时给出）。
- **先问再做**：改用法草案的接口约定；超出假设 1～11 的改动；合并。
- **不做**：假设 11 列出的事。

## 并行边界

- 独占：`spec/plan-auto-approve.md`、`tasks/plan-auto-approve/`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/module_scope.py`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`docs/commands.md`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/hooks/test_module_scope.py`、`plugins/spec-guard/hooks/test_important_requirement.py`、`plugins/spec-guard/hooks/test_stop_rules.py`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`
- 公共：无

## Open questions

- **Q1 越界拿什么比？**（2026-11-25 用户选 A）
  - A（推荐）：需求文档的并行边界（有就用）加技术方案影响面里的路径，再加本模块文档与流程文件。bug、small 没有技术方案，没有并行边界时不查越界、只记一行「未检查」。
    代价：bug、small 不写并行边界就没有越界保护（T4 仍然拦）；影响面漏写了新文件，构建时会被拦下来补。
  - B：要求每份新流程需求文档都写「并行边界」（骨架加一节），越界只按它查，同现有接管模块的越界检查；没有就停下。代价：多一节必填，和技术方案影响面内容重复；每个 bug 也要写边界。
- **Q2 自动批准算不算推送本分支、开 PR 的授权？**（2026-11-25 用户选 A）
  - A（推荐）：算。原来批 Plan 就授权推送本分支与开 PR（检查点 2 照写），自动批准沿用这一项；合并照 F3 由用户在对话里决定，发布另要授权，其余不可逆操作照旧问。
    代价：新流程模块从写需求到开 PR，用户只在需求确认（和需要时的技术方案批准）露面一次。
  - B：不算。每个新流程模块开 PR 前问一次用户。代价：多一次打扰，和草案「Plan 不交人」的意图不完全一致。

## 文档建议

`docs/commands.md` 补 review-mark 的 `plan-auto` 拒绝与 `/map --json` 的 `auto` 取值（在 C7 里）。README 讲新流程的段落在 M2 发版（takeover-redefine）时一起改。项目没有文档基线。
