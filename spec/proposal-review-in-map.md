# Spec: proposal-review-in-map

## Objective

`review()` reports `stale` / `proposal-module-already-present` when the proposed module is already in the remote
capability map, and the command docs read `stale` as "republish against a new baseline". For a promoted Proposal
the module is meant to be there, so the advice is backwards. `review()` feeds `proposal-review` and the promotion
preflight; the proof calls it on the promotion's parent, where the module is absent.

## Assumptions

Confirmed by the user on 2026-10-07:

1. The new state is `in-map`; the diagnostic stays `proposal-module-already-present`.
2. The preflight's visible state changes from `stale` to `in-map` for this case; both block promotion. Version 0.51.2.
3. `proposal-review` stays pure and does not run the proof to tell its own promotion from a name clash.

## Requirements

1. `review()` returns `in-map` (with review commit, ids, issue, stage, revision and the same diagnostic) when the
   module is already in the review map; the three drift cases (`proposal-baseline-drifted`,
   `proposal-dependency-missing`, `proposal-anchor-drifted`) stay `stale`, and baseline drift still wins over in-map.
2. `as_json` keeps the diagnostic for `in-map`.
3. Preflight reports `in-map`, never `ready`; the proof is unchanged (its parent-commit check never sees `in-map`;
   if it ever did, it is blocked, not proved).
4. Docs: `commands/proposal-review.md`, `references/proposal-review.md`, the preflight command, `spec-guard-ops`,
   and the `add-module` hint describe `in-map` — own promotion: run the proof, then closeout; otherwise a name
   clash: republish under another id.
5. Tests: review unit tests, preflight CLI test updated, a proof test that an `in-map` parent never proves.
6. CHANGELOG; 0.51.2.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_proposal_review.py
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py
```

## Boundaries

- Never: change freshness checks, proof, closeout or scan judgement; make review read Git or the tracker itself.

## Success criteria

1. A promoted Proposal's review reads `in-map` with next-step guidance, not "republish".
2. Drift still reads `stale`; nothing that blocked before is allowed now.

## Open questions

None.
