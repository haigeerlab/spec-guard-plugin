# Task list: local-ticket-ledger

Plan: [`plan.md`](plan.md)
Proposal candidate: [`../../spec/proposals/local-ticket-ledger.md`](../../spec/proposals/local-ticket-ledger.md)

This is a local implementation checklist. It records no tracker stage and does not authorize
remote writes or a capability-map change.

## Task 1: Define the pinned local-ledger runtime contract

**Dependencies:** None.

**Acceptance criteria:**

- [x] A side-effect-free status operation reports Node compatibility, fixed Epiq version, managed
      runtime validity, and project initialization state separately.
- [x] No hook, status command, or project-open path downloads a package, changes MCP configuration,
      writes `.epiq`, or starts a service.
- [x] Diagnostics do not expose secrets and do not claim GitHub/GitLab compatibility that is absent.

**Verification:**

- [x] Focused unit tests cover absent, invalid, version-mismatch, missing-Node, and ready states.
- [x] JSON command snapshots remain stable and `git diff --check` passes.

**Likely files:** `plugins/spec-guard/hooks/local_ledger_runtime.py`, focused tests, runtime reference.

**Estimated scope:** Medium.

## Task 2: Add explicit install and clean-tree initialization

**Dependencies:** Task 1.

**Acceptance criteria:**

- [x] A user-requested install places only the pinned Epiq runtime in a managed user-level directory.
- [x] A read-only preflight refuses a dirty worktree and blocks a configured `origin` until the user
      separately permits Epiq's upstream push behavior.
- [x] Project initialization refuses a dirty worktree and previews its Git-visible effects before it
      runs.
- [x] A configured `origin` blocks initialization until the user separately permits Epiq's upstream
      push attempt; an initialized no-remote repository remains locally usable and reports the failed
      push attempt as a warning rather than success.

**Verification:**

- [ ] Temporary-repository tests prove clean-tree refusal, `origin` confirmation gating,
      `.epiq/project.json` commitment, and `__epiq_state__` creation.
- [ ] Tests prove no project `node_modules` directory is created and no remote write can be executed by
      default when `origin` is configured.

**Likely files:** runtime helper, focused tests, operator command, runtime reference.

**Estimated scope:** Medium.

## Task 3: Configure narrow Claude Code and Codex MCP adapters

**Dependencies:** Tasks 1–2.

**Acceptance criteria:**

- [ ] Explicit adapter installation adds a no-secret user-scoped stdio entry for each selected host.
- [ ] Existing unrelated configuration remains byte-preserved; a conflicting managed entry is refused.
- [ ] Agent guidance supports voluntary self-description and ticket lookup without assigning roles or
      enforcing ticket workflow.

**Verification:**

- [ ] Adapter tests cover generated config, missing runtime, conflict refusal, and atomic update.
- [ ] Real Claude Code and native Codex Desktop each list/read the same local ticket after restart.

**Likely files:** `local_ledger_adapters.py`, tests, Claude/Codex config references, ledger skill.

**Estimated scope:** Medium.

## Checkpoint: Safe local tracker setup

- [ ] The runtime is opt-in, version-pinned, user-scoped, and diagnosable.
- [ ] A dirty repository cannot be initialized accidentally.
- [ ] Neither mailbox configuration nor ChatGPT in Chrome behavior has changed.

## Task 4: Document the local issue loop and optional mailbox handoff

**Dependencies:** Task 3.

**Acceptance criteria:**

- [ ] Operators can discover status, explicitly install, initialize, connect each host, and understand
      removal boundaries.
- [ ] Documentation describes bugs, requirements, comments, and completion notices as flexible
      examples—not mandatory stages.
- [ ] Documentation distinguishes durable Epiq records from optional XATS notifications and explicitly
      describes the no-automatic-GitHub/GitLab-sync boundary.

**Verification:**

- [ ] Command/skill documentation review covers both GitHub/GitLab-unavailable and later-return cases.
- [ ] Existing README and collaboration references remain internally consistent.

**Likely files:** command, skill, runtime reference, README, collaboration reference.

**Estimated scope:** Medium.

## Task 5: Prove shared durability, concurrency, and non-regression

**Dependencies:** Tasks 2–4.

**Acceptance criteria:**

- [ ] Two linked worktrees and independently launched MCP processes see the same created ticket.
- [ ] Concurrent comments from both processes survive; restarting one process preserves both comments.
- [ ] The acceptance fixture only creates and removes its own temporary paths; existing collaboration
      tests still pass.

**Verification:**

- [ ] Focused local-ledger suite passes.
- [ ] `/bin/bash scripts/validate.sh`, `test-codex-adapter.sh`, and the relevant collaboration suite
      pass.
- [ ] A final status report records runtime version, license, Node requirement, Git effects, and
      remaining remote-migration limitation.

**Likely files:** acceptance fixture, focused tests, validation script, references.

**Estimated scope:** Medium.

## Checkpoint: Ready for review

- [ ] All task verification items pass.
- [ ] The plugin has not implemented a second forge, hidden a network service, or imposed roles/groups.
- [ ] Capability Map and remote Proposal lifecycle are changed only through their existing explicit
      review and promotion path.
