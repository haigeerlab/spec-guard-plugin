# Spec: context-hint-no-paste

## Objective

Stop agents from pasting `/spec-guard:handoff` text when the context grows. On 2026-10-06 the user asked for one
line suggesting `/compact` instead of a pasted handoff block. That was recorded only as this repository's agent
memory; the plugin still tells every agent, in every project, to produce the handoff text:

- the injected `Module boundary` lines (`MODULE_BOUNDARY`, `boundary_line`) say "run /spec-guard:handoff … for
  paste-ready handoff text", and `context_line` says "continue in a new session with /spec-guard:handoff";
- the shared checkpoint rule says that at 80% during continuous build the agent stops and "给出 `/spec-guard:handoff`
  的交接文本".

The user saw a pasted handoff near a full context after "the fix" — there was no fix in any release.

## Assumptions

Confirmed by the user on 2026-10-07:

1. The agent still says one sentence (context size, `/compact` or a new session). Only the handoff text goes.
2. Thresholds (50% at a module boundary, 80% mid-module), stage judgement, which stages carry the lines, and the
   `/spec-guard:handoff` command itself are unchanged.
3. Version 0.51.1 (fix).

## Wording

- `MODULE_BOUNDARY` (size unknown): `- Module boundary: a good point to /compact or start the next piece of work in a
  new session. Say so in one sentence; do not paste handoff text (the user runs /spec-guard:handoff, Codex: spec-guard
  handoff, when they want it). This stage summary carries over, the conversation does not need to.`
- `boundary_line`: `- Module boundary: this session's context is about N k tokens (<note>); a good point to /compact
  or start the next piece of work in a new session. Say so in one sentence; do not paste handoff text (…same…). This
  stage summary carries over, the conversation does not need to.`
- `context_line`: `- Session context: about N k tokens in the last turn (<note>); every turn re-reads it. Finish or
  record the current task, then say in one sentence that the user can /compact or continue in a new session; do not
  paste handoff text (…same…).`
- Checkpoint rule (80%, continuous build): stop after finishing or recording the task, say in one sentence that the
  context is at 80% and the user can `/compact` or open a new session; do not paste handoff text — the user runs
  `/spec-guard:handoff` when they want it. The agent still does not open a session itself.
- `commands/phase.md` describes the lines accordingly.

## Requirements

1. `test-phase-guard.sh` expectations follow the new wording; injected text never contains `paste-ready`.
2. A contract check: the checkpoint rule carries "不贴交接文本" and no longer "给出 `/spec-guard:handoff` 的交接文本";
   the injected lines carry "do not paste handoff text".
3. Codex and Claude both receive the same lines (one source, `module_stage.py`).
4. CHANGELOG; 0.51.1.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
```

## Boundaries

- Never: change thresholds, stage judgement or the handoff command; add a hook write.

## Success criteria

1. No plugin text asks an agent to show handoff text unprompted.
2. Regressions red if the old wording returns.

## Open questions

None.
