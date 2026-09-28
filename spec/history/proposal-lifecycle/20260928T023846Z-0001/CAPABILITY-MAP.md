# Capability Map: Candidate Proposal Pool and Capability Map Promotion

## 目标

让正在实现既有模块的任务能够把新发现的、独立的需求分流到独立设计任务；该需求在合并到远端默认分支后成为可评审 Proposal，并只能由具备可验证主链上下文、明确人工裁决和远端授权证据的流程安全晋级到能力图。

这套能力只负责 Proposal、能力图与晋级证据，不调用、不依赖 `spec-github-bridge`，也不接管 Task、分支、PR 或交付流程。`spec-github-bridge` 的退役是后续独立迁移。

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

Build order: proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-mainline-review → proposal-promotion-proof → proposal-boundary-guidance → collaboration-messaging

---

## 评审记录

- [x] 模块边界确认（砍掉或替换一个模块，不需要重写其他模块的需求）
- [x] 依赖方向单向无环（互相依赖 = 它们本来就是一个模块）
- [x] module id 已定稿（kebab-case，之后绝不改名 —— 同一个 id 同时是
      `spec/<id>.md`、`tasks/<id>/`、`state.json`、`feat/<id>` 分支和 issue 标题的名字，
      其中后两处改不动）
- [x] 构建顺序符合依赖拓扑

评审人：用户与 Codex
日期：2026-09-15
