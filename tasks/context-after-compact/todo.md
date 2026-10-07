# Todo: context-after-compact

- [x] Task 1: size after compaction (tests first) — `session_context._compacted`: Claude `compact_boundary` gives `postTokens` (unusable → 0), Codex `compacted` gives 0; the first of reading or compaction in the backward scan wins. 6 unit tests + CLI test + 3 phase-guard cases (Claude 601k→14k, Codex 223k→compacted, later reading wins), red (8 failures / first phase case) then green (phase-guard 154). Mutations caught: drop the branch (8 + 1), read preTokens (6 + 1), ignore Codex `compacted` (2 + 1)
- [x] Checkpoint 1 (report): tests green
- [ ] Task 2: hint wording
- [ ] Checkpoint 2 (report): tests green
- [ ] Task 3: retire session-handoff
- [ ] Checkpoint 3 (report): full suites green, verify-artifacts clean
- [ ] Task 4: real host + CHANGELOG + 0.52.0
- [ ] Checkpoint 4 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 5: post-release evidence
