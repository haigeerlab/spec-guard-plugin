# Spec: map-read-failure

## Objective

Report a capability map that exists but cannot be read as a read failure, never as a state of the map. Findings F4
and F11 of the [2026-10-08 architecture audit](../docs/reports/2026-10-08-architecture-audit.md):

1. **F4.** With `spec/CAPABILITY-MAP.md` unreadable (for example mode 000), the result depends on whether module specs
   exist. Without specs the phase hint says `MAP_ONLY`, silent about the read error. With specs it says a generic
   `UNKNOWN` and sends the user to `verify-artifacts`, which then fails with "能力图无效: [Errno 13] Permission
   denied" — an environment fault reported as invalid map content.
2. **F11.** `phase-guard.sh` builds its JSON through `python3 -c`. When `python3` is on `PATH` but cannot run, the hook
   prints nothing, which looks exactly like "spec-guard is not enabled here".

Readers: Spec Guard users; maintainers of `phase-guard.sh`, `module_stage.py`, `capability-map.py` and
`verify-artifacts.sh`.

## Assumptions

Confirmed by the user on 2026-10-08:

1. Only operating-system read errors (`OSError`: permission denied, file vanished, path is a directory) count as a
   read failure. A readable file that is not UTF-8 stays "invalid map", because that is a content problem.
2. `capability-map.py` adds `"kind": "unreadable"` to its failure JSON for a read failure and exits with a distinct
   code; `verify-artifacts` reports it as "未验证：能力图读取失败（<error>）" instead of failing.
3. Phase hint: with module specs, `module_stage.describe` catches the read error and reports `UNKNOWN` with
   "Capability map: present but unreadable (<error>)"; without module specs, `phase-guard.sh` checks readability in
   bash before the `MAP_ONLY` branch and reports the same `UNKNOWN`. Error text is sanitised as phase context is.
4. F11: when `emit` fails, the hook prints a fixed, hand-written JSON message, as the existing "python3 missing"
   message does, instead of nothing.
5. Version 0.52.3.

## Requirements

1. `capability-map.py`: an `OSError` while reading gives `{"ok": false, "kind": "unreadable", "error": ...}` and exit
   code 2; `MapError` and `UnicodeError` keep `{"ok": false, "error": ...}` and exit code 1. Success output and exit
   code are unchanged.
2. `verify-artifacts.sh`: an unreadable map gives a `warn` "未验证：能力图读取失败（<error>）" and the existing note that
   module specs were not checked; it adds no `bad` line, so it does not fail on its own account. Invalid content
   still gives `bad "能力图无效: …"`.
3. `module_stage.describe`: an `OSError` from reading the map returns `当前阶段: **UNKNOWN**` with
   `- Capability map: present but unreadable (<safe_fragment(error)>)` and a next step to check the file's
   permissions and rerun. A `UnicodeError` is reported as `MAP_INVALID`, consistent with assumption 1 (today it falls
   through to the generic `UNKNOWN`).
4. `phase-guard.sh`: when `spec/CAPABILITY-MAP.md` exists but is not readable, the hook reports the same `UNKNOWN`
   unreadable message whether or not module specs exist; it never reports `MAP_ONLY` or `IDLE` for an unreadable map.
5. `phase-guard.sh`: when the `emit` pipeline fails or prints nothing, the hook prints a fixed valid JSON message
   saying python3 could not run, there is no phase injection this turn, and this is not "not enabled".
6. Readable maps: parsing, stage judgement and all existing phase and verify outputs are unchanged.
7. Regressions, run on `/bin/bash` 3.2 in temporary projects:
   - mode-000 map with and without module specs, for both phase-guard and verify-artifacts (skipped with a note when
     running as root, where mode 000 is still readable);
   - a map path that is a directory;
   - a non-UTF-8 map stays invalid in both;
   - a `python3` stub on `PATH` that passes `command -v` but exits 1 gives a non-empty valid JSON from the hook;
   - unit tests for `capability-map.py` exit codes and for `describe`.
   Each new assertion is shown to go red by breaking the code by hand.
8. CHANGELOG 0.52.3; both manifests and README `--ref`; release per `docs/release-process.md`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Boundaries

- Always: `bash` / `git` / `python3` only; temporary projects in tests; hook output is JSON.
- Ask first: push, PR, tag, release.
- Never: change judgement for readable maps; report a read failure as invalid content or as a missing map; add a
  dependency (the `grep` dependency, F12, stays in a later group).

## Success criteria

1. An unreadable map is reported as a read failure in both the phase hint and `verify-artifacts`, independent of the
   number of module specs.
2. A hook whose `python3` cannot run still prints a diagnosable JSON message.
3. Existing phase and verify suites unchanged.

## Open questions

None.
