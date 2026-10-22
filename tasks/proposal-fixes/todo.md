# Todo: proposal-fixes

- [ ] Task 0：提交已批准的 Spec 标记、Plan 与 todo
- [ ] Task 1：F6 回归（先红）
- [ ] Task 2：F6 修复
- [ ] Task 3：F18 回归（先红）
- [ ] Task 4：F18 修复
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 5：合入集成分支并跑完整检查
- [ ] Checkpoint 2（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **修复**：Proposal 收尾不再在释放时删除锁文件，同一个 Proposal 的多次收尾在多进程下严格串行，不会再同时写远端；锁文件留在私有 journal 目录。Proposal 候选池遇到列出却读不出的文件时，结果为 `unknown`（诊断 `snapshot-proposal-unreadable`，可重试），不再抛 `TypeError`。
