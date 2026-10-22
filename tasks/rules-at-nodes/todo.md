# Todo: rules-at-nodes

- [x] Task 0：同步批准标记、提交 Plan 与 todo — 按开工通知 C127 `module-crew sync` 到集成分支 e4b4ace（HEAD 450f32d）；Spec 带标记 acbb03de976c，与批准版只差 AC9 一句（用户批准 C122 时要求的范围内修正，已记变更记录，最终验收附差异）；三方合并保留了本分支 Plan 的 `pending` 行，改取集成分支带 `approved` 的版本（只差这一行）。validate、phase-guard（438 例）、verify-artifacts（74 例）全过。module-crew 入口按协调通知改用 0.11.0。
- [ ] Task 1：停点规则与检查点规则（C2、C4）
- [ ] Task 1b：交审小项对上游章节（C7）
- [ ] Task 1c：复制块、条目编号与小项新名（C8、C9）
- [ ] Task 1d：`interface.json` 升 1.9 的公共变更请求（C10）
- [ ] Task 2：阶段注入附停点规则（C3 `module_stage.py`）
- [ ] Task 3：IDLE／MAP_ONLY 附停点规则（C3 `phase-guard.sh`）
- [ ] Task 4：约定块瘦身（C1）
- [ ] Task 5：与 `cost-slim-link-follow` 重叠的说明文字（C5）
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 6：合入集成分支并跑完整检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做
