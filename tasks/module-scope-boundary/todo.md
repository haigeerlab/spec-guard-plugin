# Todo: module-scope-boundary

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：解析与路径归属（先红后绿） — 新建 `test_module_scope.py`（解析 11 例、路径归属 4 例），先因模块不存在导入失败；新建 `module_scope.py` 实现 `parse`／`Scope`／`ScopeError`／`covers` 后 15 例全绿。测试登记进 `scripts/validate.sh`，`check-tests-registered.py`（61 个文件）与 `test_python_compat` 通过。
- [ ] Task 2：越界检查 `check`（先红后绿）
- [ ] Task 3：`validate` 与 verify-artifacts（先红后绿）
- [ ] Task 4：phase-guard 不受影响的回归
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并做两次改坏验证
- [ ] Task 5：共享规则（先红后绿）
- [ ] Task 6：设计文档与 CHANGELOG
- [ ] Checkpoint 2（gate）：模块验收
