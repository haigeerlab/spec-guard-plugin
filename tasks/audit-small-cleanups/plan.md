# Plan: audit-small-cleanups

Based on [`spec/audit-small-cleanups.md`](../../spec/audit-small-cleanups.md) (assumptions confirmed by the user on
2026-10-08). Branch `claude/audit-small-cleanups`. No release of its own: every item is ticked inside this module's PR.

## Task List

### Task 1: phase-guard without grep (F12, tests first)

Regression in `test-phase-guard.sh`: a PATH with bash, git and python3 only (no grep) — activated project injects,
unrelated project silent. Red, then bash built-in checks, green; all existing activation cases unchanged. Breaks:
loosen the marker match (prose activates); drop the CLAUDE.md branch.

### Task 2: local ticket inventory module (F15, test first)

Regression: no `local_ticket_*` module (tests excluded) imports `local_ticket_portability`, and importing each in a
fresh interpreter leaves it unimported. Red, then `local_ticket_inventory.py` with re-exports in the CLI, green; all
ticket suites unchanged. Break: one module imports from the CLI again.

### Task 3: single module id pattern and current-module selection (F16)

`documentation_impact.py` imports `MODULE_ID`; `module-insert.py` uses `project_stage`. Existing documentation-impact
and module-insert suites unchanged; a static check that `documentation_impact.py` defines no `re.compile` for module
ids. Break: diverge the selection (module-insert tests red).

### Task 4: remove dead host-config helpers (F17)

Delete `remove_codex_table`, `remove_claude_server` and their tests; nothing references them; ledger adapter suites
unchanged.

### Task 5: complete command table with a check (F18)

Add the two rows; a check (in `test-checkers.sh` or `validate.sh`) that every `commands/*.md` appears in the
`docs/workflow.md` table. Red before the rows, green after. Break: drop a row.

### Checkpoint 1 (report): full suites green, ShellCheck clean

### Task 6: CHANGELOG under `## [未发布]` + macOS validation

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.
