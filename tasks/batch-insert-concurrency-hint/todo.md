# Todo: batch-insert-concurrency-hint

- [ ] Task 0：提交 Plan 与 todo；收到开工通知后 `module-crew sync`，确认 Spec 带批准标记
- [ ] Task 1：「并行评估」一节加批量插入时机（先红后绿，AC1～AC3）
- [ ] Task 2：`add-module` 两处说明加指引（先红后绿，AC4）
- [ ] Checkpoint 1（report）：改坏验证与 off 不变（AC5、AC6）
- [ ] Task 3：合入集成分支（`module-crew sync`）并跑完整检查与越界检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **变更**：多模块并行开关 `moduleConcurrency` 为 `on` 时，为同一个需求一次插入 2 个及以上模块后，按「并行评估」规则评估一次并交用户选择
> （决定 D20）；本机装了 module-crew 时提示可用其协调会话并行开发，没装只给 Build order 建议。只评估一次；开关不是 `on` 时一切不变。

## 对使用者的影响

- 只影响打开了 `moduleConcurrency` 的项目：批量插入模块后多一段并行评估与选项；单个插入、开关关着的项目没有变化。
