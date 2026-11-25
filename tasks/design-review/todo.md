# Todo: design-review

- [x] Task 0：提交 Plan、todo 与 Spec 边界修订（2026-11-25 用户「Plan 和 Spec 修订都批准」）
- [x] Task 1：`designReview` 配置键
- [x] Task 2：`inspect_design` 与 `review_mark --target design`
- [x] Task 3：审查要求、`designApproval`、阶段提示与停点
- [x] Checkpoint 1（report）：本机完整检查与变异
- [x] Task 4：`/map --json` 的 `designApproval` 与接口 1.20
- [x] Task 5：verify-artifacts 的检查
- [x] Task 6：规则文字与停点规则
- [x] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告

## 证据
- Task 1（2026-11-25）：`test_project_config.py` 先加三例跑红（取值、汇总键集合、set／unset），改 `project_config.py`（`DEFAULTS` 与 `VALIDATORS` 各一项，取值复用 `off`／`on`）后全绿；
  `commands/config.md` 表格加一行、「不注入」名单加 `designReview`。`test_flow_v2`、`test_map_view` 照常通过（配置键集合只在 `test_project_config` 里写死）。
- Task 2 的事实核对（2026-11-25）：delegate 0.12.2 `interface.json`：`review.profiles.design.criteria = design-v1`，`review.reviewer.selections` 为
  `cross_vendor`／`same_vendor_fallback`／`explicit`／`none`，`unreviewed = no_reviewer_available`，`vendors` 为 codex→openai、claude-code→anthropic；
  一份真实报告的顶层键有 `criteria`、`reviewer{vendor, backend, same_vendor, selection}`、`scope.files`（路径→sha256）、`execution_status`、`review_outcome`、`recheck`，与 Spec 假设 5 一致。
- Spec 修订（2026-11-25）：`reportSha256` 在原轮次行里没处存，轮次行末尾加 `report=<报告文件 sha256，64 位>`，假设 5、8 各改一处；用户「选 A，同意修订 Spec」，已重记批准。
- Task 2（2026-11-25）：`test_review_marker.py` 新增 `DesignMarks` 11 例先跑红（`--target design` 不存在），实现后全绿；整个文件 76 例在 3.10 与 `/usr/bin/python3` 3.9 下都通过，`test_flow_v2` 47 例通过。
  AC5 由 `test_only_unresolved_recheck_items_still_block` 证明：第二轮报告只有一条 `unresolved`、没有新发现，记成 `blocking=1`，`reviewer-approved` 被拒。
  另加一条（Plan 范围内的细化）：上一轮有阻断时，下一份报告必须带 `recheck`（用 `--previous-report`），否则拒绝（`design-recheck-missing`）。
- Task 3（2026-11-25）：`module_stage.py` 加 `design_requirement`、`design_approval`、`design_hint`，`review_hint` 在没有别的批准事项时接上技术方案的「批准」行，停点加 `design-review`（「技术方案交审」），命令表加 `author-host`（Claude Code 为 `claude-code`、Codex 为 `codex`、不明为 `<claude-code|codex>`）。
  `test_flow_v2.py` 新增 `DesignRequirementTest` 7 例、`DesignApprovalTest` 8 例：换回提交前的 `module_stage.py` 跑，15 例全红（14 错 1 失败），新版全绿，整个文件 62 例通过；`test_stop_rules.py` 加 2 例（23 例通过）；`test-phase-guard.sh` 加 5 例（546 例通过）。
  旧用例 `test_new_stages_name_the_document_and_the_skeleton` 的技术方案原来只写 `# d`，按 Plan「写不出路径按必审」现在会出审查命令，夹具改成只列新文件，断言不变。
  与 Plan 的出入：Plan 写「跨模块复用 `important()` 的判定」。实际上跨模块（`cross-module`）已经被现有规则升为重要需求，按假设 2 的顺序先落到「重要需求 → 用户批」，所以没有另写跨模块分支，由 `test_cross_module_is_important_by_rule` 锁住。只在 `NEEDS_REGRESSION` 时拦，之后的阶段只在「放行后又改过」时提示，免得已经写完回归文档的老技术方案被回头拦下。
- Checkpoint 1（2026-11-25）：Task 2、Task 3 的提交都走了完整档且全绿（validate、phase-guard 546 例、verify-artifacts 120 例、ShellCheck 无告警）。变异都在临时副本里做：
  阻断数改回只数 `findings` → `DesignMarks` 2 例失败（含 AC5 那一例）；去掉「影响面列已有文件」 → `DesignRequirementTest`、`DesignApprovalTest` 8 例失败、1 例报错。还原后全绿。
- Task 4（2026-11-25）：`test_map_view.py` 的模块字段集合加 `designApproval`，新增 `DesignApprovalMapTest` 4 例，先跑红（6 处报错）后实现，整个文件通过。`map_view.py` 只输出 Spec 假设 8 的六个键（`need`、`reason` 只在 `module_stage` 内部用）；`interface.json` 升到 1.20，加 `mapView.designApproval`、reviewMark 的 `--target design` 与拒绝码；`check-interface.py` 新增 `_design_approval`，把一个状态值改名后检查器报错，还原后「interface.json 与代码一致」；`docs/commands.md` 补 review-mark 一段与 `/map --json` 的说明。
- Task 5（2026-11-25）：判据写在 `module_stage.design_review_problems`，verify-artifacts 在原来查新流程文档的那段 Python 里一起调用，不在 shell 里重写。`test-verify-artifacts.sh` 加 7 例（标记与轮次行有效通过、轮次行写坏失败、两轮 criteria 不同失败、批准标记不带指纹失败、重要需求只有第二审查者放行时警告、老模块不查），127 例通过；把判据改成直接返回空，回归在「轮次行写坏时失败」变红。phase-guard 不涉及这几条（它只读状态，不报格式错误），由 Task 3 的阶段提示用例覆盖同一判据。
- Task 6（2026-11-25）：`workflow-checkpoints.md` 在「需求确认」之后加「## 技术方案审查」（放行顺序、审查命令与记法、阻断口径、未审、放行后修订）；`node-rules.md` 在「Spec 交审」与「Plan 交审」之间加「## 技术方案交审」。`test_workflow_checkpoints.py` 新增 `DesignReviewRuleTests`（21 个要点短语），停点规则的章节列表与要点表加这一节，92 例通过；`test_stop_rules.py` 的章节用例加 `design-review`，重要需求的停点用例断言附上了这一节的规则，23 例通过。
- Checkpoint 2（2026-11-25）：变基到 main（含 #491）后推送，开 PR #492；提议了宿主 PR 监控，用户没有选择打开。最终验收与合并合成一问，用户回「验收通过并合并」。合并前核实：validate、python 3.9、python 3.13、plugin、`CI required` 全部 SUCCESS，`mergeStateStatus` 为 CLEAN，头提交 `3de789be` 与本地一致；squash 合并后核实 state=MERGED，main 指向合并提交 `c37dc68a`。回告：发 autopr-design #22934（对方会话没在运行，排队等送达），发 delegate-owner #22935（已发出提醒，等回执），文字与验收消息里的拟回告相同。
