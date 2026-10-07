# Plan: proposal-closeout-reminder

Based on [`spec/proposal-closeout-reminder.md`](../../spec/proposal-closeout-reminder.md) (assumptions confirmed by
the user on 2026-10-07). Branch `claude/proposal-closeout-reminder`.

## Task List

### Task 1: `scan` subcommand (tests first)

Add `scan()` and the CLI subcommand in `proposal_closeout.py`, reusing `build_preview` with the already-read
publication. Tests in `test_proposal_closeout.py` per Spec requirement 1.

**Verify:** new tests red before, green after; full closeout suites.

### Task 2: proof `closeoutPending` (tests first)

`prove_from_remote` records the item's open state on a `proved` result; `as_json` emits it. Tests per requirement 2.

**Verify:** proof suite.

### Checkpoint 1 (report): scan and flag green

### Task 3: rules and docs

Checkpoint rule, release process, command docs (closeout scan section, proof flag), `spec-guard-ops`; contract
checks; CHANGELOG.

**Verify:** contract checks; validate.sh.

### Task 4: real host + 0.51.0

Scan this repository (expect all `already-closed`); bump to 0.51.0; macOS `/bin/bash` full validation.

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.

### Task 5: post-release evidence

Installed 0.51.0: scan on the real host; Codex host check per release process.
