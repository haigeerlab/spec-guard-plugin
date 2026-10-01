# Local ticket archive and explicit handoff

Run from a Git repository with an initialized Local Epiq 1.11.0 ledger. Set `ROOT` to the
installed Spec Guard plugin directory; replace angle-bracket placeholders with user-selected
paths and identities.

```bash
python3 -B "$ROOT/hooks/local_ticket_portability.py" inventory --project <repo>
python3 -B "$ROOT/hooks/local_ticket_portability.py" archive --project <repo> --output <new-private-directory>
python3 -B "$ROOT/hooks/local_ticket_portability.py" verify --archive <archive-directory>
python3 -B "$ROOT/hooks/local_ticket_portability.py" verify --archive <archive-directory> --prove
```

The archive contains `manifest.json`, a single-state-branch Git bundle, the Epiq project
identity, raw event/media files, and a private mapping journal snapshot if one exists. It
does not contain project source or other Git branches. `verify --prove` compares all source
events with Epiq's materialized view and checks a disposable write. Copy the archive to
independent storage and verify that copy before relying on it for disaster recovery. Archive
creation stops if the destination directory does not retain private POSIX mode (0700).
Archive and private preview outputs cannot be placed inside any linked worktree of the
source repository.

```bash
python3 -B "$ROOT/hooks/local_ticket_portability.py" restore \
  --archive <archive-directory> --project <empty-git-repo> \
  --epiq-global-dir <empty-epiq-directory> --confirm
```

The target repo must have no files or refs and cannot be a linked worktree sharing another
Git common directory; prepare an independent empty repository. Configure its Git author first. The Epiq directory
must exist and be empty, and must not share the original project ID's active global worktree.
Restore first proves the archive in isolation, then commits `.epiq/project.json` on the new
repo's default branch and creates `__epiq_state__` with its worktree. It does not push. If a
write is interrupted, it preserves partial target data for inspection; do not rerun into that
nonempty target. The mapping journal is exported in the archive but not imported into a new
project's user-level partition automatically. The proof uses a disposable Epiq identity;
after real restore, configure a local Epiq user identity through Epiq's setup flow before the
first write. The restore result reports `localIdentitySetupRequired: true` for this boundary.

```bash
python3 -B "$ROOT/hooks/local_ticket_portability.py" handoff-preview \
  --project <repo> --issue-id <full-epiq-id> --platform <github-or-gitlab> \
  --host <host> --target <owner/repo-or-group/project> \
  --visibility <public-or-internal-or-private> --output <new-private-preview.json>
python3 -B "$ROOT/hooks/local_ticket_portability.py" handoff-publish \
  --project <repo> --preview <private-preview.json> --confirm
```

`handoff-preview` reads source files and target metadata; it does not write to either. It
rejects unknown metadata rights or visibility mismatch. The preview file is mode 0600 and
contains the full Local history, so keep it private. A GitLab target using HTTP and any
unverified attachment transfer are called out in its limitations. `handoff-publish` can create an Issue,
post historical comments, and set closed/open state on the exact target. Show the complete
preview and obtain target-specific authorization before running it. The command rechecks the
source digest and remote metadata, records intent privately, then reads back every managed
marker. GitHub PRs and GitLab system notes are excluded from issue/comment matching.

If attachment bytes cannot be uploaded and read back under the target's visibility, the result
remains `partial` and the original Local media stays in the archive. Code references on the
target, short or indirect code references, and API token write scope are not proven by the
read-only preview. A failed or lost response can produce `publication-uncertain`; inspect
remote markers and the private journal before any retry. Two matching Issues or an edited
managed Issue/comment are `conflict`. The module does not automatically switch later daily
work to GitHub/GitLab, and it does not close the Local ticket.

An API response with a recognized, definite 4xx rejection returns `provider-rejected` with
its status code. No Issue or comment attempt is treated as successful, so correct the
permission or content, create a fresh preview if the source changes, and retry. A timeout,
server failure, or response without a reliable status remains `publication-uncertain`.
Large histories can exceed provider limits; the CLI does not split them automatically and
must not truncate the Local context to force publication.

Current handoff and restore locks use private retained files with OS advisory locks; a
process crash releases the OS lock. If a lock is reported as legacy or damaged, first prove
no older publisher or restore is still running, preserve the lock and journal for diagnosis,
then remove only that stale lock file before retrying. Never delete a mapping journal or a
partial restore target to bypass a conflict. Handoffs started before the stable source
digest change use version 1. Regenerate their preview with `handoff-preview --legacy-format`
and review it before continuation; a default version 2 preview returns
`preview-incompatible` without changing the journal. An actual old source digest mismatch
remains `conflict` rather than silently rewriting the already published remote body.
