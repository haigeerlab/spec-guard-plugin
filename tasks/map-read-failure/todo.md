# Todo: map-read-failure

- [x] Task 1: `capability-map.py` + `verify-artifacts` (tests first) — `capability-map.py` reports an `OSError` as `kind: unreadable`, exit 2; `MapError`/`UnicodeError` keep exit 1. `verify-artifacts` treats any existing map path as present and warns "未验证：能力图读取失败（…）" with no failure. 4 new cases (mode 000 x2, directory, non-UTF-8) red then green, suite 30. Mutations caught: OSError merged back into content errors (2 failures), unreadable reported with `bad` (1 failure)
- [ ] Task 2: phase hint for an unreadable map (tests first)
- [ ] Task 3: hook JSON when python3 cannot run (F11, tests first)
- [ ] Checkpoint 1 (report): full suites green, ShellCheck clean
- [ ] Task 4: CHANGELOG + 0.52.3 + macOS validation
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 5: post-release evidence
