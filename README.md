# spec-guard

spec-guard protects two deliberately separate workflows:

- Proposal lifecycle: a revision-bound, read-only path that fixes shared facts
  to the remote default branch and reads GitHub/GitLab Proposal Issues only
  through explicit adapters. Only a policy-defined mainline may produce an
  accepted candidate; Issue stages remain human-written facts.
- Local multi-spec convention: a small directory convention for capability
  maps, module specs, plans, and local task lists.

It also provides an optional, same-Mac collaboration mailbox for Claude Code
and Codex sessions. The mailbox does not change the Proposal lifecycle or
automate Git, Issue, Ticket, project grouping, or task assignment.

The Proposal lifecycle does not create or modify Issues, pull requests, merge
requests, branches, tasks, remote refs, or Proposal lifecycle state.

Install from the public marketplace with
`/plugin marketplace add yizhongkaimail-collab/spec-guard-plugin`.

The public source was recovered to `yizhongkaimail-collab/spec-guard-plugin`
in v0.16.2. Existing cached installs continue to run, but future marketplace
updates require manually re-adding this source; see the
[source-recovery migration note](docs/migrations/v0.16.2-source-recovery.md).

## Breaking migration after v0.14.0

The mutable GitHub/GitLab tracker bridge was retired.  Removed surface:

- remote tracker projection, task selection, workspace binding, and delivery;
- the former tracker-oriented commands and skills; and
- tracker synchronization previews in the desktop adapter.

Existing `.agent/state.json`, remote records, archives, release evidence, and
Git history are preserved untouched.  They are historical evidence, not input
for the new workflow.  Complete, abandon, or otherwise preserve outstanding
remote tracker work with v0.14.0 before upgrading.  See
[the migration guide](docs/migrations/v0.15-legacy-tracker-retirement.md).

## Local convention

Run the setup command in a project that wants the local convention.  Use its
preview mode first; it only creates or updates local files after confirmation.
The result is:

```text
spec/CAPABILITY-MAP.md
spec/<module-id>.md
tasks/<module-id>/plan.md
tasks/<module-id>/todo.md
.agent/state.json        # local active-module context only
```

The local state file is never a Proposal requirement or candidate pool.

## Local agent collaboration

The optional collaboration runtime lets Claude Code and Codex sessions on the
same Mac exchange durable free-text technical messages without manually
relaying them. Each session supplies only its own display context (for example,
name, project path, role, and current work); Spec Guard does not infer project
relationships or route messages automatically.

Start with `/spec-guard:collaboration` to inspect the local state. Initialization,
background service enablement, host configuration, and stale-agent removal all
require an explicit user request. The default XATS transport is loopback-only
and keeps its token in `~/.spec-guard/collaboration/`, not in project files or
MCP configuration. It gives native Codex Desktop persistent mailbox delivery,
but not active wake-up.

An experimental native transport can be installed and selected only through a
separately approved, archive-guarded cutover. It uses one private local mailbox
and may wake idle Claude Code and Codex Desktop conversations; an unsuccessful
wake leaves the message available for later reading. It does not switch Codex to
a managed app-server or change either Chrome integration. See the
[runtime reference](plugins/spec-guard/references/collaboration-runtime.md) for
the explicit setup and rollback boundaries.

## Local tickets

When GitHub or GitLab Issues are unavailable, the optional Epiq-backed local
ledger records bugs, requests, and discussion for linked worktrees of one Git
repository on the same Mac. After explicit one-time setup through
`/spec-guard:local-ticket-ledger`, use `/spec-guard:ticket` in Claude Code or
ask Codex to “show local tickets” or “record a bug.” The agent can include a
ticket's short ref in a separate collaboration message. An agent working in a
different repository needs the source project and a problem summary in that
message; the short ref alone does not grant access to this repository's ledger.
See the [ledger reference](plugins/spec-guard/references/local-ticket-ledger-runtime.md).

## Proposal mainline review

Proposal authors publish v2 documents to the remote default branch. At an
explicit mainline module boundary, the plugin reads the fixed remote Proposal
pool, policy and Issue facts, then returns candidate or human-decision results.
It never accepts automatically. Before a human creates a promotion branch,
preflight requires a fresh accepted Issue and matching immutable attestation;
post-merge proof verifies the declared capability-map insertion plus module Spec
and Plan. Existing v1 published Proposals remain readable but must be republished
as v2 before acceptance or promotion. See the
[migration guide](docs/migrations/proposal-mainline-review-v2.md).

<!-- SYNC:claude-block-local BEGIN -->
````markdown
<!-- BEGIN:agent-skills-convention -->
## Agent Skills 集成约定

> 由 `/spec-guard:setup-convention local` 生成。任务托管在**本地 todo.md**（Addy 原生路径）。
> 保留 `<!-- BEGIN/END -->` 标记，`/spec-guard:setup-convention --replace` 靠它升级本块。

- 能力图 `spec/CAPABILITY-MAP.md`，模块 spec `spec/<module-id>.md`（kebab-case，一次选定中途不改名）
- **不要**在项目根建 `SPEC.md` / `SPEC-<module>.md` —— `/build` 只认根 `SPEC.md`、
  `docs/SPEC.md`、`spec/` 三条路径，**只有第三条是通配的**
- 每个模块的产物互相隔离：`tasks/<module-id>/plan.md` + `tasks/<module-id>/todo.md`，
  **不要共用 `tasks/plan.md`**
- `/build` 取任务：读 `.agent/state.json` 的 `activeModule`，从该模块的 `todo.md`
  取第一个未勾选项，**不跨模块取**
- 切换 `activeModule` 前当前模块不能有进行中的 task；切换后重读该模块的 spec 和 plan
- 阶段交接或停止时，加载 `spec-guard:spec-guard-ops` 的共享检查点规则，预告已授权下一步。
<!-- END:agent-skills-convention -->
````
<!-- SYNC:claude-block-local END -->

## Verification

```bash
/bin/bash plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

The complete validation suite is offline.  Publishing, tagging, and any remote
action require separate authorization.
