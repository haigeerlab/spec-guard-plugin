# Todo: session-handoff

- [ ] Task 1：实测 worktree 会话的项目目录——临时 settings.local.json 记录 CLAUDE_PROJECT_DIR / cwd / pwd（先征得同意），结论写回 Spec 第 12 条
- [ ] Task 2：根目录以会话 cwd 为准——仅 Task 1 证实时做；worktree、子目录、无 cwd、未启用各用例
- [ ] Task 3：交接文本——session_handoff.py、各阶段、未合并提交、最新发布证据 not-verified、只读；登记 validate.sh
- [ ] Task 4：触发词拦截——is_trigger 正反例、Claude / Codex 两种 JSON、失败即放行、其余逐字不变
- [ ] Checkpoint：本地作答端到端、牙齿检查、claude -p 费用为 0 展示给用户
- [ ] Task 5：命令与 Module boundary 行——commands/handoff.md、spec-guard-ops handoff、MODULE_BOUNDARY、CHANGELOG
- [ ] Checkpoint：全量验证 + 审查 + PR + 发版 + Claude CLI / 桌面版 / Codex TUI 实测 + 提醒开新会话
