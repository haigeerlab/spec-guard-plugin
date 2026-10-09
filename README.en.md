# spec-guard

[简体中文](README.md) | English

spec-guard is a companion plugin for [agent-skills](https://github.com/addyosmani/agent-skills), for Claude Code and
Codex. agent-skills assumes one Spec and one plan per project; spec-guard lets one project be split into modules, each
with its own Spec, Plan and todo, and tells the agent at the start of every turn which module to work on and how far
it has got.

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
  `BUILDING`, `MODULE_DONE`, `DONE`, and injects it for the agent every turn.
- **Quick insert and Proposal**: to add a requirement halfway, insert a module at a checkpoint; when the addition needs
  a recorded, reviewed decision, use the Proposal flow.

Terms and design reasons: [concepts](docs/concepts.md) (Chinese).

## Prerequisites

- The [agent-skills](https://github.com/addyosmani/agent-skills) plugin;
- `bash`, `git`, `python3` (3.9 or later; the one that ships with macOS is fine);
- A host: Claude Code, or Codex (CLI or desktop app);
- Optional: `gh` (GitHub) or `glab` (GitLab) logged in for the Proposal flow or hosted tickets; macOS and Node.js for
  the local ticket ledger.

## Quick start

**1. Install the plugin**

| Claude Code | Codex |
|---|---|
| `/plugin marketplace add haigeerlab/spec-guard-plugin` | `codex plugin marketplace add haigeerlab/spec-guard-plugin --ref v0.55.1` |
| `/plugin install spec-guard@spec-guard-marketplace` | `codex plugin add spec-guard@spec-guard-marketplace` |
| Open a new session and review and trust spec-guard's `UserPromptSubmit` hook under `/hooks` | Open a new session |

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

The full flow, what each stage means, and the two ways to add requirements: [workflow](docs/workflow.md) (Chinese).

## Common commands

| Command (Claude Code) | What it does |
|---|---|
| `/spec-guard:setup-convention` | Install the multi-module convention in a project; `--replace` upgrades the block, `--dry-run` only previews |
| `/spec-guard:phase` | Show the current stage and the suggested next step |
| `/spec-guard:verify-artifacts` | Check the capability map format and that modules match their Specs |
| `/spec-guard:add-module` | Insert a new requirement into the capability map as a module at a checkpoint (preview, then confirm) |
| `/spec-guard:config` | View or set project config: artifact language and review cadence |
| `/spec-guard:teardown-convention` | Remove the convention and keep your Specs and plans |

Codex does not load slash commands; the same features are reached through skills in plain language (mainly
`spec-guard-ops`). Arguments and output of all 21 commands, and the Codex mapping: [command reference](docs/commands.md)
(Chinese).

## What it looks like, and a self-check

Once enabled, send the agent any message and it sees a stage hint like this in its context:

```text
## spec-guard local workflow

当前阶段: **NEEDS_PLAN**

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

In a project with an older convention block, preview `/spec-guard:setup-convention --replace --dry-run` after updating,
and replace once you have confirmed. Keep your own rules inside the block's local section
(`<!-- BEGIN:spec-guard-local -->` … `<!-- END:spec-guard-local -->`); replacing keeps it.

**Uninstall**

1. In every project that used it, run `/spec-guard:teardown-convention` (preview with `--dry-run` first). It removes
   the convention block and stops the stage hint; your `spec/` and `tasks/` stay.
2. Then remove the plugin: `claude plugin uninstall spec-guard@spec-guard-marketplace` for Claude Code;
   `codex plugin remove spec-guard@spec-guard-marketplace` for Codex, and
   `codex plugin marketplace remove spec-guard-marketplace` once you no longer need the source.

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
- Want to change code: read [contributing](CONTRIBUTING.md) and [design and architecture](docs/design.md) first.
- Maintainer documents: see the "Maintainers" group above.

## License

[MIT](LICENSE)
