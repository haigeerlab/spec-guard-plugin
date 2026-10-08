# Spec: codex-skill-root

## Objective

Resolve the plugin root in the Codex skills the same way the commands do. Finding F5 of the
[2026-10-08 architecture audit](../docs/reports/2026-10-08-architecture-audit.md): `spec-guard-ops`'s "解析环境"
block parses `codex plugin list --available --json` with its own snippet, and a well-formed but unexpected document
such as `[]` raises `AttributeError: 'list' object has no attribute 'get'` — a traceback instead of a locate
diagnosis. Since 0.50.1 every command uses one canonical bootstrap
([command-plugin-root](command-plugin-root.md)) that turns the same inputs into a diagnosable failure. Separately,
`local-ticket-ledger-ops` says "Resolve the installed plugin root" without saying how.

Readers: Codex and Claude Code users of the Spec Guard skills; maintainers of the skills.

## Assumptions

Confirmed by the user on 2026-10-08:

1. `spec-guard-ops`'s resolver is replaced by the commands' canonical bootstrap, verbatim; it works on both hosts
   (Claude substitutes `${CLAUDE_PLUGIN_ROOT}` on load, Codex falls back to `PLUGIN_ROOT` and then
   `codex plugin list`). The `PROJECT=` line stays.
2. The other skills that run hook scripts do not copy it; each says "Codex: `spec-guard-ops`'s 解析环境; Claude:
   the substituted `ROOT="${CLAUDE_PLUGIN_ROOT}"`". `ticket` and `hosted-ticket-workflow` already do;
   `local-ticket-ledger-ops` gains the same sentence.
3. Tests extend `evals/test-codex-command-roots.sh`: a static rule and a runtime run of the block extracted from the
   skill.
4. No release of its own (combined release); CHANGELOG under `## [未发布]`.
5. Forwarded by the user through 第二轮联调 after #247: the ledger `initialize` example hard-codes `--auto-sync false`
   in both `local-ticket-ledger-ops` and `commands/local-ticket-ledger.md`, while the text beside it says the value
   must come from the user. Both become a placeholder for the user's `true` or `false`.

## Requirements

1. `skills/spec-guard-ops/SKILL.md` contains the canonical bootstrap verbatim before its first `$ROOT`, followed by
   `PROJECT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`; the old resolver and its prose about an empty
   `ROOT` are gone, replaced by one line saying a locate failure is not "not installed".
2. `skills/local-ticket-ledger-ops/SKILL.md` names where `ROOT` comes from on each host.
3. Static rule: `spec-guard-ops` must carry the canonical bootstrap before its first `$ROOT`; every skill that uses
   `$ROOT` either carries it or names `spec-guard-ops` for Codex and the substituted `ROOT="${CLAUDE_PLUGIN_ROOT}"`
   for Claude.
4. Runtime, on the block extracted from the skill with a fake `codex` on a PATH without the real one:
   - list `[]`, non-JSON output and a failing query each exit 2 with the "无法定位插件根目录" diagnosis and no
     `Traceback`;
   - a list with an enabled spec-guard sets `ROOT` to its path;
   - with `${CLAUDE_PLUGIN_ROOT}` substituted, `ROOT` is that path and `codex` is not called.
5. Each new assertion is shown to go red by breaking the skill or the rule by hand.
6. `--auto-sync` in the ledger `initialize` example is a placeholder on both hosts (`"<true|false the user gave>"` in
   the skill, `"用户给的 true 或 false"` in the command); the parity checker still passes.
7. CHANGELOG entry under `## [未发布]`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash evals/test-codex-command-roots.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Boundaries

- Always: `bash` / `git` / `python3` only; fake `codex` in tests.
- Ask first: push, PR.
- Never: change any hook script; copy the bootstrap into more skills than `spec-guard-ops`.

## Success criteria

1. No Spec Guard skill can turn an unexpected plugin list into a traceback or a silently empty root.
2. Codex and Claude resolve the root in skills exactly as in commands.

## Open questions

None.
