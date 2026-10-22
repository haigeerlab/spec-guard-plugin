# Todo: tracker-provider-unify

- [x] Task 0：提交已批准的 Spec 标记、Plan 与 todo — Plan 批准（C10）后由模块协调带批准标记提交到集成分支 f6e1e77，`module-crew sync` 合入（1e81055）。按 D3 A 把 Plan 的并行边界一节补进 Spec（Boundaries 加一句说明），`module_scope.py check --base crew/fix-batch` 通过、越界 0；Spec 指纹因此改变，最终验收附差异复审。
- [x] Task 1：共享回归 `test_tracker_provider_contract.py`（先红）并登记 — 13 个用例，同一个假平台喂给托管事项、交接、收尾、Proposal 读取四个入口。先红 11 处失败 + 16 处错误，托管事项入口全绿（基准）：交接与收尾 GitLab 列表不带 `issue_type=issue`、混入 incident／task 照收（F11）；交接不认 `/-/work_items/`；收尾拒 http 实例；交接写入「退出码 0、无 HTTP 状态」当成功；Proposal 读取不接受 `host`（全部报错，F7）；结构检查列出 5 个直接调 gh/glab 的文件。未登记的测试文件会被 validate 的登记检查拦下（实测），登记前又必然红，所以这个文件与 Task 2～5 的实现一起在全绿时登记、提交。
- [ ] Task 2：共享层扩展（project id、labels、container），托管事项保持绿
- [ ] Task 3：交接改用共享层，错误短码与发布器状态不变
- [ ] Task 4：收尾改用共享层，GitLab scheme 跟随目标
- [ ] Task 5：Proposal 读取改用共享层，`--host` 与 JSON `host`，50 页
- [ ] Checkpoint 1（report）：变异核对（三种改坏都变红）
- [ ] Task 6：文档与更新说明（拟写 CHANGELOG 条目记在此处）
- [ ] Task 7：`module-crew sync` 合入集成分支并跑完整检查
- [ ] Checkpoint 2（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做
