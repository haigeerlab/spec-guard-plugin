# Todo: remote-credential-redaction

- [x] Task 1: ledger preflight redacts the origin (tests first) — `local_ledger_runtime.redact_url` replaces a scheme URL's userinfo with `***` (user:token@, token@, ssh with port); scp-style, path-only, file://, `@` in the path, empty and malformed strings unchanged. preflight reports the redacted origin in both states plus `originCredentialsRedacted: true` only when it redacted. 4 new tests red (2 failures, 10 errors) then green; mutation skipping the redaction caught (2 failures)
- [x] Checkpoint 1 (report): tests green
- [ ] Task 2: Proposal snapshot keeps the URL out of argv (tests first)
- [ ] Checkpoint 2 (report): full suites green
- [ ] Task 3: CHANGELOG + 0.52.1 + macOS validation
- [ ] Checkpoint 3 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 4: post-release evidence
