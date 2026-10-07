# Proposal review

`review()` combines an already `published` remote-default Publication with an already
`verified` read-only Proposal Issue. It never queries or changes GitHub, GitLab,
Git, the capability map, Proposal files or `.agent/state.json`.

`accepted` is an observed Issue label, not promotion authorization. `promoted-claim`
is also only an observed label; run a fresh review before the later Promotion-proof
module. `stale` means the Proposal baseline, dependency or anchor facts have drifted.
`in-map` (diagnostic `proposal-module-already-present`) means the remote review map
already contains the proposed module: after this Proposal's own promotion that is
expected (prove it, then close out), otherwise it is a clash with an existing module
(republish under another id). Review does not tell the two apart; the proof does.
Baseline drift is checked first and still reports `stale`.

The CLI `proposal_review.py --proposal-id <id> --platform <github|gitlab> --target <t>`
composes the fixed remote-default Publication, the read-only tracker adapter and this
review, and prints the JSON below. It reads the tracker only when the Proposal is
published. `/spec-guard:proposal-review` wraps it.

`as_json(review_result)` returns only safe identifiers, state/stage and stable
diagnostic codes. It omits map text, Issue body/comments, markers, URLs, tokens,
temporary paths and raw errors.
