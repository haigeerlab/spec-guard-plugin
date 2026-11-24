# Spec: requirement-confirm-gate

<!-- spec-guard: review approved 37c8db389ca9 -->

## Objective

S110 开发流程改版要求「人确认需求」：新流程模块的每个需求都由用户在对话里确认，没有接管选项；复述有缺口或是重要需求时自动转入拷问；
autopilot 的合规监测要能从 `/map --json` 读到这次确认（接口 v1 的 D' 节 `requirementConfirm`）。

现状：需求确认只是规则文字（requirement-confirm 模块，0.69 前后），确认结果没有记录；新流程模块的需求文档沿用 Spec 的批准标记，
接管档位 `spec: codex` 时 Codex 的批准也算数（flow-doc-skeletons 假设 4 留给本模块）。本模块补上三件事：
新流程模块的需求文档只认用户批准；阶段提示在需求待确认时说清怎么复述、何时拷问；`/map --json` 给出 `requirementConfirm`。

给谁用：写新流程需求文档的 agent（Claude、Codex）；读 `/map --json` 的 autopilot（合规监测）；确认需求的用户。

对外接口与用法草案一致吗：一致，对应入口表「需求确认停点」一行与 U1、U2；字段按 D' 节 `{status, by, at, sha256}`，取值细节见假设 3，
写定后发给 autopr-design 核对。

登记：ecosystem-lead #22328 分派（S110）。需求确认：用户 2026-11-24「说完了，照这样做」「确认插入，Q1–Q6 按推荐」；M1 于 2026-11-24 确认通过。
按规则是重要需求（同一需求批量插入 8 个模块），需求拷问已在 ecosystem-lead 会话做过；本模块 Spec 由用户批。

## Assumptions

1. **确认的记录就是需求文档的批准标记**：新流程模块（`spec/<id>.md` 有 `flow v2` 标记）的需求文档，用户确认后用 review-mark 记 `approved`，
   与 Spec 同一行标记、同一指纹算法。不新增文件、不改标记格式。
2. **没有接管选项**：新流程模块的需求文档，`codex-approved` 一律不算确认——不论 `takeover`／`moduleTakeover` 的 `spec` 写什么，
   按现有「重要需求」的处理（`effective_review` 记为待批，阶段提示说明 Codex 的批准在这里不算数）。老模块的接管档位照旧。
   `takeover` 里 `spec` 这一项的去留归 takeover-redefine，本模块不动配置。
3. **`/map --json` 每个模块加 `requirementConfirm`**：老模块为 `null`；新流程模块为对象：
   - `status`：`confirmed`（用户批准且指纹与当前文档一致）／`pending`（没有标记、标记为待批，或只有 Codex 的批准）／
     `revised`（批准后文档改过）／`invalid`（标记写坏）；
   - `by`：`confirmed` 时为 `"user"`，其余为 `null`；
   - `at`：`confirmed` 时为引入这行批准标记的那次提交的提交时间（ISO 8601，取自 git），标记还没提交或读不到 git 时为 `null`；
   - `sha256`：需求文档当前内容的指纹（与批准标记同一算法，sha256 的前 12 位，`spec-digest.py` 是唯一实现）；文档读不到时 `/map --json` 整体失败（退出 4，同 `review`）。
   字段名按 D' 节保留 `sha256`；说明里写明是 12 位指纹，与 0.93.0 `reviewRounds` 的 `sha256` 一致。
4. **阶段提示**：阶段值不变（批准标记本身不决定阶段，现状如此：待批时阶段照文档推进，另出一行「批准」并在下一步提示「先不要往下写」）。
   新流程模块的需求文档待确认（`pending`／`revised`；**没有标记也算待确认**，老模块没有标记照旧不提示）时，「批准」一行写「需求文档等用户确认」，下一步提示改为：在对话正文里复述需求（按骨架：目标、给谁用、使用场景、
   业务规则和异常情形、不做什么、成功标准、待定问题，加上档位），问用户是否说完；复述里「给谁用、为什么做、怎样算做成、不做什么」有一项写不出来、
   有 agent 自己补的假设，或是重要需求时，先用 agent-skills 的 `interview-me` 一次问一个问题，问清再复述；用户在对话里确认后用 review-mark 记 `approved`。
   中英文按 `artifactLanguage`。重要需求沿用现有的重要需求提示（已含拷问），只把「Spec」改称「需求文档」。
5. **规则文字**：共享检查点规则「需求确认」一节的「新流程模块的写法」改为：
   - 每个新流程需求都要用户在对话里确认，接管档位不能代替；经所装协作插件转来的用户原话按该插件的规定算用户确认（同现有批准来源规则）。
   - 用户明说「不用拷问、直接写」时只跳过拷问，不跳过确认；重要需求不能跳过拷问。
   - 自动转入拷问的三种情形（同假设 4）。
