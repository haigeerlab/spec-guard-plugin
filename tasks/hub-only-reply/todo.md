# Todo: hub-only-reply

- [x] Task 1：让步规则与镜像（先红） — `test_workflow_checkpoints.py` 在「交审时说明怎么批准」用例加 11 个关键词、镜像用例加「去决策收件箱答」，先跑红（4 failures），在规则那一条末尾加让步规则、三处镜像各补半句后 60 例全绿；已有断言未改。
- [x] Task 2：CHANGELOG — 新开「[未发布]」段加一条；两份 `plugin.json` 仍为 0.80.0。
- [x] Checkpoint 1（report）：变异核对 — `git archive HEAD` 副本未改时 60 例全过；删掉让步规则那一段后 `test_how_to_approve_uses_one_copy_block` 变红。改动范围核对：相对 `0295c86` 只改了规则、测试、三处镜像、CHANGELOG 与本模块的 spec/tasks，`hooks/` 下只有测试文件，`interface.json` 未动。
- [x] Checkpoint 2（gate）：模块最终验收；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-19 按交审小项呈现：做了什么、AC1～AC4 逐条证据、文档改动表（2 个）、其他改动表（8 个，新增 3、修改 5、删除 0，无超出 Plan 的文件）、「新增依赖、锁文件改动：无」、提交表（4d9f46b、d9a758f、74f186a，勾选本 gate 为待提交）、Spec 未改、注意（interface.json 说明一句为已知遗留；真实会话未验证；未做独立评审）；用户回复「验收通过，推送并开 PR」。版本号不变。

## 外部审查意见

<!-- spec-guard: external-review declined -->
