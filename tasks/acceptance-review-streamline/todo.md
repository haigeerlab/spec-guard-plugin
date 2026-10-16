# Todo: acceptance-review-streamline

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：三处规则文字（先红） — `test_workflow_checkpoints.py` 新增 3 例（验收附 Spec 差异、验收后接着写下一份 Spec、确认框摘要不算交审），先跑红（3 failures）；规则文件在「Plan 检查点分级」加“最终验收可以一并复审修订过的 Spec”，「阶段交接」加“验收后接着写下一份 Spec”，「交审要让用户看到内容」补“要点写在本轮正文、在会结束本轮的确认框之前”，转绿，26 例全绿，现有断言未改。三处新文字即是变异点：删掉任一处，对应断言回到改前的红。
- [x] Checkpoint 1（report）：规则测试与 `validate.sh` 全绿 — 随 Task 1 的提交跑 `verify-and-commit.sh`，通过。
- [x] Task 2：文档、CHANGELOG 与版本号 — `docs/workflow.md`「交审时你应该看到内容」补一句确认框摘要不算交审，并新增一段“最终验收少一轮确认”（附差异一次批准、验收后接着写下一份 Spec、可先 `/compact`）；`docs/design.md` 挂起说法改为可用 `--reason` 记原因、挂起时长由进度表从 git 历史读出；CHANGELOG `[0.63.3]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.63.3。`validate.sh` 随提交通过。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证：两边宿主各一次多轮真实会话观察验收消息与交审；回告观测会话
