# Todo: sibling-plugin-hints

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：约定块模板两行（先红） — `test_workflow_checkpoints.py` 加 1 例（三处文件各查四个关键词与按宿主的入口），先红（3 个子用例失败）；两份模板与 `docs/convention-block.md` 各新增两行（delegate 一行在“交审 Spec 或 Plan”之后，agent-relay 一行在“交审要点写在正文”之前、即“回告来源”之后），`git diff` 只有新增行，转绿，`check-readme-sync.py` 通过。变异：删掉 Codex 模板的 delegate 一行，新用例变红，复原。临时项目先用 0.64.0 装约定块，再用工作区版本 `--replace`：Claude 与 `--host=codex` 退出 0、无需 `--accept-removals`、两行均写入。与 Plan 的出入：全档校验报协作边界与命令名两项不通过，Codex 入口改为 `delegate:delegate-routing`、`agent-relay:session-routing`，`check-command-names.py` 放行表登记 `/delegate:review`；Spec 已改并记入变更记录，最终验收附差异一并复审。
- [x] Checkpoint 1（report）：三套核心回归、规则测试与 setup-teardown 回归全绿 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档加 `--suite setup-teardown`。
- [ ] Task 2：CHANGELOG 与版本号 — CHANGELOG `[0.64.1]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.64.1。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证 — 两边升级到 0.64.1，各跑一轮到 Spec 交审，看是否只提议一次 delegate 只读审查、未自行发起。
