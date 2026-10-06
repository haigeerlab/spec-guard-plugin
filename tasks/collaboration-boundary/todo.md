# Todo: collaboration-boundary

- [x] Task 1: owned list and boundary check (not wired; record today's violation list) — 23 hits: W1 `skills/ticket/SKILL.md:76`, W1b (baseline missed) `references/local-ticket-ledger-runtime.md:258`, W5 `validate.sh:103-112`, W6 `test_skill_entrypoints.py:8,9,21,69,107`, W8 `defect_guard.py:17`, C3 `test_host_config_removal.py:12,13,141,151,153`. W2-W4 use plain words only (not hits; reworded in Task 4 per Spec). `agent-relay:<skill>` allowed; regression 12 cases; three suites green
- [ ] Task 2: detection helper, its tests, interface §11 update (D4, assumption 7)
- [ ] Task 3: test-side cuts C3, W6, W5 with per-file count comparison
- [ ] Task 4: text cuts W1 (D3), W2–W4, W8
- [ ] Checkpoint (report): coupling points cut, check green, suites green
- [ ] Task 5: wire the check into validate.sh and compare with the baseline
- [ ] Checkpoint (gate): module review; push, PR, and merge need separate approval
