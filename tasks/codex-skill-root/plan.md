# Plan: codex-skill-root

Based on [`spec/codex-skill-root.md`](../../spec/codex-skill-root.md) (assumptions confirmed by the user on
2026-10-08). Branch `claude/codex-skill-root`. No release of its own: every item is ticked inside this module's PR.

## Task List

### Task 1: static and runtime tests (red first)

In `evals/test-codex-command-roots.sh`: `spec-guard-ops` must carry the canonical bootstrap before its first `$ROOT`;
every skill using `$ROOT` carries it or names `spec-guard-ops` and `ROOT="${CLAUDE_PLUGIN_ROOT}"`. Runtime on the block
extracted from the skill's 解析环境 section: fake `codex` printing `[]`, non-JSON, failing, a valid list; and a
substituted `${CLAUDE_PLUGIN_ROOT}`. Red on the current skill (traceback / rule).

### Task 2: skills use the canonical bootstrap

Replace the resolver in `spec-guard-ops` with the canonical bootstrap + `PROJECT=`; `local-ticket-ledger-ops` names
the root source per host. Green. Breaks: restore the old resolver; drop the sentence from the ledger skill; drop the
static rule.

### Task 3: `--auto-sync` placeholder on both hosts

Skill and command `initialize` examples take the user's value; parity checker passes. Break: the parity checker still
sees `--auto-sync` (unchanged flag), so verify by grep that no example hard-codes `false`.

### Checkpoint 1 (report): full suites green, ShellCheck clean

### Task 4: CHANGELOG under `## [未发布]` + macOS validation

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.
