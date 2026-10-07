# Plan: proposal-review-in-map

Based on [`spec/proposal-review-in-map.md`](../../spec/proposal-review-in-map.md) (assumptions confirmed by the user on
2026-10-07). Branch `claude/proposal-review-promoted`.

## Task List

### Task 1: `in-map` state (tests first)

Review unit tests (in-map fields, drift precedence, drift cases still stale), preflight CLI expectation, proof guard
test (red); then `proposal_review.py` and, if needed, the proof's parent check (green).

### Task 2: docs and contract check, CHANGELOG

### Checkpoint 1 (report): tests green, docs updated

### Task 3: real host + 0.51.2

`proposal-review` on this repository's promoted `collaboration-split` reads `in-map`; bump; macOS full validation.

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.

### Task 4: post-release evidence
