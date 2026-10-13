# Todo: changed-files-at-acceptance

- [x] Task 1：规则文字与约定块模板（先红） — `test_workflow_checkpoints.py` 新增 1 例（「Plan 检查点分级」一节的十个关键词、两份模板各有指向它的一行），先失败后通过（20 例）。共享检查点规则新增两条；两份模板与 `docs/convention-block.md` 各新增一行，已有的行未动；本仓库 `AGENTS.md` 的约定块用工作区源码先预览（只新增这一行、保留本地段 7 行、无删除）后写入。`test-setup-teardown.sh` 57 例通过。规则里补了半句“途中的其他检查点不要求”，对应 Spec 假设 1。
- [x] Task 2：文档、CHANGELOG 与版本号 — `docs/workflow.md` 补一句；CHANGELOG 新增 `[0.60.1] - 2026-10-13`；两份 `plugin.json` 改为 0.60.1，中英 README 的 `--ref` 改为 v0.60.1。
- [ ] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
