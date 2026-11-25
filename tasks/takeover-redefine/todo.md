# Todo: takeover-redefine

- [x] Task 0：提交 Spec 批准、Plan 与 todo（2026-11-25 用户「批准；Q1 A；Q2 A；Q3 A」「按处理办法改，都批准」）
- [x] Task 1：取值、换算、set 拒收、show 提示
- [x] Task 2：收窄
- [x] Task 3：技术方案的批准人
- [x] Task 4：`/map --json` 与接口 1.22
- [x] Checkpoint 1（report）：本机完整检查与变异
- [x] Task 5：verify-artifacts
- [x] Task 6：规则与文档
- [ ] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告

## 证据
- Task 1（2026-11-25）：`project_config` 新三项 `ITEMS`、预设 `none`／`design`／`merge`；旧值 `valid_takeover` 照认，`expand` 换算出新三项、`legacy` 换算出老流程的 `spec`／`plan`，`module_takeovers` 每个模块返回五个键；`set` 遇到旧写法（含 `requirement`）退出 2、拒绝码 `takeover-legacy`；`show` 的 JSON 加 `effective`／`legacy`，文本加一行生效值与两条 `note:`，`set` 预览加老流程一行和「改前是旧值」的提示。
  `important()` 的 `codex` 判断对新流程模块一律为假（R2-1）。用例：`test_project_config.py` `Takeover` 新增 4 例、改写 6 例；`test_flow_v2.py` `TakeoverImportantTest` 2 例。
  旧用例改动及原因：`Takeover`、`RetiredAutonomy` 里用旧预设 `plan` 当「合法新值」写入的用例改为 `design`（旧值现在只读不写）；预设展开与来源的期望值改成五个键（新三项 + 老流程两项）。
- Task 2（2026-11-25）：阶梯 `merge` → `design` → `none`，旧 `plan` 收一格到 `none`；自定义按 `release`、`merge`、`design` 交还并写回新格式，只剩旧项的收到 `none`；`from: "plan"` 的记录在 `set` 写 `none` 或 `design` 时删除（`_keep_narrowed` 一处）。`Narrow`、`Restore` 改写原有阶梯用例，新增 `test_old_values_narrow_to_new_ones`、`test_narrowed_from_old_plan_is_restored_by_none_or_design`。
  `test_project_config.py` 79 例通过；换回提交前的 `project_config.py`，20 例失败、1 例出错。
- Task 3（2026-11-25）：`design_approver`（重要需求 `user`，否则看档位 `design`）；`design_approval` 在 `human` 下：不需要审 → `pending-user`，审过无阻断（`reviewer-approved` 带指纹）→ `pending-user`，改稿 → `revised` → 先重审；`design_waits` 对失效的第二审查者放行在构建中也拦；`design_hint` 两条路线都写档位来源（`project_config.takeover_origin`，含「继承项目 takeover，模块覆盖无效」）；状态码加 `design_fact`；模块 checkout 的角色提示按路线写；review-mark 在 `human` 下照记 `reviewer-approved` 并提示仍要用户批；verify-artifacts 的警告条件同步（Task 5 加用例）。
  用例：`test_flow_v2.py` `HumanDesignRouteTest` 6 例、`test_review_marker.py` 1 例；换回提交前的 `module_stage.py`、`review_mark.py`，这 9 例全部变红。
  旧用例改动及原因：design-review 的用例是按「第二审查者放行即可」写的，现在这条路线是 `takeover=design`，默认档位改为交用户；所以 `hint()` 夹具、`DesignApprovalTest`、`FlowOverreachTest` 显式设 `takeover=design`，提示文字的期望值带上档位来源；`PlanAutoApproveTest.test_old_module_still_waits` 要的是旧的人批路线，改为不设档位。
- Task 4（2026-11-25）：`/map --json` 的 `takeover` 按 `TAKEOVER_FIELDS` 给 `design`、`merge`、`release`、`spec`、`plan`、`designForcedBy`、`source`、`widerThanProject`、`narrowed`；重要需求的新流程模块 `design` 报 `human`、`designForcedBy: "important"`。`interface.json` 升到 1.22（`takeover` 的预设、项、`legacy`、说明，`mapView.takeover` 的字段，`takeoverNarrow.order`），`check-interface.py` 通过。
  用例：`TakeoverTest` 改写 3 例、新增 3 例（键集合与接口一致、老流程两项与 `codexRoute`／`reviewApprovedBy`、新流程的两项与强制）；`DesignApprovalMapTest` 设 `takeover=design` 并新增 `test_human_route`。换回提交前的 `map_view.py` 与 `interface.json`，5 例变红。
- 提交前完整检查（2026-11-25）：`test_stop_rules.py` 的 `DesignReviewNode.test_a_design_with_nothing_to_review_does_not_stop` 按旧默认行为（不需要审即放行）断言，在默认 `design=human` 下变红；该文件在并行边界外，按 Plan 停下问用户，用户「可以，加进边界并改」：夹具设 `takeover=design`，Spec 并行边界补入并记修订。
  `test-phase-guard.sh` 同一段改为默认 `human` 与 `design` 各验一次（547 例）。`test_map_view.py` 的 `AutonomyTest.test_text_table_unchanged` 比较两张带生成时间的表，这次两次运行跨过分钟（18:50／18:51）变红，与本模块无关，未改。
- Checkpoint 1（2026-11-25）：Task 1～4 的提交 `f1b8eb2` 走完整档且全绿（phase-guard 547 例、verify-artifacts 134 例）。变异在临时副本里做，各自变红：
  `legacy()` 去掉 `design → plan=codex` → `test_old_values_are_read_converted`；`reviewer-approved` 不看 `approver` → `HumanDesignRouteTest` 4 例、`DesignMarks` 1 例；
  `designForcedBy` 不看重要需求 → `test_flow_v2_module_reports_the_pair_and_the_forced_design`；收窄不认旧 `plan` → `Narrow`、`Restore` 各 1 例。还原后全绿。
- Task 5（2026-11-25）：判据在 `design_review_problems`（`design=human` 时只有第二审查者放行也警告，同重要需求）。`test-verify-artifacts.sh` 加 4 例（`human` 警告、`design` 不警告、旧值有效、`design` 取值写错判无效），138 例通过；把判据改回只看重要需求，`human` 那一例变红。
- Task 6（2026-11-25，部分）：`commands/config.md`（两行、示例、收窄）、共享规则「技术方案审查」「自治档位与底线」、`docs/commands.md`、README「自动接管」一节（补新流程模块的说明，README 原来没有讲新流程的段落）、CHANGELOG「未发布」三条。
  边界外还有 `skills/spec-guard-ops/SKILL.md` 第 191 行与 `docs/concepts.md` 第 81 行写着旧档位，停下问用户。
- Task 6（2026-11-25，补完）：用户「可以，加进边界并改」，`skills/spec-guard-ops/SKILL.md` 的 `takeover` 说明与收窄一行、`docs/concepts.md` 概念表的「接管档位」一行同步成新档位；Spec 并行边界补入这两个文件。
