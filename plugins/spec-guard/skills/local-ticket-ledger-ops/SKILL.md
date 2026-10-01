---
name: local-ticket-ledger-ops
description: Inspect, explicitly enable, or connect Spec Guard's optional same-Mac local ticket ledger.
---

# Local ticket ledger operations

Use this skill only for the optional Epiq-backed local ledger. It is a durable, same-Mac fallback
for a Git repository's linked worktrees when GitHub/GitLab Issues are unavailable. It is separate
from the Spec Guard collaboration mailbox: a mailbox message may mention a ledger short ID, but
neither system may automatically create, update, route, or require the other.

For ordinary listing, reading, creating, commenting, or closing an already enabled ticket, use the
`ticket` skill. This operations skill handles status, explicit installation, initialization, and
Claude/Codex MCP connection.

The ledger is not a local GitHub/GitLab replacement. Do not introduce project groups, participant
topology, role locks, assignments, scheduling, automatic claiming, routing rules, or automatic
remote synchronization. Ticket fields are voluntary collaboration context, not access control.

Resolve the installed plugin root and run only the side-effect-free status operation first:

```bash
python3 -B "$ROOT/hooks/local_ledger_runtime.py" status --format json
```

For a requested local data access check, run `storage-check --format json` through the same
script. It reads only the effective `EPIQ_GLOBAL_DIR` directory metadata, never ticket content;
`private-posix` is limited to POSIX owner and mode, not a complete ACL audit. Do not chmod the
real directory as part of this check.

Explain `absent`, `ready`, `initialized`, `conflict`, and `invalid` accurately. `conflict` means the Epiq state
worktree (`project.stateWorktree`, state `foreign`) is owned by another repository: relay its `owner` and `path`
and the remedies in `references/local-ticket-ledger-runtime.md`, and never move or delete a worktree without the
user's explicit approval. Also inspect `project.stateWorktree` when the top level says `initialized`:
`unknown` means ownership or location has not been proved, so explain its diagnostic and do not treat
the ledger as safe for writes. Never install Epiq, initialize a
repository, change Claude/Codex configuration, or start a service merely because a status check is
successful.

When the runtime is `ready`, status also shows `runtime.lock`: `locked` means it was installed from the
shipped lockfile; `unlocked` means an older install or a newer shipped lockfile. An `unlocked` runtime keeps
working; never replace it on your own. Replacing needs the user's explicit confirmation, then:

```bash
python3 -B "$ROOT/hooks/local_ledger_runtime.py" install --confirm-install --replace-unlocked --format json
```

The replacement is installed and verified in a temporary directory first; on any failure the old runtime is
kept unchanged, and ledger data in `.epiq/` and `__epiq_state__` is never touched. After replacing, tell the
user to restart the Claude/Codex session (or its MCP server) so the ledger MCP process uses the new runtime.

Run runtime installation only after the user explicitly asks to install it, with
`install --confirm-install`. Before initialization, run `preflight`; it requires a clean Git
worktree. Tell the user that initialization creates a committed `.epiq/project.json` and a
`__epiq_state__` branch. If `origin` is configured, stop and request a separate confirmation before
using `--allow-epiq-push`, because upstream Epiq will attempt a normal/state-branch push. Do not
infer `user-name`, `preferred-editor`, or `auto-sync`; collect the user's values.

Adapter inspection is read-only and available for either host:

```bash
python3 -B "$ROOT/hooks/local_ledger_adapters.py" codex
python3 -B "$ROOT/hooks/local_ledger_adapters.py" claude
```

Configuration writes are separate one-time, user-scoped actions and require both an explicit user
request and the adapter's `--confirm-install` flag. For Codex:

```bash
python3 -B "$ROOT/hooks/local_ledger_adapters.py" install-codex --confirm-install
```

For Claude Code:

```bash
python3 -B "$ROOT/hooks/local_ledger_adapters.py" install-claude --confirm-install \
  --claude-bin "$(command -v claude)"
```

They store no ledger secret, use a stdio command only, refuse a same-name managed entry, and
require the selected client to restart. Never configure a managed Codex app-server mode or alter
ChatGPT in Chrome.

The adapters gate the 10 high-risk Epiq tools (`epiq_sync`, `epiq_project_init`,
`epiq_skill_install`, project-level deletes/removals, and contributor email tools): Claude installs
add them to user-scoped `permissions.ask`; the Codex fragment's `enabled_tools` allowlist omits them.
For a host connected before this gate existed, offer the migration in the reference
(`install-claude-guard --confirm-install`, or the printed Codex `enabled_tools` line) only when the
user asks for it.

After the Epiq MCP is available, an Agent may voluntarily state a readable name and current activity,
look for existing relevant tickets, then create or update a bug, requirement, investigation, or
completion record as appropriate. Keep the interaction natural: do not force a fixed sequence,
owner, or workflow state. For current commands and exact safety boundaries, read
`references/local-ticket-ledger-runtime.md`.
