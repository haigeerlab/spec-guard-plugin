# Plan: regression-doc-check

<!-- spec-guard: review approved -->

Spec：[spec/regression-doc-check.md](../../spec/regression-doc-check.md)（2026-11-25 批准，Q1 A、Q2 A）。Codex 第一轮 5 条阻断（R1-1～R1-5），已按下面各处改；第二轮仍有 3 条（R2-1 成批判定要 git 历史、R2-2 `git archive` 受导出属性影响、R2-3 bug 有 Plan 无 todo 提前判失败），交用户，2026-11-25 用户「按处理办法改，批准」。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 架构决定

- **唯一的解析处**（`hooks/regression_view.py`，新文件）：
  - `parse_cases(lines, start, end)`：在给定行段里找 `### R<n>[:：] <标题>`，每条用例收字段行 `- 步骤：`／`- Steps:` 等（中英文字段名一张表，冒号中英文都认）；
    字段行之后缩进的续行、紧跟的代码块（命令写在代码块里）并入当前字段。返回用例列表与问题列表（`(代码, 位置)`，位置是 `文件:行` 或用例编号）。
  - `parse_regression(text, kind)`：`kind` 为 `module`（三节：用例清单、成功标准对照、受影响的老功能）、`short`（`spec/<id>.md` 的「回归用例」一节，里面可以有一张对照表）、`usage`（联调回归：用例、「成功标准 → 联调用例」、「涉及的模块」）。
    节标题用现有的 `module_stage.SECTION_HEADING` 与 `DOC_SECTIONS` 的中英文名；不引入第二份章节名单。
  - `criteria_ids(text)`：需求文档 `## 成功标准`（或 `Success criteria`）下以 `S<n>` 开头的行（允许前面有 `- `、`* `、`**`）。
  - `case_sha256(case)`：五个字段各自压空白后按 `{"command","evidence","expected","method","steps"}` 固定键序紧凑 JSON 算 sha256。
  - `module_report(root, module)` 与 `usage_report(root, name)`：组出 Spec 假设 4 的 JSON。文件一律按字节读：顶层 `sha256` 对原始字节算，再按 UTF-8 解码解析（CRLF 不改写，R1-2）。
  - `--ref`（R1-1、R2-1、R2-2）：在 `tempfile.TemporaryDirectory` 里做一个共享对象的本地克隆（`git clone --quiet --shared --no-checkout <project> <tmp>`，再 `git -C <tmp> -c core.autocrlf=false checkout --quiet --detach <ref>`），对这个克隆跑同一个 `module_report`——能力图、流程标记、有效档位（含成批判定 `usage_draft.batches()`、其他模块与风险清单）、配置、影响面的历史基线都在克隆上按原逻辑算，不另写历史读取；原仓库不写任何东西，临时目录用完即删。
    需求文档与回归文档的字节一律用 `git -C <project> cat-file blob <ref>:<路径>` 读原始 blob（不受 `.gitattributes` 的 eol、`export-ignore`、`export-subst` 影响），摘要与解析都用这份。
    ref 上没有能力图、模块不在那时的能力图上或没有那份回归文档：退出 3 `not-at-ref`；ref 不存在、克隆或检出失败：退出 4 `unreadable`。`impact_has_old_files` 不需要额外参数。
  - CLI：`--json --project <root> (--module <id> | --usage <需求>) [--ref <ref>]`，退出码按 Spec 假设 4；输出只有固定问题代码、编号、路径和文档里解析出的字段值——字段值是消费者自己写的文本，原样放进 JSON（`json.dumps` 转义），不进阶段提示。
  - 依赖方向：`regression_view` 导入 `module_stage`（章节名、`effective_tier`、`flow_marker`、影响面判定）；`module_stage` 在函数内部延迟导入 `regression_view`，避免循环导入。
- **「影响面列了老文件」提成一个函数**：`module_stage.impact_has_old_files(root, module, text) -> bool | None`（`None` = 影响面没写路径），`design_requirement` 改用它，判定逐字不变（design-review 现有回归不改）。
  假设 3 的 `affected-existing-empty` 只在它返回 `True` 时报；技术方案不存在或影响面没写路径时不报（不把未知当成碰老逻辑，与 design-review 的「宁可多审」不同：这里报的是失败，不能靠猜）。
