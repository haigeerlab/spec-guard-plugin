# Todo: review-marker-blank-line

- [x] Task 0：本 Plan 与 todo 已随 `record-on-receipt` 的 Task 0 提交 — Plan 经用户批准（2026-10-18）。
- [x] Task 1：标记两侧的空行（先红） — `test_review_marker.py` 新增 3 例（8 种写法 × pending／approved，加上 Plan），先在旧代码上确认 13 处失败（本来合格的两种照旧通过）；`_with_marker` 改为替换或插入后保证标记前后都有空行（文件开头与末尾除外），已有空行不重复加。构建中发现 `review_mark.py` 本来就以 `\n` 写回、CRLF 会统一成 LF，Spec 里「沿用 `\r\n`」两句已修订并记入变更记录，用例按现有行为写；31 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档。
- [ ] Task 2：用 `oxfmt --check` 复查
- [ ] Task 3：文档、CHANGELOG 与 0.70.1 版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
