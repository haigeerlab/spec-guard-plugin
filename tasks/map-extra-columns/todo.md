# Todo: map-extra-columns

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-09 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」）。
- [x] Task 1：额外列补空格与预览说明（module-insert.py、test_module_insert.py） — `preview` 用 `_module_table_rows` 已定位的表头（首行号减 2）取第 4 格起的列名，新行每个额外列补 `  |`，结果多 `extra_columns`；`format_report` 在新行下打印「额外列 `X` 留空，需要时自己填」（多列用「、」）。三列时新行字符串与 0.86.6 相同、无说明。新增 3 例：四列（已有行有值）预览与 `write` 成功、严格解析通过、已有行摘要不变；五列两列都留空且说明列出两列；三列无说明。在 0.86.6 上 3 例全部失败（两例「模块表存在不完整的行」、一例缺 `extra_columns`），改后 `test_module_insert.py` 81 例通过。
- [x] Task 2：「可以开始」的说明（map.md、commands.md、concepts.md） — `commands/map.md` 状态图例、`docs/commands.md` map 段落、`docs/concepts.md` 术语表「进度表」一条各补：「可以开始」（`ready`）只表示依赖都已完成，不代表本轮要做，本轮做哪些由项目自己排（例如在能力图加一列，add-module 会把额外列留空）。JSON 的 `ready` 与表格文字未改。`validate.sh --quick` 通过。
- [x] Task 3：版本号 0.86.7 与 CHANGELOG — 两份 `plugin.json` 改 0.86.7；README 中英 `--ref v0.86.7`；CHANGELOG 加 `## [0.86.7] - 2026-11-09`（修复、文档）。`check-readme-sync.py`、`check-manifests.py` 通过。
- [ ] Checkpoint 1（report）：发布前完整检查与变异验证
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、回告 ecosystem-lead
