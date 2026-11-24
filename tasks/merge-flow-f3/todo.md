# Todo: merge-flow-f3

- [x] Task 0：提交 Plan 与 todo（2026-11-24 用户「Plan 批准」）
- [x] Task 1：共享规则与回归
- [ ] Task 2：本仓库文档
- [ ] Task 3：版本与 CHANGELOG
- [ ] Checkpoint 1（report）：本机完整检查与变异
- [ ] Checkpoint 2（gate）：推送、开 PR、最终验收、按新规则合并、回复两个会话

## 证据
- Task 1（2026-11-24）：先改回归，4 项变红（规则仍是旧句）；改规则三行后只剩 `test_no_remote_write_is_authorized_by_default` 红——它禁用「自动合并」，与 Spec 原句冲突。
  用户原话「断言放过新句」：检查前从全文去掉 F3 那一句，其余部分照样禁用（超出 Plan 列的三处，验收时说明）。91 例全绿；在新句外追加「默认自动合并。」→ 该用例变红，已还原。
