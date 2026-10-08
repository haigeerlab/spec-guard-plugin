# Plan: remote-credential-redaction

Based on [`spec/remote-credential-redaction.md`](../../spec/remote-credential-redaction.md) (assumptions confirmed by
the user on 2026-10-08). Branch `claude/remote-credential-redaction`.

## Task List

### Task 1: ledger preflight redacts the origin (tests first)

`redact_url` unit tests (userinfo with password, token-as-user, scp-style, no userinfo, malformed) and preflight tests
(both states, fake `SECRET` never in the JSON, `originCredentialsRedacted` only when redacted), red; then the helper
and `initialization_preflight`, green. Mutation: drop the redaction call.

### Checkpoint 1 (report): tests green

### Task 2: Proposal snapshot keeps the URL out of argv (tests first)

Capture every `git` argv `proposal_publication.py` runs with a fake credential remote: none contains the URL or
`SECRET`; a real local-file remote still snapshots to the same commit; existing failure-outcome tests unchanged. Red,
then `ls-remote` by remote name with `-C <project>` and `fetch` through a remote written into the temporary
repository's config. Mutation: pass the URL again.

### Checkpoint 2 (report): full suites green

### Task 3: CHANGELOG + 0.52.1 + macOS validation

CHANGELOG; both manifests and README `--ref`; validate.sh, phase-guard, verify-artifacts, Codex smoke selftest,
ShellCheck.

### Checkpoint 3 (gate): module review

Approving this Plan also authorizes pushing this branch and opening this module's PR. Merging stays with the user.

### Task 4: post-release evidence

Release per `docs/release-process.md`; on both installed copies a fake-credential origin is redacted in preflight and
the snapshot argv carries no URL.
