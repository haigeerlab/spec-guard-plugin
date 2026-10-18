# Todo: review-marker-blank-line

- [x] Task 0：本 Plan 与 todo 已随 `record-on-receipt` 的 Task 0 提交 — Plan 经用户批准（2026-10-18）。
- [x] Task 1：标记两侧的空行（先红） — `test_review_marker.py` 新增 3 例（8 种写法 × pending／approved，加上 Plan），先在旧代码上确认 13 处失败（本来合格的两种照旧通过）；`_with_marker` 改为替换或插入后保证标记前后都有空行（文件开头与末尾除外），已有空行不重复加。构建中发现 `review_mark.py` 本来就以 `\n` 写回、CRLF 会统一成 LF，Spec 里「沿用 `\r\n`」两句已修订并记入变更记录，用例按现有行为写；31 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档。
- [x] Task 2：用 `oxfmt --check` 复查 — 2026-10-18 在临时目录用工作区版 review-mark 写出 Spec 表里五种写法 × pending／approved 共 10 个样本，用使用者前端的 `oxfmt --check` 逐个检查，退出码全部为 0（修复前其中 3 种写法不合格）。
- [x] Task 3：文档、CHANGELOG 与 0.70.1 版本号 — CHANGELOG `[0.70.1] - 2026-10-18` 补本模块一条；两份 `plugin.json` 改为 0.70.1，中英 README 的 `--ref` 改为 v0.70.1；`validate.sh` 通过。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-18 在对话里列出相对 f1135b8 的 9 个文件（均在 Plan 范围内）、验证结果（全档通过；新用例先红 13 处后 31 例全绿；10 个样本 oxfmt 全部为 0）与未验证项（安装副本复查放到发版后，未做独立代码评审），以及拟回告（发版后经 Claude 原生会话消息告诉 module-crew 插件负责人 0.70.1 的改动、已有文件不批量改、升级方法，随后以「已告知」关闭 75SV50T）；用户验收通过，拟回告一并批准，确认推送与开 PR；不做外部审查。
- [ ] 发版后的验证

## 外部审查意见

<!-- spec-guard: external-review declined -->

用户在最终验收时选择直接验收、不做外部审查（2026-10-18）。
