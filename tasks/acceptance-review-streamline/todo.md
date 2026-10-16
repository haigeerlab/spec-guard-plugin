# Todo: acceptance-review-streamline

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：三处规则文字（先红） — `test_workflow_checkpoints.py` 新增 3 例（验收附 Spec 差异、验收后接着写下一份 Spec、确认框摘要不算交审），先跑红（3 failures）；规则文件在「Plan 检查点分级」加“最终验收可以一并复审修订过的 Spec”，「阶段交接」加“验收后接着写下一份 Spec”，「交审要让用户看到内容」补“要点写在本轮正文、在会结束本轮的确认框之前”，转绿，26 例全绿，现有断言未改。三处新文字即是变异点：删掉任一处，对应断言回到改前的红。
- [x] Checkpoint 1（report）：规则测试与 `validate.sh` 全绿 — 随 Task 1 的提交跑 `verify-and-commit.sh`，通过。
- [ ] Task 2：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证：两边宿主各一次多轮真实会话观察验收消息与交审；回告观测会话
