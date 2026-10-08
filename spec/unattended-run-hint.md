# Spec: unattended-run-hint

## Objective

Stop the phase hint from asking the agent to tell a user to free context when no user is there. Forwarded by the user
through 第二轮联调 on 2026-10-08: a read-only `codex exec` review run in a repository at DONE ended its answer with
"后续可用 /compact 聚焦下一模块；无关任务可用 /clear。" The hook injects the same lines into non-interactive runs
(`codex exec`, `claude -p`) as into interactive sessions, and the run's answer goes to another agent, not a person.
The lines are `MODULE_BOUNDARY` / `boundary_line` (Module boundary) and `context_line` (Session context) in
`module_stage.py`.

Readers: anyone whose agents drive `codex exec` or `claude -p` inside a Spec Guard project; maintainers of the phase
hint.

## Measured signals (2026-10-08, real runs in temporary projects)

- **`claude -p`**: the UserPromptSubmit input has no interactivity field (`session_id`, `transcript_path`, `cwd`,
  `scratchpad_dir`, `prompt_id`, `permission_mode`, `hook_event_name`, `prompt`), and the transcript file does not
  exist yet when the hook runs. Claude Code sets `CLAUDE_CODE_SESSION_ATTENDED=0` and `CLAUDE_CODE_ENTRYPOINT=sdk-cli`
  in the hook environment; an interactive desktop session has `CLAUDE_CODE_SESSION_ATTENDED=1`. A `claude -p` started
  from an attended session still gets `0` (Claude Code sets it per session, overriding the inherited value).
- **`codex exec`**: the input (also per Codex's own `UserPromptSubmitCommandInput`) has no interactivity field, but
  carries `transcript_path`; that rollout exists when the hook runs and its first record is `session_meta` with
  `originator: "codex_exec"`, `source: "exec"`. Codex Desktop sessions record `source: "vscode"`. Codex clears the hook
  environment, so Claude variables do not leak into Codex hooks.

## Assumptions

Confirmed by the user on 2026-10-08:

1. A session is unattended when `CLAUDE_CODE_SESSION_ATTENDED` is exactly `0`, or when the Codex transcript's first
   record is `session_meta` with `source` exactly `"exec"`. Anything else — the variable missing or `1`, another
   source, a missing, unreadable or malformed transcript — counts as attended and keeps today's lines.
2. Only the Module boundary and Session context lines are left out. The Location line stays (its instruction only
   applies when asking a user), as do all stage facts and judgements.
3. `CLAUDE_CODE_SESSION_ATTENDED` is not in Claude Code's public documentation; if it changes, the effect is today's
   behaviour (one extra sentence), never a wrong stage.
4. Tests use fixtures for both signals and for every attended fallback; each new assertion is shown to go red by
   breaking the code by hand. The combined release verifies one real `claude -p` and one real `codex exec`.
5. No release of its own (combined release); CHANGELOG under `## [未发布]`.

## Requirements

1. `session_context.py` reports a fourth fact, unattended, from the environment variable and the transcript's first
   record; it never raises and never reads more than the first record.
2. `phase-guard.sh` passes it to `module_stage.py` (for example `--unattended`); `describe` then omits the Module
   boundary and Session context lines and nothing else.
3. Without the flag, output is byte-for-byte what it is today for every existing case.
4. Regressions in `test-phase-guard.sh` (end-to-end through the hook, with a DONE fixture and a large-context
   transcript):
   - `CLAUDE_CODE_SESSION_ATTENDED=0` and a Codex transcript whose first record has `source:"exec"` each drop both
     lines;
   - `CLAUDE_CODE_SESSION_ATTENDED=1`, `source:"vscode"`, a missing transcript and a malformed first record keep them;
   - stage, counts and Location are identical in both cases.
5. CHANGELOG entry under `## [未发布]`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_module_stage_sanitization.py
```

## Boundaries

- Always: `bash` / `git` / `python3` only; fixtures in temporary directories; the hook stays read-only.
- Ask first: push, PR; any real host run outside the combined release's verification.
- Never: change stage judgement or thresholds; leave out a line for an attended session; read a transcript beyond its
  first record for this signal.

## Success criteria

1. `codex exec` and `claude -p` runs no longer receive the "tell the user /compact or /clear" lines.
2. Interactive sessions see exactly today's output.

## Open questions

None.
