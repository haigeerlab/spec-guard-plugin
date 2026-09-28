# Capability Map: Local Collaboration and Tickets

## 目标

为同一台 Mac 上的 Claude Code 与 Codex 会话提供两项可选的本机能力：直接交换自由文本技术消息的私有协作邮箱，以及
在 GitHub/GitLab Issue 不可用时跨 linked worktree 共享的本地事项账本。两者都需用户显式启用，互不依赖，不替代、
不同步 GitHub/GitLab Issue，也不接管 Git、分支、PR 或任务分派。

两个模块都是本 initiative 开始前已经交付的既有能力，由 2026-09-28 的一次性人工登记纳入本图，**未经 Proposal
流程**；决策与理由见 `docs/decisions/2026-09-28-initiative-rollover.md`。此后的新需求仍按 Proposal 流程进入能力图。

## 模块

| Module id | Responsibility | Depends on |
|---|---|---|
| collaboration-messaging | Provide a private same-Mac mailbox and host adapters for direct Claude Code and Codex session communication, with an experimental opt-in native transport. | — |
| local-ticket-ledger | Provide an optional local-first, worktree-shared ticket ledger and narrow Claude Code/Codex access without imposing workflow ownership or project topology. | — |

Build order: collaboration-messaging → local-ticket-ledger

---

## 评审记录

- [x] 模块边界确认（砍掉或替换一个模块，不需要重写其他模块的需求）
- [x] 依赖方向单向无环（互相依赖 = 它们本来就是一个模块）
- [x] module id 已定稿（沿用既有 id，与已交付的命令、引用和 `tasks/<id>/` 一致）
- [x] 构建顺序符合依赖拓扑（两者互不依赖，顺序只反映交付先后）

评审人：用户（一次性登记决策）
日期：2026-09-28
