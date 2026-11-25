# Todo: design-review

- [x] Task 0：提交 Plan、todo 与 Spec 边界修订（2026-11-25 用户「Plan 和 Spec 修订都批准」）
- [x] Task 1：`designReview` 配置键
- [x] Task 2：`inspect_design` 与 `review_mark --target design`
- [x] Task 3：审查要求、`designApproval`、阶段提示与停点
- [ ] Checkpoint 1（report）：本机完整检查与变异
- [ ] Task 4：`/map --json` 的 `designApproval` 与接口 1.20
- [ ] Task 5：verify-artifacts 的检查
- [ ] Task 6：规则文字与停点规则
- [ ] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告

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
