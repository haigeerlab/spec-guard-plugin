# Todo: concurrency-rule-wording

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan（含整份比对分两层的做法），review_mark 记录后与 todo 一起提交。
- [x] Task 1：共享规则新增一节与三句指引（先红后绿） — `test_workflow_checkpoints.py` 加 `CoordinatorApprovalTests` 5 例，先红 3 例（「三句原文逐字在」「模板不含开关名」本来就绿，作防线）；在「并行边界」之后新增「协调会话的批准与合并（moduleConcurrency 为 on 时）」一节，并在三处加指引后 41 例全绿，`check-no-parallel-surface.py` 通过。期间断言「一致」没命中，是规则原文没用 Spec 的说法，补成「与交审版本一致」，没有放宽断言。
- [ ] Checkpoint 1（report）：整份比对、三套核心回归与改坏验证
- [ ] Task 2：CHANGELOG
- [ ] Checkpoint 2（gate）：模块验收
