# Plan: collaboration-boundary

Based on [`spec/collaboration-boundary.md`](../../spec/collaboration-boundary.md) (reviewed by the user on
2026-10-06, D3 and D4 accepted). Branch `claude/collaboration-boundary`, worktree
`.claude/worktrees/cranky-allen-f2237a`. Reread
[`docs/collaboration-split-brief.md`](../../docs/collaboration-split-brief.md) after any context reset.

## Overview

Build the check first, so every later task is measured by it: the check lists today's violations, each
cutting task removes some, and the last task wires the check into `validate.sh` once the list is empty. The
probe is independent of the cuts except W1, which uses it, so it comes before the text cuts.

## Architecture Decisions

- **Owned list as data.** `scripts/collaboration-owned.txt`, one repository path per line (files or
  directories ending in `/`), read by the check; `collaboration-extraction` reads the same file.
- **Forbidden names as data inside the check**, grouped by the §11 classes plus assumption 7; whole-name
  matching (word boundaries; exact tool names, not a `bridge_` prefix).
- **Probe dependencies:** standard library only (`json`, `subprocess`, `pathlib`); `codex plugin list --json`
  with a short timeout; `CLAUDE_HOME`-style and `codex`-binary overrides through environment for tests.
- **No allow-list.** If a cut cannot be made cleanly, stop and ask (Spec boundary) instead of exempting a line.
- **Test counts are measured, not assumed.** Before Task 3, record per-file counts for every file that loses or
  gains cases; after it, the sums must match.
- Shared verification for every task:

  ```bash
  /bin/bash scripts/validate.sh
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  ```

## Task List

### Task 1: Owned list and boundary check

**Description:** Write `scripts/collaboration-owned.txt` from the baseline inventory (code, tests, skills,
command, references; not the historical spec/tasks/docs records, which are outside the scope anyway). Write
`scripts/check-collaboration-boundary.py`: scope per Spec assumption 2, forbidden classes per §11 and
assumption 7, `path:line: name` output, exit 1 on any hit or on a missing owned path. Add regression cases to
`scripts/test-checkers.sh`: one planted violation per class fails; an owned file, the plain words, and
`legacy_bridge_marker` pass. Do not wire into `validate.sh` yet. Run it on the repository and record the
violation list in todo.md (expected: W1–W4, W5, W6, W8, C3 locations and nothing else).

**Acceptance:** regression green; the repository run lists exactly the expected coupling points; any extra
hit is reported at the checkpoint, not exempted.

**Verify:** `bash scripts/test-checkers.sh`; `python3 scripts/check-collaboration-boundary.py` (expected
red with the list); shared commands.

**Files:** `scripts/collaboration-owned.txt`, `scripts/check-collaboration-boundary.py`,
`scripts/test-checkers.sh`

### Task 2: Detection helper and interface §11 update

**Description:** Write `plugins/spec-guard/hooks/agent_relay_probe.py` per Spec requirement 1, including the
D4 `status` field (run with a short timeout; timeout or bad output → `unknown`; `{"ready": false}` →
`runtime-not-ready` with the `setup` command in the message). Write `test_agent_relay_probe.py` covering every
state in the Spec testing strategy plus a no-write assertion; add it to `validate.sh`. Update
`docs/collaboration-interface.md` §11 for D4 (the `status` field and its output) and assumption 7 (bare skill
and command names as forbidden), nothing else.

**Acceptance:** all probe tests pass; `--host claude` and `--host codex` on this Mac print `not-installed`
with the §12 text; §11 diff limited to the two changes.

**Verify:** `python3 -B plugins/spec-guard/hooks/test_agent_relay_probe.py`; the two live probe runs; shared
commands.

**Files:** `plugins/spec-guard/hooks/agent_relay_probe.py`, `plugins/spec-guard/hooks/test_agent_relay_probe.py`,
`scripts/validate.sh`, `docs/collaboration-interface.md`

### Task 3: Test-side cuts (C3, W6, W5)

**Description:** Record per-file test counts first. Move the collaboration cases of
`test_host_config_removal.py` (imports at lines 12–13, cases around 141–153) into a new owned test file; move
the session-delegation assertions of `test_skill_entrypoints.py` (lines 8, 21, 69, 107) into a new owned test
file; add an owned runner script that runs all collaboration test files; replace the thirteen
collaboration lines and the two entry tests in `validate.sh` with one call to the runner. Add the new files to
the owned list.

**Acceptance:** the check no longer reports C3, W5, W6; the moved-case arithmetic matches (collaboration
total = 190 + moved cases; the two shared files drop by exactly those cases); every collaboration test file
still runs once through `validate.sh`.

**Verify:** count comparison recorded in todo.md; boundary check; shared commands.

**Files:** `plugins/spec-guard/hooks/test_host_config_removal.py`, `plugins/spec-guard/hooks/test_skill_entrypoints.py`,
new owned test files and runner, `scripts/validate.sh`, `scripts/collaboration-owned.txt`

### Task 4: Text cuts (W1–W4, W8)

**Description:** W1: `skills/ticket/SKILL.md` notification step runs the probe first, names the agent-relay
skill when `ready`, otherwise prints the probe message and skips (D3). W2–W4: reword to "the agent-relay
mailbox" with no internal names. W8: generalize the `defect_guard.py:17` comment. Update any existing
assertion that pins the old W1–W4 wording (for example in `test_ticket_entry.py`), with the assertion moved
to the new wording rather than deleted.

**Acceptance:** the boundary check passes on the repository; changed assertions still check the meaning
(probe-then-skill, data-not-authority).

**Verify:** boundary check green; shared commands.

**Files:** `plugins/spec-guard/skills/ticket/SKILL.md`, `plugins/spec-guard/skills/local-ticket-ledger-ops/SKILL.md`,
`plugins/spec-guard/commands/local-ticket-ledger.md`, `plugins/spec-guard/commands/proposal-closeout.md`,
`plugins/spec-guard/hooks/defect_guard.py`, affected tests

### Checkpoint (report): coupling points cut, check green, suites green

### Task 5: Wire the check and compare with the baseline

**Description:** Add `check-collaboration-boundary.py` to `validate.sh` next to the other checks. Run the
three suites and every collaboration test file; write the comparison against the baseline (suite results,
per-file counts, D3 as the only behavior difference) into todo.md. Confirm the guide plugin is still 0.49.0.

**Acceptance:** all three suites green with the check wired; comparison shows no unapproved difference;
revert-one-cut spot check (reintroduce one forbidden line in a scratch copy) turns `validate.sh` red.

**Verify:** shared commands; the spot check; `installed_plugins.json` version read.

**Files:** `scripts/validate.sh`, `tasks/collaboration-boundary/todo.md`

### Checkpoint (gate): module review

Stop and report per the brief format. Push, PR, and merge need separate approval.

## Risks

- The repository run in Task 1 may find hits the baseline missed (as C3 was found at Spec time); each one is
  reported, not exempted.
- Wording assertions in existing tests may pin W1–W4 text; Task 4 moves them, which touches files outside the
  Spec list — reported at the checkpoint.
- `validate.sh` takes about 207 s; run it once per task, not per edit.
