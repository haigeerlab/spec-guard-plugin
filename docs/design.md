# spec-guard design

## Purpose

spec-guard adds two independent safeguards around agent-skills:

1. A local multi-module file layout that prevents module plans and task lists
   from overwriting one another.
2. A Proposal lifecycle that reads a published remote-default-branch snapshot
   and explicit GitHub/GitLab Proposal Issue facts without side effects.

It also ships two optional same-Mac capabilities that need explicit setup: a
collaboration mailbox for Claude Code and Codex sessions, and a local ticket
ledger for repositories without GitHub/GitLab Issues. Neither replaces or
synchronizes remote Issues.

## Proposal boundary

`spec/CAPABILITY-MAP.md` is the single capability map for the whole plugin: an
accepted Proposal inserts its module after a declared anchor or at the end,
instead of starting a new map. The Proposal lifecycle is seven modules in it.
Proposal v2 binds its published
contents to a revision digest. A normal author branch can publish and read a
Proposal, but only the policy-defined mainline may evaluate it at an explicit
module boundary. Mainline identity is Git topology plus protected remote policy,
not a person or agent name. Acceptance additionally requires a revision-bound
immutable attestation and a separately human-written Issue stage.

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
