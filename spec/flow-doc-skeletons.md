# Spec: flow-doc-skeletons

<!-- spec-guard: review approved bbc955744868 -->

## Objective

S110 开发流程改版的第一步：给新模块一套新的文档结构，让阶段提示和 `/map` 认得它，老模块完全不受影响。

新流程是 需求文档 → 技术方案 → 回归测试文档 → 拆任务 → 实现 → 按回归验收。本模块只管「写哪几份文档、放在哪、各有哪些章节、按需求大小怎么分档」，
以及阶段怎么随文档推进；需求确认、技术方案审查、Plan 自动批准、接管档位、回归检查与合并前验证由后面七个模块各自负责（见用法草案 `spec/usage/dev-flow-v2.md`）。

给谁用：在用 spec-guard 的项目里写新需求的 agent（Claude、Codex）；读 `/map --json` 的 autopilot、module-crew。

对外接口与用法草案一致吗：一致，对应用法草案入口表前两行与 U3；字段 `tier` 是接口 v1 的 D' 一节（已与 autopr-design 核对，#22347）。

登记：ecosystem-lead #22328 分派（S110）。需求确认：用户 2026-11-24「说完了，照这样做」「确认插入，Q1–Q6 按推荐」。按规则是重要需求（同一需求批量插入 8 个模块），需求拷问已在 ecosystem-lead 会话做过、原话附在 S110 需求文档文末；本模块 Spec 由用户批。

## Assumptions

1. **新旧模块怎么区分**：新流程的模块在需求文档 `spec/<id>.md` 里有一行 `<!-- spec-guard: flow v2 tier=<档位> -->`；没有这一行的模块一律按现行规则（Spec → Plan → todo），阶段、批准、`/map` 输出逐字不变。
   不迁移、不提示老模块补这一行。
2. **四份文档与位置**（Q1 按推荐）：
   - 需求文档 `spec/<id>.md`：目标、给谁用、使用场景、业务规则和异常情形、不做什么、成功标准（要写到能验证，带编号 `S1`…）、待定问题；
   - 技术方案 `tasks/<id>/design.md`：现状调研（写明查了哪些、哪些没查）、影响面、实现方案、接口和数据改动、风险与回滚、方案取舍；
   - 回归测试文档 `tasks/<id>/regression.md`：用例清单、成功标准 → 用例对照、受影响的老功能；用例的字段格式与检查归 regression-doc-check；
   - Plan `tasks/<id>/plan.md`：只留任务列表（每个任务的验证方式）与检查点；todo 照旧。
   章节名写在 `references/doc-skeletons.md`，中英文各一套（按 `artifactLanguage` 选），阶段提示在要写某份文档时指向它。
3. **分档**（Q2 按推荐，档位由 agent 在复述里提出、用户确认需求时一并确认）：
   - `bug`：只写需求文档，含「复现步骤」「预期结果」「回归用例」三节，不写技术方案和回归文档；
   - `small`（小改动）：只写需求文档，三份的内容合成一份：需求各节之后加「做法」「回归用例」两节；
   - `normal`：四份都写；
   - `important`：四份都写（技术方案由用户批，归 design-review）。
   档位行写错（不是这四个值）时按 `normal` 处理并在阶段提示与 verify-artifacts 里指出；规则判为重要需求（`important()` 有理由）而档位写的不是 `important` 时同样指出，按 `important` 处理。
4. **阶段**：新流程模块的阶段按文档推进：`NEEDS_SPEC`（缺需求文档）→ `NEEDS_DESIGN`（缺技术方案）→ `NEEDS_REGRESSION`（缺回归文档）→ `NEEDS_PLAN` → `BUILDING` → `DONE`；
   `bug`、`small` 跳过 `NEEDS_DESIGN` 与 `NEEDS_REGRESSION`。`NEEDS_DESIGN`、`NEEDS_REGRESSION` 是新增的阶段值，只出现在新流程模块上。
   各阶段的批准（需求确认、技术方案审批、Plan 自动批准）本模块不改：在后续模块落地前，需求文档沿用 Spec 的批准标记，技术方案与回归文档只看在不在，Plan 沿用现行批准。
