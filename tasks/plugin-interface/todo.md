# Todo: plugin-interface

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-17 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：取值常量（先红后绿） — `test_review_marker.py` 新增 `ValueSets` 两例（导入失败为红），`module_stage.py` 加 `REVIEW_STATES`、`EXTERNAL_REVIEW_STATES` 后转绿，并断言代码实际返回的取值恰好覆盖两组集合；phase-guard 362 例不变。
- [ ] Task 2：map-view 的 `externalReview`（先红后绿）
- [ ] Task 3：`interface.json` 与检查器（先红后绿）
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告
- [ ] Task 4：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行
- [ ] 发版后的验证
