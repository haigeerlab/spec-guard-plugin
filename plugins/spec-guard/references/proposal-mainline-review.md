# Proposal mainline review

The evaluate function is a pure policy boundary. It has no transport or write
capability: it cannot update an Issue, capability map, branch, or task.

Only a v2 Proposal in a context whose authority, branch, upstream and workflow
exactly match the supplied single-mainline policy may produce an
accepted-candidate. The caller must supply an explicit accept, needs-revision,
defer, or reject decision. Published status by itself never selects a decision.

Local observations are deliberately restricted to a kind and nonempty module-id
list. Package-boundary, public-contract and anchor conflicts always return
needs-revision, even when the supplied decision is accept. The result carries only
stable identifiers and reason codes; observations are not promoted to shared facts.

The pool-facing entry first parses the policy and attestation stored in the same
remote-default snapshot as the Proposal pool. It then reads only the current
worktree's branch, upstream and ancestor relation to that snapshot. Callers provide
only authority id, explicit boundary and current module id; supplied branch or HEAD
text is never accepted as authority evidence.

The CLI reports the first failing layer with a stable diagnostic code and never
free text or raw errors:

| State | Diagnostic | Meaning |
| --- | --- | --- |
| unknown / invalid | `proposal-pool-unknown` / `proposal-pool-invalid` | The remote-default snapshot could not be read or does not parse; no Git context was evaluated. |
| blocked | `mainline-policy-invalid` | The snapshot has no valid mainline policy. |
| blocked | `mainline-authority-mismatch` | The supplied authority id differs from the policy. |
| blocked | `mainline-branch-unavailable` | Detached HEAD or no upstream. |
| blocked | `mainline-context-invalid` | Branch, upstream or workflow does not match the policy. |
| blocked | `mainline-review-commit-not-ancestor` | Local HEAD does not contain the remote review commit; update the mainline first. |
| blocked | `mainline-topology-unavailable` | Git could not evaluate ancestry. |
| invalid | `proposal-not-published` | The requested Proposal id is not in the snapshot. |

A candidate list also carries `skipped`: each published Proposal that is not a
candidate, with `legacy-revision-required` or `review-<state>` (for example
`review-absent` when no Proposal Issue exists). An empty candidate list therefore
still says what was seen.

## The accepted-candidate attestation

When `evaluate` returns `accepted-candidate`, its JSON additionally carries an
`attestation` object and an `attestationPath` string. No other state carries them.
The command still writes no file: a human copies `attestation`, verbatim, into a new
file at `attestationPath` on the protected mainline after deciding to accept.

`attestation` has exactly seven fields:

| Field | Value |
| --- | --- |
| `schemaVersion` | Always `1`. |
| `proposalId` | The Proposal's id, from the reviewed Proposal document. |
| `revision` | The Proposal's `revision` (the SHA-256 of its document content, from its identity comment). |
| `reviewCommit` | The remote-default commit `evaluate` reviewed the Proposal against. |
| `policyDigest` | `policy_digest(policy)`: the SHA-256 hex digest of the mainline policy, encoded with `json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`. Any change to the policy file (`spec/proposal-mainline-policy.json`) changes this digest, so an attestation silently stops matching a policy it was not written against. |
| `authorityId` | The policy's `authorityId` (for example `mainline`). |
| `decision` | Always `"accept"`; this attestation only ever records an accept. |

`attestationPath` is `spec/proposal-acceptances/<proposalId>-<revision>.json` — the
exact relative path `read_published_pool` (in `proposal_publication.py`) reads an
acceptance attestation from for that Proposal.

This file is written by a human, on the protected mainline branch, only after they
have decided to accept the Proposal — never by a command. Once it lands on the
default branch, it must never be edited or deleted: `scripts/check-acceptance-immutable.py`
enforces this by rejecting a promotion or push that changes or removes an existing
attestation file's content.
