# Todo: regression-doc-check

- [x] Task 0：提交 Spec 批准、Plan 与 todo（2026-11-25 用户「批准；Q1 A；Q2 A」「按处理办法改，批准」）
- [x] Task 1：解析与 sha256
- [x] Task 2：CLI 与 `--ref`
- [x] Task 3：接进 `flow_doc_problems` 与 `section-empty`
- [x] Task 4：阶段提示
- [x] Task 5：联调回归
- [x] Task 6：接口 1.23
- [x] Checkpoint 1（report）：本机完整检查与变异
- [x] Task 7：规则与文档
- [x] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告（用户「验收通过并合并」）
- [x] Task 8（返工，M3 实跑发现，用户「M3 A」）：bug 档修完往需求文档的「回归用例」一节补用例，不再让已确认的需求变成要重新确认——批准指纹不算 bug 档这一节的内容；旧算法批准的需求在内容不变时照样算批准
- [x] Checkpoint 3（gate）：完整检查、推送、开 PR、发版后复跑 U3（用户「验收通过并合并」「合并 #506，发 0.96.1」）

## 证据
- Task 1（2026-11-25）：新文件 `hooks/regression_view.py` 的解析部分：`parse_regression`（三种文档：模块回归、`spec/<id>.md` 的回归用例一节、联调回归）、`criteria_ids`、`case_sha256`（五个字段压空白后按固定键序算，标题与编号不算）。字段名中英文、冒号中英文都认，续行与代码块并入当前字段，围栏里的标题不算用例。
  用例：`test_flow_v2.py` `RegressionParseTest` 6 例（中英文各一份、围栏、成功标准编号、sha256 只改空白与标题不变而改内容变、九个问题代码各一份反例）；实现前运行 14 个错误（模块不存在）。
- Task 2（2026-11-25）：CLI `--json --project (--module|--usage) [--ref]` 与退出码；`--ref` 在临时目录里做共享对象的本地克隆、检出到那个提交，文档字节用 `git cat-file blob` 读原始 blob（R2-1、R2-2）。`module_stage.impact_has_old_files` 从 `design_requirement` 抽出，判定不变（`test_flow_v2.py` 全部通过）。
  用例：`RegressionViewCliTest` 7 例。实现写在这批用例之前，用例一次通过，没有经过先红；补做变异：`--ref` 改读工作区 → 3 例变红；改读克隆的检出文件而不是 blob → `test_ref_bytes_are_the_raw_blob` 变红（样本最初没有 `text eol=crlf`，检出与 blob 字节相同，这处变异没拦住，补上属性后拦住）。
- Task 3（2026-11-25）：`flow_doc_problems` 接上 `regression_problems`（`regression_view.module_report` 的问题，`tasks/<id>/regression.md` 与 bug／small 的「回归用例」一节；bug 没有用例时：只有 Spec 不报，构建中、有 Plan 无 todo、空 todo 警告，todo 有勾选项且阶段已完成（含只剩正式延期）判失败）与 `section-empty`（只查 `projectSections` 声明的章节，注释行不算内容、代码块算）。
  用例：`test_flow_v2.py` `RegressionProblemsTest` 5 例、`ShortTierCasesTest` 3 例、`ProjectSectionContentTest` 1 例，实现前 8 个失败；`test-verify-artifacts.sh` 加 5 例（143 例通过）。
  旧用例改动及原因：`ProjectSectionsTest.test_bug_and_small_…` 与 `test-verify-artifacts.sh` 的 plan-auto-approve 夹具原来用只写「不涉及」的回归用例／回归文档，本模块起 small 与 normal 的回归必须有用例，改成一条合格用例（新增辅助函数 `good_regression`）。
- Task 4（2026-11-25）：`regression_line`：新流程模块在写 Plan 或构建中、回归有问题时，阶段提示多一行（问题数、前三个问题代码与位置、跑 verify-artifacts），bug 构建中没有用例时改成补用例提醒；只写固定词、代码、编号与路径。问题数进状态码（`_describe_body` 的事实与 `_role_facts`）。
  用例：`test_flow_v2.py` `RegressionHintTest` 4 例，实现前 3 个失败（老流程那一例本来就通过）；`test-phase-guard.sh` 加 2 例（549 例通过），这 2 例写在实现之后，没有经过先红，留到 Checkpoint 1 用变异核对。
- Task 5（2026-11-25）：`usage_draft.draft_files` 跳过 `*.regression.md`；verify-artifacts 新增一段，对 `spec/usage/*.regression.md` 跑 `regression_view.usage_report`，格式问题、`module-unknown`、对照表实际引用的未知 `S<n>` 判失败，合格式时报通过。
  用例：`test_usage_draft.py` 1 例（实现前失败）；`test_flow_v2.py` `UsageRegressionTest` 3 例（解析在 Task 1 已实现，一次通过）；`test-verify-artifacts.sh` 加 3 例（146 例通过）。
- Task 6（2026-11-25）：`interface.json` 升到 1.23，加 `regressionView`（`command`、`refArgs`、`usageCommand`、`schemaVersion`、`contract`、`exitCodes`、`values` 的执行方式、问题代码、字段、用例 sha256 算法与文档位置）；`check-interface.py` 比对脚本存在、`command` 能原样运行、`refArgs`、`schemaVersion`、执行方式与问题代码和代码一致。
  偏离 Spec 假设 4 的写法：Spec 把命令模板写成带 `"[--ref <git ref>]"` 的一个数组；module-crew 的 `probe.safe_command` 把模板逐段原样当参数传入（只替换占位符），带方括号那一段会让 argparse 退出 2，module-crew 的最终验收就跑不起来。所以 `command` 只放能原样运行的形式，`--ref` 放在 `refArgs`，`--usage` 放在 `usageCommand`；验收时交用户确认。
  用例：`RegressionInterfaceTest` 1 例（按 `interface.json` 的模板代入真实路径运行，带与不带 `refArgs` 各一次，核对输出键集合与取值）；在临时副本里删掉问题代码 `module-unknown`、给 `command` 加上方括号可选参数，`check-interface.py` 各报一条失败。
