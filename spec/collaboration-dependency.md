# Spec: collaboration-dependency

## Objective

Finish Spec Guard's side of the collaboration split: delete the collaboration code that now lives in agent-relay,
keep `/spec-guard:collaboration` for one to two releases as a handoff to agent-relay, publish the migration
document, and make every user-facing description say that collaboration is a separate plugin. After this module
Spec Guard has no collaboration implementation; its only contact with collaboration is `agent_relay_probe.py` and
agent-relay skill names (interface §11–§12).

Readers: the user reviewing the split; Spec Guard users who used the built-in collaboration.

Sources: [the split brief](../docs/collaboration-split-brief.md) §1.1 item 4 and phase 4.2;
[the interface document](../docs/collaboration-interface.md) §11–§13 (agent-relay's copy is now authoritative);
[`spec/collaboration-boundary.md`](collaboration-boundary.md) (owned list, W7 deferred here);
agent-relay `README.md` and `state_migration.py` (the migration commands users run).

## Assumptions

Confirmed by the user on 2026-10-07:

1. **Delete exactly the owned list** in `scripts/collaboration-owned.txt` (34 paths: code, tests, the owned test
   suite, skills, references, the two extraction scripts), except `commands/collaboration.md`, which is rewritten as
   the handoff (assumption 3). `hooks/host_config_removal.py` and `hooks/defect_guard.py` stay (the ledger and closeout
   use them). Collaboration Specs, plans and records under `spec/`, `tasks/`, `docs/` stay as history.
2. **`validate.sh`** drops the collaboration suite line; nothing else in the runner changes.
3. **Handoff command.** `/spec-guard:collaboration` runs `agent_relay_probe.py --host claude`: `ready` → tells the agent to
   continue with agent-relay (`/agent-relay:collaboration`, or `agent-relay:collaboration-ops`); `runtime-not-ready` →
   relays agent-relay's setup hint; any other state → prints the probe message verbatim. It never runs collaboration
   itself. It is removed one to two releases later (a later module).
4. **Migration document** `docs/migrations/2026-10-07-collaboration-split.md`: what moved and why; install agent-relay;
   migrate old state with agent-relay's `state_migration.py detect` / `migrate --confirm` (backup first, copy-only,
   blockers explained); switch host entries (attach new through agent-relay, remove old with this Spec Guard's
   uninstall while it still exists — see assumption 6); rename permission rules; what is not migrated (retired XATS
   history). The probe's not-installed message and interface §12 get the real file name in place of `<date>`.
5. **User-facing docs (W7):** README feature table (three collaboration rows → one row "moved to agent-relay"),
   requirements line, docs table; `docs/optional-features.md` collaboration sections → a short pointer;
   `docs/workflow.md` command table row; `CLAUDE.md` purpose item 4; `docs/design.md` and `docs/concepts.md` mentions;
   both `plugin.json` descriptions drop "本机 Agent 协作邮箱". The convention block templates contain no collaboration
   text (checked), so they do not change.
6. **Removing old host entries needs the old uninstaller,** which is deleted here. Users who still have the old MCP
   entries are told to remove them before upgrading, or with an exact manual step given in the migration document
   (the old Claude entry with `claude mcp remove --scope user spec-guard-native-collaboration`; the old Codex table by
   deleting the exact `[mcp_servers.spec_guard_native_collaboration]` block). Spec Guard never edits host config here.

## Decisions

All three taken as recommended by the user on 2026-10-07.

- **D15 legacy-state guidance.** The brief asks to guide migration when old state is detected. Detecting it inside
  Spec Guard means naming the old state paths in Spec Guard code, which the boundary check forbids. Decision: no
  detection in Spec Guard; the handoff command and the probe's not-installed message always point to the migration
  document, and agent-relay's `detect` does the actual detection.
- **D16 when this reaches `main`.** Merging removes collaboration from `main` while the released version is 0.49.0, and
  Claude installs from `main` by version. The brief says the split Spec Guard is released only after integration
  round 1. Decision: build and review this module on its branch, use the branch (project-scoped install) for round
  1, and only then add the version bump and open the PR (release prep). No push before that.
- **D17 boundary check after removal.** With the owned paths gone, the check changes from "no reference outside the
  owned files" to "collaboration is gone": none of the listed paths exists, and no forbidden reference appears in the
  scope, which now also covers `README.md`, `CLAUDE.md`, `AGENTS.md`, `docs/optional-features.md`, `docs/workflow.md`.
  `/spec-guard:collaboration` leaves the forbidden list (it is the handoff command); the migration document is outside
  the scope because it must name the old paths. The two extraction scripts are deleted, not archived (git history and
  the agent-relay repository keep them).

## Requirements

1. Owned files deleted per assumption 1; `validate.sh` updated per assumption 2.
2. `commands/collaboration.md` rewritten per assumption 3, with a test (probe states → expected instruction) in a
   Spec Guard test file.
3. Migration document per assumption 4; `<date>` replaced in the probe message, its test, and interface §12.
4. W7 docs and manifests per assumption 5; `check-readme-sync` and other checkers stay green.
5. Boundary check per D17, with its regression updated (a planted reference in README fails; a path from the removed
   list reappearing fails; the handoff command passes).
6. `CHANGELOG.md` gains an `## [未发布]` entry describing the removal, the handoff command, and the migration document.
7. Baseline comparison: `validate.sh` pass, phase-guard 151, verify-artifacts 26; the test-count drop equals the
   moved suite (202) plus the removed probe-unrelated assertions, itemized in todo.md.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh
python3 scripts/check-collaboration-boundary.py
```

## Project structure

Deleted: the owned paths (assumption 1). Changed: `commands/collaboration.md`, `hooks/agent_relay_probe.py` (message),
`hooks/test_agent_relay_probe.py`, `scripts/validate.sh`, `scripts/check-collaboration-boundary.py`,
`scripts/collaboration-owned.txt` (becomes the removed-paths list), `scripts/test-checkers.sh`, the W7 docs, both
`plugin.json`, `CHANGELOG.md`, `docs/collaboration-interface.md` §12. New: `docs/migrations/2026-10-07-collaboration-split.md`.

## Testing strategy

- The three baseline suites and CI's ShellCheck pass; boundary check green with the extended scope.
- Handoff command test across probe states.
- Round 1 (brief 4.2, checklist D4–D7) runs on this branch installed at project scope.

## Boundaries

- Always: delete only listed paths; keep shared helpers; keep history records.
- Ask first: pushing, opening the PR, bumping the version; any change to phase injection or other workflows.
- Never: edit host configuration or permission files; delete history records; touch the installed guide plugin.

## Success criteria

1. No collaboration implementation left in Spec Guard; boundary check green over the extended scope.
2. `/spec-guard:collaboration` hands off or prints the guidance for every probe state.
3. Migration document published and referenced by the probe message.
4. Baseline suites green; test-count change itemized.

## Open questions

None; D15, D16 and D17 are decided.
