# Todo: proposal-closeout-reminder

- [x] Task 1: `scan` subcommand (tests first) — 13 new tests (10 scan, 3 CLI) red on import, then green; closeout suite 94. Hand mutations killed: already-closed counted as pending, pending not appended, unreadable pool returned as an empty scan, issueId dropped (one further mutation inside the preview branch was behavior-preserving)
- [x] Task 2: proof `closeoutPending` (tests first) — 3 CLI tests (true / false / absent when unread or unproved), 2 red before; proof suite 57 green. The duplicate guard in `as_json` was removed; the single guard in `prove_from_remote` and the inverted flag are each killed by hand mutation
- [x] Checkpoint 1 (report): scan and flag green
- [x] Task 3: rules and docs, contract checks, CHANGELOG — checkpoint rule "Proposal 晋级 PR 合并后"; closeout command scan section; proof doc `closeoutPending`; spec-guard-ops scan + no hand-label; add-module and docs/workflow.md no longer tell people to relabel by hand; release-process post-release scan; reference scan section. Contract test in test_workflow_checkpoints.py, red when a hand-label sentence is added back or the rule heading is renamed
- [ ] Task 4: real-host scan of this repository; 0.51.0
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 5: post-release evidence on the installed plugin
