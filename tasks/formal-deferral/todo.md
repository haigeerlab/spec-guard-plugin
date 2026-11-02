# Todo: formal-deferral

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-02 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」），能力图经预览确认后写入。
- [x] Task 1：判据与阶段（module_stage、test_formal_deferral，gate-tick／suspend／insert 各补一例） — `module_stage` 新增 `DEFERRED_TAIL`／`DEFERRED`／`deferred_items`，`UNCHECKED`、`OPEN_ITEM` 用同一段正则做否定前瞻；`module_state` 加 `deferred`；`module_suspend` 的 nothing-open 提示带延期数。新测试 `test_formal_deferral.py` 12 例（导入失败为红），gate-tick 与 insert 的新例在旧代码副本上失败、suspend 新例在改提示前失败，改后全部通过；已登记进 validate.sh。
- [ ] Task 2：阶段提示（test-phase-guard.sh 正反回归）
- [ ] Task 3：/map 与接口（map_view、interface.json 1.12）
- [ ] Task 4：verify-artifacts（失败与迁移提示，ShellCheck）
- [ ] Task 5：规则、模板与文档
- [ ] Task 6：版本号 0.86.0 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查、变异验证、给总负责人发口径变化通知
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、告诉总负责人
