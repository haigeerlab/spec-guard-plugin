# Plan: collaboration-map-retirement

Based on [`spec/collaboration-map-retirement.md`](../../spec/collaboration-map-retirement.md) (assumptions confirmed
by the user on 2026-10-08). Branch `claude/collaboration-map-retirement`. No release of its own: every item is ticked
inside this module's PR.

## Task List

### Task 1: Proposal baseline (before any change)

Record `proposal_closeout.py scan` and `proposal_review` output for this repository's Proposals, so the post-change
run can be compared (Requirement 5). Read-only.

### Task 2: retirement scan covers the map (F14, red first)

Add the capability map to `test-retire-legacy-tracker-bridge.sh` with the retired command names. Red on the real
tree (the `context-hint-no-paste` row). Then reword that row to today's behaviour; green. Break: put
`/spec-guard:handoff` back.

### Task 3: retire the four modules from the map and archive them (F6)

Remove the four rows and Build order entries; `audit-remediation` drops `collaboration-messaging`;
`collaboration-interface` depends on `—`. `git mv` their Spec and task files into `docs/retirements/<id>/`; add
`docs/retirements/collaboration-implementation.md`. Verify: strict parse, no retired id anywhere in the map, blob
equality for every moved file, 55 modules in the phase hint, verify-artifacts clean, Proposal scan/review equal to
Task 1. Break: leave one id in the Build order (parser red); leave one Spec in `spec/` (verify-artifacts red).

### Checkpoint 1 (report): full suites green, ShellCheck clean

### Task 4: CHANGELOG under `## [未发布]` + macOS validation

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.
