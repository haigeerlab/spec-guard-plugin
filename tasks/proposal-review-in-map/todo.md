# Todo: proposal-review-in-map

- [x] Task 1: `in-map` state (tests first) — review tests (in-map at accepted and promoted with ids/stage/diagnostic; baseline drift still `stale`), preflight CLI now expects `in-map`, proof test that an `in-map` parent review never proves; red, then `proposal_review.py` green (review 13+, proof suite OK). Hand mutations killed: state back to `stale`, in-map diagnostic dropped from JSON. One wrong expectation of mine fixed: review JSON has always shown drift as generic `proposal-stale`
- [x] Task 2: docs and contract check, CHANGELOG — commands/proposal-review.md, references/proposal-review.md, commands/proposal-promotion-preflight.md, module-insert hint; contract test in test_proposal_review.py; test_module_insert OK
- [x] Checkpoint 1 (report): tests green, docs updated
- [ ] Task 3: real-host review of a promoted Proposal; 0.51.2
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 4: post-release evidence on the installed plugin
