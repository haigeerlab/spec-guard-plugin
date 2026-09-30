# Proposal promotion proof

`prove(project, publication, review_result, remote="origin")` proves a Proposal
module's first matching inclusion in the remote default branch. It accepts a fresh
v2 `published` Publication whose Issue stage is `proposal-stage:accepted` or
`proposal-stage:promoted` (so the proof can be rerun after the promoted label is
applied). Acceptance is that Issue label plus a fresh review; no mainline policy or
acceptance attestation is read.

The function observes a newly fixed, temporary bare Git snapshot. It walks the
remote default branch's first-parent history from the Proposal's baseline commit
toward the snapshot tip and finds the first commit C whose capability map contains
the proposed module; P is C's first parent. The result is `invalid` when P already
contains the module, when C's row, dependencies or build-order position differ from
the Proposal, or when any other module row (or the order of the other modules)
changed between P and C. Freshness (baseline not drifted, module not yet present,
dependencies present, anchor valid) is judged on P's map, not the current one, and a
non-fresh P returns `stale` with the review diagnostic. Otherwise the result is
`proved` with `reviewCommit` = P and `promotionCommit` = C. A normal merge therefore
proves the merge commit, never an already-merged feature-branch commit. The
promotion commit may touch any other paths (a PR merge commit carries the whole PR);
it is not required to carry the module Spec or Plan. When no commit yet contains the
module, `prove` returns `not-promoted`: merge the promotion branch into the remote
default branch, then rerun.

`proposal_promotion_proof.py --prove` (and `/spec-guard:proposal-promotion-proof`)
first re-establishes the pool and Issue stage from the same fresh snapshot, then runs
`prove`. A missing Proposal returns `absent`; an unreadable or invalid pool returns
`unknown` or `invalid`.

A promoted Proposal excluded from the pool (see
[proposal-publication.md](proposal-publication.md#pool-reading-and-isolated-proposals))
is queried as not in the pool: preflight returns `absent` / `publication-absent` and
`--prove` returns `absent`. Preflight and proof JSON add
`"skippedProposals": [{"proposalId": ..., "diagnostic": ...}]` only when at least one
Proposal was excluded; otherwise the output is unchanged. `diagnostic` is one of
`proposal-baseline-remote-mismatch`, `proposal-baseline-unavailable` or
`proposal-invalid`; raw errors are never emitted.

The preflight function rereads the remote Proposal pool and the Issue stage, runs a
fresh review against the observed remote-default commit, and returns a ready base
commit only when the stage is `proposal-stage:accepted` and the review is fresh. If
the baseline has drifted it returns `stale` with the review diagnostic (for example
`proposal-baseline-drifted`). It is a read-only prerequisite for a human-created
promotion branch; it does not create that branch or update any tracker stage.

It never reads a consumer worktree capability map as a shared fact and never creates
or updates a commit, branch, PR, Issue, label, task, Proposal, capability map or
`.agent/state.json`. It does not invoke `spec-github-bridge` or `/sync-map`.

`as_json(proof_result)` and `preflight_as_json(preflight_result)` expose only state,
stable proof identifiers and a stable diagnostic code. They omit remote URLs,
capability-map text, Proposal/Issue bodies, temporary paths and raw transport
errors. `unknown`, `invalid`, `stale`, `not-accepted`, and `not-promoted` are not promotion
proof.

Both functions pass through the lower layer's own diagnostic when it is a stable
code. Only a missing or non-code diagnostic
falls back to a generic `promotion-preflight-<state>` / `promotion-<state>`
string, so a missing tracker Issue, a missing Proposal and a stale review are distinguishable even though their `state` can coincide:

| Cause | Diagnostic |
| --- | --- |
| The remote Proposal pool snapshot could not be read or does not parse | `proposal-pool-unknown` / `proposal-pool-invalid` |
| The Proposal is not in the published pool | `publication-absent` |
| The review finds the Proposal stale (baseline drifted, and so on) | the review's diagnostic, such as `proposal-baseline-drifted`; fallback `promotion-stale` |
| No tracker Issue carries the Proposal's marker | `tracker-absent` |
| The tracker Issue or its labels fail the tracker contract | `tracker-invalid` |

Two rejections of the promotion commit C carry their own code, both with `state`
`invalid` and `promotionCommit` = C (checked in this order, after P is found not to
contain the module):

| Cause | Diagnostic | Extra field |
| --- | --- | --- |
| C's row differs from the Proposal declaration | `promotion-row-mismatch` | `mismatchedFields`: the differing subset of `responsibility`, `dependsOn`, `position`, always in that order |
| The row matches, but C also changed another module's row or the order of the other modules | `promotion-other-rows-changed` | none |

`responsibility` is a different responsibility text, `dependsOn` a different
dependency list (order matters), `position` a build-order position that does not
satisfy the anchor (`end` must be last, `after:<id>` must immediately follow `<id>`).
The field list comes from the same function `add-module --proposal` uses for its
self-check, so the two cannot disagree.

Every other `invalid` case (P already contains the module, unreadable maps, baseline
not an ancestor, and so on) and a diagnostic that names neither a layer nor a
specific cause (Git plumbing failures inside `prove`, for example) keep the generic
`promotion-<state>` /
`promotion-preflight-<state>` form; only `not-promoted` keeps its own fixed
`promotion-not-found`.

`add-module --proposal` runs this same preflight (through `promotion_base`) before inserting, so the standalone preflight is an optional read-only preview.
