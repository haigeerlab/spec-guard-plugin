# Spec: proposal-closeout-reminder

## Objective

Stop promoted Proposals from staying open unnoticed. Step 4 of the Proposal flow (proof, then
`/spec-guard:proposal-closeout`) is the only thing that closes a Proposal item, and nothing reminds anyone to run
it. On 2026-10-07 this repository found Issue #221 still open a day after its promotion PR (#222) merged: the stage
label had been changed by hand, which the workflow allows but which does not close the item. Closeout itself worked
(`verified`) once someone ran it.

Readers: maintainers of projects that use Proposals; agents following the shared checkpoint rules.

## Assumptions

Confirmed by the user on 2026-10-07:

1. The scan resolves backend and target like closeout preview: explicit `--backend`/`--target`, else the project
   default (`tracker-default`); unresolved is `target-unselected`, never a guess.
2. The scan takes one fresh proof and one item read per published Proposal; Proposal counts are small, no cache.
3. The release-process step runs the scan when the project has `spec/proposals/`; this repository runs it every
   release.
4. Version 0.51.0 (new command capability).

## Design

1. **`proposal_closeout.py scan`** (read-only, no output file). Reads the published Proposal pool from the remote
   default branch once, then judges each Proposal with the same `build_preview` path as `preview` (fresh proof,
   item read, `closeout_decision`). Output JSON:
   `{"state": "scanned", "backend", "source", "items": [{"proposalId", "state", "issueId"?, "diagnostic"?}],
   "pending": [<proposalId>…], "skippedProposals"?}` where an item whose preview would be built is reported as
   `closeout-pending` and every other outcome keeps preview's own state and diagnostic (`already-closed`,
   `not-eligible`, `unknown`, `absent`, `invalid`, `conflict`). A pool that cannot be read is
   `{"state": "unknown"|"invalid", "diagnostic"}`, exit 2. It never writes, never builds a preview file, and an
   item it cannot read is `unknown`, not pending and not closed.
2. **Proof flag.** `proposal_promotion_proof.py --prove`: when the result is `proved` and the item read in the same
   run is open, the JSON carries `"closeoutPending": true`; closed → `false`; otherwise absent.
3. **Checkpoint rule.** `workflow-checkpoints.md` gains a "Proposal 晋级 PR 合并后" line: run the proof; on
   `proved` with the item open, preview closeout and ask for authorization; never close by label alone.
4. **Release process.** `docs/release-process.md` post-release checks run the scan when the project has
   `spec/proposals/`, and list pending items for the user.
5. Command docs: `/spec-guard:proposal-closeout` gains a scan section; `proposal-promotion-proof` documents
   `closeoutPending`; Codex `spec-guard-ops` proposal section mentions scan.

## Requirements

1. Scan unit tests: pending, already-closed, not-promoted (not-eligible), unreadable proof (unknown), unreadable
   item (unknown), unreadable pool (exit 2), mixed list keeps order; scan never calls a write method.
2. Proof tests: `closeoutPending` true / false / absent.
3. Contract checks that the checkpoint rule, release step and command docs carry the new text.
4. Real host: scan against this repository reports every Proposal `already-closed` and `pending: []`.
5. CHANGELOG; 0.51.0 in both manifests and README `--ref`.

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_proposal_closeout.py
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py
/bin/bash evals/codex-plugin-smoke.sh --selftest
```

## Boundaries

- Always: read-only scan; failed reads degrade to `unknown` with a code.
- Ask first: any closeout write (existing authorized flow), push, PR, release.
- Never: auto-close; hooks touching remote state; phase-guard reading the tracker.
- Out of scope: `proposal-review` reporting `stale` (`proposal-module-already-present`) for promoted Proposals.

## Success criteria

1. A promoted-but-open Proposal is reported by the scan, by the proof, and called for by the checkpoint rule and the
   release process.
2. Nothing new writes to a tracker.
3. Baseline suites green; new tests turn red when the scan or flag is broken by hand.

## Open questions

None.
