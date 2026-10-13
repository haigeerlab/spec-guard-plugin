# Todo: link-per-session

- [x] Task 1：实测会话标识的稳定性 — 结论：标识在恢复与压缩后都不变，设计可继续。Claude Code 2.1.296：本会话当天重启过一次，`CLAUDE_CODE_SESSION_ID` 与最初工作目录路径里的标识相同；一份压缩过一次的会话记录，压缩后的 760 条记录仍写在同一文件，文件内只有一个 sessionId 且等于文件名。codex-cli 0.162.1：`codex exec` 取到 `CODEX_THREAD_ID` 后用 `codex exec resume <id>` 恢复，再取到的值相同；一份压缩过一次的会话记录，压缩后的 49 条记录仍写在同一文件，首条 `session_meta` 的 `id` 是文件名的结尾。未实测：两边 hook 输入里的 `session_id` 字段（设计以 `transcript_path` 的文件名为准，另认该字段作为补充）；压缩后的标识是由“记录仍写在同一文件”推出的，不是在压缩后直接读环境变量。
- [x] Task 2：解析支持会话登记（先红） — `test_project_link.py` 新增 7 例（本会话的登记优先、没登记时退回目录级、只有别人的登记时为 none、会话登记的相对路径与目标不存在、版本 1 忽略会话标识、13 种版本 2 的无效写法、空的 sessions 加目录级指向合法），先因 `resolve_for` 不存在失败。`project_link.py` 新增 `read_link` 与 `resolve_for`（返回状态、目标、来源），原 `resolve` 改为它的目录级包装，返回值不变。26 例全绿，原有用例未改；phase-guard 284 例不变。
- [ ] Task 3：钩子按会话查找（先红）
- [ ] Checkpoint 1（report）：核心回归全绿，ShellCheck 无警告
- [ ] Task 4：命令支持 `--session`（先红）
- [ ] Task 5：命令文件、技能、文档、那句规则、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
