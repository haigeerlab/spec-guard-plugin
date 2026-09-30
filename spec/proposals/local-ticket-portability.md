# Proposal: Preserve and migrate Local ticket context
<!-- spec-guard-proposal:v2 id=local-ticket-portability revision=sha256:3c80a65c118244828596d26e2ce0244274954a5b7f851f6294e033249061fde0 -->

## Summary

Add a portable, verified archive and explicit one-way handoff for the existing Local
ticket ledger. A local project must be able to recover its full Epiq context after
checkout or machine changes and later move selected work items to a chosen GitHub
or GitLab project without silently dropping history or creating duplicate Issues.
This is a separate capability from ordinary ticket use because it owns recovery,
source coverage, destination mapping and partial-publication reconciliation.

## Integration intent

| Field | Value |
| --- | --- |
| Problem | The existing Local ledger can retain tickets on one Mac, but a copied project identity can collide with another clone; committed state may omit pending events; there is no verified portable restore or explicit remote Issue handoff. |
| In scope | Read-only source inventory; versioned archive with event and attachment coverage; fresh-environment restore check; deterministic GitHub/GitLab Issue preview; per-ticket explicit publication, readback and resumable mapping. |
| Out of scope | Local PR/MR or CI server, automatic provider switch, background or bidirectional sync, native recreation of historical authors and timestamps, daily hosted Tracker adapters, and changes to Proposal governance. |
| Safety boundaries | Preserve existing Epiq worktrees and pending files; never infer absence from an incomplete lookup; no hidden sync or push; require an exact destination and show visibility before hosted writes; reconcile uncertain writes by stable non-Proposal markers; keep Local readable after cutover. |
| Initial dependency assumptions | The shipped local-ticket-ledger and ledger-worktree-owner contracts remain intact, including the pinned runtime and conflict diagnostics; Proposal readers remain read-only and independent. |
| Acceptance intent | A fixture with pending and committed events, edits, ordered comments, open/closed states and attachments survives an offline archive/restore with matching identities and hashes; simulated partial GitHub and GitLab publication resumes without a duplicate Issue or comment and changes each ticket's active work surface only after verified readback. |

## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | origin |
| Default branch | main |
| Commit | b9d71cab39a57363cc23c00f15f0a36d1a7b79dc |
| Capability map | spec/CAPABILITY-MAP.md |
| Goal digest | 03cd446c69f5 |
| Build order | proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-mainline-review → proposal-promotion-proof → proposal-boundary-guidance → collaboration-messaging → collaboration-safe-defaults → local-ticket-ledger → ledger-dependency-lock → local-convention → phase-and-verification → module-insert → capability-history → documentation-baseline → documentation-impact → documentation-verification → audit-remediation → done-stage-split → module-interrupt → plan-without-todo → proposal-pool-isolation → proposal-label-acceptance → proposal-add-module-promotion → proposal-submit → promotion-proof-diagnostics → insert-existing-spec → ledger-worktree-owner → done-unmerged-hint → git-fixture-template |

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
| collaboration-safe-defaults | fa11d17d3934 |
| local-ticket-ledger | 75ed35684de9 |
| ledger-dependency-lock | bc3f8bbc3b88 |
| local-convention | bd5ffdd20fdf |
| phase-and-verification | 299bdf8b6c4f |
| module-insert | 4cc89d8f78a4 |
| capability-history | 83a5c722e8ac |
| documentation-baseline | 80dbe13f6626 |
| documentation-impact | 866e51ab31da |
| documentation-verification | 8cdc2b63fb9b |
| audit-remediation | 03c43e1aa4a0 |
| done-stage-split | d67afc026e5b |
| module-interrupt | 4b68634e117e |
| plan-without-todo | 21280242c951 |
| proposal-pool-isolation | 32cee16b8f9d |
| proposal-label-acceptance | 53184b625ccc |
| proposal-add-module-promotion | 97861b18bdf8 |
| proposal-submit | 10b6be5202b3 |
| promotion-proof-diagnostics | 20ab47b3f8e0 |
| insert-existing-spec | 4cdf90f9133d |
| ledger-worktree-owner | 49f7ed5e6610 |
| done-unmerged-hint | 062ea6636717 |
| git-fixture-template | db1c3f2cc74a |

## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | local-ticket-portability |
| Responsibility | Verify and restore complete Local ticket context, then explicitly hand off selected tickets to a chosen GitHub or GitLab Issue with resumable per-ticket reconciliation. |
| Depends on | local-ticket-ledger, ledger-worktree-owner |
| Build-order anchor | end |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | local-ticket-portability |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
