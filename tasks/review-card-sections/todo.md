# Todo: review-card-sections

- [x] Task 1：交审小项与怎么批准（先红） — `test_workflow_checkpoints.py` 新增 3 例（五类小项按位置断言先后与写全要求；怎么批准的复制块、选项后果与卡住时的写法；三处镜像），先跑红（8 failures、4 errors），改共享检查点规则「交审要让用户看到内容」「交审时说明怎么批准」与「第二次过不去」一条、同步 `review-mark.md`、`spec-guard-ops` SKILL 与 `docs/commands.md` 后 60 例全绿；已有断言一条未改。改写中两处断行把小项名拆开（“验收标准（按 AC1、AC2… 编号）”“中途会停下来问你的地方”）被断言拦下，已改为不跨行。
- [ ] Task 2：interface.json 的 reviewKinds（先红）
- [ ] Task 3：CHANGELOG
- [ ] Checkpoint 1（report）：变异核对与契约对齐
- [ ] Checkpoint 2（gate）：模块最终验收；推送与开 PR 在此由用户确认，合并由用户进行

## 外部审查意见

<!-- spec-guard: external-review declined -->
