# Todo: ledger-local-only

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：`--local-only` 预检与初始化（先红） — `test_local_ledger_runtime.py` 新增 8 例（preflight 有 origin 时给 `localOnly: available` 且 `--local-only` 得 ready／`disabled-local-only`、两者同给 invalid、无 origin 时不受影响；initialize 只对 Epiq 子进程追加 `remote.origin.pushurl`、已有 `GIT_CONFIG_COUNT=1` 时追加为第 2 条、不带时 `environment` 为 `None`；CLI 透传与互斥；预检文本列出两种选择）。改前 7 例红（不带新选项那例改前即成立）；实现 `local_only_environment` 与两处参数，转绿，72→80 例，现有用例未改。变异：传 `environment=None` 时两例变红。
- [ ] Task 2：status 报告未提交事件数（先红）
- [ ] Task 3：标识在别的分支上，与初始化后的提示（先红）
- [ ] Checkpoint 1（report）：三套核心回归与账本测试全绿，ShellCheck 无警告（若改 `.sh`）
- [ ] Task 4：文档、Spec 补句、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