5. **`/map --json`**：每个模块加 `tier`（`bug`／`small`／`normal`／`important`，老模块为 `null`），`step` 新增取值 `design`、`regression`；表格视图在进行中的新流程模块上显示所在的文档步骤。
6. **verify-artifacts**：新流程模块按档位检查该有的文档存在、各文档有骨架里的章节（章节可以写「不涉及」，不能缺）；老模块不查这些。
7. **接口与版本**：`interface.json` 加 `mapView.tier`、`stage` 与 `step` 的新取值，接口升一个次版本（在 0.93.0 的 1.17 之上为 1.18）；`check-interface.py` 同步。
   本模块不改插件版本号，M1 的版本号在 project-sections 里改、M1 一次发版。
8. **规则文本**：`workflow-checkpoints.md` 里写需求、写 Spec 的停点加一段「新流程模块」的写法指向骨架；现行 Spec、Plan 交审规则不删，老模块继续用。项目 CLAUDE.md、AGENTS.md 的约定块模板不改（命令、项目规矩挪到项目文件是 S110 第四节的建议，各项目自己做）。
9. **不做**：需求确认停点与拷问触发（requirement-confirm-gate）；技术方案审查与批准（design-review）；Plan 自动批准（plan-auto-approve）；接管档位（takeover-redefine）；
   回归用例格式与覆盖检查、`regression_view`（regression-doc-check）；项目追加章节（project-sections）；合并前验证（verification-criteria）；老模块迁移或补文档。

## Contract

- **C1** `hooks/module_stage.py`：读流程标记与档位；新流程模块的阶段计算（假设 1、3、4）；老模块路径不变。
- **C2** `hooks/map_view.py`：`tier`、`step` 新取值、表格显示（假设 5）。
- **C3** `hooks/phase-guard.sh` 与阶段提示文本：新阶段的说明与下一步建议，指向骨架（假设 4、8）。
- **C4** `references/doc-skeletons.md`：四份文档的章节骨架与分档（假设 2、3）。
- **C5** verify-artifacts 的新流程模块检查（假设 6）。
- **C6** `interface.json` 1.18、`check-interface.py`、`workflow-checkpoints.md`、`docs/commands.md`（假设 7、8）。

## Acceptance criteria

- **AC1** 没有流程标记的模块：阶段提示、`/map --json`（除新增的 `tier: null`）、verify-artifacts 的输出与改动前一致；现有 phase-guard、verify-artifacts、map 回归全部不改、全绿（唯一例外：`test_map_view.py` 的模块字段集合常量加 `tier`）。
- **AC2** `normal`／`important` 模块依次只有需求文档、再加技术方案、再加回归文档、再加 Plan、再勾完 todo 时，阶段依次为 `NEEDS_DESIGN`、`NEEDS_REGRESSION`、`NEEDS_PLAN`、`BUILDING`、`DONE`，`/map` 的 `step` 依次为 `design`、`regression`、`plan`、`build`。
- **AC3** `bug`、`small` 模块只有需求文档时阶段为 `NEEDS_PLAN`，不要求技术方案和回归文档。
- **AC4** 档位写错时按 `normal` 处理并出现提示；规则判为重要而档位不是 `important` 时按 `important` 处理并出现提示。
- **AC5** verify-artifacts 对缺文档、缺骨架章节的新流程模块报失败，章节写「不涉及」的通过；对老模块不报。
- **AC6** 阶段提示在 `NEEDS_DESIGN`、`NEEDS_REGRESSION` 时说明要写哪份文档、放在哪、骨架在哪，中英文按 `artifactLanguage`。
- **AC7** 变异：去掉流程标记的识别、`bug`／`small` 不跳过、verify-artifacts 不查章节，各让对应回归变红。
- **AC8** `validate.sh`、phase-guard、verify-artifacts 全绿；`interface.json` 为 1.18，`check-interface.py` 通过；macOS `/bin/bash` 下通过。

## Boundaries

- **会做**：C1～C6 及回归。
- **先问再做**：改老模块的任何行为；改批准标记的格式；改 todo 的写法。
- **不做**：假设 9 列出的事。

## 并行边界

- 独占：`spec/flow-doc-skeletons.md`、`tasks/flow-doc-skeletons/`、`plugins/spec-guard/references/doc-skeletons.md`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`scripts/validate.sh`、`plugins/spec-guard/references/workflow-checkpoints.md`、`docs/commands.md`
- 公共：无

## 文档建议

`references/doc-skeletons.md` 是新增的权威骨架；`docs/commands.md` 在 `/map --json` 一句里补 `tier`；README 本模块不改（M1 发版时在 project-sections 里改）。项目没有文档基线。
