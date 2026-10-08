# Plan: unattended-run-hint

Based on [`spec/unattended-run-hint.md`](../../spec/unattended-run-hint.md) (assumptions confirmed by the user on
2026-10-08). Branch `claude/unattended-run-hint`. No release of its own: every item is ticked inside this module's
PR; the real `claude -p` / `codex exec` check belongs to the combined release.

## Task List

### Task 1: end-to-end regressions (red first)

In `test-phase-guard.sh`, on a fixture whose stage carries the Module boundary line and a transcript large enough for
the Session context line: `CLAUDE_CODE_SESSION_ATTENDED=0`, and a Codex-shaped transcript whose first record is
`session_meta` with `source:"exec"`, each drop both lines; `ATTENDED=1`, `source:"vscode"`, a missing transcript and a
malformed first record keep them; stage, counts and Location are identical. Red on the current hook.

### Task 2: the unattended fact and its use

`session_context.py` emits the fact (environment variable, or the first transcript record only; never raises);
`phase-guard.sh` passes `--unattended` to `module_stage.py`; `describe` omits only those two lines. Green; existing
cases byte-for-byte unchanged. Breaks: treat a missing transcript as unattended; accept any `source`; drop the
Session context omission.

### Checkpoint 1 (report): full suites green, ShellCheck clean

### Task 3: CHANGELOG under `## [未发布]` + macOS validation

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.
