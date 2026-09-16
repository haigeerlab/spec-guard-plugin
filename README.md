# spec-guard

spec-guard protects two deliberately separate workflows:

- Proposal lifecycle: a revision-bound, read-only path that fixes shared facts
  to the remote default branch and reads GitHub/GitLab Proposal Issues only
  through explicit adapters. Only a policy-defined mainline may produce an
  accepted candidate; Issue stages remain human-written facts.
- Local multi-spec convention: a small directory convention for capability
  maps, module specs, plans, and local task lists.

It does not create or modify Issues, pull requests, merge requests, branches,
tasks, remote refs, or Proposal lifecycle state.

Install from the public marketplace with
`/plugin marketplace add haigeer-labs/spec-guard-plugin`.

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
