# Todo: plugin-interface

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-17 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：取值常量（先红后绿） — `test_review_marker.py` 新增 `ValueSets` 两例（导入失败为红），`module_stage.py` 加 `REVIEW_STATES`、`EXTERNAL_REVIEW_STATES` 后转绿，并断言代码实际返回的取值恰好覆盖两组集合；phase-guard 362 例不变。
- [x] Task 2：map-view 的 `externalReview`（先红后绿） — `test_map_view.py` 的 `MODULE_KEYS` 加字段，新增 `ExternalReviewTest` 两例（字段集合失败 + 取值报错为红；todo 读不出走退出码 4 原本就成立，留作护栏）；`map_view.build` 用 `external_review_state` 加 `externalReview` 后 36 例全绿。`spec/map-view.md` 的 JSON 示例与字段说明补上这一项，verify-artifacts 因此报「map-view 批准后已修订」警告：在 Checkpoint 2 附差异交用户复审，复审通过后重新记录批准。
- [ ] Task 3：`interface.json` 与检查器（先红后绿）
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告
- [ ] Task 4：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行
- [ ] 发版后的验证
