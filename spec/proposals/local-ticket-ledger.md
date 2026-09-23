# Proposal: Add a local ticket ledger
<!-- spec-guard-proposal:v2 id=local-ticket-ledger revision=sha256:9600e00fd6b7e8cb89901692e8d81f7104d1662e32710f238583221a481a6f30 -->

## Summary

Provide an optional, durable local ticket ledger for a Git repository when GitHub or GitLab
Issue services are unavailable.  The ledger lets independent Claude Code and Codex sessions in
different linked worktrees create, inspect, discuss, and close the same local records without
manual copy-paste.  It is a separate capability because it owns local record persistence,
worktree visibility, explicit setup, and future migration boundaries; it does not expand the
mailbox into a workflow engine or recreate a forge.

## Integration intent

| Field | Value |
| --- | --- |
| Problem | A local repository without available GitHub or GitLab Issues has no shared, durable place for agents to record bugs, requirements, investigation context, and completion results across worktrees. |
| In scope | An explicitly enabled local-first ticket backend; one shared repository ledger across linked worktrees on the same Mac; Claude Code and Codex MCP access; free-text ticket discussion and state changes; optional mailbox notifications that reference a ticket. |
| Out of scope | Project groups, routing or ownership rules, mandatory roles, task scheduling, Git mutation, pull requests, CI, a local GitHub/GitLab clone, automatic remote Issue synchronization, cross-machine networking, and replacing the existing mailbox. |
| Safety boundaries | Initialization is explicit and reports every repository change; the implementation preserves a clean separation between durable ticket state and free-text messaging; no secret is stored in project files; failures to reach a remote do not lose local state or claim a remote update succeeded. |
| Initial dependency assumptions | The ledger remains useful without the mailbox. When the optional collaboration mailbox is available, an agent may send a free-text notification containing a ledger reference, but neither component may require or mutate the other. |
| Acceptance intent | In a real same-Mac repository with two linked worktrees, two ordinary Claude Code/Codex sessions can see the same ticket, retain concurrent discussion, and still read it after either MCP process restarts; a user can later preserve ticket references while creating corresponding GitHub or GitLab Issues explicitly. |

## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | origin |
| Default branch | main |
| Commit | e552a6216398aef52127249cd896144ce5751f20 |
| Capability map | spec/CAPABILITY-MAP.md |
| Goal digest | 06b3ede4f7a1 |
| Build order | proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-mainline-review → proposal-promotion-proof → proposal-boundary-guidance |

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

## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | local-ticket-ledger |
| Responsibility | Provide an optional local-first, worktree-shared ticket ledger and narrow Claude Code/Codex access without imposing workflow ownership or project topology. |
| Depends on | — |
| Build-order anchor | end |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | local-ticket-ledger |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
