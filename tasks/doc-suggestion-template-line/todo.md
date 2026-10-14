# Todo: doc-suggestion-template-line

- [x] Task 1：模板新增一行（先红） — `test_workflow_checkpoints.py` 的文档建议用例补两份模板的三个关键词，先 2 处失败后通过（21 例）。两份模板与 `docs/convention-block.md` 各新增一行，已有行未动；本仓库 `AGENTS.md` 的约定块用工作区源码先预览（只新增这一行、保留本地段 7 行、无删除）后写入，差异为 +2 行。`test-setup-teardown.sh` 57 例通过。CHANGELOG 顶部新开 `[未发布]` 记一条；文件下方另有一段早先遗留的 `[未发布]`（维护者工具），未动。
- [x] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-14 在对话里展示验证结果、未验证项、实际改动的文件清单（取自版本库：10 个文件，新增 3、修改 7、删除 0，无超出 Plan 预计的文件）与文档建议（无），用户确认推送开 PR。验证链（`verify-and-commit.sh` 全档，macOS `/bin/bash`）：`validate.sh` 通过、phase-guard 298 例、verify-artifacts 60 例、`test_workflow_checkpoints.py` 21 例、`test-setup-teardown.sh` 57 例；第一次提交时 phase-guard 第 9 段 3 秒时限用例在负载均值约 30 时失败，单独重跑通过后重试提交通过。未验证：agent 是否因此在全部完成时提收尾建议（0.60.3 发版后看）；未做独立代码评审。
