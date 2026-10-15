# Todo: gate-tick-before-commit

- [x] Task 1：规则加一句（先红） — `test_workflow_checkpoints.py` 的最终验收用例补五个关键词，先失败后通过（21 例）。共享检查点规则「Plan 检查点分级」在“最终验收列出实际改动的文件”之后新增一条；CHANGELOG 新增 `[0.60.4] - 2026-10-15`；两份 `plugin.json` 改为 0.60.4，中英 README 的 `--ref` 改为 v0.60.4。
- [x] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-15 在对话里展示验证结果、未验证项、实际改动的文件清单（取自版本库：11 个文件，新增 3、修改 8、删除 0，无超出 Plan 预计的文件）与收尾文档建议（README 不用改，其他无），用户回复“继续”，按推送开 PR 执行。按本模块的新规则，先勾上本检查点并提交，再推送。验证链（`verify-and-commit.sh` 全档，macOS `/bin/bash`）：`validate.sh` 通过、phase-guard 298 例、verify-artifacts 60 例、`test_workflow_checkpoints.py` 21 例；没有 `.sh` 改动，未跑 ShellCheck。未验证：agent 在真实会话里是否照做（发版后两边各跑一次）；未做独立代码评审。
- [x] 发版后的验证（2026-10-15，v0.60.4） — 两份安装副本上新规则在、对应用例通过。临时项目的 Plan 写明提交须在最终 gate 批准精确文件清单后才做；两边各跑两轮真实会话（第一轮做到最终 gate，第二轮批准验收与提交）。两边在 gate 上都说明了会先勾 gate、核对状态记录再提交；批准后的那一个提交里都带着已勾的 gate，工作区干净。Claude Code 把 `.agent/state.json` 也列进清单一并提交；Codex 没改它（前后都为空，没有留下过期状态）。各只跑了一次。记录见 `docs/releases/v0.60.4-*.json`。
