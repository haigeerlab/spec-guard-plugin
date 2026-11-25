# Spec: regression-doc-check

<!-- spec-guard: review approved e87a86dede6c -->

## Objective

开发流程改版（S110）M3 的第一个模块。flow-doc-skeletons 只给回归测试文档 `tasks/<id>/regression.md` 定了三节标题（用例清单、成功标准对照、受影响的老功能），
用例本身怎么写、写得对不对，现在没有任何检查；合并前验证（⑦，verification-criteria 与 autopilot）要照回归文档逐条执行，却没有一个可靠的地方把 Markdown 读成用例。
本模块定用例格式、查回归文档写得对不对，并提供唯一的解析入口 `regression_view --json`：Markdown 只在这里解析，autopilot、module-crew 都读它的输出。

给谁用：写回归文档的 agent（阶段提示与 verify-artifacts 指出哪里不合格式）；照回归执行的非作者（autopilot）；module-crew 的最终验收（列出缺的用例）。

对外接口与用法草案一致吗：用例格式与 `regression_view` 输出字段与草案 B 节一致；草案没写的在下面补上：命令行字段名（假设 1）、`--ref` 与用例内容 sha256（假设 4，#22354 已和 autopr-design 说定）、
bug／small 的回归用例（假设 6）、多模块需求的整体联调回归（假设 7，module-crew 的提案，Q1）。草案有三处字面与 M2 实现不一致，本模块改草案（假设 9）。

登记：用法草案 dev-flow-v2（用户 2026-11-24「确认插入，Q1–Q6 按推荐」），M3 里程碑；草案「后续模块已收到的输入」一节列的五项（mc-coord #22381、ecosystem-lead #22380、#22354、M1 验收时的 projectSections、M2 实跑的三处字面差异）都在本 Spec 处理。
需求确认沿用草案的确认，本 Spec 交审即确认范围；2026-11-25 用户回「批准；Q1 A；Q2 A」。

## Assumptions

1. **用例格式**（草案 B 节）：每条用例一个三级标题 `### R<n>: <标题>`（冒号中英文都认），下面是字段行，每行一个，中英文任选一种：

   | 中文 | English | 必填 |
   |---|---|---|
   | `- 步骤：` | `- Steps:` | 是 |
   | `- 预期：` | `- Expected:` | 是 |
   | `- 执行方式：` | `- Method:` | 是，取 `command`／`script`／`ai-operate`／`manual` 之一 |
   | `- 命令：` | `- Command:` | 执行方式为 `command`／`script` 时必填，其他时不写 |
   | `- 证据：` | `- Evidence:` | 是，写证据形式（如「运行输出」「截图」「用户原话」） |

   字段值可以跨行：字段行之后、下一个字段行或标题之前的缩进行并入这个字段；命令可以写在字段行后的代码块里。同一文档里编号不重复。
2. **成功标准对照**：需求文档 `## 成功标准` 里每条成功标准以 `S<n>` 开头（骨架已要求带编号），回归文档 `## 成功标准对照` 用一张表 `| 成功标准 | 用例 |`，
   每行一个 `S<n>`，用例格用逗号或顿号分隔 `R<n>`。每条成功标准至少对应一条存在的用例；表里出现需求文档没有的 `S<n>`、或不存在的 `R<n>`，都算问题。
3. **受影响的老功能**：`## 受影响的老功能` 下面也写 `### R<n>` 用例（编号与用例清单连续、不重复），这些用例在输出里标 `affectedExisting: true`。
   技术方案的影响面列出了模块开始前就有的文件（同 design-review 判「碰老逻辑」的同一函数）时，这一节至少要有一条用例；否则可以只写「不涉及」。
4. **`regression_view.py --json --project <root> --module <id> [--ref <git ref>]`**（只读）：
   - 读哪份：`normal`／`important` 读 `tasks/<id>/regression.md`；`bug`／`small` 读 `spec/<id>.md` 的 `## 回归用例` 一节（假设 6）。
   - 输出：`schemaVersion: 1`、`module`、`tier`、`document`（路径）、`sha256`（整份文档字节，verification-criteria 绑定用）、`ref`（没给为 null）、
     `criteria`（需求文档里的 `S<n>`）、`cases`（每条 `id`、`title`、`steps`、`expected`、`method`、`command`（没有为 null）、`evidence`、`criteria`（对照表里覆盖的 `S<n>`）、`affectedExisting`、`sha256`）、
     `problems`（与 verify-artifacts 同一份问题列表，固定问题代码加位置）。
   - 用例 `sha256`：步骤、预期、执行方式、命令、证据五项，各自把连续空白压成一个空格、去掉首尾空白后，按固定键序的紧凑 JSON 算 sha256；标题与编号不算在内。autopilot 跑 base、head 两次，按编号加 sha256 判新增或改过的用例。
   - `--ref`：用 `git show <ref>:<路径>` 读那个提交上的文档（需求文档同样从那个 ref 读）；该 ref 上没有这份文档时退出 3，stdout 为 `{"schemaVersion":1,"error":"not-at-ref"}`。
   - 退出码：0 正常（有 `problems` 也是 0，由读的一方决定怎么用）；2 用法错误、模块不在能力图上；3 不是新流程模块（`not-flow-v2`）、文档还没写（`no-document`）或 `not-at-ref`，stdout 为一行 JSON 错误；4 文档读不了、ref 不存在（`unreadable`）。
   - `interface.json` 加 `regressionView` 条目（命令模板 `["python3","-B","hooks/regression_view.py","--json","--project","<project-root>","--module","<module-id>","[--ref <git ref>]"]`、`schemaVersion`、退出码、取值），
     名字与 module-crew 已按草案 v1 实现的 `regressionView` 一致；接口 1.22 → 1.23，`scripts/check-interface.py` 同步。
