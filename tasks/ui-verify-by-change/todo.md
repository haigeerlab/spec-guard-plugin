# Todo: ui-verify-by-change

- [x] Task 1：改写「UI 自验」与模板一行（先红） — `test_workflow_checkpoints.py` 的 UI 自验用例补九个新关键词与两份模板的两个关键词，原有六个关键词保留；先失败后通过（21 例）。「UI 自验」一节改写为按实际改动触发、在任务里验证、怎么验、怎么报、做不了时、Plan 预计到时提前准备，以及原有的兜底与桌面应用例外。两份模板与 `docs/convention-block.md` 各新增一行，已有行未动；`docs/workflow.md` 改一句；本仓库 `AGENTS.md` 的约定块用工作区源码先预览（只新增这一行、保留本地段 7 行、无删除）后写入，差异 +2 行。`test-setup-teardown.sh` 57 例通过。
- [ ] Task 2：CHANGELOG 与版本号
- [ ] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
