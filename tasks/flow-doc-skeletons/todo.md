# Todo: flow-doc-skeletons

- [x] Task 0：提交 Spec、Plan 与 todo
- [x] Task 1：doc-skeletons.md、DOC_SECTIONS、flow_info 与回归
- [x] Task 2：新阶段、BEFORE_PLAN 替换、下一步文本与回归
- [x] Task 3：/map 的 tier、step，接口 1.18 与回归
- [x] Task 4：verify-artifacts 的 v2 检查与回归
- [ ] Task 5：规则文本与 docs/commands.md
- [ ] Checkpoint 1（report）：完整检查、变异与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行

## 证据

- Checkpoint 1 的检查结果、变异与实跑记在这里。

## 外部审查意见

- Plan 经 Codex（/delegate:review，对照 module_stage.py）审两轮：第 1 轮 5 条阻断、第 2 轮 4 条阻断，均已改进 Plan（轮次行见 plan.md）；按两轮上限转用户，2026-11-24 用户「Plan 批准」，同时批准 Spec 两处修订（AC1 例外、并行边界）。