- **问题接进 `flow_doc_problems`**（verify-artifacts 与阶段提示同一份）：
  - `normal`／`important`：`regression.md` 存在时，追加 `regression_view` 的问题，级别 `fail`；消息写成「`tasks/<id>/regression.md` 回归问题：<代码>（<位置>）」。
  - `small`：`spec/<id>.md` 的「回归用例」一节同样查、`fail`；`bug`：没有用例时按 `module_state` 的阶段判（R1-3）——`BUILDING` 为 `warn`，`DONE` 且 `todo.md` 存在、里面至少有一个勾选项（已勾或正式延期）为 `fail`（R2-3；只剩正式延期、最终 gate 已有验收记录同阶段提示的判据），`DONE` 但没有 todo 或 todo 没有勾选项时为 `warn`，其余阶段（只有 Spec、还没 Plan）不报；有用例但格式错照样 `fail`。
  - `section-empty`（假设 8）：`projectSections` 声明的章节，标题到下一个二级标题之间没有非空、非注释行就报，级别 `fail`；只对追加章节，骨架章节不查（Q2 A）。
  - 老流程模块 `flow_doc_problems` 本来就返回 `[]`，不变（AC9）。
- **阶段提示**：在 `phase_text` 组装 `counts` 的地方加一行，仅当新流程模块处于 `NEEDS_PLAN`／`BUILDING` 且有回归问题：「回归文档有 N 处问题：<前三个问题代码与位置>；完整列表跑 verify-artifacts」；
  bug 构建中没有用例时这一行改成「修完在 `spec/<id>.md` 的回归用例一节补一条用例」。只写固定词、问题代码、编号与路径，不写文档内容。
  这一行的问题数进状态码（`_describe_body` 的状态事实），问题数变化就重新注入完整提示；`_role_facts()` 同样读它。
- **联调回归**（Q1 A）：`usage_draft.draft_files` 跳过 `*.regression.md`；verify-artifacts 新增一段，对 `spec/usage/*.regression.md` 跑 `usage_report`：格式问题、`涉及的模块` 不在能力图上（`module-unknown`）、对照表实际引用的 `S<n>` 不在对应用法草案 `spec/usage/<需求>.md` 的成功标准里（`criterion-unknown`，每个未知编号一条），都判失败；对照表没有引用任何 `S<n>` 时不报，草案有没有成功标准一节都一样（R1-4）。
- **接口**：`interface.json` 1.23 加 `regressionView`：`command`（含 `[--ref <git ref>]`，`--usage` 写在 `usageCommand`）、`schemaVersion: 1`、`exitCodes`、`values`（`method` 四个取值、问题代码表）、`contract: spec/regression-doc-check.md`。
  `check-interface.py` 加：`regressionView` 必须有这几个键，`values.method` 与 `regression_view.METHODS` 相同，问题代码与 `regression_view.PROBLEM_CODES` 相同。
- **测试放哪**：新用例放进已登记的 `test_flow_v2.py`（`RegressionViewTest`、`RegressionProblemsTest`、`ShortTierCasesTest`、`UsageRegressionTest`、`ProjectSectionContentTest`）与 `test_usage_draft.py`；
  不新建 `test_regression_view.py`——新建测试文件要在 `scripts/validate.sh` 登记，那个文件不在并行边界内。Spec 边界里列的 `test_regression_view.py` 不创建。

## 任务

- **Task 0**：提交 Spec 批准、本 Plan 与 todo。验证：`verify-and-commit` 快档。
- **Task 1**：解析与 sha256（含 CRLF 文档：顶层 `sha256` 等于原始字节的 sha256，R1-2）。先写会红的 `RegressionViewTest`：中文、英文各一份合格式文档，字段全部解析（含续行、代码块里的命令、`affectedExisting`、对照表的 `criteria`），`problems` 为空（AC1）；
  sha256 只改空白不变、改命令或预期变、改标题不变（AC5 前半）；每个问题代码一份最小反例（AC2 的解析一半）。再实现 `regression_view.py` 的解析部分。验证：`test_flow_v2.py`。
