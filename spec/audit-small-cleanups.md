# Spec: audit-small-cleanups

## Objective

Close the small findings of the [2026-10-08 architecture audit](../docs/reports/2026-10-08-architecture-audit.md)
(group 7) without changing behaviour:

1. **F12.** `phase-guard.sh` uses `grep` for its three activation checks, so the invariant "depends only on `bash`,
   `git` and `python3`" is not literally true; without `grep` an activated project exits silently.
2. **F15.** Eleven `local_ticket_*` modules import `InventoryError` and inventory helpers from the top-level CLI
   `local_ticket_portability.py`, which in turn imports them: an import cycle.
3. **F16.** The module id pattern is defined twice (`capability_map.py`, `documentation_impact.py`), and "current
   module" selection is implemented twice (`module_stage.project_stage`, `module-insert.py` `_current_module`).
4. **F17.** `host_config_removal.remove_codex_table` and `remove_claude_server` are called only by their tests since
   collaboration moved out.
5. **F18.** The `docs/workflow.md` command table lacks `cost-report` and `local-ticket-portability`.

Readers: maintainers.

## Assumptions

Confirmed by the user on 2026-10-08:

1. F12: the three checks use bash built-ins (line-by-line read and `[[ =~ ]]`), bash 3.2 compatible, with the same
   judgement — the marker alone on its line with surrounding whitespace; the `"activeModule"` key anywhere. The
   invariant text stays as is, because it becomes true.
2. F15: the inventory code (`InventoryError`, `inventory_project`, `worktree_roots`, `_event_lines` and their helpers)
   moves to `local_ticket_inventory.py`; the ticket modules import from there; `local_ticket_portability` keeps
   re-exporting those names so existing imports keep working.
3. F16: `documentation_impact.py` imports `MODULE_ID` from `capability_map`; `module-insert.py` selects the current
   module through `module_stage.project_stage`.
4. F17: delete the two helpers and their tests; keep `add_claude_server` (used by the ledger adapters).
5. F18: add the two rows.
6. No release of its own (combined release); CHANGELOG under `## [未发布]`.
7. Forwarded by the user through 第二轮联调 after #249: the Markdown link to the collaboration Spec in
   `docs/reports/2026-10-03-audit-reconciliation.md` broke when `collaboration-map-retirement` archived it; it points
   to `docs/retirements/collaboration-messaging/spec.md`. Plain-text mentions of old paths in other history documents
   stay as written. There is no link checker in the repository and none is added here.

## Requirements

1. `phase-guard.sh` contains no `grep`; with a `PATH` that has `bash`, `git` and `python3` but no `grep`, an activated
   project gets its phase injection and an unrelated project stays silent. Existing activation cases (marker in prose,
   CRLF block, nested `activeModule`, other tools' state files) are unchanged.
2. No `local_ticket_*` module other than the CLI's own tests imports from `local_ticket_portability`; importing each
   ticket module in a fresh interpreter does not import `local_ticket_portability`. A regression enforces both.
3. `documentation_impact.py` defines no module id pattern of its own; `module-insert.py` has no `_current_module`
   selection logic of its own. Existing suites unchanged.
4. `remove_codex_table` and `remove_claude_server` no longer exist; nothing references them.
5. The workflow table has one row per command in `plugins/spec-guard/commands/` (a check enforces it).
6. The 2026-10-03 reconciliation report's link to the collaboration Spec resolves to the archived file.
7. Each new assertion is shown to go red by breaking the code by hand. CHANGELOG entry under `## [未发布]`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_local_ticket_portability.py
python3 -B plugins/spec-guard/hooks/test_module_insert.py
```

## Boundaries

- Always: `bash` / `git` / `python3` only; bash 3.2.
- Ask first: push, PR.
- Never: change activation, ticket, documentation-impact or module-insert judgement.

## Success criteria

1. The phase hook's dependency invariant is literally true.
2. No import cycle between the ticket modules and the CLI.
3. One module id pattern and one current-module selection.
4. No dead host-config helpers; the command table is complete.

## Open questions

None.
