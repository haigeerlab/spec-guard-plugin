# Capability Map: Spec Guard

## 目标

Spec Guard 是 agent-skills 的配套插件。本图是整个插件的唯一能力图：新需求以 Proposal 提出，经主链评审与人工接受后，
按声明的锚点插入到已有模块之后或追加到末尾，不为每个需求另建一张图；只有与本插件无关的独立产品才另起能力图。

当前登记的能力：只读的 Proposal 生命周期（共享事实只来自远端默认分支快照，GitHub/GitLab 只作为只读 Proposal
Issue 来源，不创建或修改 Issue、PR、分支或任务），以及两项需显式启用的本机能力：Claude Code 与 Codex 会话之间的
协作邮箱，和在 GitHub/GitLab Issue 不可用时跨 linked worktree 共享的本地事项账本。二者都不替代、不同步远端 Issue。

本地多模块约定、阶段注入与产物校验、能力历史、文档治理等更早交付的能力目前只在 `spec/history/` 中有当时的记录，
待另行登记到本图。`collaboration-messaging` 与 `local-ticket-ledger` 是既有能力的一次性人工登记，未经 Proposal
流程；决策见 `docs/decisions/2026-09-28-single-capability-map.md`。

## 模块

| Module id | Responsibility | Depends on |
|---|---|---|
| proposal-contract | 定义并严格校验 Proposal v1/v2 文档、内容绑定 revision、阶段标签、能力图基准摘要和受支持变更类型。 | — |
| proposal-publication | 只从远端默认分支的固定快照读取一个已发布 Proposal 或候选池，拒绝把其他 worktree 的本地文件当作共享事实。 | proposal-contract |
| proposal-tracker-read | 用最小的 GitHub/GitLab 只读适配器核验普通 Proposal Issue 的唯一 revision marker 与唯一阶段，不使用旧 bridge。 | proposal-contract |
| proposal-review | 汇总发布、tracker 与当前能力图事实，给出与人工授权分离的 freshness/stale/blocked/unknown 结果。 | proposal-publication, proposal-tracker-read |
| proposal-mainline-review | 验证唯一主链上下文和远端 acceptance attestation，接收受限本地观察并输出人工主链裁决。 | proposal-review |
| proposal-promotion-proof | 对已接受、已预检的 new-module Proposal 核验严格 promotion diff、首次纳入和必要 Spec/Plan。 | proposal-mainline-review |
| proposal-boundary-guidance | 提供 intake/review/主链评审/晋级核验入口，并仅在模块交付或推进边界给出非阻断提醒。 | proposal-mainline-review, proposal-promotion-proof |
| collaboration-messaging | Provide a private same-Mac mailbox and host adapters for direct Claude Code and Codex session communication. | — |
| local-ticket-ledger | Provide an optional local-first, worktree-shared ticket ledger and narrow Claude Code/Codex access without imposing workflow ownership or project topology. | — |

Build order: proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-mainline-review → proposal-promotion-proof → proposal-boundary-guidance → collaboration-messaging → local-ticket-ledger

---

## 评审记录

- [x] 模块边界确认（砍掉或替换一个模块，不需要重写其他模块的需求）
- [x] 依赖方向单向无环（互相依赖 = 它们本来就是一个模块）
- [x] module id 已定稿（kebab-case，之后绝不改名 —— 同一个 id 同时是
      `spec/<id>.md`、`tasks/<id>/`、`state.json`、`feat/<id>` 分支和 issue 标题的名字，
      其中后两处改不动）
- [x] 构建顺序符合依赖拓扑

评审人：用户与 Codex（Proposal 模块，2026-09-15）；用户（改为全插件一张图并登记账本，2026-09-28）
