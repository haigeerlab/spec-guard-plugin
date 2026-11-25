# Todo: plan-auto-approve

- [x] Task 0：提交 Plan 与 todo（2026-11-25 用户「Plan 和 Spec 修订都批准」）
- [x] Task 1：自动批准本身与 review-mark 的 `plan-auto`
- [x] Task 2：`/map --json` 与接口 1.21
- [ ] Task 3：越界
- [ ] Task 4：T4
- [ ] Checkpoint 1（report）：本机完整检查与变异
- [ ] Task 5：verify-artifacts 警告
- [ ] Task 6：规则文字
- [ ] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告

## 证据
- Task 1（2026-11-25）：`test_flow_v2.py` 新增 `PlanAutoApproveTest` 3 例、`test_review_marker.py` 新增 `PlanAutoRefusal` 2 例（24 个子情形），先跑红（7 处失败、24 处失败）再实现，`test_flow_v2` 65 例、`test_review_marker` 78 例通过；`test_stop_rules.py` 加 `PlanAutoNode` 新旧对照，phase-guard 546 例通过。
  旧用例 `test_stop_node_is_not_plan_review_before_the_plan` 原来断言新流程 `NEEDS_PLAN` 是 `plan-review`，这正是本模块要改掉的行为，断言改为不是停点（老模块的同一断言在 `PlanAutoNode` 里保留）。
- Task 2（2026-11-25）：`test_map_view.py` 新增 `PlanAutoMapTest` 3 例先跑红（2 处失败），实现后整个文件通过；同一例里 Plan 带旧 `pending` 标记，断言 `review.plan` 仍是 `pending`、`reviewApprovedBy.plan`、`codexRoute.plan` 为 `auto`、`awaitingReview` 不列它。`APPROVED_BY`、`CODEX_ROUTE` 加 `auto`，`interface.json` 升到 1.21，`check-interface.py` 本来就比对这两组取值，通过。代码在 2894252 提交；`docs/commands.md` 与本条勾选因脚本替换失败没进那个提交，补在下一个提交里。
