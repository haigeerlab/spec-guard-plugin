> Superseded: the mainline review layer was retired; see [the retirement note](../retirements/proposal-mainline-review.md).

# Proposal v2 mainline-review migration

Existing published v1 Proposals remain readable from the remote default branch and
their matching Proposal Issues remain untouched. They are not silently upgraded,
discarded, accepted, or promoted.

To bring a still-relevant v1 Proposal forward, a human creates a new v2 revision on
the remote default branch with the required Integration intent and revision marker.
The matching Issue must carry that exact complete marker. The mainline then reviews
the v2 revision at an explicit module boundary. Any accepted label associated with
the old v1 document is not transferable.

The protected mainline process records the immutable acceptance attestation only
after an explicit human accept decision. It separately updates the one Proposal
Issue stage. Promotion preflight rereads all current remote facts before a human
creates a promotion branch.

No migration reads another worktree, restores old tracker mappings, or writes Issue,
branch, capability-map, task, or attestation data automatically.
