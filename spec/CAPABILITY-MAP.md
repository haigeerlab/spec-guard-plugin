# Capability Map: Spec Guard

## 目标

Spec Guard 是 agent-skills 的配套插件。本图是整个插件的唯一能力图：新需求在模块检查点经带校验的快速插入加进本图，
需要留痕时改走 Proposal（经主链评审与人工接受后插入）；两种方式都按声明的锚点插到已有模块之后或追加到末尾，不为每个
需求另建一张图；只有与本插件无关的独立产品才另起能力图。

插件的能力分四类：只读的 Proposal 生命周期（共享事实只来自远端默认分支快照，GitHub/GitLab 只作为只读 Proposal Issue
来源，不创建或修改 Issue、PR、分支或任务）；防止多模块产物互相覆盖的本地约定，以及只报告事实的阶段注入与产物校验；
在检查点把新模块校验后插进能力图的快速插入；可核验的能力历史与显式的文档治理；以及需显式启用的本机协作邮箱与本地事项账本，二者都不替代、不同步远端 Issue。
各模块的登记来源写在其模块 Spec 中。

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
| collaboration-safe-defaults | 协作信箱默认不绑定唤醒、Claude 启动器不把 token 放进会话环境，并用测试防止回退。 | collaboration-messaging |
| local-ticket-ledger | Provide an optional local-first, worktree-shared ticket ledger and narrow Claude Code/Codex access without imposing workflow ownership or project topology. | — |
| ledger-dependency-lock | 用插件附带的 lockfile 与 npm ci 安装本地事项账本运行时，校验全部依赖的完整性，并写明 XATS 依赖尚未锁定的剩余风险。 | local-ticket-ledger |
| local-convention | Install and remove the local multi-module directory convention and its managed declaration block, without touching user specs or plans. | — |
| phase-and-verification | Inject the current phase for activated projects and verify landed artifacts read-only, degrading to unverified when probes fail. | local-convention, proposal-contract |
| module-insert | At a module checkpoint, validate and insert one new module into the capability map with a spec skeleton, after previewing and explicit confirmation. | local-convention, phase-and-verification |
| capability-history | Keep verifiable history of archived capability maps and artifacts, with read-only verify and audit, append-only corrections, and migration preview. | proposal-contract |
| documentation-baseline | 定义显式启用的项目级文档基线协议、解析事实和初始化入口 | — |
| documentation-impact | 在模块 Spec、Plan 与交付前表达并收口对文档基线的遵循、补全、变更或不适用结论 | documentation-baseline |
| documentation-verification | 提供只读核验、保守提醒和跨宿主回归，确保缺失或未知不被伪装为文档完成 | documentation-baseline, documentation-impact |
| audit-remediation | 修复项目审计中已核实、不改变设计的缺陷：假成功、诊断丢失、Codex 路由与校验缺口、文档漂移。 | proposal-mainline-review, proposal-promotion-proof, collaboration-messaging, local-convention, module-insert, capability-history, documentation-verification |
| done-stage-split | 把阶段提示里的 DONE 拆成两种：当前模块已完成但还有别的模块未完成、全部模块已完成，各给出正确的下一步。 | phase-and-verification, module-insert |

Build order: proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-mainline-review → proposal-promotion-proof → proposal-boundary-guidance → collaboration-messaging → collaboration-safe-defaults → local-ticket-ledger → ledger-dependency-lock → local-convention → phase-and-verification → module-insert → capability-history → documentation-baseline → documentation-impact → documentation-verification → audit-remediation → done-stage-split

---

## 评审记录

- [x] 模块边界确认（砍掉或替换一个模块，不需要重写其他模块的需求）
- [x] 依赖方向单向无环（互相依赖 = 它们本来就是一个模块）
- [x] module id 已定稿（kebab-case，之后绝不改名 —— 同一个 id 同时是
      `spec/<id>.md`、`tasks/<id>/`、`state.json`、`feat/<id>` 分支和 issue 标题的名字，
      其中后两处改不动）
- [x] 构建顺序符合依赖拓扑

评审人：用户与 Codex（Proposal 模块，2026-09-15）；用户（改为全插件一张图并登记账本，2026-09-28；
补登本地约定、阶段与校验、能力历史、文档治理，2026-09-28）
