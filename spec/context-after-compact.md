# Spec: context-after-compact

## Objective

Make the context hints true after a compaction and match how the user actually frees context, and retire the session
handoff command that this makes redundant.

1. **Stale size after /compact.** The phase hint reads the context size from the last main-session usage record in the
   transcript. Right after `/compact` that record is still the pre-compaction turn, so the first prompt after compacting
   is told the context is long. Measured 2026-10-08 in this repository's own session (Claude Code 2.1.291): last usage
   601,430; `compact_boundary` record with `preTokens` 601,658 and `postTokens` 13,951; the first post-compaction prompt
   was told "about 601 k tokens"; the next usage record was 93,435. Codex has the same gap: a `compacted` record, then a
   `token_count` of 0 (skipped today as synthetic), so the scan falls through to the pre-compaction 223,005.
2. **Wording.** The hints say "/compact or start … in a new session". The user does not switch sessions: a new session
   loses the peers it talks to. Claude Code's docs give the criterion as relatedness, not size: `/compact` (optionally with
   a focus) to continue, `/clear` when switching to unrelated work. Codex CLI documents the same `/compact`, `/clear` and
   `/rename`. Measured 2026-10-08 (Claude Code CLI 2.1.291, session named with `--name`): after `/clear` the session kept
   its name and peer id in `ListAgents`, and a cross-session message sent after `/clear` was received.
3. **Handoff.** `/spec-guard:handoff` (Codex: `spec-guard handoff`) produced paste-ready text for a new session. With
   no session switching it has no job: the phase hint already gives location, stage, counts and unmerged commits every
   turn, and resumable state lives in Spec, Plan and todo. The user decided to remove it.

Readers: Spec Guard users on Claude Code and Codex; maintainers of the phase hint.

## Assumptions

Confirmed by the user on 2026-10-08:

1. Claude: a `system` record with subtype `compact_boundary` carries `compactMetadata.postTokens`; when it is newer than
   the newest usage reading, that number is the context size.
2. Codex: a `compacted` record carries no size; when it is newer than the newest non-zero usage reading, the size is
   treated as below both thresholds (no context line, and no size-less Module boundary line either).
3. A usage reading newer than the compaction record wins, as today.
4. The hint wording follows the official criterion: `/compact` with a focus when the next work is related, `/clear`
   when it is unrelated; it no longer suggests starting a new session. Thresholds (50% / 80%) and stage judgement are
   unchanged.
5. `session-handoff` is retired following `retired-module-separation`: no replacement stub, a CHANGELOG note instead.
6. Version 0.52.0 (a user-visible command is removed).

## Design

### A. Size after compaction (`hooks/session_context.py`)

`context_usage` scans the transcript tail backwards as today, and also recognises compaction records:

- Claude `{"type":"system","subtype":"compact_boundary","compactMetadata":{"postTokens":N}}` with a non-negative
  integer `N` → return `(N, None)`; a malformed or missing `postTokens` → treated as the Codex case below.
- Codex `{"type":"compacted", …}` → return a "compacted, size unknown" result that `module_stage.describe` treats as
  below both thresholds. The window, if a later record carries one, is not needed.

Whichever comes first in the backward scan wins: a usage reading after the compaction is used as before. Unreadable
input stays `None` (unknown), as today. The hook output contract (`TOKENS` line empty or digits) is kept: the
"compacted, size unknown" case prints `0`, and `describe` treats `0` as below the thresholds (it is below them already;
the size-less Module boundary line is only for `None`).

### B. Wording (`hooks/module_stage.py`, references, docs)

- `NO_PASTE` loses the parenthesis naming the handoff command: "do not paste handoff text".
- Module boundary (sized and size-less): "… a good point to free context. Say in one sentence that the user can
  /compact with a focus on the next module, or /clear if the next work is unrelated; do not paste handoff text. This
  stage summary carries over, the conversation does not need to."
- Session context (80%): "… Finish or record the current task, then say in one sentence that the user can /compact with
  a focus on it, or /clear if the next work is unrelated; do not paste handoff text."
- `references/workflow-checkpoints.md`, `commands/phase.md`, `docs/workflow.md`: same criterion; "换会话" becomes
  "/compact 或 /clear"; one note that `/clear` keeps a name set with `/rename` (peers still reach the session) but drops
  conversation-only agreements, so long-lived ones belong in the project's agent instructions or memory.

### C. Retire `session-handoff`

- Remove `commands/handoff.md`, `hooks/session_handoff.py`, `hooks/test_session_handoff.py`, the local-answer branch in
  `hooks/phase-guard.sh` and its regressions in `test-phase-guard.sh`, the `handoff` section of
  `skills/spec-guard-ops/SKILL.md`, and the `validate.sh` line.
- Capability map: remove the `session-handoff` row and its Build order entry; `context-hint-thresholds` depends on
  `fresh-session-hint` only. Its Spec and Plan move by `git mv` to `docs/retirements/session-handoff/{spec,plan}.md`
  (todo stays with them as `todo.md`), plus `docs/retirements/session-handoff.md` saying what was removed, why, and that
  the archive is history only. `spec/CAPABILITY-HISTORY.json` and older history are not rewritten.
- `test_session_context.py` keeps its cwd-root test; only the comment's spec reference changes.
- Unrelated "handoff" uses stay: local ticket handoff, project-audit handoff, the collaboration handoff command.

## Requirements

1. After a Claude `compact_boundary` newer than any usage reading, the hint uses `postTokens`; a 601k-before /
   14k-after transcript at `DONE` gives no Module boundary line. A usage reading after the boundary is used instead.
2. After a Codex `compacted` record (followed by a zero `token_count`), no context line and no Module boundary line;
   a later non-zero `token_count` is used as before.
3. Malformed compaction records and unreadable transcripts degrade to today's behaviour; the hook never fails.
4. Hint lines and the shared checkpoint rule carry the new wording on both hosts; no hint, command or skill text
   mentions `/spec-guard:handoff` or `spec-guard handoff` or suggests starting a new session.
5. The handoff command, script, tests and hook branch are gone; a prompt equal to `/spec-guard:handoff` or
   `spec-guard handoff` gets the normal stage injection.
6. `session-handoff` is out of the capability map and Build order, archived under `docs/retirements/session-handoff/`;
   the map parses strictly and `verify-artifacts` is clean.
7. Each new assertion is shown to go red by breaking the code by hand; baseline suites green.
8. CHANGELOG 0.52.0 (fixed: stale size after compaction; changed: hint wording; removed: handoff, with what to use
   instead); both manifests and README `--ref` at 0.52.0; release per `docs/release-process.md`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_session_context.py
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh
```

## Boundaries

- Always: `bash` / `git` / `python3` only; read only the usage and compaction fields, never transcript content.
- Ask first: push, PR, tag, release.
- Never: change thresholds or stage judgement; guess a size; remove the other "handoff" features.

## Success criteria

1. A just-compacted session is never told its context is long, on either host.
2. The hints suggest `/compact` or `/clear` by relatedness, in one sentence, and never a new session or handoff text.
3. `session-handoff` is retired cleanly with its history kept.

## Open questions

None.
