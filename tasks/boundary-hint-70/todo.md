# Todo: boundary-hint-70

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：边界阈值改为 70%（先红） — `test-phase-guard.sh` 三处按 50% 写的用例就地改为 70%：DONE（Claude 699,999 不出、700,000 出，新增 500k 不再出；Codex 180,880 出、180,879 不出，新增 129,200 不再出；压缩后新读数改用 180,880）、MODULE_DONE（700k 出、600k 不出）、NEEDS_SPEC（700k 出、600k 不出、850k 只改说明、无人值守改用 700k、Codex 180,880 出）；BUILDING 80% 用例未改。改前跑红（第 9、10、16 段）；`module_stage.py` 的 `BOUNDARY_SHARE` 0.5→0.7、有窗口算式 5→7、说明 50%→70%，转绿，336→339 例。变异：`BOUNDARY_SHARE` 改回 0.5 时第 9、10、16 段变红（各段先失败的是说明文字那一例，阈值与说明出自同一个数，无法只改其一）；有窗口算式改回 5 时“Codex DONE 低于窗口 70% 时不出行”变红。
- [x] Checkpoint 1（report）：三套核心回归全绿 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档。
- [x] Task 2：文档、CHANGELOG 与版本号 — `commands/phase.md`、`references/workflow-checkpoints.md`、`docs/design.md` 的 50% / 500k 改为 70% / 700k；CHANGELOG `[0.63.5]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.63.5。grep 确认除 CHANGELOG 历史条目与发版记录外不再有把模块边界写成 50% / 500k 的说法。与 Plan 的出入：`commands/phase.md` 原把 `NEEDS_SPEC` 写在 80% 一档，与 0.63.2 起的行为不符，顺带更正为走模块边界那一档。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
