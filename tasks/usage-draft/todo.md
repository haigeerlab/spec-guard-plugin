# Todo: usage-draft

- [x] Task 0：提交能力图两行、已批准的 Spec、用法草案与 Plan 草稿 — 2026-11-19 用户批准能力图两行、用法草案与 Spec（「批准」），Spec 修订（假设 9、AC5：草案写在「拆成哪些模块」小项里，不改 interface.json）与 Plan 一并批准（「Plan 批准」）。
- [x] Task 1：`usage_draft.py` 与单元测试 — 新增 `hooks/usage_draft.py`（`parse`、`validate`、`milestones`、`draft_files`；CLI `validate --project` 行格式或 `--format json`，失败退出 1、参数错误退出 2），表格行切分与去围栏复用 `capability_map` 的 `_table_cells`、`_visible_lines`，Build order 位置用 `declared_groups`（逗号组按写法算同一位置）；`test_usage_draft.py` 26 例，实现前因模块不存在全部报错，实现后通过（Homebrew Python 与系统 3.9.6 各一次）；`validate.sh` 登记新测试。本仓库 `spec/usage/usage-milestones.md` 自检 `ok 1`。
- [x] Task 2：接入 verify-artifacts — `verify-artifacts.sh` 在「预先声明」之后加「用法草案」一段：只在有 `spec/usage/` 时调 `usage_draft.py validate`，`ok` 报「用法草案结构正确（N 份）」，`bad` 逐条判失败，`warn` 为提醒，能力图读不了或脚本异常报「未验证」。`test-verify-artifacts.sh` 新增 4 例（没有草案不出现、合格通过、引用不存在的用法判失败并点名、入口模块不在里程碑判失败），接入前「合格用法草案通过」失败，接入后 92 例通过。
- [x] Task 3：接入 add-module 预览 — `preview` 结果多 `usage`（没有草案为 None）：草案文件、锚点、锚点所在里程碑或读草案的错误；`format_report` 在「新的 Build order」与「能力图 diff」之间加「用法草案」一段（文件列表、锚点所在里程碑、提醒一句；读不出写「未读取到用法草案」），没有草案时报告逐字不变（用例把 `usage` 去掉后比对同一报告）。`test_module_insert.py` 新增 5 例，实现前 4 例失败（`--confirm` 不改草案一例本来成立，作为守护），实现后 86 例通过，系统 Python 3.9.6 同样通过。`commands/add-module.md` 与 `skills/spec-guard-ops/SKILL.md`（Codex 入口，Plan 未列，超出预计影响面）补一句。
- [x] Task 4：规则文本与模板 — `workflow-checkpoints.md` 新增「用法草案」一节（何时出、三部分格式、拆分核对、批准后 Spec 一致性与 README 展开、add-module 后补里程碑、verify-artifacts 只查结构、已开发项目不追溯），交审小项「拆成哪些模块」与 Spec「目标」、文档建议「能力图全部完成」各补一句，不新增小项；`node-rules.md` 三处同步（各节字节数仍在上限内）。新增 `templates/USAGE.md`（setup-convention 不复制它），把占位换成模块名后 `usage_draft.py` 判 `ok`。`test_workflow_checkpoints.py` 加 4 个共用短语与 `UsageDraftRuleTests` 2 例，改前 5 失败 1 报错，改后 87 例通过；`test_stop_rules.py` 通过。
- [ ] Task 5：文档
- [ ] Task 6：版本号 0.87.0 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查与变异验证
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、回告 ecosystem-lead
- [ ] M1 停点（gate）：用安装副本在临时项目跑 U1、U2，证据摆给用户判定
