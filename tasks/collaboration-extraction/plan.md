# Plan: collaboration-extraction

Based on [`spec/collaboration-extraction.md`](../../spec/collaboration-extraction.md) (reviewed by the user on
2026-10-06, D5–D7 accepted). Branch `claude/collaboration-extraction`, worktree
`.claude/worktrees/cranky-allen-f2237a`. Reread
[`docs/collaboration-split-brief.md`](../../docs/collaboration-split-brief.md) after any context reset.

## Overview

Write down exactly what moves, build a script that moves it and proves the result, rehearse into a scratch
directory, show you the rehearsal, then create the real repository. Spec Guard's tree only gains this module's
own files.

## Architecture Decisions

- **Path file is the single source.** `scripts/collaboration-extraction-paths.txt` uses `git filter-repo`'s
  `--paths-from-file` syntax: literal paths, plus `old==>new` rename lines for D6. Earlier names (Spec
  assumption 6) are discovered with `git log --follow --name-only --format=` per file and added as literal
  paths with the same rename target.
- **The script verifies, not just moves.** `scripts/extract-collaboration.sh <base> <target>` clones with
  `--no-local --single-branch`, filters, drops tags and `origin`, then runs the Spec requirement 3 checks and
  exits non-zero on any mismatch. Byte identity uses `git rev-parse <base>:<path>` against
  `git rev-parse HEAD:<new path>` (blob ids), not file copies.
- **Base commit** = the commit on this branch that contains the path file, the script, and the plan (the last
  commit of Task 2), recorded in todo.md. Cloning from this local repository works for unpushed commits.
- **Owned list** gains the path file and the script (they name collaboration paths, so the boundary check
  needs them exempt); `collaboration-dependency` removes them with the rest.
- **Scratch first.** The rehearsal target is in the session scratchpad; the real target is created only after
  the rehearsal checkpoint.
- Shared verification for every task:

  ```bash
  /bin/bash scripts/validate.sh
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  ```

## Task List

### Task 1: Path file

**Description:** Write `scripts/collaboration-extraction-paths.txt` from Spec assumption 5 (owned list + C1/C2
copies + three split documents + D5 records) with D6 rename rules: `plugins/spec-guard/` →
`plugins/agent-relay/`, the records → `docs/history/spec-guard/<original path>`, split documents unchanged.
Add earlier names found by `git log --follow`. Add the path file to the owned list.

**Acceptance:** every listed current path exists at HEAD; every earlier name has a rename target; boundary
check green.

**Verify:** a one-off listing of current paths vs `git ls-files`; shared commands.

**Files:** `scripts/collaboration-extraction-paths.txt`, `scripts/collaboration-owned.txt`

### Task 2: Extraction script

**Description:** Write `scripts/extract-collaboration.sh` per the Architecture Decisions: argument checks
(base resolves, target absent or empty), clone, `git filter-repo --paths-from-file … --force` on the clone,
`git tag -l | xargs git tag -d`, `git remote remove origin`, then the checks: blob identity for every path,
no extra paths, `git log --follow` pre-boundary commits on three samples, and the re-rooted collaboration suite
result (expect 198 pass, the 4 D7 errors). Bash 3.2 compatible, no `cmd | grep -q`. Add the script to the
owned list.

**Acceptance:** `bash -n` clean; `check-bash32`/`check-grep-pipe` pass; refuses a non-empty target and an
unknown base.

**Verify:** the two refusal cases run by hand; shared commands.

**Files:** `scripts/extract-collaboration.sh`, `scripts/collaboration-owned.txt`

### Checkpoint (gate): install the tool

Ask for approval of `brew install git-filter-repo` unless it was already given at Plan review; install; record
`git filter-repo --version`.

### Task 3: Rehearsal into scratch

**Description:** Run the script with the recorded base commit into a scratchpad directory. Record HEAD, commit
count, file count, the check results, and the 4 D7 errors by name.

**Acceptance:** every check passes; the only suite errors are the 4 D7 tests.

**Verify:** the script's own exit code and printed report.

**Files:** `tasks/collaboration-extraction/todo.md`

### Checkpoint (gate): rehearsal review

Show the file tree, counts, history samples, and suite result; wait for approval to create the real target.

### Task 4: Create agent-relay

**Description:** Run the script into `/Users/vilin/Documents/haigeerlab/agent-relay` with the same base.
Confirm the result matches the rehearsal (same file list and blob ids). Delete the scratch rehearsal. Confirm
Spec Guard's tree has no changes outside this module and the guide plugin is still 0.49.0.

**Acceptance:** Spec success criteria 1–4.

**Verify:** the script's report; comparison with the rehearsal; shared commands.

**Files:** `tasks/collaboration-extraction/todo.md` (no Spec Guard code changes)

### Checkpoint (gate): module review

Stop and report per the brief format. Push, PR, and merge of this branch need separate approval; the new
repository is never pushed.

## Risks

- `git log --follow` can report false renames for small or similar files; each earlier name is checked by eye
  before it enters the path file.
- `--no-local` clone of a large history is slower; acceptable for a one-off run.
- `git filter-repo` refuses to run on a non-fresh clone without `--force`; the script uses a fresh clone and
  passes `--force` only for that clone.
