# Todo: crew-interface

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：取值常量与一致性检查（先红后绿） — `test-checkers.sh` 的 check-interface 段加 8 例，夹具 `mkifc` 同时放四个脚本占位。写入 1.1 之前，3 例真红（scopeCheck、checkoutRole 脚本缺失与 mapView 缺 1.0 的键未被检查）；另有 5 例当时显示通过但并不真实（真实文件里还没有这些键，夹具生成就失败，检查自然报错），写入 1.1 后才有意义。加 `module_scope.SCOPES`、`checkout_role.ROLE_KINDS` 并让字面量引用它们，两模块单元测试原样全绿；`check-interface.py` 扩展为核对四个入口、脚本存在、三组取值与 `mapView` 1.0 键。
- [x] Task 2：`interface.json` 1.1 — 写入 `moduleConcurrency`、`scopeCheck`、`checkoutRole`、`reviewMark` 与 `mapView.concurrency`，`interface` 为 1.1；`check-interface.py` 通过，检查回归 133 例全绿。只加不改：本地与远端都没有 v0.67.1 tag（0.67.1 尚未发版），改以 #345 合并提交 `5798c7a` 为基准，去掉新增后解析结果相同。在演示仓库按登记的命令逐条实跑（mapView、scopeCheck、checkoutRole 四条、reviewMark），退出码均为 0，写入类只预览。
- [x] Checkpoint 1（report）：三套核心回归、改坏验证与实跑核对 — `6231abc` 提交时全档通过（validate、phase-guard 395、verify-artifacts 68、repo-artifacts、ShellCheck 无告警）。改坏验证：`scopeCheck.command` 的脚本路径少一个字符时报「引用的 hooks/module_scop.py 不存在」；`SCOPES` 的 own 改成 mine 时报 scope 取值不一致；均已复原。新入口命令的实跑结果见 Task 2。
- [x] Task 3：对外说明、版本号与 CHANGELOG — README 中英文各加「多模块并行（可选）」一节、「对外接口」补 1.1 一句，`--ref` 改为 v0.68.0；`docs/design.md`「对外接口」补 1.1 的四个入口并新增「规划层与运行层」小节；两份 `plugin.json` 为 0.68.0；CHANGELOG「未发布」改为 `[0.68.0] - 2026-10-18` 并写明 7 个模块，「新增」加 interface 1.1 一条。`check-readme-sync.py`、`check-interface.py`、`check-no-parallel-surface.py` 通过；`codex-plugin-smoke.sh --selftest` 退出 0（日志里的 ❌ 行是自检喂给判决器的反例）。
- [ ] Checkpoint 2（gate）：模块验收与本批收尾
