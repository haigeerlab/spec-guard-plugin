# Proposal: Split collaboration into the agent-relay plugin
<!-- spec-guard-proposal:v2 id=collaboration-split revision=sha256:2d9307d29870db931adf51c57b1462d33c45a341abe6a788e8010c2c658b74f9 -->

## Summary

Move the optional collaboration capability (native mailbox, unified session routing, cross-host session delegation) out of Spec Guard into a standalone plugin, `agent-relay`, installable on both Claude Code and Codex. Design sessions need cross-session communication without the Spec Guard workflow; the communication layer follows host-native interfaces on its own release cadence; wake and authorization need separate audit; and its macOS + Node.js dependency should not burden workflow-only users.

This Proposal records the split decision and adds its first module, `collaboration-interface`: the public interface document that every later step is judged against. The full brief is [docs/collaboration-split-brief.md](../../docs/collaboration-split-brief.md) and the behavior baseline is [docs/baselines/collaboration-pre-split.md](../../docs/baselines/collaboration-pre-split.md). Proposal v2 adds one module per Proposal, so the remaining Spec Guard-side modules are inserted with `/spec-guard:add-module` at their checkpoints, in this order and each after review: `collaboration-boundary` (route every collaboration call through one entry and fail a check on any direct internal reference), `collaboration-extraction` (move the code and its history into the new repository with git filter-repo), and `collaboration-dependency` (remove the moved code, keep `/spec-guard:collaboration` as a one-to-two-release handoff, guide legacy state migration).

## Integration intent

| Field | Value |
| --- | --- |
| Problem | Collaboration is built into Spec Guard, so communication-only sessions must install the workflow, the two cannot be released or audited independently, and there is no written public contract that a split could be checked against. |
| In scope | `docs/collaboration-interface.md`: tool list with inputs and outputs, message structure, session states (registered is not online) and delivery states (enqueued is not read is not done), delivery semantics without exactly-once, identity rules, the single Spec Guard entry for collaboration, versioning, detection and degradation with the not-installed message, and the state-data migration plan with mandatory backup. Every item has a current column taken from the pre-split baseline and a hardening-target column. |
| Out of scope | Code changes, moving files, creating the new repository, cross-machine or cross-platform transport, changing the authorization model, adopting OpenSwarm's same-user trust model, and moving the local ticket ledger, documentation governance, or capability history. |
| Safety boundaries | Joining defaults to `wake: null`; auto-approved sessions never bind wake; setup, configuration changes, new identities, and widened permissions each need explicit confirmation; project and global permissions are never changed automatically; no push, tag, release, or remote setting change without explicit approval. |
| Initial dependency assumptions | The current column describes the shipped `collaboration-messaging`, `host-native-session-routing`, and `authorized-session-delegation` behavior as recorded in the pre-split baseline, including the pinned upstream bridge at `8f12c880cfdba73812b6ab7bc0f373fc467e0343`; Codex 0.160 has no plugin-dependency field, so Spec Guard must detect the new plugin at run time. |
| Acceptance intent | The document exists, covers every listed item in both columns, cites the baseline for each current-column fact, and is reviewed and accepted before `collaboration-boundary` starts. |

## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | origin |
| Default branch | main |
| Commit | 54d0426f5883934914b2a8b3832c5e36ab47e222 |
| Capability map | spec/CAPABILITY-MAP.md |
| Goal digest | 03cd446c69f5 |
| Build order | proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-promotion-proof → collaboration-messaging → collaboration-safe-defaults → local-ticket-ledger → ledger-dependency-lock → local-convention → phase-and-verification → module-insert → capability-history → documentation-baseline → documentation-impact → documentation-verification → audit-remediation → done-stage-split → module-interrupt → plan-without-todo → proposal-pool-isolation → proposal-label-acceptance → proposal-add-module-promotion → proposal-submit → promotion-proof-diagnostics → insert-existing-spec → ledger-worktree-owner → done-unmerged-hint → git-fixture-template → local-ticket-portability → retired-module-separation → audit-handoff → hosted-ticket-workflow → authorized-session-delegation → host-native-session-routing → tracker-backend-default → proposal-closeout → phase-context-sanitization → build-task-dispatch → module-cost-report → fresh-session-hint → session-handoff → context-hint-thresholds → checkpoint-tiers |

### Module digests

| Module id | Row digest |
| --- | --- |
| proposal-contract | f84b24340ec2 |
| proposal-publication | e563ad8b3b2b |
| proposal-tracker-read | 7e155de3579e |
| proposal-review | f8e8cdcfb46b |
| proposal-promotion-proof | 6d0cdfcf3656 |
| collaboration-messaging | 2a091b441012 |
| collaboration-safe-defaults | fffe65d8f0be |
| local-ticket-ledger | 75ed35684de9 |
| ledger-dependency-lock | f2ca1dff9b0b |
| local-convention | bd5ffdd20fdf |
| phase-and-verification | 299bdf8b6c4f |
| module-insert | 4cc89d8f78a4 |
| capability-history | 83a5c722e8ac |
| documentation-baseline | 80dbe13f6626 |
| documentation-impact | 866e51ab31da |
| documentation-verification | 8cdc2b63fb9b |
| audit-remediation | 256eb0614aee |
| done-stage-split | d67afc026e5b |
| module-interrupt | 3e3e44278a97 |
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
| local-ticket-portability | cdfd994a5018 |
| retired-module-separation | 67deaf21283a |
| audit-handoff | 73d62ca69073 |
| hosted-ticket-workflow | 3c5a2a094702 |
| authorized-session-delegation | 7723a7a85a9b |
| host-native-session-routing | a720a7a7a21b |
| tracker-backend-default | 03b0b7e275ff |
| proposal-closeout | 38766c924147 |
| phase-context-sanitization | b4edacfbceff |
| build-task-dispatch | 82284dec0a21 |
| module-cost-report | 89f5e48a4e55 |
| fresh-session-hint | 11f904607a8e |
| session-handoff | 18a1c3d10125 |
| context-hint-thresholds | d17ae8a63a44 |
| checkpoint-tiers | ed30a6dbd3b3 |

## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | collaboration-interface |
| Responsibility | Define the public collaboration interface, with current and hardening-target columns, that the split into agent-relay is checked against. |
| Depends on | collaboration-messaging, authorized-session-delegation, host-native-session-routing |
| Build-order anchor | end |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | collaboration-split |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