- Task 6 提交前（2026-11-25）：`scripts/test-checkers.sh` 的接口夹具 `mkifc` 没有 `regression_view.py`，「与代码一致 → 放行」一例变红；该文件在并行边界外，停下问用户，用户「可以，加进边界并改」：脚本名列表加 `regression_view`，Spec 并行边界补入并记修订。
- Checkpoint 1（2026-11-25）：Task 1～6 的每次提交都走了完整档且全绿（最后一次 `d3e10fa2`：phase-guard 549 例、verify-artifacts 146 例）。
  老流程输出比对（AC9、R1-5）：已安装的 0.95.0 与工作区代码分别跑本仓库（全是老流程模块）和一个老流程临时夹具（三个模块，当前模块分别为构建中、缺 Plan，带 `projectSections`），阶段提示 `additionalContext`、`map_view --json`（去掉 `generatedAt`）、verify-artifacts（逐行输出与退出码）两边逐字相同；第一次跑夹具时没有激活信号、阶段提示两边都是空，补上 `.agent/state.json` 后重跑。
  `test-verify-artifacts.sh` 加 1 例锁住老流程夹具的计数（3 通过 · 1 警告 · 0 失败）与退出码 0，0.95.0 与工作区对同一夹具都是这个结果。
  变异（临时副本）：sha256 不压空白、不查 command 用例缺命令、受影响的老功能不看影响面、`draft_files` 不排除 `.regression.md`、注释行算章节内容、bug 完成不看 todo、去掉阶段提示行，各自让对应用例变红（去掉提示行也让 `test-phase-guard.sh` 的新用例变红）。sha256 那处第一次没拦住：用例只改了首尾空白，而解析时首尾空白已去掉；改成同一步骤跨行与单行两种写法后拦住。还原后全绿。
- Task 7（2026-11-25）：`references/doc-skeletons.md` 回归一节写全用例格式（字段表、例子、对照表、受影响的老功能、bug／small、检查在哪里）与多模块联调回归；共享检查点规则「新流程模块的写法」一条引用它；`docs/commands.md` 的 verify-artifacts 表加三行、加 `regression_view.py` 一节；
  `spec/usage/dev-flow-v2.md` 改 U1（只有 `takeover=design`／`merge` 才无需你批）、U2（技术方案先批、再写回归文档）、U3（小改动不走技术方案审查），「后续模块已收到的输入」记已处理；CHANGELOG 新增「未发布」一条；版本 0.95.0 → 0.96.0（两份 plugin.json）。
  提交前快档校验要求两份 README 的安装命令 `--ref` 与清单版本一致；两份 README 在并行边界外，停下问用户，用户「可以，加进边界并改」：改成 `v0.96.0`，Spec 并行边界补入并记修订。
- Checkpoint 2（2026-11-25）：基于 main `560c5731` 推送，开 PR #500 并绑定到会话；验收消息里提了宿主 PR 监控，由用户决定，没有打开。最终验收与合并合成一问，用户回「验收通过并合并」（同时批准修订后的 Spec：并行边界补入 `scripts/test-checkers.sh`、两份 README）。拟回告发给 mc-coord 与 autopr-design。
- M3 实跑（2026-11-26，安装版 0.96.0）：bug 修完往 `spec/a.md` 的「回归用例」一节补用例后，阶段提示变成「需求文档确认后又改过，要用户重新确认」，`requirementConfirm.status` 为 `revised`，verify-artifacts 多一条「批准后已修订」。用户「M3 A」：这次不通过，追加 Task 8。
- Task 8（2026-11-26）：`module_stage.review_digest` 对新流程 bug 档需求文档不算「回归用例」一节的内容（标题保留，围栏里的标题不算）；`review_state` 与基线查找同时认 0.96.0 及更早的整份指纹（`whole_review_digest`），旧批准在内容不变时照样有效。小改动照旧算进指纹。写批准标记的 review-mark 走同一个 `review_digest`，不用改。
  用例：`test_flow_v2.py` `BugCaseNoReconfirmTest` 4 例（bug 补用例保持已确认、改复现步骤仍要重新确认；small 补用例仍要重新确认；旧算法的批准照样有效；围栏里的标题不开启这一节），实现前核心那例失败。变异：不看围栏、不去掉这一节、不认旧指纹，各自让对应用例变红。文档：`doc-skeletons.md` 的 bug 一条补一句；CHANGELOG「未发布」；版本 0.96.0 → 0.96.1（两份 plugin.json、两份 README 的 `--ref`）。
- Checkpoint 3（2026-11-26）：#505 合并（fce30e2f）；0.96.1 发布（#506 合并 e8390a66，资产 sha256 07f65487…d490），本机两侧已装、Codex smoke 通过。用安装版 0.96.1 复跑 U3：bug 修完补用例后 `requirementConfirm.status` 仍为 `confirmed`、阶段提示不再要求重新确认、verify-artifacts 0 警告 0 失败；再改复现步骤则为 `revised`。合并前阶段提示报「16 个文件越界」是误报：越界检查以本模块最初开工前的提交为基线，把之后别的模块的合并也算了进来；#505 实际只改了边界内的 9 个文件。
