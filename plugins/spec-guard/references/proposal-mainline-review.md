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
