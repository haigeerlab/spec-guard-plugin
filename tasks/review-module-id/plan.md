# Plan: review-module-id

Based on [`spec/review-module-id.md`](../../spec/review-module-id.md) (assumptions confirmed by the user on 2026-10-07).
Branch `claude/review-module-id`.

## Task List

### Task 1: `moduleId` in review and preflight (tests first)

Review tests (in-map, accepted, stale-after-read carry it; publication absent does not) and preflight CLI tests (ready
and in-map carry it), red; then `proposal_review.py` and `proposal_promotion_proof.py`, green; docs.

### Checkpoint 1 (report): tests green

### Task 2: real host + CHANGELOG + 0.51.3

Real review of `collaboration-split`; CHANGELOG; bump; macOS full validation.

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.

### Task 3: post-release evidence
