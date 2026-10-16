# Todo: map-view

- [x] Task 1：`map_view.py` 的测试（先红） — `hooks/test_map_view.py` 26 例，覆盖六种状态与先后、传递依赖（多层与菱形）、关键卡点、待审核三种取值、step／progress、折叠与 `--all`、截断与清理、三种退出码与错误 JSON、`--project` 无效走 2、git 的 unmerged／unpushed／分离头指针、generator 版本、键集合固定；没有实现时全部失败；在 `scripts/validate.sh` 登记。
- [x] Task 2：实现 `map_view.py` — 26 例全绿。两处变异各有断言变红：`blocked` 只看直接依赖（3 例红）、折叠时漏掉 `ready`（1 例红）。本仓库实跑 0.18 秒（93 个模块）。
- [ ] Task 3：挂起原因（`module_suspend.py --reason`）
- [ ] Checkpoint 1（report）：脚本与挂起原因回归全绿
- [ ] Task 4：命令、技能与实跑
- [ ] Task 5：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
