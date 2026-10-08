# Plan: unattended-long-first-record

Based on [`spec/unattended-long-first-record.md`](../../spec/unattended-long-first-record.md) (assumptions confirmed by
the user on 2026-10-08). Branch `claude/unattended-long-first-record`. No release of its own: every item is ticked
inside this module's PR.

## Task List

### Task 1: regressions (red first)

In `test_session_context.py`'s `Unattended` class: a ~100 KB first `session_meta` record with `source: "exec"` is
unattended (red today: the 64 KB read truncates it); a first record over 1 MB with `source: "exec"` is attended.

### Task 2: raise the first-record limit to 1 MB

A named constant; a read that fills the limit without a line end counts as attended. Green; existing session_context
and phase-guard suites unchanged. Breaks: restore 64 KB (100 KB case red); drop the "no line end" check (over-1 MB case
red only if the truncated prefix parses — so also assert it via a record whose first 1 MB is valid JSON on its own).

### Checkpoint 1 (report): full suites green, ShellCheck clean

### Task 3: CHANGELOG under `## [未发布]` + macOS validation

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.
