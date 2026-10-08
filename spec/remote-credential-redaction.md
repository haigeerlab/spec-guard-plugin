# Spec: remote-credential-redaction

## Objective

Keep credentials that a user embedded in a Git remote URL (`https://user:token@host/...`, or a token in the user
position) out of Spec Guard's output and out of process arguments. Findings F1 and F2 of the
[2026-10-08 architecture audit](../docs/reports/2026-10-08-architecture-audit.md):

1. **F1.** `local_ledger_runtime.py preflight --format json` reports `origin` verbatim, so a credential-bearing origin
   is printed into the terminal and the agent's context.
2. **F2.** `proposal_publication.py` reads the remote URL with `git remote get-url` and passes it to `git ls-remote`
   and `git fetch` as an argument, where any local process listing can read it.

Readers: Spec Guard users whose remotes carry credentials; maintainers of the ledger and Proposal readers.

## Assumptions

Confirmed by the user on 2026-10-08:

1. Only URLs with a scheme (`scheme://userinfo@host...`) are redacted; the whole userinfo becomes `***`
   (`https://***@host/...`), because some tokens sit in the user position. scp-style `user@host:path` is left as is.
   When something was redacted, the result says so (`originCredentialsRedacted: true`).
2. The ledger's push-confirmation judgement is unchanged.
3. The snapshot lists the remote head by remote name in the project (`git -C <project> ls-remote --symref <remote>
   HEAD`), and fetches in its private temporary bare repository through a remote whose URL is written into that
   repository's config file by Python, never passed on a command line. The temporary directory stays owner-only and
   is removed as today.
4. Only F1 and F2: the audit found no token in `gh`/`glab` argv or URLs.
5. Version 0.52.1.

## Requirements

1. `redact_url(url)` (in one shared place, used by the ledger) replaces the userinfo of a scheme URL with `***` and
   leaves every other string unchanged; malformed input is returned unchanged, never raises.
2. `preflight` (both `push-confirmation-required` and `ready`) reports the redacted origin and
   `originCredentialsRedacted: true` only when it redacted something; the state is the same as before for every input.
3. No `git` argv built by `proposal_publication.py` contains the remote URL; `ls-remote` uses the remote name with
   `-C <project>`, `fetch` uses a configured remote name in the temporary repository.
4. Snapshot behaviour is unchanged: the same head, the same fetched commit, and the same `HEAD_UNAVAILABLE` /
   `FETCH_FAILED` / `TIP_MOVED` outcomes for the existing fixtures.
5. Regressions: a fake credential (`https://user:SECRET@example.invalid/repo.git` and `https://SECRET@…`) never
   appears in preflight output or in any captured `git` argv; scp-style and credential-free URLs are unchanged; a real
   local-file remote still snapshots. Each new assertion is shown to go red by breaking the code by hand.
6. CHANGELOG 0.52.1; both manifests and README `--ref`; release per `docs/release-process.md`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_local_ledger_runtime.py
python3 -B plugins/spec-guard/hooks/test_proposal_publication.py
```

## Boundaries

- Always: `bash` / `git` / `python3` only; use fake credentials and temporary repositories in tests.
- Ask first: push, PR, tag, release.
- Never: read, print or log a real credential; change the user's Git config; change ledger or Proposal judgement.

## Success criteria

1. A credential-bearing origin is never printed by the ledger preflight.
2. No Proposal snapshot `git` process carries the remote URL in its arguments.
3. Existing ledger and Proposal behaviour and suites unchanged.

## Open questions

None.
