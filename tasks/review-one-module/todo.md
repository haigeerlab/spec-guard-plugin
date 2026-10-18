# Todo: review-one-module

- [x] Task 0：提交已批准的 Plan 与 todo — Plan 经用户批准（2026-10-18），与本 todo 一次提交。
- [x] Task 1：规则与模板行（先红） — `test_workflow_checkpoints.py` 新增 1 例，先失败；规则「评审状态标记」新增「一次交审只放一个模块」一条（两种例外、按模块分组、不按产物类型横排、不主动提议、能力图评审不算），「按需求批量前置审」第一段改为只在用户明确要求时使用，「返工与小模块」那句改为用户也要求一次审完时，「协调会话的批准与合并」补一句分组写法；三处约定块各新增一行，`git diff` 无删除行；规则测试全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档。
- [x] Task 2：文档、CHANGELOG 与 0.70.2 版本号 — `docs/workflow.md` 交审一段补「一次一个模块、一起审时按模块分组」；CHANGELOG `[0.70.2]`；两份 `plugin.json` 改为 0.70.2，中英 README 的 `--ref` 改为 v0.70.2；`validate.sh` 通过。另核对：先用 0.70.1（`git archive v0.70.1`）装约定块，再用工作区版本 `setup-convention local --replace`（Claude 与 `--host=codex` 各一次），退出码都是 0，新行已写入，不需要 `--accept-removals`。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
