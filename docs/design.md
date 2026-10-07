# spec-guard design

> Maintainer-facing design notes. For the user-facing design principles and glossary, see
> [concepts.md](concepts.md).

## Purpose

spec-guard adds two independent safeguards around agent-skills:

1. A local multi-module file layout that prevents module plans and task lists
   from overwriting one another.
2. A Proposal lifecycle that reads a published remote-default-branch snapshot
   and explicit GitHub/GitLab Proposal Issue facts without side effects.

It also ships an optional same-Mac local ticket ledger, which needs explicit
setup, for work explicitly tracked locally. Session collaboration moved to the
standalone agent-relay plugin; Spec Guard only detects it. The Local ledger does not
synchronize remote Issues. An on-demand hosted ticket workflow handles ordinary
GitHub/GitLab Issues after an explicit target choice; it does not project tasks
or bind worktrees. The separate Local ticket
portability workflow can archive the ledger and explicitly hand off selected
items to GitHub/GitLab Issues after a target-specific preview and authorization.

A project-audit handoff convention bounds a review batch, records its findings,
and moves confirmed bugs into the existing ticket and agent-skills repair flows.
It does not add an audit state to the phase hook or revive mutable remote
tracker adapters.

## Proposal boundary

`spec/CAPABILITY-MAP.md` is the single capability map for the whole plugin: an
accepted Proposal inserts its module after a declared anchor or at the end,
instead of starting a new map. The Proposal lifecycle is seven modules in it.
Proposal v2 binds its published
contents to a revision digest. Acceptance is a human-written Issue stage label
(`proposal-stage:accepted`) plus a fresh review of the published Proposal
against the remote default branch; no mainline policy, acceptance attestation
or authority identity is read. The post-merge proof starts from the Proposal's
baseline commit and judges freshness on the promotion commit's parent.

The tracker adapters are read-only and only recover a normal Proposal Issue by
its complete identity marker in an explicitly supplied container. A preflight
and post-merge proof are read-only; neither can create the promotion branch,
modify the capability map, or write tracker state.

## Local boundary

The optional local convention stores module documents under `spec/` and
`tasks/<module-id>/`.  Its state file can record a local active module, but is
not a Proposal pool and is never read by Proposal code.

## Retired boundary

The v0.14-era mutable remote tracker bridge is not part of the product.  It is
not hidden behind a compatibility route: remote projection, selection, binding,
delivery, and synchronization preview are absent.  Historical records remain
immutable evidence.  The full decision, migration rules, and acceptance
criteria live in [the retirement spec](retirements/spec-github-bridge-retirement.md).
