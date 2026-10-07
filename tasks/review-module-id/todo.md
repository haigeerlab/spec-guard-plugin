# Todo: review-module-id

- [x] Task 1: `moduleId` in review and preflight (tests first), docs — review test with a Proposal whose id (`split`) differs from its module (`gamma`) across accepted / in-map / stale / tracker-absent, none on publication-absent; preflight in-map CLI and `preflight_as_json` tests; red (6 errors), then green. One existing exact-match expectation (tracker-unknown after reading the Proposal) gained `moduleId`, as the Spec requires. Mutation filling moduleId with the Proposal id is caught. Command docs list `moduleId`, contract-checked
- [x] Checkpoint 1 (report): tests green
- [x] Task 2: real-host review; CHANGELOG; 0.51.3 — source review and preflight of collaboration-split (GitHub): `in-map`, proposalId collaboration-split, moduleId collaboration-interface. Both manifests 0.51.3, README `--ref v0.51.3`, CHANGELOG `## [0.51.3] - 2026-10-07`. macOS 15.7.3, `/bin/bash` 3.2.57: validate.sh pass, phase-guard 151, verify-artifacts 26, Codex smoke selftest pass
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 3: post-release evidence on the installed plugin