5. **在哪里查**：
   - verify-artifacts：新流程模块的回归文档存在时，假设 1～3 的每个问题都判失败（与现在缺章节同级）；老流程模块不查。
   - 阶段提示：新流程模块在写 Plan 或构建中、回归文档有问题时，多一行「回归文档有 N 处问题：<前三个问题>；完整列表跑 verify-artifacts」，不阻止往下走（hook 只报告）。
   - 问题代码固定：`case-field-missing`、`case-method-invalid`、`case-command-missing`、`case-command-unexpected`、`case-id-duplicate`、`criterion-uncovered`、`criterion-unknown`、`case-unknown`、`affected-existing-empty`、`no-cases`。
6. **bug／small 的回归用例**（ecosystem-lead #22380）：这两档只写一份需求文档，`## 回归用例` 一节按假设 1 的格式写用例；不要求成功标准对照（`small` 有成功标准时同样按假设 2 查，写在 `## 回归用例` 里的一张对照表；`bug` 没有成功标准一节，不查）。
   - `small`：用例在开工前写好，与 `normal` 一样有问题就判失败。
   - `bug`：「修完补一条回归用例」，构建中还没有用例时阶段提示提醒「修完在 `spec/<id>.md` 的回归用例一节补一条用例」，verify-artifacts 只警告；模块完成（todo 全勾）时没有用例判失败。
7. **多模块需求的整体联调回归**（mc-coord #22381 的提案，Q1）：
   - 位置 `spec/usage/<需求>.regression.md`，用例格式同假设 1，另有 `## 成功标准 → 联调用例`（对照用法草案里的 `S<n>`，只放跨模块的成功标准，不要求每条 `S<n>` 都有）与 `## 涉及的模块`（能力图上的模块 id）两节。
   - `usage_draft.draft_files` 排除 `*.regression.md`（否则会被当成用法草案读、报格式错误）；这一条不论 Q1 怎么选都做。
   - Q1 选 A 时：`regression_view.py --json --project <root> --usage <需求>` 解析它（输出同假设 4，`module` 为 null、多一个 `usage` 字段），verify-artifacts 查格式、`涉及的模块` 都在能力图上、对照表里的 `S<n>` 在用法草案里有。
     什么时候跑、谁跑、结论怎么记归 autopilot 与 verification-criteria；module-crew 的提示归 module-crew。用法草案里加需求一级各节（目标……成功标准 `S<n>`）由写草案的会话照做，本模块只在 `references/` 写明写法，不查这些节。
8. **项目追加章节要有内容**（M1 验收时记下）：`projectSections` 声明的章节，标题下到下一个二级标题之间至少有一行非空内容（可以是「不涉及」），只有标题判失败（`section-empty`）。
   只对项目追加章节，骨架自带的章节不加这条（Q2）。
9. **改用法草案的三处字面**（M2 实跑发现）：
   - U1「无需你批」改为：`takeover` 为 `design`（或 `merge`）时第二审查者审过即可，无需你批；默认档位（`design=human`）审完仍交你批，不需要审的也交你批。
   - U2 改为：技术方案先批，批了再写回归文档（与 design-review 的实现一致）。
   - U3 小改动改为：一份文档里写需求、做法和回归用例三节，不走技术方案审查，其余按普通需求走。
10. **规则与文档**：`references/doc-skeletons.md` 的「回归测试文档」一节写出用例格式、对照表、受影响的老功能和联调回归（Q1 A 时）的写法；
    共享检查点规则「技术方案审查」之后写回归文档的那一步引用它；`docs/commands.md` 加 `regression_view`；CHANGELOG「未发布」加本模块一条。
11. **发版**：插件版本 0.95.0 → 0.96.0（按 PR 节奏，模块 PR 带版本号）；合并后发版另取用户授权。发版时把 `regressionView` 的实际字段发给 mc-coord（账本 JFMRNH5），与草案 v1 不同的地方单独列出。
12. **不做**：合并前验证报告与校验器（verification-criteria）；执行回归用例（autopilot）；module-crew 的提示与验收改动；检查用例内容是否「写到能验证」（只查结构）；
    给老流程模块补回归文档；改消费者项目的文件。

## Contract

