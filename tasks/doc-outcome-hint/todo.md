# Todo: doc-outcome-hint

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-04 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」）。
- [x] Task 1：核验缺整张 outcome 表时点名（documentation_verification.py、test_documentation_verification.py） — `verify_documentation` 在有需交付关注点、且 Plan 里一张 `Documentation outcome` 表都没有（复用 `_has_outcome_table` 数表，不看行数）时，`attention` 第一行写 `tasks/<id>/plan.md has no Documentation outcome table; add one before final acceptance (format: references/documentation-verification.md)`，逐项行照旧。新增 3 例：缺整张表在 0.86.4 上失败（第一行仍是逐项行），改后通过；只漏一行、不需要 outcome 两例是防误报的护栏，0.86.4 上本就通过。既有 `test_missing_outcome_is_attention_not_invalid` 原断言 `attention[0]` 含关注点名，因新行排在最前改为断言逐项行在列表中（有意的输出变化）。29 例全部通过。顺带发现 0.86.4 既有问题：outcome 表只有表头没有数据行时，命令行抛 `ImpactError` 堆栈而不是输出 `invalid` JSON（`main` 只接 `VerificationError`），不在本 Spec 范围，未改，交最终验收决定。
- [x] Task 2：文档（documentation-impact 空模板、文档链两步、optional-features、documentation-verification 命令说明） — `documentation-impact.md` 的 Documentation delivery 说明后补「最终验收前在同一份 Plan 补 Documentation outcome 表，否则核验判 attention 并点名缺表，可写成最后一个普通任务」与 ```markdown 围栏里的空模板；`workflow-checkpoints.md` 文档链第 2、3 步各补一句；`docs/optional-features.md` 核验一条与 `commands/documentation-verification.md` 讲 attention 的地方同步。`validate.sh --quick` 通过。临时项目实跑命令行：缺表时第一行点名缺表、后跟逐项行；照空模板填一行 deferred 后缺表行消失、只剩 `architecture is declared deferred`。
- [ ] Task 3：版本号 0.86.5 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查与变异验证
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、回告 ecosystem-lead
