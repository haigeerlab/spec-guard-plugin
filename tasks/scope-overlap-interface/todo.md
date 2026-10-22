# Todo: scope-overlap-interface

- [ ] Task 0：提交 Plan 与 todo；收到开工通知后 `module-crew sync`，确认 Spec 与 Plan 带批准标记
- [ ] Task 1：重叠判定挪进 `module_scope.py`（纯搬家，`map_view` 改调共用函数）
- [ ] Task 2：`overlap` 子命令（先红后绿，AC1～AC5）
- [ ] Checkpoint 1（report）：改坏验证
- [ ] Task 3：接口文件经【公共变更请求】落地，`check-interface.py` 与夹具核对 `scopeOverlap`（AC6）
- [ ] Task 4：`docs/design.md` 追加 1.10 一段（AC6）
- [ ] Task 5：合入集成分支（`module-crew sync`）并跑完整检查与越界检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **新增**：`interface.json` 升 1.10，新增 `scopeOverlap`：`python3 -B hooks/module_scope.py overlap [--project <项目根>] --spec <模块 id>=<文件> ...`，
> 只读地给出几份 Spec（可并入项目里进行中、就绪的模块）两两之间的独占重叠与来源，不受 `moduleConcurrency` 限制；判据与 `/map` 的
> `startable.conflicts` 同一份（O10）。

## 对使用者的影响

- 只多一个只读命令；`/map`、阶段提示、verify-artifacts 的输出都不变。
