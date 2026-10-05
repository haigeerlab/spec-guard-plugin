# Plan: local-ticket-ledger

> 登记说明：本模块是既有能力的一次性人工登记，未经 Proposal 流程
> （见 [`docs/decisions/2026-09-28-single-capability-map.md`](../../docs/decisions/2026-09-28-single-capability-map.md)）。登记时已交付，因此没有
> `tasks/<module-id>/todo.md`；`plan-without-todo` 判据据此按已完成计，这不是漏建。

Proposal candidate: [`../../spec/proposals/local-ticket-ledger.md`](../../spec/proposals/local-ticket-ledger.md)

## Overview

交付一个可选的本地事项账本接入：当 GitHub 或 GitLab Issue 不可用时，同一台 Mac 上属于同一 Git
仓库的 linked worktree、Claude Code 会话和 Codex 会话可以读取并更新同一份持久事项。账本使用
固定版本的开源 Epiq 作为后端；Spec Guard 只负责安全的显式安装、项目初始化、宿主 MCP 配置和
可诊断的操作入口，不重新实现 tracker。

现有 `collaboration-messaging` 仍是自由文本邮箱。事项账本是持久事实，邮箱只可选地发送诸如
“`R85YPWB` 已修复，请拉取代码验证”的通知。两者不得互相要求、互相写入或自动路由。

## Architecture decisions

- **Backend:** 固定 `epiq@1.11.0`（MIT）作为可替换的本地账本运行时。它的 MCP server 经 stdio
  为 Claude Code 和 Codex 提供读写工具；不部署常驻 HTTP 服务、数据库服务或本机网络端口。
- **One repository, one ledger:** Epiq 初始化时把非秘密项目身份提交到 `.epiq/project.json`，并维护
  `__epiq_state__` 状态分支。相同 macOS 用户下，该项目的 linked worktree 通过这个身份读取同一
  本机账本。初始化前必须要求工作树干净，并清晰列出这些可见 Git 影响。
- **Explicit lifecycle:** 插件安装、项目打开、hook、状态诊断都不得下载依赖、修改仓库、修改 MCP 配置
  或初始化账本。用户明确选择后才可安装固定运行时、初始化项目、或追加 Claude/Codex 的无秘密 MCP
  条目；同名配置存在时拒绝覆盖。Epiq 上游初始化会尝试推送分支，因此检测到 `origin` 时，Spec Guard
  必须在调用上游前停下并要求一次单独、明确的“允许本次 Epiq 推送”确认；无 `origin` 的本地项目可继续，
  并把上游失败的推送尝试报告为警告。
- **Free coordination:** Agent 自行通过 `epiq_actor_assume` 声明可读名字和当前工作；不实现项目组、
  角色、指派锁、自动认领、自动排期或基于项目路径的投递规则。Epiq 的标签、泳道、assignee 只是
  用户／Agent 可选记录，不成为 Spec Guard 的强制流程。
- **Remote return path:** 本阶段不连接、同步、导入或创建 GitHub/GitLab Issue。事项正文可保存远端
  Issue URL／编号等普通引用；远端恢复后的批量迁移或双向同步是独立能力，必须另立设计。
- **Runtime ownership:** 固定运行时安装到受管的用户级目录，而不是项目 `node_modules`；要求 Node.js
  18+，运行时文件与项目 Git 内容分离。没有该前置条件时给出准确的诊断和安装指引，不伪报本地账本
  可用。

## Dependency graph

```text
fixed runtime contract + non-mutating diagnostics
                    ↓
explicit user install + clean-tree project initialization
                    ↓
Claude/Codex stdio MCP adapters + agent self-description guidance
                    ↓
operator command + optional mailbox reference guidance
                    ↓
isolated worktree / concurrency / restart acceptance
```

## Implementation slices

### Slice 1: Fixed runtime contract and read-only diagnostics

Define a local-ledger runtime contract, including the pinned package version, expected user-level
directory, Node prerequisite checks, safe executable discovery, and JSON status output. Status must
be side-effect free and distinguish absent runtime, bad version, missing Node, invalid executable,
uninitialized repository, and healthy project configuration.

**Verification:** Focused tests exercise all status modes without installing packages or writing a
repository; diagnostics never print environment secrets or claim that Epiq is a GitHub/GitLab
replacement.

### Slice 2: Explicit runtime install and project initialization

