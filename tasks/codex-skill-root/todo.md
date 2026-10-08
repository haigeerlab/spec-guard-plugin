# Todo: codex-skill-root

- [x] Task 1: static and runtime tests (red first) — `evals/test-codex-command-roots.sh`: spec-guard-ops must carry the verbatim bootstrap before its first `$ROOT`; every other skill using `$ROOT` carries it or names spec-guard-ops and `ROOT="${CLAUDE_PLUGIN_ROOT}"`. Runtime on the block extracted from spec-guard-ops's 解析环境: substituted root without calling codex, a valid list, and `[]` / failing query / no spec-guard / non-JSON / no codex each exit 2 with the diagnosis and no traceback. Red on the old skill: static rule (2 skills) and runtime (substituted case gave `ROOT=`)
- [x] Task 2: skills use the canonical bootstrap — spec-guard-ops's 解析环境 is the canonical bootstrap + `PROJECT=`, with one line saying exit 2 is a locate failure, not "not installed"; local-ticket-ledger-ops names `ROOT` per host. Green. Mutations caught: old resolver restored (static red), ledger sentence removed (static red)
- [x] Task 3: `--auto-sync` placeholder on both hosts — the ledger `initialize` example takes `"<true|false the user gave>"` (skill) and `"用户给的 true 或 false"` (command); `grep -E -- '--auto-sync (true|false)'` over commands and skills finds nothing; parity checker passes (20 command files)
- [ ] Checkpoint 1 (report): full suites green, ShellCheck clean
- [ ] Task 4: CHANGELOG under `## [未发布]` + macOS validation
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
