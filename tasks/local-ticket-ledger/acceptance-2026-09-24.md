# Local ticket ledger host acceptance — 2026-09-24

## Runtime

- Backend: `epiq@1.11.0` (MIT), installed only after explicit user confirmation in
  `~/.spec-guard/local-ticket-ledger/runtime/`.
- Node: `v24.18.0` (meets the Node.js 18+ contract).
- Transport: local stdio MCP; no HTTP daemon, database server, listener port, token, or project
  `node_modules` directory.

## Real-host result

The user-scoped, no-secret `spec_guard_local_ledger` stdio entry was installed separately for native
Codex Desktop and Claude Code. After each host restarted, both successfully used `epiq_issue_list` in
the same repository.

Codex created issue `B7PAPH5` (`验证：Claude 与 Codex 本地账本互通`). Claude assumed the voluntary
identity `claude/e2e-validation`, read that issue, and added comment `01M38SBMFS5YGSEQ4ND02VGA1N`.
A fresh Codex MCP process then read the same comment and its author. This proves the real sequence:

```text
Codex creates a ticket → Claude reads and comments → a fresh Codex process reads the comment
```

The test ticket remains as explicit local acceptance evidence; it was not automatically converted into
a GitHub or GitLab Issue.

## Git-visible effects

After explicit user approval, Epiq initialization committed `.epiq/project.json` to `main`, created
`__epiq_state__`, and attempted its documented initial push. The push completed with no warnings:

- `main`: `2e58da297aadce2279c9f7dc81462ea2e117fcc5` (`[epiq:init-project]`)
- `__epiq_state__`: `519d2c126840905ba6450e5b9e4b3c5b0caf0dfc`

`auto-sync=false`. Routine local ticket creation and comment writes do not automatically synchronize
with a Git remote.

## Remaining boundaries

- One ledger is shared by linked worktrees of one Git repository on this Mac. Independent repositories
  retain independent ledgers; cross-project discussion remains the optional collaboration mailbox's job.
- There is no automatic GitHub/GitLab Issue creation, import, export, or synchronization.
- Spec Guard supplies a narrow adapter around Epiq; it does not implement a second forge, roles,
  assignment locks, routing, or scheduling. ChatGPT in Chrome is not configured through the managed
  Codex app-server path.
