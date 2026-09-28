# 决策：整个插件只用一张能力图

状态：已批准并实施（2026-09-28）。取代同日的
[`2026-09-28-initiative-rollover.md`](2026-09-28-initiative-rollover.md)。

## 背景

本仓库原先按 initiative 分图：每项较大的工作新建一张 `spec/CAPABILITY-MAP.md`，完成后连同模块 Spec 与 Plan
归档到 `spec/history/`，下一项工作从空图开始。已有 12 个 initiative 这样归档。

这带来两个问题：每个新需求都要另起一张图；想看软件整体能做什么，要翻历史归档。2026-09-28 的审计还发现，
当时的 Proposal 图里混入了与它无关的 `collaboration-messaging`，而已交付的本地事项账本不在任何图里。

同日先按“继续分图”实施了一版（PR #7：把 Proposal initiative 归档为 `proposal-lifecycle`，另建
`local-collaboration` 图）。用户随后明确了真实设想，本决策取代它。

## 决策

- **整个插件只有一张能力图。** `spec/CAPABILITY-MAP.md` 描述整个产品；已完成的模块留在图里，作为软件能做什么的
  记录。
- **新需求按锚点插入，不另建图。** Proposal 的 `Build-order anchor` 本就是 `after:<module-id>` 或 `end`；
  `proposal-mainline-candidates` 在模块交付或推进边界读取已发布 Proposal 与对应 Issue，这就是“开发中定期去
  Issue 看有没有要插入当前图的需求”的机制。
- **只有与本插件无关的独立产品才另起能力图。**
- **目标陈述一次写成产品级，以后只追加。** Proposal 评审只在目标或既有模块行改变时判为 `stale`，追加不相关的
  新模块不会让其他 Proposal 失效；因此以后不要为了新模块改写目标或已有行。

## 本次改动

- 撤回 PR #7 的归档：恢复 7 个 `spec/proposal-*.md` 与 `tasks/proposal-*/plan.md`，历史账本恢复到 PR #7 之前，
  删除 `proposal-lifecycle` 与 `local-collaboration` 的快照目录。
- 能力图：原有 8 行逐字保留；标题与目标改写为产品级；末尾追加 `local-ticket-ledger`，Build order 相应延长。
- `collaboration-messaging` 与 `local-ticket-ledger` 是既有能力的一次性人工登记，未经 Proposal 流程
  （Proposal 流程在本仓库暂时走不通：仓库复制后没有 Issue，`integration/mainline` 落后于 `main`）。
- 保留 PR #7 中与模型无关的部分：`spec/local-ticket-ledger.md`、协作 Spec 的治理说明、README 与设计文档的定位。

## 影响

- 目标改写一次，已发布的两份 Proposal（`collaboration-messaging`、`local-ticket-ledger`）评审会报 `stale`。
  二者的模块都已在图中，它们只是历史记录；Proposal 文件与 acceptance attestation 均未修改。
- 历史账本不再有活跃 initiative（`capability-history.py active` 报告没有唯一活跃项），与 PR #7 之前相同。
  一张图模型下，历史账本只保存已归档的旧 initiative。

## 后续

- 本地多模块约定（phase、verify-artifacts）、能力历史、文档治理等更早交付的能力，按用户决定另开一个 PR，
  按现状写当前模块 Spec 后登记到本图。
