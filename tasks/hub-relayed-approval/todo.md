# Todo: hub-relayed-approval

- [x] Task 0：提交已批准的 Spec、能力图、Plan 与 todo — Spec 与 Plan 均于 2026-10-18 在本会话经用户批准，review_mark 记录后一起提交。
- [x] Task 1：共享规则（先红后绿） — `test_workflow_checkpoints.py` 新增 `HubRelayedApprovalTests` 6 例并把 `ORIGINALS[0]` 改为新措辞，先红（4 失败 5 错误）；规则改 `approved` 一条、「标记不是授权来源」一条、新增「经收件枢纽转来的批准」一节（含预览由本会话核对指纹后直接 `--confirm`，不必回枢纽确认预览）、协调会话一节第一与第三条；该文件用例除 Task 2 的 2 个子用例外全绿。与 Task 2 一起提交（Task 2 的断言在同一个文件，分开提交过不了检查）。
- [x] Task 2：review-mark 命令、Codex 技能与脚本提示（先红后绿） — `test_review_marker.py` 新增 1 例先红；改 `commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md` 与 `review_mark.py` 的文档串和两句提示（只改字符串）；两套用例全绿。
- [x] Checkpoint 1（report）：三套核心回归、模板未改与改坏验证 — 约定块模板与 `docs/convention-block.md` 相对 `origin/main` 0 行差异；改坏验证：删「【答复告知】与【协调通知】」→ `test_section_lists_what_does_not_count` 红，删「回显核对」→ `test_section_states_every_condition` 红，`approved` 一条改回「用户于当前对话明确批准」→ 3 例红（含 `test_approved_rule_names_both_sources`）；均已用提交版本复原，复原后全绿。三套核心回归随 72b3fa4 全档通过（phase-guard 403、verify-artifacts 68）。
- [x] Task 3：文档、CHANGELOG 与版本号 — `docs/workflow.md`、`docs/commands.md` 各补一句；CHANGELOG `[0.70.0]`；两份 `plugin.json` 与中英 README `--ref` 改为 0.70.0。
- [ ] Checkpoint 2（gate）：模块验收；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