Add user-invoked operations that install the exact package into the managed user directory and then
call Epiq project initialization only in a clean Git worktree. Before a write, preview the precise
effects: package installation, `.epiq/project.json` commit, `__epiq_state__` branch, and Epiq's
upstream push behavior. If `origin` exists, require a separate explicit push confirmation before
calling Epiq; without `origin`, continue locally and report Epiq's failed push as a warning. The command
must preserve a usable local ledger if no GitHub/GitLab remote exists.

**Verification:** Isolated temporary Git repositories verify clean-tree refusal, `origin` confirmation
gating, no-remote warning, committed project identity, state-branch creation, and no project-local
runtime dependency directory.

### Slice 3: Narrow Claude Code and Codex MCP adapters

Generate and optionally install user-scoped stdio MCP entries that execute the pinned Epiq MCP
binary. Configuration carries neither ledger data nor secrets. Add agent-facing guidance to adopt a
free self-description at the start of a session and to query existing tickets before creating a new
one; it must not turn that advice into assignment or routing policy.

**Verification:** Unit tests prove generated Claude/Codex configuration is deterministic, points
only to the verified managed runtime, preserves existing config, and refuses same-name overwrite.
Real-host acceptance proves both hosts can read the same ticket from separate worktrees.

### Slice 4: Minimal Spec Guard operator experience

Provide a dedicated command and skill for status, explicit installation, explicit project init, and
connection instructions. Document the optional composition with XATS: messages may carry a ticket
reference, but ticket mutation and message delivery remain separate intentional actions.

**Verification:** Command snapshots distinguish unavailable, ready-but-uninitialized, initialized,
and unusable states. Documentation examples cover bug intake, investigation, completion notice, and
the no-GitHub/GitLab local loop without describing a mandatory workflow.

### Slice 5: Cross-worktree durability and safety review

Run acceptance against two linked worktrees and independently launched MCP server processes: create
from one, read from the other, concurrently comment, restart one process, and read both comments.
Record Epiq's external-runtime version, license, Node requirement, user-visible Git changes, and
remote migration limitation. Run the repository's applicable validation suite.

**Verification:** A reproducible isolated acceptance script/fixture reports every expected
observable result and cleans up only its own temporary paths. Existing collaboration tests remain
green, proving XATS was not coupled to ticket state.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Epiq upstream changes behavior or MCP schema | Medium | Pin the version, validate executable identity, isolate adapter construction, and make upgrade an explicit future operation. |
| Initialization alters a developer's repository unexpectedly | High | Never initialize implicitly; require clean-tree preflight, print the exact `.epiq` / state-branch effects, and require a second confirmation before upstream Epiq may push to an existing `origin`. |
| Agents treat local tickets as mandatory bureaucracy | Medium | Expose tools and examples only; prohibit role, routing, ownership, and scheduling enforcement. |
| Users confuse local persistence with GitHub/GitLab synchronization | High | Use separate status wording; document that remote creation/import/sync is absent and requires explicit future work. |
| Multiple worktrees lose concurrent updates | High | Retain the actual two-process concurrent-comment acceptance test; do not substitute a git-ref backend whose concurrent updates silently overwrite one another. |
| Managed runtime becomes a hidden large dependency | Medium | Show Node/version/disk implications before explicit install; keep it user-level, versioned, and removable independently of project files. |

## Open questions

- Epiq has no built-in GitHub/GitLab Issue migration in this scope. A future design must decide whether
  to provide explicit one-way export, only reference linking, or a different forge adapter.
- The initial pinned version is `1.11.0`, verified in an isolated POC. A release-time dependency review
  should re-check its license, MCP compatibility, and package integrity before distribution.
- This module does not make independent clones on different machines communicate without a shared Git
  remote. Cross-device mode is deliberately outside the same-Mac local fallback.

## Stop conditions

- Stop before implementation if the pinned Epiq package cannot provide the verified stdio MCP contract
  on both Claude Code and native Codex Desktop.
- Stop and return to design if initialization cannot transparently preserve the clean-worktree and
  explicit-write boundary, or if a required adapter would affect ChatGPT in Chrome.
- Do not alter `spec/CAPABILITY-MAP.md`, create remote tracker objects, or represent this candidate as
  accepted until the repository's Proposal review/promotion workflow has produced that evidence.