- **Task 2**：CLI 与 `--ref`。用例：`--module` 在 normal、small、bug 三档读对文档（AC6 后半）；`--ref` 读到旧提交上的版本，没有文档退出 3 `not-at-ref`，ref 不存在退出 4（AC5 后半）；旧提交上为 `small`、工作树改成 `normal` 时，档位、文档路径与用例都来自旧提交（R1-1）；旧提交上只因成批加入而判为重要需求的 `small` 模块按完整文档读（R2-1）；带 `export-ignore`、`export-subst` 属性的回归文档照样读到、摘要等于原始 blob（R2-2）；ref 上的 CRLF 文档摘要等于 blob 原始字节（R1-2）；老流程模块退出 3 `not-flow-v2`，没写回归文档退出 3 `no-document`，模块不在能力图退出 2。先红后实现。验证：同上。
- **Task 3**：接进 `flow_doc_problems` 与 `section-empty`。先写会红的用例：`RegressionProblemsTest`（AC2 的 verify-artifacts 一半、AC3、AC4，含影响面全是新文件时「不涉及」通过）；`ShortTierCasesTest`（small 判失败；bug 只有 Spec 不报、构建中（含最终 gate 未勾）警告、todo 全勾失败、只剩正式延期也失败、有 Plan 无 todo 与空 todo 只警告，AC6、R1-3、R2-3）；
  `ProjectSectionContentTest`（只有标题失败、「不涉及」通过、骨架章节空着不报，AC8）。再实现，含 `impact_has_old_files` 抽取（design-review 现有回归不变）。验证：`test_flow_v2.py`、`test-verify-artifacts.sh`（加正反各一例）。
- **Task 4**：阶段提示。`test-phase-guard.sh` 加：normal 模块构建中回归有问题时出那一行（列前三个代码）、问题修好后这一行消失；bug 构建中出补用例提醒；问题数变化时状态码改变；老流程模块提示逐字不变（AC9）。先红后实现。验证：`test-phase-guard.sh`、`test_flow_v2.py`。
- **Task 5**：联调回归。`test_usage_draft.py`：`spec/usage/` 下有 `<需求>.regression.md` 时 `draft_files` 不列它，里程碑与 `/map` 照常（AC7）；`UsageRegressionTest`：`--usage` 解析、`module-unknown`、`criterion-unknown`，草案只有现有三节且对照表不引用 `S<n>` 时没有问题（R1-4）；
  `test-verify-artifacts.sh` 加联调回归的正反各一例。先红后实现。验证：这三个文件。
- **Task 6**：接口 1.23。`interface.json` 的 `regressionView`、`check-interface.py` 的比对；一条用例按 `interface.json` 的命令模板代入真实路径运行，输出键集合与 `values` 一致（AC10 前半）。验证：`check-interface.py`、`test_flow_v2.py`。
- **Checkpoint 1（report）**：完整档三条检查全绿；老流程输出比对（AC9、R1-5）：对本仓库（全是老流程模块）和 `test-phase-guard.sh` 的一个老流程夹具，分别用已安装的 0.95.0 与工作区代码跑阶段提示 `additionalContext`、`map_view --json`（去掉生成时间）、verify-artifacts（逐行输出、通过／警告／失败计数、退出码），两边逐字相同；`test-verify-artifacts.sh` 另加一例锁定老流程夹具的计数与退出码；在临时副本里做变异（sha256 不压空白；不查 `command` 用例缺命令；`affected-existing-empty` 不看影响面；`draft_files` 不排除 `.regression.md`；`section-empty` 把注释行算内容），各自让对应用例变红，还原后全绿。
- **Task 7**：规则与文档。`references/doc-skeletons.md` 回归一节写全格式、例子、对照表、受影响的老功能、bug／small 的写法与联调回归；共享检查点规则里写回归文档那一步引用它；`docs/commands.md` 加 `regression_view`；
  `spec/usage/dev-flow-v2.md` 改 U1、U2、U3 三处字面（Spec 假设 9），「后续模块已收到的输入」一节的 regression-doc-check 一条标为已处理；CHANGELOG「未发布」加一条；版本 0.95.0 → 0.96.0（两份 plugin.json）。验证：快档（含读规则文件的现有回归）。
- **Checkpoint 2（gate）**：最后一次改动后重跑完整档三条并全绿；推送、开 PR、提议宿主 PR 监控；最终验收与合并合成一问（merge-ask-no-wait），验收消息写明当前头提交的 `CI required` 结果；
  给出给 mc-coord 的拟回告（`regressionView` 的实际字段、与草案 v1 的差别，账本 JFMRNH5），发出要用户同意；发 0.96.0 另取授权。

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=5 sha256=cd5f25d42642 -->
<!-- spec-guard: codex-review round=2 blocking=1 sha256=d2e47ef07773 -->
