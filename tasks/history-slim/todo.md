# Todo: history-slim

- [ ] Task 0：提交已批准的 Spec 标记、Plan 与 todo
- [ ] Task 1：回归测试先红
- [ ] Task 2：去掉 audit 与 correct（C1）
- [ ] Task 3：两侧入口对齐（C2）
- [ ] Task 4：接口 Spec 与文档（C3）
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 5：公共文件请求（C4）
- [ ] Task 6：合入集成分支并跑完整检查
- [ ] Checkpoint 2（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **变更**：能力历史只保留 verify 核对与迁移预览（Claude `/spec-guard:history-integrity` 与 Codex `spec-guard-ops` 的 history 节一致）；
> `audit` 与 `correct` 已去掉（决定 D16）。已有账本里的补正记录照常校验，归档快照不变；事件时间 `at` 是迁移时抄下的原值，不作为时间证据。
