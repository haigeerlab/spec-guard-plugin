# Todo: collaboration-map-retirement

- [x] Task 1: Proposal baseline (before any change) — against the remote default branch (the tools never read the working tree): `proposal_closeout.py scan --backend github` -> pending [], authorized-session-delegation already-closed, collaboration-messaging absent, collaboration-split / hosted-ticket-workflow / local-ticket-portability already-closed, local-ticket-ledger absent; `proposal_review` -> collaboration-messaging `absent`, authorized-session-delegation `stale` at `proposal-stage:promoted`
- [x] Task 2: retirement scan covers the map (F14, red first) — `test-retire-legacy-tracker-bridge.sh` now scans `spec/CAPABILITY-MAP.md` for retired command names (legacy bridge names, `spec-guard:handoff`, `spec-guard handoff`, `session_handoff`). Red on the real tree: the context-hint-no-paste row and this module's own new row; both reworded (one sentence suggesting /compact or /clear; "the retired handoff command"), green. Mutation caught: `/spec-guard:handoff` put back into the row
- [ ] Task 3: retire the four modules from the map and archive them (F6)
- [ ] Checkpoint 1 (report): full suites green, ShellCheck clean
- [ ] Task 4: CHANGELOG under `## [未发布]` + macOS validation
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
