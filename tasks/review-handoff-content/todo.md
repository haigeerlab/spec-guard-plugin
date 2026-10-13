# Todo: review-handoff-content

- [x] Task 1：规则文字与约定块模板（先红） — `test_workflow_checkpoints.py` 新增 1 例（「评审状态标记」含 Spec 六个要点、Plan 四个要点、“只给链接…不算交审”“授权什么”“同时批准 Spec 与 Plan”“不记为 approved”“不能替代内容”；「评审节奏」含“第一次交审时说明一次”“之后不再重复”与 config 命令；两份模板各含“在对话里呈现内容要点”“只给链接不算交审”），先失败后通过。共享检查点规则新增“交审要让用户看到内容”一条、改写“请求审核时说明怎么批准”一条、「评审节奏」补一段；两份模板与 `docs/convention-block.md` 各改一行。本仓库 `AGENTS.md` 的约定块用工作区源码 `setup-convention.sh local --host=codex --replace` 先 dry-run（换掉一行、保留本地段、无需确认的删除）后写入。
- [ ] Task 2：`review_mark.py` 的提醒（先红）
- [ ] Task 3：接入完成时的输出（先红）
- [ ] Checkpoint 1（report）：三套核心回归与上述测试全绿，ShellCheck 无警告
- [ ] Task 4：命令文件、技能、文档与版本号
- [ ] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
