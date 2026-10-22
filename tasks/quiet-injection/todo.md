# Todo: quiet-injection

- [x] Task 0：同步批准标记 — 按开工通知 C150 单独 `module-crew sync` 到集成分支 cb1e55c（HEAD 520fc41e）；Spec、Plan 取集成分支带批准标记的版本。validate、phase-guard（443 例）、verify-artifacts（74 例）全过。按用户批准 C145 的原话改 Spec 的 AC9 并在变更记录记一行（Spec 指纹随之变为修订，最终验收附这段差异）。
- [ ] Task 1：删 80% 行、修 Claude 窗口（改动 2）
- [ ] Task 2：状态码（改动 1 前半）
- [ ] Task 3：一行形式与选择（改动 1 后半）
- [ ] Task 4：英文标签与评测脚本（改动 3、改动 5 的 evals）
- [ ] Task 5：说明文字（改动 4）
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 6：真实宿主核对（AC9）
- [ ] Task 7：合入集成分支并跑完整检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做
