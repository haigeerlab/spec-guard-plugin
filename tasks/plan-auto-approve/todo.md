# Todo: plan-auto-approve

- [x] Task 0：提交 Plan 与 todo（2026-11-25 用户「Plan 和 Spec 修订都批准」）
- [x] Task 1：自动批准本身与 review-mark 的 `plan-auto`
- [x] Task 2：`/map --json` 与接口 1.21
- [x] Task 3：越界
- [x] Task 4：T4
- [x] Checkpoint 1（report）：本机完整检查与变异
- [x] Task 5：verify-artifacts 警告
- [x] Task 6：规则文字
- [x] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告
- [x] Task 7：`own_doc` 与 `t4_hits` 去掉本模块文档与流程记账（返工，Spec 假设 12、14）
- [x] Task 8：`important()` 去掉本模块文档（返工，Spec 假设 13）
- [x] Task 9：规则文字与版本 0.97.1
- [x] Checkpoint 3（report）：完整档、变异、沙盒复跑与老输出比对
- [ ] Checkpoint 4（gate）：推送、开 PR、最终验收并同时问合并

## 证据
- Task 1（2026-11-25）：`test_flow_v2.py` 新增 `PlanAutoApproveTest` 3 例、`test_review_marker.py` 新增 `PlanAutoRefusal` 2 例（24 个子情形），先跑红（7 处失败、24 处失败）再实现，`test_flow_v2` 65 例、`test_review_marker` 78 例通过；`test_stop_rules.py` 加 `PlanAutoNode` 新旧对照，phase-guard 546 例通过。
  旧用例 `test_stop_node_is_not_plan_review_before_the_plan` 原来断言新流程 `NEEDS_PLAN` 是 `plan-review`，这正是本模块要改掉的行为，断言改为不是停点（老模块的同一断言在 `PlanAutoNode` 里保留）。
- Task 2（2026-11-25）：`test_map_view.py` 新增 `PlanAutoMapTest` 3 例先跑红（2 处失败），实现后整个文件通过；同一例里 Plan 带旧 `pending` 标记，断言 `review.plan` 仍是 `pending`、`reviewApprovedBy.plan`、`codexRoute.plan` 为 `auto`、`awaitingReview` 不列它。`APPROVED_BY`、`CODEX_ROUTE` 加 `auto`，`interface.json` 升到 1.21，`check-interface.py` 本来就比对这两组取值，通过。代码在 2894252 提交；`docs/commands.md` 与本条勾选因脚本替换失败没进那个提交，补在下一个提交里。
- Task 3（2026-11-25）：`module_scope.flow_scope` 返回 `ok`／`none`／`unknown`／`invalid`；`classify` 对新流程不认预先声明、流程文件算 `flow`；`check` 命令（`none` 退出 3、`unknown`／`invalid` 退出 4）、`declared`（字段不变，新流程 `planApproved` 看 Plan 在不在、`approvedCommit` 为 null）、`validate-declared`（新流程报 `ignored`）、阶段提示 `_flow_overreach`、最终验收 `_outside` 都改走它，老模块分支一字未改。
  用例：`test_module_scope.py` `FlowScope` 8 例先红（5 失败 3 错）后绿，整个文件 65 例；`test_flow_v2.py` `FlowOverreachTest` 6 例、`test_review_marker.py` `AcceptanceFlowScope` 2 例，换回提交前的三个源文件跑，前者 5 例红（剩下 1 例测的是 design-review 原有的「改过即 revised」）、后者 2 例红。phase-guard 546 例通过。
  旧用例 `test_scope_line_stays_but_the_requirement_comes_first` 对新流程模块断言的是旧越界措辞，改成新措辞，用例意图不变。夹具：`FlowScope` 里两例显式传 `--base base`（`Repo` 的基线提交已含 `spec/m.md`）。
- Task 4（2026-11-25）：`module_stage.t4_hits`（只看 T4，`ok`／`no-list`／`no-base`，`stops` = 有命中且不是重要需求）；`important()` 对新流程模块加读技术方案影响面；阶段提示把越界与 T4 两部分各出一行，`check` 命令的 JSON 加 `t4`（只新流程模块），最终验收的范围检查先查 T4、再看范围。
  用例：`test_important_requirement.py` `ImpactRiskPath`（新旧对照）、`test_flow_v2.py` `T4Test` 6 例、`test_module_scope.py` `FlowT4`、`test_review_marker.py` `AcceptanceT4`，换回提交前的源文件跑都变红。
  写用例时发现并修了一处实现漏洞：最终验收在 bug、small 没有边界（`none`）时先返回了，T4 被跳过；改为先查 T4。`AcceptanceFixture` 的能力图是一次插入两个模块，按规则已是重要需求，所以最终验收的 T4 用例另建单模块仓库直接调 `_outside`。
- Checkpoint 1（2026-11-25）：Task 1～4 的提交都走完整档且全绿（phase-guard 546 例、verify-artifacts 127 例）。变异在临时副本里做，各自在两个入口变红：
  `effective_review` 不给新流程 `auto` → `PlanAutoApproveTest` 5 处、`PlanAutoMapTest` 1 处失败；`classify` 对新流程照旧认预先声明 → `FlowOverreachTest`、`FlowScope` 各 1 处；T4 去掉「不是重要需求」 → `T4Test`（已是重要需求改影响面里的 T4 路径）、`FlowT4`（`stops`）各 1 处。还原后全绿。
