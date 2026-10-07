# Spec: review-module-id

## Objective

`proposal-review` and the promotion preflight print `proposalId` but not the module the Proposal adds. On
2026-10-07 a session reviewing `collaboration-split` called the module `collaboration-split`; the module is
`collaboration-interface`. The proof already prints `moduleId`; review and preflight should too.

## Assumptions

Confirmed by the user on 2026-10-07:

1. The field is `moduleId`, as in the proof output.
2. It appears only on results that read the Proposal (where `proposalId` comes from the Proposal itself); `absent`,
   publication failures and the like carry none.
3. Additive output only; version 0.51.3.

## Requirements

1. `Review` carries `module_id`; `review()` sets it from `proposal.change.module_id` on every result built after the
   Proposal was read; `as_json` emits `moduleId` when present.
2. `Preflight` carries `module_id` from the same Proposal on `ready` and on every non-ready result after the
   publication was found; `preflight_as_json` emits it.
3. States, diagnostics and judgement unchanged.
4. Docs: review and preflight commands list `moduleId`.
5. Tests first; a real review of `collaboration-split` shows `"moduleId": "collaboration-interface"`.
6. CHANGELOG; 0.51.3.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_proposal_review.py
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py
```

## Boundaries

- Never: change states or judgement; guess a module id when the Proposal was not read.

## Success criteria

1. Review and preflight name the module whenever they read the Proposal.
2. Nothing else in their output changes.

## Open questions

None.
