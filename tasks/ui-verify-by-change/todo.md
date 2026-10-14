# Todo: ui-verify-by-change

- [x] Task 1：改写「UI 自验」与模板一行（先红） — `test_workflow_checkpoints.py` 的 UI 自验用例补九个新关键词与两份模板的两个关键词，原有六个关键词保留；先失败后通过（21 例）。「UI 自验」一节改写为按实际改动触发、在任务里验证、怎么验、怎么报、做不了时、Plan 预计到时提前准备，以及原有的兜底与桌面应用例外。两份模板与 `docs/convention-block.md` 各新增一行，已有行未动；`docs/workflow.md` 改一句；本仓库 `AGENTS.md` 的约定块用工作区源码先预览（只新增这一行、保留本地段 7 行、无删除）后写入，差异 +2 行。`test-setup-teardown.sh` 57 例通过。
- [x] Task 2：CHANGELOG 与版本号 — CHANGELOG 顶部的 `[未发布]` 改为 `[0.60.3] - 2026-10-15`，并加本模块一条；两份 `plugin.json` 改为 0.60.3，中英 README 的 `--ref` 改为 v0.60.3。
- [x] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-15 在对话里展示验证结果、未验证项、实际改动的文件清单（取自版本库：16 个文件，新增 3、修改 13、删除 0，无超出 Plan 预计的文件）与收尾文档建议（README 不用改，其他无），用户确认推送开 PR。验证链（`verify-and-commit.sh` 全档，macOS `/bin/bash`）：`validate.sh` 通过、phase-guard 298 例、verify-artifacts 60 例、`test_workflow_checkpoints.py` 21 例、`test-setup-teardown.sh` 57 例；没有 `.sh` 改动，未跑 ShellCheck。未验证：agent 在真实会话里是否照做（发版后两边各跑一次改页面文字的临时项目）；未做独立代码评审。
