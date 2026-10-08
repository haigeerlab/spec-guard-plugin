# Todo: audit-small-cleanups

- [x] Task 1: phase-guard without grep (F12, tests first) — `file_has_line` (bash `read` + `[[ =~ ]]`, last line without newline included) replaces the three `grep -Eq` activation checks, same patterns. New cases with a PATH of only git and python3: activated, CRLF-block and activeModule projects inject; other-state, prose and empty stay silent. Red before (no output), green after; phase-guard 166. Mutations caught: unanchored marker (prose activates), CLAUDE.md branch dropped (CRLF case red)
- [ ] Task 2: local ticket inventory module (F15, test first)
- [ ] Task 3: single module id pattern and current-module selection (F16)
- [ ] Task 4: remove dead host-config helpers (F17)
- [ ] Task 5: complete command table with a check (F18)
- [ ] Checkpoint 1 (report): full suites green, ShellCheck clean
- [ ] Task 6: CHANGELOG under `## [未发布]` + macOS validation
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
