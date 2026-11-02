# Todo: formal-deferral

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-02 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」），能力图经预览确认后写入。
- [x] Task 1：判据与阶段（module_stage、test_formal_deferral，gate-tick／suspend／insert 各补一例） — `module_stage` 新增 `DEFERRED_TAIL`／`DEFERRED`／`deferred_items`，`UNCHECKED`、`OPEN_ITEM` 用同一段正则做否定前瞻；`module_state` 加 `deferred`；`module_suspend` 的 nothing-open 提示带延期数。新测试 `test_formal_deferral.py` 12 例（导入失败为红），gate-tick 与 insert 的新例在旧代码副本上失败、suspend 新例在改提示前失败，改后全部通过；已登记进 validate.sh。
- [x] Task 2：阶段提示（test-phase-guard.sh 正反回归） — 计数行追加「· 延期 n」／` · Deferred n`；DONE 建议在有延期时改说「除 n 项延期（用 map 查看）外没有未勾选的 todo 项」，挂起分支追加同一句；DONE 的状态码事实加延期总数。phase-guard 加 3 例（只剩延期为完成且计数带延期、DONE 建议中英、缺恢复条件仍未完成），在 Task 1 版本副本上第 11 段失败（「计数行应带 Deferred 1」），改后 512 例全部通过。
- [x] Task 3：/map 与接口（map_view、interface.json 1.12） — JSON 每模块加 `deferred`、顶层加 `deferredTotal`（`DEFERRAL_FIELDS`）；表格「✅ 已完成（延期 n）」且有延期的已完成模块不折叠；表后「延期项：」一节逐条列模块 · 事项 · 恢复条件（经 clean 与截断）。`interface.json` 1.12 加 `mapView.deferral`（字段与口径变化），`check-interface.py` 核对字段。`test_map_view.py` 加 3 例并更新固定键集合（改前 4 失败 1 报错），`test-checkers.sh` 加 2 个反例（补说明后、加检查前为红），改后 map 80 例、检查器 161 例全部通过。用例发现：Build order 里紧跟的下游会被当作当前模块算进行中（现有规则），所以「可以开始」用排在后面的另一个下游验证。
- [ ] Task 4：verify-artifacts（失败与迁移提示，ShellCheck）
- [ ] Task 5：规则、模板与文档
- [ ] Task 6：版本号 0.86.0 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查、变异验证、给总负责人发口径变化通知
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、告诉总负责人
