# Todo: compact-phase-injection

- [ ] Task 1：动手前的宿主实测（Spec Assumptions 8、9） — 2026-10-15 实测（未勾：Codex 一项有 Spec 没预料到的结果，停下交用户决定）。
  - Claude Code（2.1.296，`claude -p --plugin-dir` 加载只带探针的临时插件）：手动 `/compact` 后插件的 `SessionStart(compact)` 触发，注入的标记被模型原样读到；用 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=3` 逼出一轮中途的自动压缩，同一轮压缩 3 次、钩子跟着触发 3 次。钩子输入只有 `source: "compact"`，没有区分手动与自动的字段。`-p` 运行不需要先在 `/hooks` 信任；交互会话是否要信任未测。
  - Codex（0.162.1，临时改动已安装副本的 `hooks.json`，只在末尾追加一项，原有一项逐字不变）：已有的 `user_prompt_submit` 信任记录不受影响，阶段提示照常注入；新增的插件 `SessionStart` 一项在一轮里压缩 4 次都没有运行，绕过信任（`--dangerously-bypass-hook-trust`）、再加一条 `enabled = true` 的状态记录、去掉 matcher 让它在启动时运行，都没有运行。对照：写在配置里的 `SessionStart(compact)` 钩子在中途压缩后运行了（复现观测会话的结果）。推测是 Codex 在安装插件时登记插件钩子，原地改文件不会被读到——未证实。`codex exec` 里的 `/compact` 被当作普通提示，手动压缩未测成。
  - 恢复：两份插件副本与 `~/.codex/config.toml` 都已从备份恢复，SHA-256 与实测前一致。
- [ ] Task 2：测试先行（先红）
- [ ] Task 3：实现
- [ ] Checkpoint 1（report）：钩子回归全绿，ShellCheck 无告警
- [ ] Task 4：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