- Task 5（2026-11-25）：判据在 `module_stage.plan_auto_problems`（只看未完成的新流程模块，范围用同一个 `flow_scope`）：并行边界写坏失败、normal 没有范围警告、Plan 带标记警告；`validate-declared` 的 `ignored` 行在 verify-artifacts 里出警告「预先声明不起作用」。`test-verify-artifacts.sh` 加 7 例，134 例通过；把判据改成直接返回空，第一条新用例就变红。
- Task 6（2026-11-25）：共享规则新增「## 新流程 Plan 自动批准」（授权什么、不授权什么，越界与 T4 停下后怎么放行）；`node-rules.md`「Plan 交审」「中途 gate」各加一行。`test_workflow_checkpoints.py` 新增 `PlanAutoApproveRuleTests` 3 例（共 31 个短语），96 例通过；`test_stop_rules.py` 通过。
  与 Spec 假设 8 的出入：假设 8 写「『批准标记』一节加一条」，但已有用例 `test_review_markers` 断言那一节不出现「自动批准」（防泛泛的自动批准规则），所以写成紧跟其后的单独一节，内容不变，那条保护保留。
- Checkpoint 2（2026-11-25）：基于 main `0ba7caf7` 推送，开 PR #494；提议了宿主 PR 监控，用户没有选择打开。最终验收与合并合成一问，用户回「验收通过并合并」。当时 `validate` 未跑完，按 #493 的做法开 GitHub 自动合并（squash，只认头提交 `7f0db60d`）；核实：五项检查（含 `CI required`）SUCCESS，state=MERGED，main 指向合并提交 `27eada19`。回告：发 autopr-design #22967（对方会话没在运行，排队等送达），文字与验收消息里的拟回告相同。
- Task 7（2026-11-26）：`module_stage.own_doc`（`spec/<id>.md` 与 `tasks/<id>/` 下 `OWN_DOCS` 四个文件名，只比字符串）、`T4_FLOW_FILES`（能力图、`.agent/state.json`）；`t4_hits` 对新流程模块比清单前去掉这两类。用例：`test_flow_v2.py` `T4OwnDocsTest` 3 例（只改自己文档不停；别的模块文档、`tasks/a/notes.md`、`spec/usage/`、风险清单本身、`.agent/config.json` 各自照旧停；老模块命中不变）、`test_module_scope.py` `FlowT4` 一例（`check --json` 的 `t4`）、`test_review_marker.py` `AcceptanceT4` 一例（最终验收）。实现前 7 处 + 2 处失败（老模块一例实现前已通过，锁住现状），实现后三个文件 328 例通过。夹具注意：两个模块同批写进能力图按规则就是重要需求、T4 不停，所以夹具只放一个模块。
- Task 8（2026-11-26）：`important()` 对新流程模块拼好边界、预先声明、影响面的路径后，去掉 `own_doc` 认出的文件与 `tasks/<id>/` 目录项。用例：`test_important_requirement.py` `OwnDocsRiskPath` 3 例（边界与影响面只写自己文档不判 `risk-path`；另列 `.github/ci.yml` 或影响面写别的模块的 `spec/beta.md` 照旧判；老模块照旧判），实现前第一例失败，另两例实现前已通过、锁住现状；与 `test_flow_v2.py` 共 170 例通过。风险清单写在 `check()` 里而不是 `setUp`，否则继承来的老用例换了清单会变红。
- Task 9（2026-11-26）：共享检查点规则重要需求一段与「碰 T4」一条各补一句；`test_workflow_checkpoints.py` 加 `test_own_documents_are_not_t4`（3 个短语，旧规则文件里一个都没有，即改前会红）；CHANGELOG「未发布 · 修复」一条；版本 0.97.0 → 0.97.1（两份 plugin.json、两份 README 的 `--ref`）。Task 8 与 Task 9 因检查脚本要求工作区全部暂存，合在一个提交里。
- Checkpoint 3（2026-11-26）：Task 7、8+9 的提交都走完整档且全绿。变异（临时副本）：`t4_hits` 不去掉 `own_doc` → 7 处失败；`.agent/config.json` 也去掉 → 1 处；`important()` 不去掉 `tasks/<id>/` 目录项 → 1 处；去掉 `_v2` 判断 → 1 处；还原后全绿。沙盒 drill-pow 只读复跑（克隆到暂存目录、检出 `c2ec343`，基线 `21217fd^`）：`t4_hits` 从 8 个命中降到只剩 `.agent/config.json`，`stops` 为 True——在这个提交上 `src/calc.py` 还不是 T3，drill-pow 不是重要需求，所以开工时给自己设 `moduleTakeover: merge` 会停一次交用户（Q1 A 的预期代价）。已安装的 0.97.0 与本分支对本仓库的阶段提示、verify-artifacts 逐字相同。
