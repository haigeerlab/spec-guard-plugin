# Spec: command-plugin-root

## Objective

Make every Spec Guard command find its own plugin root on Claude Code, and make the failure message honest when it
cannot. Today the commands start with `ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"`. Claude Code does not export
`CLAUDE_PLUGIN_ROOT` to the Bash tool and only substitutes the exact token `${CLAUDE_PLUGIN_ROOT}` in command
Markdown, so on Claude the line yields an empty root: the command exits 2 with "spec-guard 插件未安装或未启用" —
false, since the command itself came from the installed plugin — or, where `codex` is on `PATH`, silently runs the
Codex install, which may be a different version.

Readers: Spec Guard users on Claude Code; maintainers adding commands.

## Evidence (2026-10-07, Claude Code 2.1.291)

A probe plugin loaded with `--plugin-dir`, run headless (`claude -p "/rootprobe:probe"`) and interactively (tmux,
typed slash command), gave the same result both ways:

| Text in the command Markdown | Text the model received |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | the absolute plugin path |
| `"${CLAUDE_PLUGIN_ROOT}/hooks"` | the absolute path + `/hooks` |
| `${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}` | unchanged |
| `$CLAUDE_PLUGIN_ROOT` | unchanged |
| Bash env `CLAUDE_PLUGIN_ROOT`, `PLUGIN_ROOT` | both empty |

This matches the official plugin reference (code.claude.com/docs/en/plugins/manifest-reference, "Where each variable
resolves"): the variables are not present in the Bash tool environment; skill, command and agent content get the
`${...}` reference substituted inline. `setup-convention` and `teardown-convention` already use the exact token and
work. The broken pattern predates 0.50.0 (`phase.md` since aa78195).

## Assumptions

Confirmed by the user on 2026-10-07:

1. Install paths contain no `"`, `$` or backtick (the substituted path lands inside a double-quoted shell string).
2. Codex behavior is unchanged and not re-measured here: Codex CLI exports `PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT`
   (CHANGELOG, 2026-09-27 smoke), and the `codex plugin list` fallback stays. Only the Codex smoke selftest is run.
3. `collaboration` and `local-ticket-ledger`, which had no Codex fallback, get the same bootstrap as the others.

## Design

One canonical bootstrap, copied verbatim at the top of the first Bash block of every command that uses `$ROOT`:

1. `ROOT="${CLAUDE_PLUGIN_ROOT}"` — Claude substitutes the path at load time; on a host that does not substitute,
   the shell reads the environment variable instead.
2. Empty → `PLUGIN_ROOT`.
3. Still empty and `codex` exists → `codex plugin list --available --json`, keeping its exit code, parsed by
   `python3` into: a path (exit 0), unreadable output (3), or no enabled spec-guard with a path (4).
4. Still empty → exit 2 with `spec-guard 无法定位插件根目录：<which lookups failed>。这是定位失败，不代表插件未安装。`
   naming each failed step (no substitution and no environment variable; no `codex`; `codex` exit code or unreadable
   output; not listed). A root that is not a directory → exit 2 naming the path.

No message text may contain the exact token, because Claude substitutes it even after a backslash.
The two plugin skills that tell Claude to use "`CLAUDE_PLUGIN_ROOT`" in prose (`ticket`, `hosted-ticket-workflow`)
write `ROOT="${CLAUDE_PLUGIN_ROOT}"` instead, so the substituted path reaches the model. The Codex-only
`spec-guard-ops` skill keeps its resolution but no longer calls an empty result "not installed" when the query failed.

## Requirements

1. Every command whose Bash uses `$ROOT` starts its first Bash block with the canonical bootstrap.
2. No command or skill Markdown contains `${CLAUDE_PLUGIN_ROOT:-` or a bare `$CLAUDE_PLUGIN_ROOT`, nor the message
   "插件未安装或未启用" / "插件根目录不可用".
3. Regression (`evals/test-codex-command-roots.sh`): the substituted bootstrap runs `phase` with an empty environment
   and no `codex`; the Codex fallback still works; each failure path exits 2 with its own reason and without
   "未安装"; a non-directory root names the path; the static rules of requirement 2 hold. Each assertion is shown to
   go red by breaking the bootstrap by hand.
4. Real host: the installed candidate's `/spec-guard:phase` on Claude Code runs the plugin's hook through the
   substituted root (recorded in the release evidence).
5. CHANGELOG entry; version 0.50.1 in both manifests and README `--ref`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash evals/test-codex-command-roots.sh
/bin/bash evals/codex-plugin-smoke.sh --selftest
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh
```

## Boundaries

- Always: keep `bash` / `git` / `python3` only; exit 2 with a diagnosable reason on failure.
- Ask first: push, PR, tag, release.
- Never: claim "not installed" from a failed lookup; change hooks, phase judgement or Codex resolution order.

## Success criteria

1. On Claude Code every root-using command reaches its script without relying on `codex`.
2. A failed lookup says which lookup failed and never says the plugin is not installed.
3. Regressions guard both the bootstrap and the static rules; baseline suites green.

## Open questions

None.
