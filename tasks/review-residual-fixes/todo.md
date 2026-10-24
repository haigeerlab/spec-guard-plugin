# Todo: review-residual-fixes

- [x] Task 0：提交已批准的 Spec、Plan 草稿与能力图 — 2026-10-24 用户批准 Plan（「批准 review-residual-fixes 的 Plan」）；Spec、能力图、Plan 草稿在 `400041f8` 提交，Plan 批准标记随本次提交。
- [x] Task 1：review-mark 提醒（C1，先红后绿） — `test_review_marker.py` 原「names_both_sources」改为断言通用说法（installed collaboration plugin、current conversation），并断言输出与源码不含 decision hub、session-protocol、item number；改前 31 例中 1 例红，改 `review_mark.py` 文件头与两句提醒后 31 例全绿。仓库里没有别处断言旧提醒。
- [ ] Task 2：create 类文档核验（C2，先红后绿）
- [ ] Task 3：setup-convention 先校验（C3，先红后绿）
- [ ] Task 4：状态码含文档基线（C4，先红后绿；含 C10 注释）
- [ ] Task 5：围栏配对（C5，先红后绿）
- [ ] Task 6：projectId 共用判据（C6，先红后绿）
- [ ] Task 7：history-migration 清理（C7，先红后绿）
- [ ] Task 8：规则文字（C8、C9）
- [ ] Checkpoint 1（report）：三套核心回归
- [ ] Task 9：版本号与 CHANGELOG 0.84.2
- [ ] Checkpoint 2（gate）：最终验收；发版前告诉 ecosystem-lead，推送与开 PR 由用户确认，合并由用户进行
