# Todo: rework-scope-baseline

- [x] Task 0：提交 Spec 批准、能力图新行、Plan 与 todo（2026-11-26 用户「批准；Q1 A」）
- [x] Task 1：`rework_base` 与 `scope_base`
- [x] Task 2：接到调用点与提示
- [ ] Checkpoint 1（report）：本机完整检查、变异与老输出比对
- [ ] Task 3：规则与文档
- [ ] Checkpoint 2（gate）：推送、开 PR、最终验收并同时问合并

## 证据
- Task 0（2026-11-26）：能力图插入 rework-scope-baseline（用户「批准；Q1 A」）；Plan 经 Codex 两轮：第一轮 3 条阻断（返工勾完后丢基线、只剩正式延期不算完成、提示写错提交），改后第二轮全部解决、没有新阻断，记 codex-approved（第一次运行超时无结论，重跑）。
- Task 1（2026-11-26）：`module_scope.rework_info`（todo 历史从新到旧：最新的有未勾选项状态（工作区优先）→ 它之前最近的全部勾完提交 → 二者之间最旧的有未勾选项提交 R，返回 `{base: R^, start: R}`；只在工作区时 `{base: HEAD, start: None}`；正式延期算勾完；没有勾完过、读不到 git 时 None）与 `scope_base`（有返工用它，否则 `default_base`）。用例：`test_module_scope.py` `ReworkBase` 7 例，实现前 7 个出错。
- Task 2（2026-11-26）：改用 `scope_base` 的六处——老流程越界 `scope_overreach`、新流程越界 `_scope_part`（Spec 写的「scope_overreach」实际分两个函数）、`t4_hits`、`acceptance_step`、`review_mark._outside`、`module_scope.py check` 的默认基线；`_merge_at_base`、`module_baseline` 保持原基线。两处越界提示在返工时加「；返工：从提交 `<R 前 12 位>` 起算」，只在工作区时加「；返工：还没提交，与 HEAD 比较」（`_rework_note`）。用例：`test_flow_v2.py` `ReworkOverreachTest` 5 例（继承 `FlowOverreachTest` 一起跑），实现前核心 2 例失败；`_merge_at_base` 与 `module_baseline` 两例放在这个类里（Plan 写的是 `test_review_marker.py`，为共用夹具放这里）。
