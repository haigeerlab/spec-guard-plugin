# Proposal: Generate a valid Proposal draft
<!-- spec-guard-proposal:v2 id=proposal-draft revision=sha256:e0206a6fb836b9faa4c2947783cbf2058ef29288986c819bb045d5632b79feb4 -->

## Summary

Writing a Proposal today means hand-copying the capability-map baseline from the remote default branch, running
`spec-digest.py` for every module row, and computing the content revision with an internal Python function. Users
get this wrong or give up, which makes the Proposal lifecycle the hardest part of the plugin to adopt. A draft
generator reads the fixed remote snapshot, fills the baseline, digests and revision, and writes one local draft file
that the existing contract validator accepts. It is an independent capability because it owns authoring only: it
never publishes, never touches trackers, and reuses the existing contract and snapshot code instead of changing them.

## Integration intent

| Field | Value |
| --- | --- |
| Problem | Authoring a v2 Proposal requires manual baseline digests and a revision computed by an internal function, so users make mistakes or skip the Proposal lifecycle. |
| In scope | A Claude command and Codex skill entry that read the remote default-branch snapshot, fill the baseline table, module digests, Build order and revision, take the new module fields from the user, write `spec/proposals/<id>.md`, and validate it with the existing contract. |
| Out of scope | Publishing, committing, pushing, opening pull requests, creating or labelling Issues, editing the capability map, and Proposal change types other than new-module. |
| Safety boundaries | Write only the one local draft file after showing a preview and receiving explicit confirmation; refuse to overwrite an existing Proposal file; read shared facts only from the fixed remote snapshot; reuse spec-digest.py and proposal_contract instead of copying their algorithms. |
| Initial dependency assumptions | Depends on proposal-contract for the format and revision, and on proposal-publication for the fixed remote default-branch snapshot. |
| Acceptance intent | A generated draft passes the existing contract validation unchanged, and after a user merges it and opens the matching Issue, proposal-review reports it as fresh on a real GitHub repository. |

## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | origin |
| Default branch | main |
| Commit | 35b8701e1c03931970d76d264363b61aa5789962 |
| Capability map | spec/CAPABILITY-MAP.md |
| Goal digest | 97db66d00baa |
| Build order | proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-mainline-review → proposal-promotion-proof → proposal-boundary-guidance → collaboration-messaging → local-ticket-ledger → local-convention → phase-and-verification → capability-history → documentation-baseline → documentation-impact → documentation-verification |

### Module digests

| Module id | Row digest |
| --- | --- |
| proposal-contract | f84b24340ec2 |
| proposal-publication | e563ad8b3b2b |
| proposal-tracker-read | 7e155de3579e |
| proposal-review | f8e8cdcfb46b |
| proposal-mainline-review | 403f2901bd0d |
| proposal-promotion-proof | b236226e282f |
| proposal-boundary-guidance | 491564a83c5b |
| collaboration-messaging | 2a091b441012 |
| local-ticket-ledger | 75ed35684de9 |
| local-convention | bd5ffdd20fdf |
| phase-and-verification | 299bdf8b6c4f |
| capability-history | 83a5c722e8ac |
| documentation-baseline | 80dbe13f6626 |
| documentation-impact | 866e51ab31da |
| documentation-verification | 8cdc2b63fb9b |

## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | proposal-draft |
| Responsibility | Generate a contract-valid v2 Proposal draft from the fixed remote default-branch snapshot and write only that local file after confirmation. |
| Depends on | proposal-contract, proposal-publication |
| Build-order anchor | after:proposal-publication |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | proposal-draft |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
