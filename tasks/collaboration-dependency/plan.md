# Plan: collaboration-dependency

Based on [`spec/collaboration-dependency.md`](../../spec/collaboration-dependency.md) (reviewed by the user on
2026-10-07, D15–D17 accepted). Branch `claude/collaboration-dependency`, worktree
`.claude/worktrees/cranky-allen-f2237a`; stays local until integration round 1 (D16). Reread
[`docs/collaboration-split-brief.md`](../../docs/collaboration-split-brief.md) after any context reset.

## Overview

Rework the boundary check first (so it guards the deletion), then delete, then the handoff command and migration
document, then the user docs and CHANGELOG, and finally the baseline comparison.

## Architecture Decisions

- `scripts/collaboration-owned.txt` becomes the removed-paths list (same file, new header): the check fails if any
  listed path exists or any forbidden reference appears in the extended scope (D17).
- The handoff command is text for the agent; its behavior is pinned by a contract test like the other command tests.
- Test-count accounting: record per-file counts of every deleted test file before deleting.
- Verification for every task: the three suites; CI's ShellCheck whenever a `.sh` changes.

## Task List

### Task 1: Collaboration-is-gone check

**Description:** Rewrite `check-collaboration-boundary.py` per D17 (removed paths must not exist; scope adds README,
CLAUDE.md, AGENTS.md, docs/optional-features.md, docs/workflow.md; `/spec-guard:collaboration` no longer forbidden;
`commands/collaboration.md` scanned like any file). Update its regressions in `test-checkers.sh` (path reappears →
fail; README reference → fail; handoff wording → pass). Not wired green yet: on this tree it lists the files still to
delete and the docs still to change.

**Acceptance:** checker regressions green; the repository run lists exactly the remaining deletions and W7 mentions.

**Verify:** `bash scripts/test-checkers.sh`; one repository run recorded.

**Files:** `scripts/check-collaboration-boundary.py`, `scripts/collaboration-owned.txt`, `scripts/test-checkers.sh`

### Task 2: Delete the moved code

**Description:** Record per-file test counts; `git rm` the owned paths except `commands/collaboration.md`; drop the
suite line from `validate.sh`; remove the two extraction scripts from the list's "must be absent" set as they are
deleted too.

**Acceptance:** no import or reference to a deleted file remains (suites green); count drop itemized.

**Verify:** the three suites; ShellCheck.

**Files:** owned paths (deleted), `scripts/validate.sh`

### Task 3: Handoff command and migration document

**Description:** Rewrite `commands/collaboration.md` per Spec assumption 3; contract test in
`hooks/test_agent_relay_probe.py` or a new `hooks/test_collaboration_handoff.py`; write
`docs/migrations/2026-10-07-collaboration-split.md` per assumption 4 and 6; replace `<date>` in the probe message,
its test, and interface §12.

**Acceptance:** handoff test covers every probe state; probe message names the real migration file.

**Verify:** the three suites.

**Files:** `commands/collaboration.md`, a handoff test, the migration document, `hooks/agent_relay_probe.py`,
`hooks/test_agent_relay_probe.py`, `docs/collaboration-interface.md`

### Checkpoint (report): code removed, handoff and migration document in place

### Task 4: User docs, manifests, CHANGELOG

**Description:** W7 edits per assumption 5; both `plugin.json` descriptions; `CHANGELOG.md` `## [未发布]` entry; the
boundary check now passes over the extended scope.

**Acceptance:** boundary check green; `check-readme-sync`, manifest checks, and all suites green.

**Verify:** the three suites; ShellCheck.

**Files:** README.md, CLAUDE.md, docs/optional-features.md, docs/workflow.md, docs/design.md, docs/concepts.md, both
`plugin.json`, CHANGELOG.md

### Task 5: Baseline comparison

**Description:** Run the three suites and ShellCheck; write the comparison with the pre-split baseline and the
boundary module's numbers into todo.md; confirm the guide plugin is still 0.49.0; confirm nothing was pushed.

**Acceptance:** no unexplained difference.

**Verify:** recorded outputs.

**Files:** `tasks/collaboration-dependency/todo.md`

### Checkpoint (gate): module review

Stop and report per the brief format. Push, PR and version bump wait for round 1 (D16).

## Risks

- A checker or eval may list command files and expect `collaboration.md` with its old description; Task 3 keeps the file
  and updates its frontmatter description, and Task 4 runs every checker.
- Removing the extraction scripts makes the agent-relay creation non-reproducible from this branch alone; the previous
  commits on `main` still hold them.
