# Todo: rework-scope-baseline

- [x] Task 0：提交 Spec 批准、能力图新行、Plan 与 todo（2026-11-26 用户「批准；Q1 A」）
- [x] Task 1：`rework_base` 与 `scope_base`
- [ ] Task 2：接到调用点与提示
- [ ] Checkpoint 1（report）：本机完整检查、变异与老输出比对
- [ ] Task 3：规则与文档
- [ ] Checkpoint 2（gate）：推送、开 PR、最终验收并同时问合并

## 证据
- Task 0（2026-11-26）：能力图插入 rework-scope-baseline（用户「批准；Q1 A」）；Plan 经 Codex 两轮：第一轮 3 条阻断（返工勾完后丢基线、只剩正式延期不算完成、提示写错提交），改后第二轮全部解决、没有新阻断，记 codex-approved（第一次运行超时无结论，重跑）。
- Task 1（2026-11-26）：`module_scope.rework_info`（todo 历史从新到旧：最新的有未勾选项状态（工作区优先）→ 它之前最近的全部勾完提交 → 二者之间最旧的有未勾选项提交 R，返回 `{base: R^, start: R}`；只在工作区时 `{base: HEAD, start: None}`；正式延期算勾完；没有勾完过、读不到 git 时 None）与 `scope_base`（有返工用它，否则 `default_base`）。用例：`test_module_scope.py` `ReworkBase` 7 例，实现前 7 个出错。
