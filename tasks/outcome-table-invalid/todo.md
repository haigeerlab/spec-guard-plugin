# Todo: outcome-table-invalid

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-04 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」）。
- [x] Task 1：坏的 outcome 表报 invalid（documentation_verification.py、test_documentation_verification.py） — `_outcomes` 里 `_table(_regular(...))` 包进 try，`ImpactError` 以原文改抛 `VerificationError`；`main` 未改。新增 2 例：四种坏表（只有表头、缺分隔行、分隔行写错、某行格数不对）各一个 subTest 抛 `VerificationError`；命令行入口对只有表头的表输出 `{"state": "invalid", "error": "Documentation outcome table has no entries"}` 并返回 1。在 0.86.5 上全部失败（抛 `ImpactError`），改后 31 例通过。「缺分隔行」夹具第一次写成带数据行，被解析成分隔行写错，改为只留表头。测试里没有断言 outcome 表抛 `ImpactError` 的既有用例。
- [x] Task 2：版本号 0.86.6 与 CHANGELOG — 两份 `plugin.json` 改 0.86.6；README 中英 `--ref v0.86.6`；CHANGELOG 加 `## [0.86.6] - 2026-11-04`（修复）。`check-readme-sync.py`、`check-manifests.py` 通过。
- [ ] Checkpoint 1（report）：发布前完整检查与变异验证
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR
