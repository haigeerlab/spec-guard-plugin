# Todo: checker-hardening

- [x] Task 1: command bootstrap for every non-exempt command (F7) — `evals/test-codex-command-roots.sh` drops the `users < 15` floor: every command not in `EXEMPT` (setup/teardown-convention, ticket, local-ticket-portability, each with a reason) must carry the verbatim bootstrap before its first `$ROOT`; a missing exempted name and zero command files fail. Before the change, stripping cost-report.md of its whole bootstrap stayed green; after, it is red. Mutations caught: bootstrap removed (1 line), exemption for a non-existent command (1 line)
- [ ] Task 2: flag parity and the ledger initialize command (F8)
- [ ] Task 3: separator-row negative test (F9)
- [ ] Task 4: grader propagates hidden-test failure (F10)
- [ ] Task 5: single fingerprint implementation checker (F13)
- [ ] Task 6: ShellCheck covers eval subdirectories (F19)
- [ ] Checkpoint 1 (report): full suites green, ShellCheck clean
- [ ] Task 7: CHANGELOG under `## [未发布]` + macOS validation
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
