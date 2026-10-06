# Spec: collaboration-interface

## Objective

Write `docs/collaboration-interface.md`: the public contract of the collaboration capability that is being
moved from Spec Guard into the standalone `agent-relay` plugin. Every later split step is checked against it:
`collaboration-boundary` enforces its single entry, `collaboration-extraction` moves exactly what it lists, the
agent-relay translation modules must reproduce its **current** column, and the hardening modules must reach its
**hardening target** column.

Readers: the user reviewing the split, agents working in either repository, and authors of sessions (for
example design sessions) that will use agent-relay without Spec Guard.

Source decisions: [Proposal collaboration-split](proposals/collaboration-split.md) (Issue #221, accepted),
[the split brief](../docs/collaboration-split-brief.md), and
[the pre-split baseline](../docs/baselines/collaboration-pre-split.md).

## Assumptions

Confirmed by the user on 2026-10-06:

1. This module writes documents only (this Spec and the interface document, both in English); no code,
   hook, skill, manifest, or test changes.
2. Every current-column fact cites its evidence: a section of the pre-split baseline or a code location at
   `54d0426`. Nothing without evidence enters the current column.
3. The hardening-target column states direction and acceptance wording, not final parameters. Values such
   as the queue expiry or the pending cap are written as "configurable; default proposed in module X" and
   decided when that hardening module's Spec is reviewed.
4. Hardening targets cover the OpenSwarm gap items a–k and the seven findings of the baseline live run;
   each target names the hardening module that owns it.
5. Spec Guard's single entry into collaboration is (a) one detection helper inside Spec Guard that reports
   whether agent-relay is installed, its interface version, and the not-installed message, and (b) agent-relay
   skill names in workflow text. No Spec Guard file may reference collaboration internals. This document
   defines the entry; `collaboration-boundary` implements and enforces it.
6. agent-relay uses its own semver. The document carries an interface version; Spec Guard declares only the
   minimum interface version it needs. Codex 0.160 has no plugin-dependency field, so both hosts detect at
   run time; a Claude manifest dependency may be added later but is never relied on.
7. Acceptance is by checklist and review; no new validator in this module. A structural check (every item
   has both columns) may be added by `collaboration-boundary`.

Decisions taken with the user on 2026-10-06:

- **D1 naming.** The translated plugin renames the MCP server from `spec-guard-native-collaboration` to
  `agent-relay` and the state root from `~/.spec-guard/native-collaboration/` to `~/.agent-relay/`; tool
  names `bridge_*` stay. Old names, host entries, and permission rules
  (`mcp__spec-guard-native-collaboration__bridge_*`) are migrated by `state-migration` after a backup. This
  is an approved naming difference from the baseline, not a behavior change.
- **D2 expiry in a pull mailbox.** Hardening target for "expired, never delivered later": an expired
  message is marked `expired`, no longer returned by default from inbox or wait, and still kept in
  history and readable by explicit query.

## Contract: required content of `docs/collaboration-interface.md`

Every section below is one table with three columns — **Item**, **Current (baseline)**, **Hardening
target** — unless it is marked *single column*. "Current" for a not-yet-existing behavior is written as
"none", with the gap-item letter.

1. **Scope and versioning** *(single column)* — what agent-relay is and is not (same-Mac only, no network
   service, no tracker, no authority channel); interface version `1.0`; agent-relay semver; how a breaking
   interface change is versioned; the minimum interface version Spec Guard requires.
2. **Tool list** — every MCP tool with inputs and outputs: the ten mailbox tools
   (`bridge_register`, `bridge_send`, `bridge_inbox`, `bridge_ack`, `bridge_outbox`, `bridge_agents`,
   `bridge_sessions`, `bridge_wake_status`, `bridge_thread`, `bridge_wait`), the denied upstream tools, and
   the command-line entries (runtime status/probe/install, host adapter install/uninstall, identity retire,
   delegation controller subcommands). Target column adds `doctor`, `whoami`, status/wait by message id,
   body from file (gap h, i).
3. **Message structure** — fields of a stored message (id, from, to, body, thread, idempotency key,
   timestamps, acknowledgement) and of a wake job.
4. **Session states** — formal definitions with *registered ≠ online*: registered, wake-bound, wake-held,
   retired, unknown; how each is observed (`bridge_agents`, `ListAgents`, Codex threads).
5. **Delivery states** — formal definitions with *enqueued ≠ read ≠ done*: message enqueued, read,
   acknowledged, replied; wake states pending, sending, accepted, read, held, refused, unknown, cancelled,
   expired. Target: the a/c state machine (queued, sending, accepted, failed, unknown, expired) per D2, and the
   baseline finding that a wake job stays `read` after acknowledgement.
6. **Delivery semantics** *(single column plus target note)* — no exactly-once; "accepted by the native
   interface" is not "processed by the peer"; unknown is never replayed automatically (gap b); persist before
   submit (gap d); ordering, independence, and cap (gap e); idempotency and reply de-duplication (gap f).
7. **Identity rules** — naming, first-registration reuse, no takeover of another session's name, sender
   field is free text today (gap g), only-recipient-replies target, host identity check, guidance when
   identity is missing.
8. **Authorization and wake rules** — `wake: null` default; explicit opt-in; auto-approved sessions never
   bind; per-item confirmation for setup, config change, new identity, widened permission; no automatic
   permission edits. Target adds detection of Codex `approvals_reviewer = "guardian_subagent"` (finding 1).
9. **Routing** — Claude↔Claude via `ListAgents`/`SendMessage`, Codex↔Codex via App task/thread tools,
   Claude↔Codex via the mailbox; fallback rules; nothing copied into the mailbox on a host-native success.
10. **Delegation** — permission intents, authority modes, lifecycle (create, continue, status, cancel),
    result return, disambiguation, public JSON fields. Current column includes the baseline findings: integer
    `--expires-at`, held create persisting a named envelope, Claude-target round two reporting `target-busy`
    while idle, background sessions hanging on prompts.
11. **Spec Guard's single entry** *(single column)* — the detection helper's name, inputs, and output; the
    allowed references (agent-relay skill names only); what counts as a violation for
    `collaboration-boundary`; the coupling points it must cut (from the baseline inventory).
12. **Detection and degradation** *(single column)* — installed / not installed / too old / runtime not
    ready; Spec Guard's exact not-installed message text; the rule that workflow commands never fail because
    agent-relay is absent; `/spec-guard:collaboration` handoff period of one to two releases.
13. **State data and migration** — current paths and contents (from the baseline), new paths per D1, and
    the migration plan: detect, back up first, migrate, verify, never delete silently; uninstall keeps
    message history (gap k); test isolation through an environment override of the state root (gap j).
14. **Gap and findings index** *(single column)* — a table mapping gap items a–k and findings 1–7 to the
    section that describes them and to the owning hardening module (`test-isolation`,
    `delivery-state-machine`, `durable-ordering`, `idempotency`, `identity-check`, `ops-commands`,
    `safe-uninstall`).

## Commands

Read-only checks used while writing and reviewing:

```bash
git show 54d0426:plugins/spec-guard/hooks/native_collaboration_runtime.py | sed -n '140,152p'
python3 -B plugins/spec-guard/hooks/session_delegation_control.py --help
/bin/bash scripts/validate.sh
```

`validate.sh` must stay green; this module adds no tests of its own.

## Project structure

- `docs/collaboration-interface.md` — the deliverable (new).
- `spec/collaboration-interface.md` — this Spec.
- No other file changes. The document is copied into agent-relay by `collaboration-extraction`; from then
  on the agent-relay copy is authoritative and Spec Guard links to it.

## Testing strategy

No executable tests. Verification is a review checklist run before MODULE_DONE:

- every section in the Contract exists, in that order;
- every three-column row has a non-empty current and target cell;
- every current-column fact has a citation that resolves (baseline section anchor or `path:line` at
  `54d0426`);
- every gap item a–k and finding 1–7 appears in section 14 with an owning module;
- `validate.sh` passes.

## Boundaries

- Always: cite evidence for current-column facts; keep D1 and D2 as decided; keep the target column
  parameter-free.
- Ask first: adding a section, changing the single-entry definition, changing a decision, writing anything
  outside the two files.
- Never: change code, hooks, skills, manifests, or tests in this module; describe a target as already
  current; copy OpenSwarm code or text.

## Success criteria

1. `docs/collaboration-interface.md` exists with the fourteen sections above, each complete per the
   testing checklist.
2. The user reviews and accepts the document.
3. `validate.sh`, `test-phase-guard.sh`, and `test-verify-artifacts.sh` pass unchanged from the baseline.

## Open questions

None at Spec time. Parameter values for the hardening targets are deferred to the hardening modules by
assumption 3.
