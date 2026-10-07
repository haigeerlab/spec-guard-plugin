# Plan: command-plugin-root

Based on [`spec/command-plugin-root.md`](../../spec/command-plugin-root.md) (design and assumptions confirmed by the
user on 2026-10-07). Branch `claude/great-bouman-4da4d6`.

## Overview

Regression first (red on the current commands), then roll the canonical bootstrap into every command and fix the
skill prose, then CHANGELOG and the 0.50.1 bump, then real-host evidence after release.

## Task List

### Task 1: Regression (red)

Extend `evals/test-codex-command-roots.sh`: canonical bootstrap present in every `$ROOT` command; static bans;
substituted run with empty env and no `codex`; Codex fallback; each failure reason; non-directory root.

**Verify:** the script fails on the current tree for the reasons above.

### Task 2: Canonical bootstrap in every command; skill prose

Replace the old bootstrap in all `$ROOT` commands (incl. `collaboration`, `local-ticket-ledger`); update `ticket`,
`hosted-ticket-workflow` and `spec-guard-ops` wording.

**Verify:** Task 1 green; hand-break the bootstrap and see each assertion go red; the three suites; Codex smoke
selftest.

### Checkpoint (report): commands fixed, regressions green

### Task 3: CHANGELOG, lens, 0.50.1

CHANGELOG entry; a lens in `docs/lenses.md`; both manifests and README `--ref` to 0.50.1; macOS `/bin/bash` run of
the full validation.

### Checkpoint (gate): module review; push, PR, tag and release wait for the user

### Task 4: Post-release evidence

Installed 0.50.1 on Claude Code: `/spec-guard:phase` reaches the hook via the substituted root; Codex host check per
release process.
