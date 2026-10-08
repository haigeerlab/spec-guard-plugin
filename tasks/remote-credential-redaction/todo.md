# Todo: remote-credential-redaction

- [x] Task 1: ledger preflight redacts the origin (tests first) — `local_ledger_runtime.redact_url` replaces a scheme URL's userinfo with `***` (user:token@, token@, ssh with port); scp-style, path-only, file://, `@` in the path, empty and malformed strings unchanged. preflight reports the redacted origin in both states plus `originCredentialsRedacted: true` only when it redacted. 4 new tests red (2 failures, 10 errors) then green; mutation skipping the redaction caught (2 failures)
- [x] Checkpoint 1 (report): tests green
- [x] Task 2: Proposal snapshot keeps the URL out of argv (tests first) — `_head` lists by remote name with `git -C <project> ls-remote`; the snapshot's bare repository gets a `spec-guard-source` remote written into its config file (quotes and backslashes escaped; newline or NUL in the URL fails as SNAPSHOT_FAILED) and fetches through it. New tests: a mocked `https://user:SECRET@…` remote never reaches any argv; a real local remote snapshots with its path in no argv; a remote path with spaces, quotes and backslashes still snapshots. Red (3 failures) then green; mutations putting the URL back into fetch (3 failures) or ls-remote (3 failures, 2 errors) caught. submit, promotion-proof, closeout and review suites unchanged
- [x] Checkpoint 2 (report): full suites green — validate.sh pass, phase-guard 150, verify-artifacts 26
- [ ] Task 3: CHANGELOG + 0.52.1 + macOS validation
- [ ] Checkpoint 3 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 4: post-release evidence
