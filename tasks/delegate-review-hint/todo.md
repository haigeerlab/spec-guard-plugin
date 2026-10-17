# Todo: delegate-review-hint

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-17 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：测试隔离（先做，行为不变） — `test-phase-guard.sh` 的 `run()` 默认把 `CLAUDE_CONFIG_DIR`、`CODEX_HOME` 指向空目录（用例可用 `SG_CLAUDE_HOME`／`SG_CODEX_HOME` 伪造安装），339 例不变。其余会走到阶段提示的测试在 Task 3 实现后按本机（装了 delegate）实跑结果补隔离。
- [x] Task 2：`sibling_plugins.py` 安装判断（先红后绿） — 先写 `test_sibling_plugins.py`（Claude 6 例、Codex 5 例），导入失败为红；实现后 11 例全绿。Claude 侧的记录读取与 settings 合并抽成 `claude_plugin_root(project, plugin)`，`agent_relay_probe` 改为调用它（断言不改、全绿）；阶段提示用的那条路径从 worktree 的 `.git` 文件定位主检出设置，不调 git。`test_python_compat` 通过；新测试登记进 `validate.sh`。
- [ ] Task 3：外部审查状态判定与阶段提示行（先红后绿）
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并在草稿副本上做一次改坏验证
- [ ] Task 4：规则、文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行
- [ ] 发版后的验证
