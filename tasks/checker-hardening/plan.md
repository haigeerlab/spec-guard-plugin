# Plan: checker-hardening

Based on [`spec/checker-hardening.md`](../../spec/checker-hardening.md) (assumptions confirmed by the user on
2026-10-08). Branch `claude/checker-hardening`. Each task: make the check strict, show it red on a hand-made break of
what it guards, green on the real tree.

## Task List

### Task 1: command bootstrap for every non-exempt command (F7)

Replace the `users < 15` floor in `evals/test-codex-command-roots.sh` with: every command not in an exemption list
(name -> reason) has the canonical bootstrap before its first `$ROOT`; an exempted name that does not exist fails.
Breaks: delete one command's bootstrap block; exempt a missing command.

### Task 2: flag parity and the ledger initialize command (F8)

`scripts/check-command-parity.py` also reports each `(command, script, flag)` whose flag is missing from every skill
that names the script (continuations joined). Fixtures in `scripts/test-checkers.sh`. Red on the real tree (4 ledger
`initialize` flags), then add `preflight` + `initialize` to the `local-ticket-ledger-ops` skill, green. Break: remove
`--prove` from the skill.

### Task 3: separator-row negative test (F9)

A map whose module table's second row is `| x | y | z |` is invalid in `test-verify-artifacts.sh` and
`test_module_insert.py`. Break: disable the separator rule in `capability_map.py`.

### Task 4: grader propagates hidden-test failure (F10)

`evals/dispatch-cost/grade.sh` records the hidden-test exit status, prints the cost section, then exits non-zero on
failure. Test on a fixture with a stubbed `PYTHON` (no paid run). Break: drop the status.

### Task 5: single fingerprint implementation checker (F13)

New `scripts/check-digest-single-source.py` in `validate.sh`; fixtures in `test-checkers.sh` (planted copy fails, clean
tree passes, empty input fails as not found). Break: plant a copy in the real tree.

### Task 6: ShellCheck covers eval subdirectories (F19)

CI adds `evals/*/*.sh`; fix the two warnings in `evals/dispatch-cost/`. Break: revert one fix and see the warning.

### Checkpoint 1 (report): full suites green, ShellCheck clean

### Task 7: CHANGELOG under `## [未发布]` + macOS validation

No version bump: this module ships in the combined release after the remaining audit groups (user decision,
2026-10-08), so every item here is ticked inside this module's own PR and the module is DONE on main.

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.
