# Plan: local-ticket-ledger daily use

Existing scope: [`../../spec/proposals/local-ticket-ledger.md`](../../spec/proposals/local-ticket-ledger.md)
Existing backend acceptance: [`acceptance-2026-09-24.md`](acceptance-2026-09-24.md)

## Goal and acceptance

An enabled Claude Code or Codex session can handle a local ticket from one natural request: list or
find it, read it, create it, comment, update its state, or close it. When the request also names a
collaboration recipient, the agent can send a separate message with the ticket's short reference.
The user does not need to know Epiq MCP tool names, board IDs, swimlane IDs, or Git state branches.

The first complete scenario is same-repository, same-Mac worktrees: one agent records a bug, sends
its ref to another agent, the second agent reads and comments, and the first agent verifies and
closes it. Independent repositories still have independent ledgers. For a cross-project message,
include the source project and a useful summary because the recipient cannot resolve another
repository's local ticket solely from its ref.

## Implementation

1. Add one short, natural-language `ticket` skill for ordinary operations. Use the already installed
   `epiq_*` MCP tools and the caller's current Git repository. Reads choose `epiq_issue_get` for a
   known ref or `epiq_issue_list` for discovery. Creation uses an existing open swimlane; choose
   from context and ask only if the available lanes are genuinely ambiguous. Do not create boards,
   lanes, tags, assignments, or agent identities as a side effect of a ticket request.
2. Expose the same entry as a Claude Code `/spec-guard:ticket` command. Keep setup and repair in the
   existing `local-ticket-ledger-ops` entry. When MCP is unavailable, give one accurate next step
   after a read-only status check.
3. Update the operator reference and README with the everyday entry and one concrete handoff
   example. A message is sent only when the user's request includes a recipient or explicitly asks
   for notification; a successful ticket write is not represented as successful message delivery.

## Verification

- Validate the skill frontmatter and command name against the repository's validators.
- Check the named MCP tools against the pinned `epiq@1.11.0` runtime.
- Run the focused local ledger and collaboration tests plus repository validation.
- Review the final diff for hidden setup, remote synchronization, and cross-project ref claims.

## Boundary

This pass adds no storage backend, network service, GitHub/GitLab synchronization, workflow engine,
or automatic ticket creation from mailbox messages. It does not alter the accepted capability map or
the existing Proposal's revision-bound text.
