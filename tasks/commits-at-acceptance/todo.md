# Todo: commits-at-acceptance

- [x] Task 1：规则与摘要补一句（先红） — `test_workflow_checkpoints.py` 最终验收用例补 5 个规则关键词与 2 个摘要关键词，先失败后通过（57 例）。共享检查点规则「最终验收列出实际改动的文件」末尾补列提交清单与推送时只列不一致；两份约定块模板与 `docs/convention-block.md` 的摘要行同步。
- [x] Task 2：CHANGELOG — 顶部新增 `## [未发布]` 段写这一条；两份 `plugin.json` 仍为 0.79.0。
- [x] Checkpoint 1（gate）：模块最终验收；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-19 在对话里展示验证结果、未验证项、实际改动的文件清单（取自版本库：10 个文件，新增 3、修改 7、删除 0，无超出 Plan 预计的文件，无新增依赖与锁文件改动）、本模块的提交清单（127d65c、caf3bbd、4146643，勾选本 gate 为待提交）与文档建议（README 不用改，其他无），用户回复「验收通过：勾上 gate 提交，推送并开 PR，把 PR 号抄送接入协调」。验证链（`verify-and-commit.sh` 全档，macOS `/bin/bash`）：`validate.sh`、phase-guard、verify-artifacts 72 例、`test_workflow_checkpoints.py` 57 例通过；无 `.sh` 改动，未跑 ShellCheck。未验证：agent 在真实会话里是否照做（发版后两边各跑一次）；未做独立代码评审。版本号不变（阶段丙冻结）。

## 外部审查意见

<!-- spec-guard: external-review declined -->
