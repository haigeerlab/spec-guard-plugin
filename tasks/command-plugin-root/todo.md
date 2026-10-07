# Todo: command-plugin-root

- [x] Task 1: regression (red on the current commands) — static: 17 commands lacked the canonical bootstrap, 15 carried the false "未安装或未启用" message and 2 the undiagnosable "根目录不可用", all 17 used `${CLAUDE_PLUGIN_ROOT:-`, two skills told Claude to read the env var
- [x] Task 2: canonical bootstrap in every `$ROOT` command; skill prose — 17 commands (18 snippets; history-integrity has two) carry the canonical bootstrap verbatim; ticket / hosted-ticket-workflow use `ROOT="${CLAUDE_PLUGIN_ROOT}"`; spec-guard-ops separates query failure from not listed. Regression green; 7 hand mutations (RC lost, exit 4→3, no dir check, no PLUGIN_ROOT step, `:-` form back, "未安装" wording, exit 1) each go red. validate.sh pass, phase-guard 151, verify-artifacts 26, Codex smoke selftest pass, ShellCheck clean. Source run on Claude Code 2.1.291 (`claude -p /spec-guard:phase --plugin-dir <worktree>/plugins/spec-guard`): transcript shows the worktree path substituted, phase reported; sonnet and a second haiku run used it; one earlier haiku run retyped the path wrongly (main checkout) — model copy error, host text was right
- [x] Checkpoint (report): commands fixed, regressions green
- [ ] Task 3: CHANGELOG, lens, 0.50.1
- [ ] Checkpoint (gate): module review; push, PR, tag and release wait for the user
- [ ] Task 4: post-release evidence on the installed plugin
