# Spec: collaboration-boundary

## Objective

Make Spec Guard reach collaboration through exactly one entry, as defined in
[docs/collaboration-interface.md §11-12](../docs/collaboration-interface.md#11-spec-guards-single-entry), and make
that rule a failing check instead of a review habit. After this module, the collaboration code still lives in
Spec Guard (it moves in `collaboration-extraction`), but nothing outside the collaboration-owned files refers to
it, so extraction can delete those files without touching anything else.

Readers: the user reviewing the split and agents working on the next two Spec Guard modules.

Source decisions: [the interface document](../docs/collaboration-interface.md) (accepted 2026-10-06),
[the pre-split baseline](../docs/baselines/collaboration-pre-split.md), and
[the split brief](../docs/collaboration-split-brief.md).

## Assumptions

Confirmed by the user on 2026-10-06:

1. **Code stays.** No collaboration file is moved or deleted here. The thirteen collaboration test files keep
   running in `validate.sh` (through one owned runner, see 5) so every step can be compared with the baseline.
   The "tests move with the code" half of W5 and W6 is done by `collaboration-extraction`.
2. **Check scope in this module.** The boundary check scans the shipped plugin tree `plugins/spec-guard/**`,
   `scripts/**`, `evals/**`, and the manifests, minus the collaboration-owned list. User-facing repository docs
   (`README.md`, `CLAUDE.md`, `AGENTS.md`, `docs/optional-features.md`, `docs/workflow.md`) are W7 and are
   rewritten by `collaboration-dependency`, which then adds them to the scope (the migration document they must
   link to does not exist yet). Historical records (`spec/`, `tasks/`, `docs/` records, `CHANGELOG.md`) are never
   in scope: they describe the past and are not call sites.
3. **Owned list is a file, not a pattern.** The collaboration-owned list is one explicit path list kept next to
   the check, taken from [BL §Inventory and coupling points] plus the files this module adds to it (4, 5). The
   same list is the input `collaboration-extraction` moves, so the two cannot drift.
4. **One coupling the baseline missed (C3).** `hooks/test_host_config_removal.py:12-13, 141-153` imports
   `native_collaboration_adapters` and `native_collaboration_runtime`. Those cases move into a new owned test
   file; the shared test keeps only the ledger and generic cases. The total test count is unchanged.
5. **Owned runner.** A new owned script runs the collaboration test files; `validate.sh` calls it with one line
   whose text names no collaboration internal. `collaboration-dependency` deletes that line.
6. **Exact names, not loose patterns.** The forbidden list matches whole names (the ten `bridge_*` tool names
   and the seven denied tools from interface §2, not any `bridge_` prefix) so that unrelated words such as
   `legacy_bridge_marker` in `test_proposal_tracker_read.py` are not violations.
7. **Spec Guard's own collaboration skill and command names are internals too.** References to the `collab`,
   `collaboration-ops`, `session-routing`, and `session-delegation` skills and to `/spec-guard:collaboration`
   from outside the owned list are violations; the replacement is the agent-relay skill name. (§11 lists their
   paths; this extends it to their bare names, which is how W1 refers to `collab`.)
8. **The probe is offline and read-only.** It reads the host's plugin record and the plugin's `interface.json`,
   runs no network call, writes nothing, takes no message content, and is never called by phase injection.
9. **No release in between.** The next Spec Guard release that contains this module also contains
   `collaboration-dependency`, so the temporary difference in decision D3 is never shipped on its own.

## Decisions

Both taken as recommended by the user on 2026-10-06.

- **D3 ticket notification (W1), a behavior difference from the baseline.** The `ticket` skill today sends
  notifications through Spec Guard's `collab` skill. After this module it names the agent-relay skill and, when
  the probe is not `ready`, says so and skips the notification (interface §11 W1). Until agent-relay exists the
  probe reports `not-installed`, so on this branch ticket notifications are skipped with the message. Accepted
  because of assumption 9.
- **D4 runtime readiness.** Interface §12 has a `runtime-not-ready` state, but §11 gives the probe no public way
  to ask agent-relay whether its runtime is ready. Decision: add one optional field to `interface.json`,
  `"status": ["<argv relative to the plugin root>"]`, a command that prints `{"ready": true|false, "setup":
  "<command>"}`; the probe runs it with a short timeout, and a timeout or bad output is `unknown`. This changes
  §11, so the interface document is updated in the same module.

## Requirements

1. **Detection helper** `plugins/spec-guard/hooks/agent_relay_probe.py`
   - Usage: `python3 -B agent_relay_probe.py --host claude|codex [--project <dir>]`; prints exactly one JSON
     object `{"state", "interface", "required", "message"}` as in interface §11 and exits 0 for every state.
   - Claude: installed when `~/.claude/plugins/installed_plugins.json` has an `agent-relay@<marketplace>` entry;
     enabled when the merged `enabledPlugins` of user, project, and local settings has it `true`. Codex: an
     entry named `agent-relay` with `installed` and `enabled` in `codex plugin list --json`.
   - Reads `interface.json` at the plugin root; `interface` within `>=1.0,<2.0` or the state is `incompatible`
     (with found and required versions in the message); a missing or unreadable `interface.json` is
     `incompatible`, not `ready`.
   - Any probe failure (unreadable record, command timeout, malformed JSON) is `unknown`, never `not-installed`.
   - `not-installed` message is the §12 text verbatim, with `<date>` still a placeholder (filled by
     `collaboration-dependency`).
   - Paths of the Claude home and the `codex` binary can be overridden by environment for tests.
2. **Boundary check** `scripts/check-collaboration-boundary.py`
   - Reads the owned list, scans the scope in assumption 2, and fails (exit 1) listing `path:line: name` for every
     forbidden reference from interface §11 plus assumption 7.
   - Also fails when an owned-list path does not exist (a stale list would silently widen the exemption).
   - Wired into `validate.sh` next to the other `scripts/check-*.py` checks; its own regression goes into
     `scripts/test-checkers.sh` (a planted violation in each forbidden class turns it red; an owned file and the
     words "协作信箱", "mailbox", "agent-relay" do not).
3. **Coupling points cut** (interface §11 table)
   - W1 per decision D3; the skill text tells the agent to run the probe first.
   - W2–W4 reworded to "the agent-relay mailbox", no internal names.
   - W5 `validate.sh` calls the owned runner (assumption 5) instead of the thirteen lines.
   - W6 the session-delegation assertions in `test_skill_entrypoints.py` move into an owned test file.
   - W8 the `defect_guard.py:17` comment no longer names a delegation module.
   - C3 per assumption 4.
   - W7, C1, C2 are not in this module: W7 belongs to `collaboration-dependency`; C1 and C2 are agent-relay's
     side and happen in `collaboration-extraction`.
4. **Interface document** updated only where D4 and assumption 7 change §11; nothing else.

## Commands

```bash
python3 -B plugins/spec-guard/hooks/agent_relay_probe.py --host claude
python3 -B plugins/spec-guard/hooks/test_agent_relay_probe.py
python3 scripts/check-collaboration-boundary.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Project structure

New:
- `plugins/spec-guard/hooks/agent_relay_probe.py`, `test_agent_relay_probe.py` — stay in Spec Guard.
- `scripts/check-collaboration-boundary.py` and its owned-list file — stay in Spec Guard.
- Owned (move later): the collaboration test runner, the host-config collaboration test (C3), the
  session-delegation entrypoint test (W6).

Changed: `skills/ticket/SKILL.md`, `skills/local-ticket-ledger-ops/SKILL.md`, `commands/local-ticket-ledger.md`,
`commands/proposal-closeout.md`, `hooks/defect_guard.py`, `hooks/test_host_config_removal.py`,
`hooks/test_skill_entrypoints.py`, `scripts/validate.sh`, `scripts/test-checkers.sh`, and
`docs/collaboration-interface.md` §11 (D4, assumption 7).

## Testing strategy

- Probe: unit tests with a fake Claude home and a fake `codex` binary for every state, including disabled
  plugin, interface `0.9` and `2.0`, missing `interface.json`, malformed record, and `codex` timeout →
  `unknown`; one test asserts the probe writes no file.
- Boundary check: planted-violation regression per forbidden class, plus the clean repository passing.
- Baseline comparison: `validate.sh`, `test-phase-guard.sh` (151), `test-verify-artifacts.sh` (26) pass; the
  collaboration test total stays 190 plus the moved cases, shared `test_host_config_removal.py` and
  `test_skill_entrypoints.py` totals drop by exactly the moved cases. Any other difference is listed and needs
  approval.

## Boundaries

- Always: keep collaboration behavior identical to the baseline except D3; keep the probe read-only and
  offline; keep the owned list the single source for both the check and extraction.
- Ask first: widening the check scope, adding an allow-list entry, changing interface §11-12 beyond D4 and
  assumption 7.
- Never: move or delete collaboration code; make any workflow command, hook, or phase injection depend on the
  probe; report a failed probe as `not-installed`.

## Success criteria

1. The probe returns the right state in every unit case and `not-installed` on this Mac today.
2. `check-collaboration-boundary.py` passes on the repository and fails on each planted violation.
3. No file outside the owned list (within the scope) references a collaboration internal.
4. The three baseline suites pass and the test-count comparison matches the testing strategy.

## Open questions

None; D3 and D4 are decided.
