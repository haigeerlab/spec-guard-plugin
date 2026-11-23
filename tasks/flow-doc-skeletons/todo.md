# Todo: flow-doc-skeletons

- [x] Task 0：提交 Spec、Plan 与 todo
- [x] Task 1：doc-skeletons.md、DOC_SECTIONS、flow_info 与回归
- [x] Task 2：新阶段、BEFORE_PLAN 替换、下一步文本与回归
- [x] Task 3：/map 的 tier、step，接口 1.18 与回归
- [x] Task 4：verify-artifacts 的 v2 检查与回归
- [x] Task 5：规则文本与 docs/commands.md
- [x] Checkpoint 1（report）：完整检查、变异与实跑
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行

2026-11-24 用户「验收通过」。推送与开 PR 等 PR #483 合并后再做。

## 证据

- Checkpoint 1（2026-11-24，提交 cb75ad0 上的 verify-and-commit 全套，macOS `/bin/bash`）：`validate.sh` 退出 0「校验通过 ✅」；`test-phase-guard.sh` 退出 0「phase-guard regression passed (540 cases)」；
  `test-verify-artifacts.sh` 退出 0「verify-artifacts regression passed (113 cases)」；`check-interface.py` 退出 0「interface.json 与代码一致」，`interface.json` 为 1.18。
  另：把 `mapView.flow.tierValues` 去掉 small 时 `check-interface.py` 退出 1（已还原）。
- 变异（各自还原）：不识别流程标记 → `test_flow_v2` 16 例失败；`SHORT_TIERS` 置空（bug／small 不跳过）→ `test_bug_and_small_skip_design_and_regression` 两个子用例失败；
  不查章节 → `test-verify-artifacts.sh`「新流程模块：回归文档缺章节时失败」失败。
- 本仓库新旧比对（旧代码取自 3de8412，Task 1 之前）：`/map --json` 去掉 `tier` 后逐字相同（194 个模块的 `tier` 全为 null）；阶段提示逐字相同；`verify-artifacts.sh` 输出与退出码（0）逐字相同。
- 临时项目实跑（normal 档，zh-CN）：需求已批 → `NEEDS_DESIGN`（step design，提示写 `tasks/alpha/design.md` 并指向骨架）→ 加技术方案 → `NEEDS_REGRESSION`（step regression）→ 加回归 → `NEEDS_PLAN`（提示 Plan 只留任务并指向骨架）
  → 加 Plan 与 todo → `BUILDING` → 勾完 → `DONE`；每步 `tier` 为 normal；最后 verify-artifacts「5 通过 · 0 警告 · 0 失败」。

## 外部审查意见

- Plan 经 Codex（/delegate:review，对照 module_stage.py）审两轮：第 1 轮 5 条阻断、第 2 轮 4 条阻断，均已改进 Plan（轮次行见 plan.md）；按两轮上限转用户，2026-11-24 用户「Plan 批准」，同时批准 Spec 两处修订（AC1 例外、并行边界）。
