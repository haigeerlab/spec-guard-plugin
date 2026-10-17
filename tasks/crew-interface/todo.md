# Todo: crew-interface

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：取值常量与一致性检查（先红后绿） — `test-checkers.sh` 的 check-interface 段加 8 例，夹具 `mkifc` 同时放四个脚本占位。写入 1.1 之前，3 例真红（scopeCheck、checkoutRole 脚本缺失与 mapView 缺 1.0 的键未被检查）；另有 5 例当时显示通过但并不真实（真实文件里还没有这些键，夹具生成就失败，检查自然报错），写入 1.1 后才有意义。加 `module_scope.SCOPES`、`checkout_role.ROLE_KINDS` 并让字面量引用它们，两模块单元测试原样全绿；`check-interface.py` 扩展为核对四个入口、脚本存在、三组取值与 `mapView` 1.0 键。
- [x] Task 2：`interface.json` 1.1 — 写入 `moduleConcurrency`、`scopeCheck`、`checkoutRole`、`reviewMark` 与 `mapView.concurrency`，`interface` 为 1.1；`check-interface.py` 通过，检查回归 133 例全绿。只加不改：本地与远端都没有 v0.67.1 tag（0.67.1 尚未发版），改以 #345 合并提交 `5798c7a` 为基准，去掉新增后解析结果相同。在演示仓库按登记的命令逐条实跑（mapView、scopeCheck、checkoutRole 四条、reviewMark），退出码均为 0，写入类只预览。
- [ ] Checkpoint 1（report）：三套核心回归、改坏验证与实跑核对
- [ ] Task 3：对外说明、版本号与 CHANGELOG
- [ ] Checkpoint 2（gate）：模块验收与本批收尾
