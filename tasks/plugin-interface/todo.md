# Todo: plugin-interface

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-17 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：取值常量（先红后绿） — `test_review_marker.py` 新增 `ValueSets` 两例（导入失败为红），`module_stage.py` 加 `REVIEW_STATES`、`EXTERNAL_REVIEW_STATES` 后转绿，并断言代码实际返回的取值恰好覆盖两组集合；phase-guard 362 例不变。
- [x] Task 2：map-view 的 `externalReview`（先红后绿） — `test_map_view.py` 的 `MODULE_KEYS` 加字段，新增 `ExternalReviewTest` 两例（字段集合失败 + 取值报错为红；todo 读不出走退出码 4 原本就成立，留作护栏）；`map_view.build` 用 `external_review_state` 加 `externalReview` 后 36 例全绿。`spec/map-view.md` 的 JSON 示例与字段说明补上这一项，verify-artifacts 因此报「map-view 批准后已修订」警告：在 Checkpoint 2 附差异交用户复审，复审通过后重新记录批准。
- [x] Task 3：`interface.json` 与检查器（先红后绿） — `scripts/test-checkers.sh` 新增 8 例（2 正 6 反），先因文件不存在两例正例变红；写出 `plugins/spec-guard/interface.json` 与 `scripts/check-interface.py`（导入 `map_view.SCHEMA_VERSION` 与 `module_stage` 两组常量对照，不运行 map_view）后 125 例全绿，并逐个核对 5 个反例报出的是对应原因；接进 `validate.sh`。真文件 `schemaVersion` 改成 2 时 `validate.sh` 退出 1、指出不一致，复原后通过。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — Task 3 提交时 `verify-and-commit.sh` 全档（含 ShellCheck）通过。
- [x] Task 4：文档、CHANGELOG 与版本号 — `docs/design.md` 新增「对外接口」一节，`map_view.py` 一行补「接口说明见 `interface.json`」；README 中英各新增「对外接口」一节；顺带补上 0.65.0 在「数据与隐私」里漏写的一点（钩子在评审检查点会读本机插件记录），这一点超出了 Plan，交审时说明；CHANGELOG `[0.66.0]`（新增两条、维护者工具一条、文档一条）；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.66.0。
- [ ] Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行
- [ ] 发版后的验证
