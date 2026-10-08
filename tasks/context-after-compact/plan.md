# Plan: context-after-compact

Based on [`spec/context-after-compact.md`](../../spec/context-after-compact.md) (assumptions confirmed by the user on
2026-10-08). Branch `claude/context-after-compact`.

## Task List

### Task 1: size after compaction (tests first)

`test_session_context.py`: Claude transcript with usage 601k, then `compact_boundary` postTokens 13,951 → 13,951;
usage after the boundary wins; malformed `postTokens` → below thresholds; Codex `token_count` 223k, `compacted`,
`token_count` 0 → 0; later non-zero `token_count` wins. `test-phase-guard.sh`: DONE project with the Claude transcript
gives no Module boundary line; the Codex one neither. Red, then `session_context.py`, green. Mutations: drop the
compaction branch; let the boundary override a newer reading.

### Checkpoint 1 (report): tests green

### Task 2: hint wording

`module_stage.py` lines (`NO_PASTE`, `MODULE_BOUNDARY`, `boundary_line`, `context_line`) per Spec B; expected strings in
`test-phase-guard.sh`; `references/workflow-checkpoints.md` and its contract test; `commands/phase.md`;
`docs/workflow.md` (with the `/rename` note).

### Checkpoint 2 (report): tests green

### Task 3: retire session-handoff

Delete the command, script, its test, the `phase-guard.sh` local-answer branch and its regressions, the
`spec-guard-ops` handoff section, the `validate.sh` line. Capability map: remove the row and Build order entry,
`context-hint-thresholds` depends on `fresh-session-hint`. `git mv` spec/plan/todo to
`docs/retirements/session-handoff/`, add `docs/retirements/session-handoff.md`. A static check (in
`test_workflow_checkpoints.py`) that no command, skill, reference or hint names `/spec-guard:handoff` or
`spec-guard handoff`, and a phase-guard case that such a prompt now gets the normal stage injection.

### Checkpoint 3 (report): full suites green, verify-artifacts clean

### Task 4: real host + CHANGELOG + 0.52.0

Real Claude transcript replay: this session's transcript cut right after its compaction gives no boundary line. CHANGELOG;
both manifests and README `--ref` 0.52.0; macOS full validation and ShellCheck.

### Checkpoint 4 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.

### Task 5: post-release evidence

Release per `docs/release-process.md`; on both installed copies the stage hint after a compaction carries no context
line and `/spec-guard:handoff` is gone.
