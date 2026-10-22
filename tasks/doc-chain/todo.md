# Todo: doc-chain

- [x] Task 0：同步批准标记，按 C190 修订 Spec — 按开工通知（C198）单独 `module-crew sync` 到集成分支 e41f7df（HEAD d84aecf5），Spec、Plan 取集成分支带批准标记的版本；validate、phase-guard（488 例）、verify-artifacts（74 例）全过。按 C190 改 Spec：改动 4 对 `docs/optional-features.md` 只改基线路径说法（现有两处已是 `docs/DOCUMENTATION-BASELINE.md`，不用改），并行边界独占清单去掉它，重叠一节写明分工，末尾加变更记录；`module_scope.py validate` 通过。Spec 指纹随之变为修订，最终验收附这段差异。
- [ ] Task 1：核验按状态区分（改动 1、改动 5 前半）
- [ ] Task 2：最终 gate 注入核验要求（改动 2、改动 5 后半）
- [ ] Task 3：规则文字（改动 3）
- [ ] Task 4：说明文字（改动 4）
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 5：临时消费者项目实跑（AC10）
- [ ] Task 6：合入集成分支并跑完整检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做
