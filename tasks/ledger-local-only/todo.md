# Todo: ledger-local-only

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：`--local-only` 预检与初始化（先红） — `test_local_ledger_runtime.py` 新增 8 例（preflight 有 origin 时给 `localOnly: available` 且 `--local-only` 得 ready／`disabled-local-only`、两者同给 invalid、无 origin 时不受影响；initialize 只对 Epiq 子进程追加 `remote.origin.pushurl`、已有 `GIT_CONFIG_COUNT=1` 时追加为第 2 条、不带时 `environment` 为 `None`；CLI 透传与互斥；预检文本列出两种选择）。改前 7 例红（不带新选项那例改前即成立）；实现 `local_only_environment` 与两处参数，转绿，72→80 例，现有用例未改。变异：传 `environment=None` 时两例变红。
- [x] Task 2：status 报告未提交事件数（先红） — 新增 4 例（两个 `~pending` 文件共 3 个非空行 → 3 且文本有离线归档提醒；只有已提交事件 → 0 且无提醒；事件目录不可读 → `null`、state 不变、不出计数行；状态工作树归别的仓库时不出该字段）。与 Plan 的出入：现有用例 `test_text_status_without_conflict_keeps_one_line` 断言整段文本只有一行，因 Spec 规定 owned 时总出计数行，改名为 `..._adds_only_the_pending_count_line` 并把期望改为两行。改前 4 例红；实现 `pending_event_count`（只数行、不解析，跳过符号链接）与文本两行，转绿，80→84 例。变异：计数恒为 0 时“3 个非空行”那例变红。
- [x] Task 3：标识在别的分支上，与初始化后的提示（先红） — 新增 5 例（另一本地分支提交了 `.epiq/project.json` → `identityElsewhere` 为该分支且文本说明合进默认分支；只在 `__epiq_state__` 上 → 不报；哪里都没有 → 不报；git 查询失败 → 不报且 state 不变；初始化成功文本含“合进默认分支”，`--local-only` 时另有“未推送”）。改前 3 例红（查询失败那例改前即成立）；实现 `identity_elsewhere`（一次 `for-each-ref` 后逐个 `cat-file -e`，找到第一个即停，跳过 `HEAD` 与状态分支）与文本行，转绿，84→89 例。变异：查询恒为空时“另一分支”那例变红。
- [x] Checkpoint 1（report）：三套核心回归与账本测试全绿，ShellCheck 无警告（若改 `.sh`） — 随 Task 3 的提交跑 `verify-and-commit.sh` 全档；本模块没有改 `.sh`。
- [ ] Task 4：文档、Spec 补句、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
