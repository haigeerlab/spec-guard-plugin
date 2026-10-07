# Plan: context-hint-no-paste

Based on [`spec/context-hint-no-paste.md`](../../spec/context-hint-no-paste.md) (assumptions confirmed by the user on
2026-10-07). Branch `claude/no-handoff-paste`.

## Task List

### Task 1: injected lines (tests first)

Update `test-phase-guard.sh` expectations and add the no-`paste-ready` assertion (red), then change the three strings
in `module_stage.py` (green).

### Task 2: checkpoint rule and docs (tests first)

Contract check in `test_workflow_checkpoints.py` (red), then `workflow-checkpoints.md` and `commands/phase.md`; CHANGELOG.

### Checkpoint 1 (report): wording changed, regressions green and red under the old wording

### Task 3: 0.51.1 and full validation

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.

### Task 4: post-release evidence

Installed 0.51.1: a sized boundary line on a real host (headless transcript or the hook run with a transcript) shows
the new wording; Codex smoke.
