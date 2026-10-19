# Todo: tables-at-acceptance

- [x] Task 1：规则与摘要改成表格呈现（先红） — `test_workflow_checkpoints.py` 最终验收用例补 10 个规则关键词与 3 个摘要关键词（改前在规则里都不存在），先失败后通过。共享检查点规则「最终验收列出实际改动的文件」按 Contract 改写，原「清单末尾再写一行」的依赖说法改为有就用表格；两份约定块模板与 `docs/convention-block.md` 摘要行同步。
- [x] Task 2：CHANGELOG — 「[未发布]」段加一条；两份 `plugin.json` 仍为 0.79.0。
- [x] Checkpoint 1（gate）：模块最终验收；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-19 按本模块的新规则在对话里呈现：验证结果、未验证项、文档改动表（2 个）、其他改动表（8 个，新增 3、修改 7、删除 0，无超出 Plan 预计的文件）、「新增依赖、锁文件改动：无」、本模块的提交表（ea2b3c2、ab5693d、487639e，勾选本 gate 为待提交）与文档建议（README 不用改，其他无）；用户回复「验收通过：勾上 gate 提交，推送并开 PR」。验证链（`verify-and-commit.sh` 全档，macOS `/bin/bash`）：`validate.sh`、phase-guard、verify-artifacts 72 例、`test_workflow_checkpoints.py` 通过；无 `.sh` 改动，未跑 ShellCheck。未验证：agent 在真实会话里是否照做（发版后两边各跑一次）；未做独立代码评审。版本号不变（阶段丙冻结）。

## 外部审查意见

<!-- spec-guard: external-review declined -->
