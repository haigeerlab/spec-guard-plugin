# Todo: collaboration-dependency

- [x] Task 1: collaboration-is-gone check (D17) and its regressions — list = 33 moved paths (`commands/collaboration.md` dropped from it: kept as the handoff); scope adds README, CLAUDE.md, AGENTS.md, docs/optional-features.md, docs/workflow.md; `/spec-guard:collaboration` and the command path no longer forbidden. 12 regressions green. Repository run: 33 moved paths present plus exactly the remaining W7/command hits (`commands/collaboration.md` 7, README:27-28, optional-features:77, workflow:233). validate.sh is red by design until Task 4; nothing is pushed (D16)
- [ ] Task 2: delete the moved code; validate.sh; itemized test-count drop
- [ ] Task 3: handoff command, migration document, `<date>` filled
- [ ] Checkpoint (report): code removed, handoff and migration document in place
- [ ] Task 4: user docs (W7), manifests, CHANGELOG; boundary check green
- [ ] Task 5: baseline comparison
- [ ] Checkpoint (gate): module review; push, PR and version bump wait for round 1 (D16)
