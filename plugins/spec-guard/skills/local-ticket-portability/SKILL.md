---
name: local-ticket-portability
description: Archive, verify, restore, or explicitly hand off an enabled Local Epiq ticket ledger to GitHub or GitLab Issues; use for Local ticket portability, not ordinary ticket edits.
---

# Local ticket portability

Use the current project's pinned Epiq runtime and the CLI in
`hooks/local_ticket_portability.py`. Read `references/local-ticket-portability.md` for
commands, outputs, and failure states before a restore or hosted handoff.

Start with read-only `inventory`; `foreign` or `unknown` state worktree ownership is a stop,
not an empty ledger. A valid archive preserves raw event and media bytes, including pending
files. `verify --prove` uses disposable Git and Epiq state. It does not establish off-machine
durability; a separate copy must be verified on independent storage for that claim.

Restore only to a user-selected empty Git repository and empty Epiq global directory after
showing the exact archive and paths. A restore commits the project identity in that new repo
and establishes a separate state worktree. Never move, prune, overwrite, or sync the original
ledger to make a restore fit.

For hosted handoff, generate a private `handoff-preview` for an explicit issue, host, project,
and visibility. Inspect the complete preview, including all history, comments, source digest,
attachment status, and code-reference limits. Obtain authorization for that exact target and
content before invoking `handoff-publish --confirm`. Recheck source and target facts at publish
time. A public target may expose Local history, so apply the session's external-communication
sanitization rules before any hosted write. Never use `epiq_sync` as a substitute.

`verified` means the previewed snapshot was read back on the target; it does not make the
hosted provider the new daily Tracker. `partial`, `conflict`, and `publication-uncertain` leave
the Local source authoritative. Do not retry an uncertain create or comment just because an
immediate search is empty. Local does not need a PR/MR. This workflow does not mutate Proposal
Issues, the capability map, or `.agent/state.json`.