6. **verify-artifacts**：新流程模块的需求文档只有 `codex-approved` 时报警告（「Codex 的批准对需求文档不算，需用户确认」），不判失败——
   这和老模块里不合接管档位的 `codex-approved` 同级处理。
7. **接口与版本**：`interface.json` 加 `mapView.requirementConfirm`，`values.codexRoute` 加取值 `requirement`（新流程模块的需求文档只由用户确认），接口 1.18 → 1.19，`check-interface.py` 同步。插件版本不改，M2 在 takeover-redefine 里一次发版。
8. **不做**：技术方案审批（design-review）；Plan 自动批准（plan-auto-approve）；`takeover` 取值改动（takeover-redefine）；机器判断复述有没有缺口（只能写成规则，由 agent 自查）；
   给老模块补 `requirementConfirm`；改批准标记格式或加时间戳。

## Contract

- **C1** `hooks/module_stage.py`：新流程模块需求文档的批准路由（假设 2）；待确认时的下一步提示（假设 4）；`requirement_confirm(root, module)` 计算字段（假设 3）。
- **C2** `hooks/map_view.py`：`requirementConfirm` 字段（假设 3）。
- **C3** `hooks/verify-artifacts.sh`：`codex-approved` 的警告（假设 6）。
- **C4** `references/workflow-checkpoints.md` 需求确认一节（假设 5）。
- **C5** `interface.json` 1.19、`scripts/check-interface.py`、`docs/commands.md` 的 `/map --json` 一句（假设 7）。

## Acceptance criteria

- **AC1** 老模块：阶段提示、verify-artifacts 输出不变，`/map --json` 只多 `requirementConfirm: null`；现有回归全绿（唯一例外：`test_map_view.py` 的模块字段集合加 `requirementConfirm`）。
- **AC2** 新流程模块的需求文档：无标记、`pending`、只有 `codex-approved` 时 `status` 为 `pending`，阶段提示出「需求文档等用户确认」一行、下一步不往下写；
  用户批准后为 `confirmed`、`by` 为 `user`，这一行消失；批准后改动文档为 `revised`；标记写坏为 `invalid`。阶段值在这几种情形下与改动前相同。
- **AC3** 接管档位 `spec: codex`（项目或模块级）时，老模块的 `codex-approved` 照旧算批准；新流程模块的不算，阶段提示写明 Codex 的批准不算、需用户确认。
- **AC4** `at`：批准标记已提交时等于引入它的提交的提交时间；未提交时为 `null`；不在 git 仓库时为 `null` 且不报错。
- **AC5** `sha256` 等于 `spec-digest.py text` 对需求文档算出的值。
- **AC6** 待确认时的下一步提示列出复述的各项、拷问的三种情形和 review-mark，中英文按 `artifactLanguage`；重要需求的提示把「Spec」称为「需求文档」。
- **AC7** verify-artifacts 对只有 `codex-approved` 的新流程需求文档报警告、不判失败。
- **AC8** 变异：不区分新旧流程（让 Codex 批准对新流程也算）、`revised` 当 `confirmed`，各让对应回归变红。
- **AC9** `validate.sh`、phase-guard、verify-artifacts 全绿；`interface.json` 为 1.19，`check-interface.py` 通过；新流程模块的 `codexRoute.spec` 为 `requirement`。

## Boundaries

- **会做**：C1～C5 及回归；写定后把 `requirementConfirm` 的取值发给 autopr-design 核对。
- **先问再做**：改批准标记格式；给老模块加确认要求；让 verify-artifacts 对 `codex-approved` 判失败。
- **不做**：假设 8 列出的事。

## 并行边界

- 独占：`spec/requirement-confirm-gate.md`、`tasks/requirement-confirm-gate/`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`plugins/spec-guard/references/workflow-checkpoints.md`、`docs/commands.md`
- 公共：无

## 文档建议

`docs/commands.md` 在 `/map --json` 一句里补 `requirementConfirm`；CHANGELOG 在 M2 发版时（takeover-redefine）一起写。项目没有文档基线。

## 变更记录

- 2026-11-24：假设 7、AC9 加 `codexRoute` 的新取值 `requirement`（Plan 第 1 轮 Codex 审查 B6 引出），待用户批。
- 2026-11-24：假设 3 的 `sha256` 在文档读不到时改为 `/map --json` 整体失败（Plan 第 2 轮 Codex 审查引出），待用户批。