- **C1** 新文件 `hooks/regression_view.py`（解析与 CLI，假设 1～4、6，Q1 A 时含 `--usage`）；解析函数供 module_stage 与 verify-artifacts 复用，Markdown 只在这一处解析。
- **C2** `hooks/module_stage.py`：`flow_doc_problems` 接上回归问题与 `section-empty`（假设 5、8）；阶段提示的回归问题行与 bug 补用例提醒（假设 5、6）；「影响面列了老文件」提成一个函数，design-review 与假设 3 共用。
- **C3** `hooks/usage_draft.py`：`draft_files` 排除 `*.regression.md`（假设 7）。
- **C4** `hooks/verify-artifacts.sh`：新流程模块的回归检查；Q1 A 时联调回归检查（假设 5、7）。
- **C5** `interface.json` 1.23（`regressionView`）、`scripts/check-interface.py`（假设 4）。
- **C6** `references/doc-skeletons.md`、`references/workflow-checkpoints.md`、`docs/commands.md`、`spec/usage/dev-flow-v2.md`（假设 9）、CHANGELOG、版本号（假设 10、11）。

## Acceptance criteria

- **AC1** 合格式的回归文档（中文、英文字段各一份）`regression_view --json` 输出每条用例的全部字段，`problems` 为空；verify-artifacts 通过。
- **AC2** 假设 5 列的每个问题代码各有一份反例，verify-artifacts 判失败并给出代码与位置，`regression_view` 的 `problems` 与之一致；改回合格式后转绿。
- **AC3** 每条成功标准都有用例：需求文档有 S1～S3、对照表缺 S2 时报 `criterion-uncovered`；对照表写了 S9 报 `criterion-unknown`。
- **AC4** 技术方案影响面列了老文件、受影响的老功能只写「不涉及」时报 `affected-existing-empty`；影响面全是新文件时「不涉及」通过。
- **AC5** 用例 sha256：只改空白不变，改命令或预期就变，改标题不变；`--ref` 读到该提交上的版本，该 ref 没有文档时退出 3 并报 `not-at-ref`。
- **AC6** bug：构建中没有用例时阶段提示有补用例提醒、verify-artifacts 只警告，todo 全勾后判失败；small 的用例按 normal 的同样规则查；两档 `regression_view` 都从 `spec/<id>.md` 读。
- **AC7** `spec/usage/` 下放一份 `<需求>.regression.md`，`/map`、阶段提示、里程碑停点照常（不被当作草案）；Q1 A 时 `--usage` 解析它、verify-artifacts 查它。
- **AC8** `projectSections` 声明的章节只有标题时判 `section-empty`，写「不涉及」通过；骨架章节不受影响。
- **AC9** 老流程模块（本仓库全部模块）的阶段提示、`/map`、verify-artifacts 输出不变。
- **AC10** `interface.json` 1.23 的 `regressionView` 与实际输出一致，`check-interface.py` 通过；本机 `validate.sh`、phase-guard、verify-artifacts 全绿；合并前头提交的 `CI required` 通过。

## Boundaries

- **会做**：C1～C6 及正反回归；拟给 mc-coord 的字段回告（假设 11，发出要用户同意）。
- **先问再做**：超出假设 1～12 的改动；改用法草案除假设 9 以外的约定；并行边界外的文件；合并；发版。
- **不做**：假设 12 列出的事。

## 并行边界

- 独占：`spec/regression-doc-check.md`、`tasks/regression-doc-check/`、`plugins/spec-guard/hooks/regression_view.py`、`plugins/spec-guard/hooks/test_regression_view.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/usage_draft.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_usage_draft.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`plugins/spec-guard/references/doc-skeletons.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`docs/commands.md`、`spec/usage/dev-flow-v2.md`、`CHANGELOG.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`
- 公共：无

## Open questions

- **Q1 module-crew 提的多模块整体联调回归（`spec/usage/<需求>.regression.md`），spec-guard 采纳到什么程度？**（2026-11-25 用户选 A）
  - A（推荐）：采纳位置与格式，`regression_view --usage` 解析、verify-artifacts 查格式（假设 7）。结果：autopilot 跑联调回归时和模块回归读同一个入口，Markdown 仍只在一处解析；
    module-crew 的 crew-flow-v2 按提案照做。代价：本模块多一个入口和一组检查，约多两三个任务。
  - B：只排除 `*.regression.md`，不解析、不查，联调回归的解析留到以后单开模块。代价：autopilot 要跑联调回归时没有解析入口，要么等新模块、要么自己解析 Markdown（违背「只在一处解析」）。
- **Q2 「有内容或写不涉及」只查项目追加章节，还是骨架自带的章节也查？**（2026-11-25 用户选 A）
  - A（推荐）：只查项目追加章节（M1 验收时记下的范围）。结果：已发的 M1、M2 新流程模块不会因为新检查突然判失败；回归文档的三节已由用例检查覆盖。
  - B：所有章节都查。代价：消费者项目里已写好的新流程文档可能有空章节，升级后 verify-artifacts 变红，要逐个补。

## 文档建议

`references/doc-skeletons.md` 的回归一节是写回归文档的人唯一要看的说明，C6 里写全格式与例子；`docs/commands.md` 加 `regression_view` 一行。项目没有文档基线。
