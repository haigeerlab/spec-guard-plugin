# Todo: map-view

- [x] Task 1：`map_view.py` 的测试（先红） — `hooks/test_map_view.py` 26 例，覆盖六种状态与先后、传递依赖（多层与菱形）、关键卡点、待审核三种取值、step／progress、折叠与 `--all`、截断与清理、三种退出码与错误 JSON、`--project` 无效走 2、git 的 unmerged／unpushed／分离头指针、generator 版本、键集合固定；没有实现时全部失败；在 `scripts/validate.sh` 登记。
- [x] Task 2：实现 `map_view.py` — 26 例全绿。两处变异各有断言变红：`blocked` 只看直接依赖（3 例红）、折叠时漏掉 `ready`（1 例红）。本仓库实跑 0.18 秒（93 个模块）。
- [x] Task 3：挂起原因（`module_suspend.py --reason`） — `test_module_suspend.py` 新增 8 例（带原因挂起、替换原因只换一行、给已挂起无原因的模块补原因、已挂起不带原因仍拒绝、恢复删两行、五种不合法原因被拒且不改文件、恢复时给 `--reason` 报参数错误、孤立原因行不算挂起），新增 6 例先红；实现后全绿，现有用例期望值未改。`test_map_view.py` 加一例：用 `module_suspend.py` 写原因、`map_view.py` 读回（27 例）。
- [x] Checkpoint 1（report）：脚本与挂起原因回归全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [x] Task 4：命令、技能与实跑 — 新建 `commands/map.md`（定位片段与 cost-report 相同，要求把表格原样给用户）；`spec-guard-ops` 加 map 一节；`commands/module-suspend.md` 与技能的挂起一节写明 `--reason`（只按用户说的写，不从上下文推断）。实跑：本仓库（93 个模块，`BUILDING map-view`，未合入 1、未推送 1）；临时项目 7 个模块，用 `module_suspend.py --reason` 挂起一个后，表头显示“关键卡点：quality-gates 挂起（2 个高危漏洞，上游未修复）→ 挡住 1 个：pwa-lifecycle”、待审核一项与下一个 gate，六种状态各出现一次，`--all` 展开未就绪那一行并写出缺哪个依赖，JSON 的 bottlenecks、awaitingReview、totals 与表一致；不是 git 仓库时两项写“判断不了”。临时目录已删。
- [ ] Task 5：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
