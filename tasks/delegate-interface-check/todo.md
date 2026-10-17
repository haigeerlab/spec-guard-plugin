# Todo: delegate-interface-check

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-17 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：`delegate_review_entry`（先红后绿） — `test_sibling_plugins.py` 新增 12 例（函数不存在，全部报错），公共准备代码抽成 `Fixture`，避免原有 11 例重复运行；实现 `codex_plugin_cache`（`codex_plugin_enabled` 改为调用它）、`_delegate_root` 与 `delegate_review_entry` 后 23 例全绿。期间一例写成 `/delegate:review2` 被拒，因为 Spec 规定只收小写字母和连字符，所以改的是测试值（`/delegate:review-two`），不是实现。`test_agent_relay_probe`、`test_python_compat` 通过。
- [ ] Task 2：阶段提示改用 `delegate_review_entry`（先红后绿）
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并做一次改坏验证
- [ ] Task 3：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行
- [ ] 发版后的验证
