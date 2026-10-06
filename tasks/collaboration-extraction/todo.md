# Todo: collaboration-extraction

- [x] Task 1: path file (owned list + C1/C2 + split documents + D5 records, D6 renames, earlier names) — 54 entries → 92 tracked files: 35 plugin paths, 3 split documents, 16 records; `git log --follow` found no renamed file in the set (deleted XATS-era predecessors are retired history, not in the Spec set); path file added to the owned list (33); three suites green
- [x] Task 2: extraction script with built-in verification — `bash -n`, bash32, grep-pipe clean; refuses unknown base, non-empty target, target inside the repo (rc 2 each, nothing created); path file read from the base commit itself; script added to the owned list (34); three suites green. This commit is the extraction base
- [x] Checkpoint (gate): install git-filter-repo (approval) — approved at Plan review 2026-10-06; Homebrew git-filter-repo 2.47.0 installed (`git filter-repo --version` → a40bce548d2c)
- [ ] Task 3: rehearsal into the scratchpad
- [ ] Checkpoint (gate): rehearsal review; approval to create the real target
- [ ] Task 4: create /Users/vilin/Documents/haigeerlab/agent-relay and compare with the rehearsal
- [ ] Checkpoint (gate): module review; push, PR, and merge need separate approval
