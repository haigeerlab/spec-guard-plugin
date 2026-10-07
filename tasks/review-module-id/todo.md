# Todo: review-module-id

- [x] Task 1: `moduleId` in review and preflight (tests first), docs — review test with a Proposal whose id (`split`) differs from its module (`gamma`) across accepted / in-map / stale / tracker-absent, none on publication-absent; preflight in-map CLI and `preflight_as_json` tests; red (6 errors), then green. One existing exact-match expectation (tracker-unknown after reading the Proposal) gained `moduleId`, as the Spec requires. Mutation filling moduleId with the Proposal id is caught. Command docs list `moduleId`, contract-checked
- [x] Checkpoint 1 (report): tests green
- [ ] Task 2: real-host review; CHANGELOG; 0.51.3
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 3: post-release evidence on the installed plugin
