# Todo: delegate-interface-check

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-17 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：`delegate_review_entry`（先红后绿） — `test_sibling_plugins.py` 新增 12 例（函数不存在，全部报错），公共准备代码抽成 `Fixture`，避免原有 11 例重复运行；实现 `codex_plugin_cache`（`codex_plugin_enabled` 改为调用它）、`_delegate_root` 与 `delegate_review_entry` 后 23 例全绿。期间一例写成 `/delegate:review2` 被拒，因为 Spec 规定只收小写字母和连字符，所以改的是测试值（`/delegate:review-two`），不是实现。`test_agent_relay_probe`、`test_python_compat` 通过。
- [x] Task 2：阶段提示改用 `delegate_review_entry`（先红后绿） — 第 17 段新增 3 例：没有 interface.json 时逐字不变、interface 1.0 时命令名取自文件、2.0 时不出提示。其中「命令名取自文件」一例为红；`external_review_hint` 改用 `delegate_review_entry`、`COMMANDS` 改为带 `%(review)s`／`%(doctor)s` 占位的模板后转绿。原 Codex 夹具只有空的 `cache/dm/delegate` 目录，按 Spec「没有版本目录判为没装」后不再出提示，所以给夹具补了一个 `0.5.2` 版本目录（真实安装总有版本目录）。回归 362→365 例。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并做一次改坏验证 — Task 2 提交时 `verify-and-commit.sh` 全档（含 ShellCheck）通过；版本上限放宽到 `<3.0` 后，phase-guard「interface 2.0：主版本不兼容，不出提示」与 sibling 两例（Claude、Codex 的不兼容用例）变红，已复原。
- [x] Task 3：文档、CHANGELOG 与版本号 — `workflow-checkpoints.md`「外部审查意见」补「接口主版本不兼容时不出提示」；`docs/design.md` 的 `sibling_plugins.py` 一行补上读 delegate 的 interface.json 并按 `>=1.0,<2.0` 校验；CHANGELOG `[0.67.0]`「变更」一条；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.67.0。
- [x] Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行 — 2026-10-17 在对话正文列出：实际改动的 15 个文件（新增 3、修改 12、删除 0）；五种情况下的提示原文（1.x 取文件命令、缺文件／读不懂／命令不合规用默认值、主版本 2 不出提示）；验证结果；两处与计划不一致（测试值 `review2` 改为 `review-two`；0.65.0 的 Codex 夹具补了版本目录）；未验证项（真实 delegate 0.5.3 的文件）；拟回告。用户验收通过，PR #343 转为可评审，合并由用户进行。
- [ ] 发版后的验证
