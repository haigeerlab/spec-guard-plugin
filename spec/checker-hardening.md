# Spec: checker-hardening

## Objective

Make the repository's guard checks fail when the thing they guard is broken. Findings F7, F8, F9, F10, F13 and F19 of
the [2026-10-08 architecture audit](../docs/reports/2026-10-08-architecture-audit.md):

1. **F7.** `evals/test-codex-command-roots.sh` only requires at least 15 commands that use `$ROOT`; 16 do, so any one
   command can drop its whole bootstrap and the check stays green.
2. **F8.** `scripts/check-command-parity.py` checks that each `hooks/<script>` a command calls appears in some skill,
   not the flags passed to it; removing a flag such as `--prove` from the skill stays green. Measured on this baseline:
   4 of the 77 flags commands pass to hook scripts are missing from every skill that routes the script — the ledger
   `initialize` flags `--confirm-initialize`, `--user-name`, `--preferred-editor` and `--auto-sync`, so Codex has no
   correct initialize command.
3. **F9.** The strict capability-map parser rejects a second table row that is not a separator, but no test says so;
   disabling the rule leaves every suite green.
4. **F10.** `evals/dispatch-cost/grade.sh` runs the hidden tests through `| tail -3` without `pipefail`, so it exits 0
   when they fail.
5. **F13.** "`spec-digest.py` is the only fingerprint algorithm" is kept by convention only; nothing rejects a copy.
6. **F19.** CI ShellCheck uses `evals/*.sh` and misses the three scripts under `evals/dispatch-cost/`, two of which
   have warnings today.

Readers: maintainers of this repository.

## Assumptions

Confirmed by the user on 2026-10-08:

1. F7: every command must contain the canonical bootstrap before its first `$ROOT`, unless it is in an exemption list
   with a one-line reason: `setup-convention` and `teardown-convention` (they call `${CLAUDE_PLUGIN_ROOT}` directly),
   `ticket` and `local-ticket-portability` (they route to skills and call no hook script). No fixed list of 16 names.
2. F8: every `--flag` on a command's `hooks/<script>` invocation (backslash continuations joined) must appear in some
   skill that also names that script. The missing ledger `initialize` command is added to the
   `local-ticket-ledger-ops` skill; the old "Codex owns the ledger files" coordination no longer applies.
3. F9: a negative test only; the parser does not change.
4. F10: `grade.sh` still prints the cost section, then exits non-zero when the hidden tests failed.
5. F13: a checker in `validate.sh`: a non-test Python file other than `spec-digest.py` fails when it uses `hashlib`
   together with `normalized_row` or a truncated `hexdigest()[:`. Today it matches nothing.
6. F19: CI ShellCheck adds `evals/*/*.sh`; the two existing warnings are fixed (`run.sh`'s `project,local` is one
   argument — a disable comment; `verify-seed.sh` uses `find -print0 | xargs -0`).
7. Each item is shown to go red by breaking the guarded thing by hand.
8. No release of its own: the user decided on 2026-10-08 to finish the remaining audit groups and the forwarded
   non-interactive-hint fix first and release them together. The only user-visible change here is the ledger
   `initialize` command in the Codex skill.

## Requirements

1. `evals/test-codex-command-roots.sh`: the bootstrap rule applies to every command not exempted; an exempted name
   that no longer exists fails; the `users < 15` floor is removed.
2. `scripts/check-command-parity.py` reports each missing `(command, script, flag)`; `scripts/test-checkers.sh` gains
   a fixture where the skill names the script but lacks a flag (fails) and one where it has it (passes).
3. `local-ticket-ledger-ops` skill shows `preflight` and the `initialize` command with the four flags and the same
   rule as the command: never guess the values.
4. A parser test: a map whose module table's second row is `| x | y | z |` is invalid, in `verify-artifacts` and in
   `module-insert`'s parser path.
5. `grade.sh`: a failing hidden test gives a non-zero exit after the cost section; a passing run is unchanged.
6. `scripts/check-digest-single-source.py` (name may change) with fixtures in `test-checkers.sh`: a planted copy fails,
   the real tree passes, zero input files fail as "not found".
7. CI ShellCheck covers `evals/*/*.sh` and is clean on the current tree.
8. A CHANGELOG entry under `## [未发布]`; no version bump, tag or release in this module.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh evals/*/*.sh
```

## Boundaries

- Always: `bash` / `git` / `python3` only; fixtures in temporary directories.
- Ask first: push, PR, tag, release.
- Never: change product judgement; weaken an existing check; run the paid dispatch-cost eval (the grader is tested on
  a fixture).

## Success criteria

1. Each of the six checks goes red on a hand-made break of what it guards and is green on the real tree.
2. Codex's ledger skill carries the same initialize command as the Claude command.

## Open questions

None.
