# Plan: hosted-ticket-untrusted-text

Based on [`spec/hosted-ticket-untrusted-text.md`](../../spec/hosted-ticket-untrusted-text.md) (assumptions confirmed
by the user on 2026-10-08). Branch `claude/hosted-ticket-untrusted-text`.

## Task List

### Task 1: `public_result` (tests first)

Unit tests: an injected body (heading, backticks, newlines, ESC, zero-width) prints as one sanitised line within the
bound and `bodyLength` is the full length; `id`/`url`/`closed` kept; 25 candidates print 10 with `candidatesTotal`;
`remoteText` only when an Issue is present; results without Issues and odd shapes unchanged. Red, then the function
(beside the provider), green.

### Task 2: wire the three CLIs, skill text

Apply `public_result` before each `print`; one CLI-level test per script on a fake provider; existing hosted-ticket
suites unchanged; skill line on remote text. Mutations: drop the call in one CLI; return the body unfiltered.

### Checkpoint 1 (report): full suites green

### Task 3: CHANGELOG + 0.52.2 + macOS validation

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.

### Task 4: post-release evidence

Release per `docs/release-process.md`; on both installed copies a fake injected Issue prints filtered.
