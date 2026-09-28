# Proposal promotion proof

`prove(project, publication, review_result, remote="origin")` proves a Proposal
module's first matching inclusion in the remote default branch. It accepts only a
fresh v2 `published` Publication and an `accepted` mainline result with matching
Proposal revision, review-commit and authority identities. A tracker accepted label
alone is not sufficient.

The function observes a newly fixed, temporary bare Git snapshot. It walks the
remote default branch's first-parent history from the review commit toward the
snapshot tip and returns `proved` only when the first map containing the proposed
module has a first parent without that module and exactly matches the Proposal's
responsibility, dependencies and build-order anchor. A normal merge therefore proves
the merge commit, never an already-merged feature-branch commit. The promotion diff
must contain only the capability map, module Spec and module Plan, and both artifacts
must be present; it may additionally include the module's `tasks/<id>/todo.md`, which
is optional and never required. When no commit yet contains the module, `prove`
returns `not-promoted`: merge the promotion branch into the remote default branch,
then rerun.

`proposal_promotion_proof.py --prove` (and `/spec-guard:proposal-promotion-proof`)
first re-establishes acceptance from the same fresh snapshot, the current Issue stage
and the revision-addressed attestation, then runs `prove`. A missing Proposal returns
`absent`; an unreadable or invalid pool returns `unknown` or `invalid`.

The preflight function rereads the remote Proposal pool, policy and
revision-addressed attestation before it returns a ready base commit. It is a
read-only prerequisite for a human-created promotion branch; it does not create
that branch or update any tracker stage.

It never reads a consumer worktree capability map as a shared fact and never creates
or updates a commit, branch, PR, Issue, label, task, Proposal, capability map or
`.agent/state.json`. It does not invoke `spec-github-bridge` or `/sync-map`.

`as_json(proof_result)` exposes only state and stable proof identifiers. It omits
remote URLs, capability-map text, Proposal/Issue bodies, temporary paths and raw
transport errors. `unknown`, `invalid`, `not-accepted`, and `not-promoted` are not
promotion proof.
