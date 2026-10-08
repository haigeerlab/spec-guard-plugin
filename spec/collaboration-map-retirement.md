# Spec: collaboration-map-retirement

## Objective

Keep `spec/CAPABILITY-MAP.md` to current modules. Findings F6 and F14 of the
[2026-10-08 architecture audit](../docs/reports/2026-10-08-architecture-audit.md):

1. **F6.** Four collaboration implementation modules — `collaboration-messaging`, `collaboration-safe-defaults`,
   `authorized-session-delegation`, `host-native-session-routing` — moved to the agent-relay plugin
   ([collaboration-extraction](collaboration-extraction.md), [collaboration-dependency](collaboration-dependency.md))
   but are still rows of the current map, against AGENTS.md ("退役 Spec 与 Plan 位于 `docs/retirements/`，不加入当前
   能力图") and the precedent of [retired-module-separation](retired-module-separation.md).
2. **F14.** The `context-hint-no-paste` row still says the user runs `/spec-guard:handoff`, retired in 0.52.0; the
   retirement scan does not look at the map, so nothing caught it.

Readers: maintainers and anyone reading the capability map or phase hint of this repository.

## Assumptions

Confirmed by the user on 2026-10-08:

1. The four ids leave the module table and the Build order together, as in `retired-module-separation`.
   `audit-remediation` drops `collaboration-messaging` from its dependencies; `collaboration-interface` depends on
   nothing (`—`). No other row changes except F14. The map is edited by hand; `module-insert` only inserts.
2. Archive with `git mv`, byte-for-byte: `spec/<id>.md` -> `docs/retirements/<id>/spec.md`, and every file of
   `tasks/<id>/` -> `docs/retirements/<id>/` (including the 30 acceptance and plan records of
   `collaboration-messaging`). Links inside the archive that point at old paths stay as history. A new
   `docs/retirements/collaboration-implementation.md` says what moved, where it lives now, what replaces it, and where
   the archive is.
3. Current Specs and Plans that mention the old paths, `spec/proposals/`, `spec/history/`, `spec/CAPABILITY-HISTORY.json`
   and release evidence are not edited. The Proposal scan and review are run once to confirm the two promoted
   Proposals naming these modules do not fail because the module left the map; if they do, stop and ask the user.
4. F14: the `context-hint-no-paste` row states today's behaviour — the hint asks for one sentence suggesting
   /compact or /clear and never pasted handoff text.
5. The retirement scan also requires that the capability map contains no retired command name:
   `/spec-guard:handoff`, `spec-guard handoff`, `session_handoff`, and the legacy tracker bridge names.
6. Module count goes from 58 to 55. No release of its own (combined release); CHANGELOG under `## [未发布]`.

## Requirements

1. The map parses strictly; none of the four ids appears as a row, in the Build order or in any `Depends on`; the
   Build order still matches the table.
2. The archived files' Git blobs equal the pre-move blobs; `spec/` and `tasks/` keep no file of the four modules.
3. `verify-artifacts` reports no Spec outside the map; the phase hint counts 55 modules and reports the stage only from
   the current map.
4. `test-retire-legacy-tracker-bridge.sh` fails when the capability map names a retired command; it passes on the
   real tree after F14.
5. `proposal_closeout.py scan` and `proposal_review` on the repository give the same verdicts for the collaboration
   Proposals as before the change (or the work stops for a decision).
6. CHANGELOG entry under `## [未发布]`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/verify-artifacts.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh
```

## Boundaries

- Always: `git mv` for every archived file; byte-for-byte.
- Ask first: push, PR; anything that changes a Proposal or a history snapshot.
- Never: edit archived content, `spec/history/`, `CAPABILITY-HISTORY.json`, Proposals or release evidence; touch
  remote Issues.

## Success criteria

1. The capability map lists only current modules, and no current row describes a retired command.
2. The retirement scan would have caught F14.
3. The four modules' material stays readable, unchanged, under `docs/retirements/`.

## Open questions

None.
