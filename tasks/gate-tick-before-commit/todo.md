# Todo: gate-tick-before-commit

- [x] Task 1：规则加一句（先红） — `test_workflow_checkpoints.py` 的最终验收用例补五个关键词，先失败后通过（21 例）。共享检查点规则「Plan 检查点分级」在“最终验收列出实际改动的文件”之后新增一条；CHANGELOG 新增 `[0.60.4] - 2026-10-15`；两份 `plugin.json` 改为 0.60.4，中英 README 的 `--ref` 改为 v0.60.4。
- [x] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-15 在对话里展示验证结果、未验证项、实际改动的文件清单（取自版本库：11 个文件，新增 3、修改 8、删除 0，无超出 Plan 预计的文件）与收尾文档建议（README 不用改，其他无），用户回复“继续”，按推送开 PR 执行。按本模块的新规则，先勾上本检查点并提交，再推送。验证链（`verify-and-commit.sh` 全档，macOS `/bin/bash`）：`validate.sh` 通过、phase-guard 298 例、verify-artifacts 60 例、`test_workflow_checkpoints.py` 21 例；没有 `.sh` 改动，未跑 ShellCheck。未验证：agent 在真实会话里是否照做（发版后两边各跑一次）；未做独立代码评审。
