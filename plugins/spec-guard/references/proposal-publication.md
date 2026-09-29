# Proposal publication

Publication reads one Proposal only from an explicit Git remote's current default branch. It uses a temporary bare snapshot and returns JSON; it never reads a local Proposal or capability map as shared fact, and it never calls a tracker API.

```bash
python3 -B plugins/spec-guard/hooks/proposal_publication.py \
  --project . --proposal-id example-proposal --remote origin
```

The response contains `state` and, when known, `reviewCommit`. A `published` result also names `proposalId` and `baselineCommit`. It deliberately omits remote URLs, temporary paths and document/map contents.

- `published`: the fixed remote-default snapshot and Proposal contract both validate.
- `absent`: the Proposal path is not on that snapshot.
- `invalid`: a found Proposal or its provenance is invalid.
- `unknown`: remote observation could not safely complete; this is not a successful remote verification.

Publication does not read GitHub/GitLab Issues. Tracker marker and stage validation belongs to `proposal-tracker-read`.

## Pool reading and isolated Proposals

`read_published_pool` reads every Proposal in the snapshot. One already-promoted Proposal
that has gone stale must not block the rest of the pool, so it is excluded instead of
invalidating the pool, and only when all of these hold:

- it parses;
- its declared `Module id` is already in the remote default-branch capability map (it has been promoted); and
- its baseline check (remote/default branch mismatch, baseline commit not on the default
  branch, or its baseline map missing) or validation fails.

A typical cause is a repository migration after which a long-promoted historical
Proposal's baseline commit no longer exists.

Everything else is unchanged: parse failures, failures of a Proposal not yet promoted,
duplicate ids, a missing or invalid capability map and the pool size limit still make the
pool invalid or unknown. Healthy promoted Proposals stay in the pool. The pool never reads a mainline policy file
or acceptance records: every publication's `review_commit` is the observed remote-default
commit. An excluded Proposal is reported in the pool's `skipped` list; querying it by id behaves as if it were not
in the pool.

`read_published` (one Proposal, used by `/spec-guard:proposal-review`) is not affected: it
still reports such a Proposal as `invalid`, which is how to see the full reason.
