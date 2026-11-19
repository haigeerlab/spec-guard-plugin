# Todo: usage-draft

- [x] Task 0：提交能力图两行、已批准的 Spec、用法草案与 Plan 草稿 — 2026-11-19 用户批准能力图两行、用法草案与 Spec（「批准」），Spec 修订（假设 9、AC5：草案写在「拆成哪些模块」小项里，不改 interface.json）与 Plan 一并批准（「Plan 批准」）。
- [x] Task 1：`usage_draft.py` 与单元测试 — 新增 `hooks/usage_draft.py`（`parse`、`validate`、`milestones`、`draft_files`；CLI `validate --project` 行格式或 `--format json`，失败退出 1、参数错误退出 2），表格行切分与去围栏复用 `capability_map` 的 `_table_cells`、`_visible_lines`，Build order 位置用 `declared_groups`（逗号组按写法算同一位置）；`test_usage_draft.py` 26 例，实现前因模块不存在全部报错，实现后通过（Homebrew Python 与系统 3.9.6 各一次）；`validate.sh` 登记新测试。本仓库 `spec/usage/usage-milestones.md` 自检 `ok 1`。
- [x] Task 2：接入 verify-artifacts — `verify-artifacts.sh` 在「预先声明」之后加「用法草案」一段：只在有 `spec/usage/` 时调 `usage_draft.py validate`，`ok` 报「用法草案结构正确（N 份）」，`bad` 逐条判失败，`warn` 为提醒，能力图读不了或脚本异常报「未验证」。`test-verify-artifacts.sh` 新增 4 例（没有草案不出现、合格通过、引用不存在的用法判失败并点名、入口模块不在里程碑判失败），接入前「合格用法草案通过」失败，接入后 92 例通过。
- [ ] Task 3：接入 add-module 预览
- [ ] Task 4：规则文本与模板
- [ ] Task 5：文档
- [ ] Task 6：版本号 0.87.0 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查与变异验证
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、回告 ecosystem-lead
- [ ] M1 停点（gate）：用安装副本在临时项目跑 U1、U2，证据摆给用户判定
