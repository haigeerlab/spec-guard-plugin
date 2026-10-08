# Todo: unattended-long-first-record

- [x] Task 1: regressions (red first) — two `Unattended` cases: a ~100 KB `session_meta` first record with source "exec" is unattended; a complete JSON record padded past 1 MB (its first 1 MB parses on its own) is attended. Both red on the 64 KB code — the second because a truncated read that still parsed counted as unattended
- [x] Task 2: raise the first-record limit to 1 MB — `FIRST_RECORD_LIMIT = 1 << 20`; a first read without a line end (cut at the limit, or a file with no newline) counts as attended. session_context 47, phase-guard 175. Mutations caught: limit back to 64 KB (100 KB case red), line-end check removed (over-1 MB case red)
- [x] Checkpoint 1 (report): full suites green, ShellCheck clean — validate.sh pass, session_context 47, phase-guard 175, verify-artifacts 31, CI ShellCheck glob clean
- [x] Task 3: CHANGELOG under `## [未发布]` + macOS validation — added to the unattended entry under `## [未发布]` / 修复. macOS 15.7.3, `/bin/bash` 3.2.57: validate.sh pass
- [x] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user — branch pushed and the module PR opened for the user's review; ticked inside the PR (combined release)
