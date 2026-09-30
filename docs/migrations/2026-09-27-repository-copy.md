# Repository source copy to haigeerlab

The source was copied from `yizhongkaimail-collab/spec-guard-plugin` to
`haigeerlab/spec-guard-plugin`. The original repository was not changed.

The new repository contains the source repository's 82 branches and 81 tags,
including the same `main` commit at the copy point. Git history is preserved.
GitHub Issues, pull requests, release records, stars, and repository settings
are platform data, not Git refs, and were not moved by this copy. Historical
release evidence and old source URLs remain unchanged in prior records.

To receive future marketplace updates, add the current source in Claude Code:

```text
/plugin marketplace add haigeerlab/spec-guard-plugin
```

Keep the old source and local checkouts until any platform records and active
integrations that matter to you have been reviewed. Do not assume GitHub will
redirect links from the old location; this was a copy, not a transfer.

## Migration acceptance status (2026-09-27)

- A manual `workflow_dispatch` run passed on Ubuntu and macOS in the new
  repository ([run 36309399578](https://github.com/haigeerlab/spec-guard-plugin/actions/runs/36309399578)).
  This confirms the workflow can execute, not that automatic triggers work.
- GitHub recorded a `main` push after the workflow became active, but no `push`
  workflow run appeared. The cause is unconfirmed. Verify `pull_request` on the
  next substantive PR and `push` after its merge; do not make an empty commit
  solely to manufacture an event.
- The copied `v0.20.0` tag still points to the pre-migration release commit.
  A Release draft in the new repository is unpublished. Review the tag,
  package metadata, and installation evidence before publishing a new Release.

## Local ticket ledger

A copied repository keeps the Epiq `projectId` in `.epiq/project.json`, so a
copy and its original on the same Mac share one Epiq state worktree path. The
repository that created it owns the path, and the other repository's ledger
calls fail. Run the ledger `status` command: it reports `conflict` with the
owning repository. See `plugins/spec-guard/references/local-ticket-ledger-runtime.md`
for the cause and the remedies.
