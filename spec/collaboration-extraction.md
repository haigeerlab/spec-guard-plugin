# Spec: collaboration-extraction

## Objective

Create the local agent-relay repository at `/Users/vilin/Documents/haigeerlab/agent-relay` from Spec Guard's
history with `git filter-repo`, so that the collaboration code, its tests, and its records arrive with their
per-file history. This is a move, not a rewrite: file contents are byte-identical to Spec Guard at the
extraction base, and Spec Guard's own tree is not changed (deleting the moved code is
`collaboration-dependency`). Adapting the code to stand alone is agent-relay's translation modules.

Readers: the user reviewing the split and agents working in either repository.

Source decisions: [the split brief](../docs/collaboration-split-brief.md) §1.2 and the phase 0 decision
"migration = git filter-repo", [the interface document](../docs/collaboration-interface.md), and the owned list
[`scripts/collaboration-owned.txt`](../scripts/collaboration-owned.txt) built by `collaboration-boundary`.

## Assumptions

Confirmed by the user on 2026-10-06:

1. **Base.** The extraction runs on a fresh clone of this repository's `main` at the commit that contains this
   module's Spec and Plan (recorded in todo.md). The working repository is never filtered in place.
2. **Only `main`.** Other branches and all tags are dropped from the new repository: Spec Guard tags
   (`v0.x`) would be wrong in agent-relay, which starts its own semver.
3. **No remote.** The new repository has no `origin`; nothing is pushed (brief: deliverables are local).
4. **Tool.** `git-filter-repo` 2.47.0 (Homebrew, MIT, no dependencies) is installed with
   `brew install git-filter-repo`, after your approval at Plan review. It is a developer tool on this Mac,
   not a dependency of either plugin.
5. **Path set** = the owned list (32 paths) plus:
   - C1/C2 copies: `hooks/host_config_removal.py`, `hooks/test_host_config_removal.py`, `hooks/defect_guard.py`
     (Spec Guard keeps its originals for the ledger and closeout);
   - the split documents: `docs/collaboration-interface.md`, `docs/collaboration-split-brief.md`,
     `docs/baselines/collaboration-pre-split.md`;
   - the collaboration records (decision D5): `spec/{collaboration-messaging,collaboration-safe-defaults,
     authorized-session-delegation,host-native-session-routing}.md`, `spec/proposals/{collaboration-messaging,
     authorized-session-delegation}.md`, the four matching `tasks/` directories,
     `docs/decisions/{2026-09-28-xats-sunset,2026-10-04-native-only-collaboration-sunset}.md`,
     `docs/reports/{2026-10-04-a10-native-promotion-readiness,2026-10-04-native-only-collaboration-closeout}.md`,
     `docs/research/2026-09-17-agent-collaboration-design.md`, `docs/retirements/xats-collaboration-transport.md`.
   `docs/retirements/spec-github-bridge-*` are about the retired tracker bridge, not collaboration, and stay out.
   The exact list is one file written in Task 1 and reviewed at the Plan checkpoint.
6. **History of renamed files** is followed with `--paths-from-file` plus each file's earlier names found by
   `git log --follow --name-only`, so a file that was renamed inside Spec Guard keeps its older history.
7. **The interface document's authority moves.** From extraction on, agent-relay's copy of
   `docs/collaboration-interface.md` is authoritative (brief §1.2.3); Spec Guard's copy is replaced by a link in
   `collaboration-dependency`, not here.

## Decisions

All three taken as recommended by the user on 2026-10-06.

- **D5 records go with the code.** The four collaboration modules' Specs, plans, and decision records move with
  history, so agent-relay keeps the reasoning behind its behavior. Spec Guard keeps its copies (its capability
  map and history still reference them).
- **D6 layout.** Paths are re-rooted, file names are not changed:
  `plugins/spec-guard/` → `plugins/agent-relay/`; the records go under `docs/history/spec-guard/<original path>`
  so they cannot collide with agent-relay's own `spec/` and `tasks/` when spec-guard's convention is installed
  there (global step 4); the three split documents keep `docs/…`. D1 renames (MCP server, state root) and any
  file renames belong to agent-relay's translation modules.
- **D7 four tests that read Spec Guard files.** Measured on a copy of the path set: 15 files, 202 tests, of which
  198 pass standalone and 4 error because they read files that stay in Spec Guard (`docs/optional-features.md`,
  `scripts/validate.sh`) or that D6 re-roots (`spec/collaboration-messaging.md`,
  `docs/decisions/2026-10-04-native-only-collaboration-sunset.md`):
  `test_skill_entrypoints.py` (2) and `test_native_only_collaboration.py` (2). The extraction leaves file
  contents untouched and records these 4 as known, expected errors; agent-relay's first translation module
  (`acceptance-kit` or `packaging`) re-points them.

## Requirements

1. A path file `scripts/collaboration-extraction-paths.txt` in Spec Guard: every path in assumption 5 plus earlier
   names (assumption 6), and the rename rules of D6, in the format `git filter-repo --paths-from-file` accepts.
2. A script `scripts/extract-collaboration.sh` that, given the base commit and an empty target directory:
   clones the base with `--no-local --single-branch`, refuses a non-empty target, runs `git filter-repo` with the
   path file, drops tags, removes the `origin` remote, and prints the resulting HEAD, commit count, and file list.
   It never writes inside the Spec Guard working tree.
3. Verification printed by the same script and recorded in todo.md:
   - every path-set file at the base exists in the new repository at its re-rooted path, byte-identical
     (`git hash-object` on both sides);
   - no file outside the path set exists in the new repository;
   - `git log --follow` on three sample files shows commits from before the boundary module;
   - the collaboration suite (re-rooted) gives 198 pass and exactly the 4 errors of D7.
4. Spec Guard unchanged: `git status` clean apart from this module's own files; the three baseline suites pass.

## Commands

```bash
brew install git-filter-repo                      # once, after approval
/bin/bash scripts/extract-collaboration.sh <base-commit> /Users/vilin/Documents/haigeerlab/agent-relay
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Project structure

- `spec/collaboration-extraction.md`, `tasks/collaboration-extraction/` — this module.
- `scripts/collaboration-extraction-paths.txt`, `scripts/extract-collaboration.sh` — kept in Spec Guard as the
  reproducible record of how agent-relay was created; removed or archived by `collaboration-dependency`.
- New repository `/Users/vilin/Documents/haigeerlab/agent-relay` — created, not modified further here
  (skeleton, convention, and capability map are global step 4).

## Testing strategy

The extraction script's checks in requirement 3 are the test; a dry run into a scratch directory precedes the
real target. The boundary check's own scope is unchanged: the two new scripts name collaboration paths, so they
are added to the owned list (they define what moves).

## Boundaries

- Always: filter a fresh clone; verify byte identity; keep Spec Guard's tree unchanged.
- Ask first: installing `git-filter-repo`; creating the real target directory; any change to file contents in the
  new repository; adding paths beyond assumption 5.
- Never: run `filter-repo` on this working repository; push, tag, or add a remote to the new repository; delete
  anything from Spec Guard.

## Success criteria

1. `/Users/vilin/Documents/haigeerlab/agent-relay` exists as a local repository with only `main`, no tags, no
   remote, and exactly the re-rooted path set.
2. All path-set files are byte-identical to the base; sampled files keep pre-boundary history.
3. The re-rooted collaboration suite: 198 pass, 4 known errors (D7).
4. Spec Guard's three baseline suites pass; its tree is unchanged apart from this module's files.

## Open questions

None; D5, D6, D7 are decided.
