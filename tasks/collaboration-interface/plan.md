# Plan: collaboration-interface

Based on [`spec/collaboration-interface.md`](../../spec/collaboration-interface.md) (reviewed by the user on
2026-10-06). Branch `claude/promote-collaboration-interface`, worktree
`.claude/worktrees/vigilant-pasteur-e6db3b`. Reread
[`docs/collaboration-split-brief.md`](../../docs/collaboration-split-brief.md) after any context reset.

## Overview

Write `docs/collaboration-interface.md` with the fourteen sections the Spec requires. The work is
documentation only; each task fills a group of sections from evidence and ends with one commit. Facts for the
current column come from the pre-split baseline or from code at `54d0426` (Spec Guard) and the pinned
upstream bridge `8f12c880` installed at `~/.spec-guard/native-collaboration/src`; nothing is written from
memory.

## Architecture Decisions

- **Evidence first.** For each section, read the cited source, then write the row. A citation is either a
  baseline anchor (`docs/baselines/collaboration-pre-split.md#…`) or `path:line` at a fixed commit
  (`54d0426` for Spec Guard, `8f12c880` for the bridge).
- **Targets stay parameter-free** (Spec assumption 3) and name their owning hardening module.
- **D1/D2 are applied, not re-decided.** New names appear only in target or migration rows.
- **No new files beyond the deliverable.** The upstream source is read in place; no message bodies are read.
- Shared verification for every task:

  ```bash
  /bin/bash scripts/validate.sh
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  ```

## Task List

### Task 1: Sections 1–5 (scope, tools, messages, session and delivery states)

**Description:** Scope and versioning; every MCP tool with inputs/outputs from the bridge tool schemas and
the denied list in `native_collaboration_runtime.py`; command-line entries (runtime, adapters, retire,
delegation controller); stored message and wake-job fields from the bridge schema; session and delivery
state definitions including the baseline finding that a wake job stays `read` after acknowledgement.

**Acceptance:** sections 1–5 exist; each three-column row has both cells; every current cell cites evidence.

**Verify:** shared commands; manual citation spot-check of every row in sections 2 and 5.

**Files:** `docs/collaboration-interface.md`

### Task 2: Sections 6–10 (semantics, identity, authorization, routing, delegation)

**Description:** Delivery semantics (no exactly-once; gaps b, d, e, f); identity rules (gap g); authorization
and wake rules (finding 1, guardian detection target); routing per host pair; delegation intents, lifecycle,
public JSON fields, and the baseline findings (integer `--expires-at`, held create envelope, Claude round-two
`target-busy` while idle, background prompt hangs, Codex manual approval prompts).

**Acceptance:** sections 6–10 exist and meet the row rules; every baseline finding referenced here links to
its baseline row.

**Verify:** shared commands; spot-check delegation fields against `session_delegation_control.py --help` and
the baseline items 7–9.

**Files:** `docs/collaboration-interface.md`

### Task 3: Sections 11–13 (single entry, detection and degradation, state and migration)

**Description:** Define the detection helper (name, inputs, output, interface-version check) and the allowed
references; list the coupling points from the baseline inventory that `collaboration-boundary` must cut;
write the exact not-installed message and the degradation rules; current state paths and contents; new paths
per D1; migration plan (detect, back up, migrate, verify, never delete silently); uninstall keeps history;
state-root environment override target (gap j).

**Acceptance:** sections 11–13 exist; section 11 is precise enough that a check can be written from it; the
not-installed message is quoted verbatim.

**Verify:** shared commands; confirm every coupling point named in the baseline appears in section 11.

**Files:** `docs/collaboration-interface.md`

### Checkpoint (report): sections 1–13 drafted

Record progress in `todo.md` and continue.

### Task 4: Section 14 index and review checklist

**Description:** Map gap items a–k and findings 1–7 to sections and owning hardening modules; run the Spec's
review checklist over the whole document and fix any gap.

**Acceptance:** every checklist item in the Spec's testing strategy passes; the index has 18 rows (11 gaps +
7 findings), each with a section and a module.

**Verify:** shared commands; checklist results written into `todo.md`.

**Files:** `docs/collaboration-interface.md`, `tasks/collaboration-interface/todo.md`

### Checkpoint (gate): user review of the interface document

Stop and present the document for review. MODULE_DONE only after the user accepts it. Then, with the user's
separate approval: push `claude/promote-collaboration-interface`, open one PR carrying the promotion commit,
this Spec, this plan, and the document; after merge run `/spec-guard:proposal-promotion-proof` for
`collaboration-split`, and the user relabels Issue #221 to `proposal-stage:promoted` once it is `proved`.

## Risks

- **Large upstream source.** The bridge is ~5,200 lines of TypeScript; read only the schema and tool
  definition regions, not whole files.
- **Context size.** This session is past 500k tokens; a context reset mid-module is likely. Mitigation: each
  task commits, `todo.md` records state, and the brief is reread first.
