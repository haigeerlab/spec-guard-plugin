# spec-guard

[简体中文](README.md) | English

spec-guard is a companion plugin for [agent-skills](https://github.com/addyosmani/agent-skills), for Claude Code and
Codex. agent-skills' `/spec` can already split a requirement into a capability map and one Spec per module, but `/plan`
always writes the same `tasks/plan.md` and `todo.md`, so modules overwrite each other and the next turn does not know how
far the work has got. spec-guard gives each module its own Spec, Plan and todo, and tells the agent at the start of
every turn which module to work on and how far it has got.

Linked documents other than this README are in Chinese.

## Use cases and limits

**Good fit**: you already use agent-skills, and your project splits into several modules, or several agents or
worktrees work on it in parallel.

**Not needed**: single-file scripts or one-off small changes; the single-Spec flow of agent-skills is enough.

It solves three problems:

| Problem | What spec-guard does |
|---|---|
| Modules share one `tasks/plan.md` and overwrite each other from the second module on | A multi-module layout: one capability map, and a Spec, Plan and todo per module |
| The agent does not know which module is current or how far it is | The current stage is injected at the start of every turn, e.g. "`NEEDS_PLAN`: write the plan for `billing`" |
| A new requirement turns up halfway, and editing the capability map by hand breaks it | Quick insert: propose a new module at a checkpoint; it is validated and previewed, and inserted after you confirm |

Limits:

- Installing it **does not switch anything on**. It works only in projects where setup has been run; it is silent everywhere else.
- The stage hint only reports facts and suggests a next step. It never writes files or changes anything remote.
- Writing the capability map, creating tickets, or changing GitHub/GitLab always shows a preview first and runs only after you explicitly confirm.

## Core concepts

- **Capability map** `spec/CAPABILITY-MAP.md`: one table listing every module, its responsibility and dependencies,
  plus one Build order line.
- **Module**: one row of the capability map. Each module has `spec/<module>.md` (the Spec) and
  `tasks/<module>/plan.md` and `todo.md`.
- **Stage**: spec-guard infers progress from those files, e.g. `MAP_ONLY` (only a capability map), `NEEDS_PLAN`,
  `BUILDING`, `MODULE_DONE`, `DONE`, and injects it for the agent: in full when the state changes, in a new session or
  after compaction, as one line on the other turns.
- **Quick insert and Proposal**: to add a requirement halfway, insert a module at a checkpoint; when the addition needs
  a recorded, reviewed decision, use the Proposal flow.

Terms and design reasons: [concepts](docs/concepts.md) (Chinese).

## Prerequisites

- The [agent-skills](https://github.com/addyosmani/agent-skills) plugin: `/spec`, `/plan` and `/build` come from it, not from spec-guard.
  Its [README](https://github.com/addyosmani/agent-skills#quick-start) is the authority for installing it; when this was written (2026-10-28):
  - Claude Code: `/plugin marketplace add addyosmani/agent-skills`, then `/plugin install agent-skills@addy-agent-skills`;
  - Codex: `codex plugin marketplace add addyosmani/agent-skills`, then `codex plugin add agent-skills@agent-skills`. Codex has no such slash
    commands; call the matching skill with `@`, for example `@spec-driven-development`;
- `bash`, `git`, `python3` (3.9 or later; the one that ships with macOS is fine);
- A host: Claude Code, or Codex (CLI or desktop app);
- Optional: `gh` (GitHub) or `glab` (GitLab) logged in for the Proposal flow or hosted tickets; macOS and Node.js for
  the local ticket ledger.

## Quick start

**1. Install the plugin**

| Claude Code | Codex |
|---|---|
| `/plugin marketplace add haigeerlab/spec-guard-plugin` | `codex plugin marketplace add haigeerlab/spec-guard-plugin --ref v0.85.0` |
| `/plugin install spec-guard@spec-guard-marketplace` | `codex plugin add spec-guard@spec-guard-marketplace` |
| Open a new session and review and trust spec-guard's `UserPromptSubmit` hook and its two `SessionStart` hooks under `/hooks` | Open a new session |

For Codex, use the version of the [latest release](https://github.com/haigeerlab/spec-guard-plugin/releases) as `--ref`.

**2. Enable it in a project**

| Claude Code | Codex |
|---|---|
| Run `/spec-guard:setup-convention`, read the preview, confirm to write | Ask the agent to "install the convention in this project with spec-guard-ops", read the preview, confirm to write |

Setup creates `spec/` and `tasks/`, and writes a [convention block](docs/convention-block.md) into `CLAUDE.md`
(`AGENTS.md` for Codex).

**3. Start a multi-module project**

Write the capability map with agent-skills' `/spec`, then for each module write the Spec, generate the plan with
`/plan`, and implement with `/build`. The stage hint tells the agent what to do at each step.

**Shortest path**: install the plugin → run setup once in the project → talk to the agent as usual and follow the
stage hint.

The full flow, what each stage means, and the two ways to add requirements: [workflow](docs/workflow.md) (Chinese). Using it for the
first time? Start with [getting started](docs/getting-started.md) (Chinese): a small example from install to the first module's
acceptance, with the stage hint the agent sees at every step, a table of what you do and what the agent does, and when to turn on each optional feature.

## Features at a glance

| Area | Command (Claude Code) | What it does |
|---|---|---|
| Convention and stage | `/spec-guard:setup-convention` | Install the multi-module convention in a project; `--replace` upgrades the block, `--dry-run` only previews |
| | `/spec-guard:teardown-convention` | Remove the convention and keep your Specs and plans |
| | `/spec-guard:phase` | Show the current stage and the suggested next step |
| | `/spec-guard:verify-artifacts` | Check the capability map, module Specs, review markers and other artifacts |
| | `/spec-guard:config` | View or set project config (artifact language, review cadence and more; every key is in the command reference) |
| | `/spec-guard:review-mark` | Record whether a Spec or Plan is approved; the agent runs it after you approve |
| | `/spec-guard:module-suspend` | Suspend or resume a module that is waiting on something outside |
| | `/spec-guard:link-project` | Point a session whose folder is not the project at the actual project |
| Adding requirements | `/spec-guard:add-module` | Insert a new requirement into the capability map as a module at a checkpoint (preview, then confirm) |
| | `/spec-guard:proposal-submit`, `proposal-review`, `proposal-promotion-preflight`, `proposal-promotion-proof`, `proposal-closeout` | The Proposal flow when the decision must be on record in an Issue: submit, review, preflight, proof, closeout |
| Tickets | `/spec-guard:ticket` | Record a bug or a request in plain language; the hosted flow when you choose GitHub/GitLab. Without the local ticket ledger enabled it only diagnoses and gives the step to enable it; see [optional features](docs/optional-features.md#本地事项账本) |
| | `/spec-guard:local-ticket-ledger` | Inspect or enable the local ticket ledger |
| | `/spec-guard:local-ticket-portability` | Verify, archive, restore or hand off local tickets |
| | `/spec-guard:tracker-default` | Set the project's default ticket backend, used only to prefill previews |
| Documentation and history | `/spec-guard:documentation-baseline`, `documentation-impact`, `documentation-verification` | The documentation baseline, a module's documentation impact, and the delivery check |
| | `/spec-guard:history-integrity` | Verify the capability history left by older versions |
| Reports | `/spec-guard:map` | Module progress table: status, review, what is blocking |
| | `/spec-guard:cost-report` | Tokens of the main agent and subagents and main-session turns, per task |
| Several modules at once | `/spec-guard:checkout-role` | Label each checkout's role when the switch is on |

Codex does not load slash commands; say one sentence to the agent instead, for example "use spec-guard-ops to show the stage".
Arguments and output of every command, and what to say in Codex: [command reference](docs/commands.md) (Chinese).

## What it looks like, and a self-check

Once enabled, send the agent any message and it sees a stage hint like this in its context:

```text
## spec-guard local workflow

Current stage: **NEEDS_PLAN**

- Capability map: present
- Current module: `billing` (next in Build order)
- Modules 3 · Specs 2 · Plans 1 · In progress 0 · Done 1

Suggested next step: create `tasks/billing/plan.md` and `tasks/billing/todo.md` (for example with `/plan`).
```

Self-check:

- `/spec-guard:phase` shows the same stage information;
- `/spec-guard:verify-artifacts` should report every check as passed;
- In a project where setup has not been run, the hook prints nothing. That is expected.

## Update and uninstall

**Update**

| Claude Code | Codex |
|---|---|
| `claude plugin marketplace update spec-guard-marketplace` | Change the `ref` of `[marketplaces.spec-guard-marketplace]` in `~/.codex/config.toml` to the new version |
| `claude plugin update spec-guard@spec-guard-marketplace`, then reopen the session | `codex plugin marketplace upgrade`, then open a new session |

Claude Code fixes the plugin directory when a session starts: without reopening, commands in an already open session
keep calling the old version's scripts while the hook may already be the new one, so two versions mix.

When Codex is upgraded from an older version, trust each newly added `SessionStart` hook once and restart Codex, or that
injection is skipped without an error: coming from 0.60.x or earlier, the one injected after compaction; coming from
0.68.x or earlier, also the one for session start and clear.

In a project with an older convention block, preview `/spec-guard:setup-convention --replace --dry-run` after updating,
and replace once you have confirmed. Keep your own rules inside the block's local section
(`<!-- BEGIN:spec-guard-local -->` … `<!-- END:spec-guard-local -->`); replacing keeps it.

**Uninstall**

1. In every project that used it, run `/spec-guard:teardown-convention` (preview with `--dry-run` first). It removes
   the convention block and stops the stage hint; your `spec/` and `tasks/` stay.
2. If you used the local ticket ledger and connected it to a host, remove what it wrote into the host configuration
   before removing the plugin (skip this if you never connected it):
   - Claude Code: run `claude mcp remove --scope user spec-guard-local-ledger`, then delete the 10 rules starting with
     `mcp__spec-guard-local-ledger__` from `permissions.ask` in `~/.claude/settings.json`;
   - Codex: run `codex mcp remove spec_guard_local_ledger` (or delete the whole `[mcp_servers.spec_guard_local_ledger]`
     table from `~/.codex/config.toml` by hand);
   - if you no longer use the ledger, you can delete the managed runtime `~/.spec-guard/local-ticket-ledger/runtime`
     (under `SPEC_GUARD_STATE_DIR` when that is set).

   The ledger data (`.epiq/` in the project, the `__epiq_state__` state worktree, `~/.epiq-global`) is your record and
   does not need to be deleted; to take it elsewhere, archive it with `local-ticket-portability` first.
3. Then remove the plugin: `claude plugin uninstall spec-guard@spec-guard-marketplace` for Claude Code;
   `codex plugin remove spec-guard@spec-guard-marketplace` for Codex, and
   `codex plugin marketplace remove spec-guard-marketplace` once you no longer need the source.

## Developing several modules at once (optional)

By default spec-guard moves one module at a time. When there are many modules and several are independent, several sessions can each work on
one: spec-guard does the **planning**, and the companion plugin module-crew does the **running** (opening sessions, creating worktrees,
messaging, merging). spec-guard does not depend on it: without module-crew, turning the switch on gives only the planning-layer
rules below. With the switch off none of this appears and nothing changes.

1. Set `moduleConcurrency` to `on` with `/spec-guard:config` (only once everyone is on 0.68.0; earlier versions treat the whole configuration as invalid; from 0.84.0 on, an unknown key is ignored on its own).
2. At the capability-map review the agent adds a concurrency assessment: which modules could become comma groups in the Build order, which are worth moving up.
3. Each module Spec gets a "并行边界" (concurrency boundary) section naming the directories it owns; `verify-artifacts` checks its format and the final acceptance marks files changed outside it.
4. `/spec-guard:map` lists the modules that can start together, overlapping boundaries, and the progress in each module worktree.
5. `/spec-guard:checkout-role` gives each checkout a role: a module checkout's stage hint points only at its module, the coordinating checkout is never told to build.

Who records review approvals and who merges locally is set out in its own section of the shared checkpoint rules ("协调会话的批准与合并"); merging into the remote is always yours.

## External interface

Other plugins that read progress and review state should use `interface.json` at the plugin root: for every entry it lists
(the read-only commands, the switch and checks used for developing several modules at once, and so on) it gives the format
version, the exit codes and what each value means, so a reader can check the interface version. See "对外接口" in [docs/design.md](docs/design.md).

## Data and privacy

- **What it reads**:
  - At the start of every turn the hook reads only this project's capability map, module Specs, plans, todos, the
    settings under `.agent/` and local git refs (it never fetches).
  - At a review checkpoint it also reads this machine's plugin records to see whether delegate is installed.
  - From the session transcript the host provides it reads only the tail: the latest usage numbers (to suggest
    freeing context at a module boundary), the state code of its own last injection (one line when nothing changed)
    and compaction markers; on Codex it also reads the first record to tell an unattended run. It does not read the
    conversation between you and the agent.
  - In a project with the local ticket ledger enabled, the hook only checks whether `.epiq/project.json` exists; it
    does not read the ledger.
  - A project with only the ledger and no convention still gets the ledger reminders at session start, after a clear
    or a compaction, and when another session's message arrives.
- **What it writes**: the hook writes no files. Commands write only after you have seen a preview and confirmed:
  `spec/`, `tasks/`, `.agent/` and the convention block in `CLAUDE.md`／`AGENTS.md` inside the project; machine state
  goes to `~/.spec-guard/` (move it with `SPEC_GUARD_STATE_DIR`).
- **When it goes online**: only when you explicitly use one of these. Proposal commands, `ticket` with GitHub/GitLab,
  and archiving, restoring or handing over local tickets reach GitHub／GitLab through your local `gh`／`glab` and
  `git ls-remote`／`git fetch`, using the logins those tools already have; enabling the local ticket ledger installs
  its runtime with `npm ci` from the lock files shipped in the package. The hook and every other command, such as
  `map`, `phase`, `verify-artifacts`, `review-mark` and `cost-report`, stay offline.
- **Usage statistics and uploads**: `cost-report` reads the local Claude Code (`~/.claude/projects/`) and Codex
  (`~/.codex/sessions/`) session transcripts offline. It uses their token counts, user prompt times (to cut the module
  wrap-up), whether a tool call errored and subagent spawns (to count a subagent's usage toward the task that started
  it), only in memory during the run to attribute them to tasks; the output is counts only, never session content, and is printed to the terminal. The plugin has no
  telemetry and reports nothing anywhere.

Details: [design and architecture](docs/design.md) (Chinese).

## Troubleshooting

| Symptom | Check first |
|---|---|
| No stage hint appears | Has setup been run in this project? In Claude Code, is the hook trusted under `/hooks`? Did you open a new session after installing? |
| The stage is `MAP_INVALID` | Run `/spec-guard:verify-artifacts`; it points at what is wrong in the map, e.g. the header line of every module table when there is more than one |
| The hint says python3 is unavailable or cannot run | Check that `python3 --version` is 3.9 or later and on the PATH the host starts with; the hint returns on the next turn once fixed |
| spec-guard is missing in Codex | Run `codex plugin list` and check spec-guard is installed and enabled; after changing `ref`, run `codex plugin marketplace upgrade` |

More cases (what `UNKNOWN`, `Paused`, `Suspended` and other hints mean): [troubleshooting](docs/troubleshooting.md)
(Chinese).

## Architecture and documentation

**Users**

- [Getting started](docs/getting-started.md): a real-run small example, who does what, choosing optional features
- [Workflow](docs/workflow.md): from nothing to delivery, two ways to add requirements
- [Command reference](docs/commands.md): arguments and output of every command, and the Codex mapping
- [Troubleshooting](docs/troubleshooting.md)
- [Concepts](docs/concepts.md)
- [Optional features](docs/optional-features.md): local ticket ledger, documentation governance, capability history;
  session collaboration has moved to the separate agent-relay plugin
- [Convention block](docs/convention-block.md): what setup writes into `CLAUDE.md` / `AGENTS.md`
- [Migrations](docs/migrations/), [changelog](CHANGELOG.md)

**Developers**

- [Design and architecture](docs/design.md)
- [Contributing](CONTRIBUTING.md)
- [Decisions](docs/decisions/)

**Maintainers** (releases and repository upkeep; not needed to use the plugin):
[maintainer workflow](docs/maintainer-workflow.md), [release process](docs/release-process.md),
[failure modes and review lenses](docs/lenses.md), [upstream analysis](docs/upstream-analysis.md).

This repository manages its own development with spec-guard: the root `spec/` and `tasks/` are this repository's
module records, not templates for users to copy.

## Development, contributing and feedback

- Found a bug or want something: open a [GitHub issue](https://github.com/haigeerlab/spec-guard-plugin/issues) with
  the matching template; [contributing](CONTRIBUTING.md) says what to include.
- Found a security vulnerability: do not open a public issue; report it privately as described in the
  [security policy](SECURITY.md) (Chinese).
- Want to change code: read [contributing](CONTRIBUTING.md) and [design and architecture](docs/design.md) first.
- Maintainer documents: see the "Maintainers" group above.

## License

[MIT](LICENSE)
