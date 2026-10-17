# Todo: concurrency-assessment

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：共享规则新增「并行评估」一节（先红后绿） — `test_workflow_checkpoints.py` 新增 `ConcurrencyAssessmentTests` 5 例，先红 4 例（「模板里不出现 moduleConcurrency」本来就绿，作防线）；在「文档建议」与「按需求批量前置审」之间新增「并行评估（moduleConcurrency 为 on 时）」一节，「文档建议」的能力图评审一条末尾加指引后 33 例全绿，`check-no-parallel-surface.py` 通过。
- [x] Checkpoint 1（report）：三套核心回归全绿，并做两次改坏验证 — `d4df4a4` 提交时全档通过（validate、phase-guard 367、verify-artifacts 63、repo-artifacts）。改坏验证：删掉节首适用条件时 `test_section_exists_and_says_when_it_applies` 变红；在 `claude-block-local.md` 加入 `moduleConcurrency` 时 `test_convention_blocks_never_mention_the_switch` 变红；两处均已复原。`git diff --stat` 确认改动只在共享规则、测试与本模块流程文件。
- [x] Task 2：CHANGELOG — 「未发布」小节「新增」加一条。
- [ ] Checkpoint 2（gate）：模块验收
