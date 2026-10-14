# Todo: doc-suggestion-at-handoff

- [x] Task 1：文档建议与 ADR 询问（先红） — `test_workflow_checkpoints.py` 新增 1 例（「文档建议」一节的十五个关键词、交审清单与两处入口都有“文档建议”、异常停点带 ADR 询问），先失败后通过（21 例）。共享检查点规则新增「文档建议」一节，Spec 交审清单加一项、异常停点加半句；`commands/review-mark.md` 与 `spec-guard-ops` 的交审内容各加“文档建议”，`spec-guard-ops` 另加一句指向另外两个位置；`docs/workflow.md` 停点同步并补一句。
- [x] Task 2：影响检查的 Spec 阶段说明（先红） — `test_documentation_impact.py` 新增 1 例，先用真实解析器在临时目录里固定行为：Spec 有 `update`／`create` 而 Plan 不存在时报 `module plan must be a regular file`；影响表只有 `follow`、`pending`、`not-applicable` 时得到 `valid`；Plan 是符号链接时报同一句。行为断言在旧说明上都通过，失败只在两处说明缺这段文字；补上后 10 例全绿。代码未改。Plan 原写“临时项目里实跑”，改用测试里的临时目录跑同一个解析器，结果留在回归里。
- [ ] Task 3：CHANGELOG 与版本号
- [ ] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
