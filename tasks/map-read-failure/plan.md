# Plan: map-read-failure

Based on [`spec/map-read-failure.md`](../../spec/map-read-failure.md) (assumptions confirmed by the user on
2026-10-08). Branch `claude/map-read-failure`.

## Task List

### Task 1: `capability-map.py` + `verify-artifacts` (tests first)

Regressions in `test-verify-artifacts.sh`: mode-000 map (skipped as root) and a directory at the map path give a
"未验证：能力图读取失败" warning and no failure; a non-UTF-8 map still fails as invalid. Red, then split `OSError`
(`kind: unreadable`, exit 2) from `MapError`/`UnicodeError` (exit 1) and map it in `verify-artifacts.sh`, green.
Mutations: catch `OSError` with the content errors again; report the unreadable case with `bad`.

### Task 2: phase hint for an unreadable map (tests first)

Regressions in `test-phase-guard.sh`: mode-000 map with and without module specs and a directory map all report
`UNKNOWN` with "present but unreadable", never `MAP_ONLY`/`IDLE`; a non-UTF-8 map reports `MAP_INVALID`; unit test for
`describe`. Red, then `describe` catches `OSError` (sanitised) and `UnicodeError`, and `phase-guard.sh` checks
readability before the `MAP_ONLY` branch, green. Mutations: drop the bash readability check; drop the `OSError`
branch in `describe`.

### Task 3: hook JSON when python3 cannot run (F11, tests first)

Regression: a `python3` stub on `PATH` that exits 1 gives a non-empty valid JSON naming the fault. Red, then a fixed
fallback message when `emit` fails or prints nothing, green. Mutation: remove the fallback.

### Checkpoint 1 (report): full suites green, ShellCheck clean

### Task 4: CHANGELOG + 0.52.3 + macOS validation

### Checkpoint 2 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.

### Task 5: post-release evidence

Release per `docs/release-process.md`; on both installed copies a mode-000 map reports the read failure in the phase
hint and `verify-artifacts`.
