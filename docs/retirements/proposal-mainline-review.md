# 退役：Proposal 主链裁决层

状态：已退役（2026-09-30，用户决定）。

## 退役的是什么

Proposal 流程里"主链裁决 → 人工写验收记录"这一层：主链策略文件 `spec/proposal-mainline-policy.json`、
验收记录 `spec/proposal-acceptances/<id>-<revision>.json`、`--authority-id`／`--boundary`／
`--current-module-id` 参数、受保护的 `integration/mainline` 分支、两个 mainline 命令与
`proposal_boundary_guidance`。它们的设计见[迁移说明](../migrations/proposal-mainline-review-v2.md)（已被本文取代）。

## 为什么退役

- 它是 Proposal 流程里摩擦最大的一层：一个消费者项目的主链策略文件失效后，预检只能报 `mainline-policy-invalid`，
  所有 Proposal 都无法晋级。
- 接受本来就是人的决定，靠 Issue 标签即可留痕；再叠一份不可修改的验收记录、一条要保持快进的主链分支与一套
  模块边界参数，只增加了维护与出错的面。
- 流程因此精简为提交、接受、晋级、收尾四步；本次先落地"接受只看标签与新鲜度"，晋级方式与四步文档由后续模块完成。

## 移除的内容

- 命令：`/spec-guard:proposal-mainline-candidates`、`/spec-guard:proposal-mainline-review`（含 `spec-guard-ops` 中对应入口）
- hook：`hooks/proposal_mainline_review.py`、`hooks/proposal_boundary_guidance.py` 及其测试
- 参考文档：`references/proposal-mainline-review.md`、`references/proposal-boundary-guidance.md`
- 预检、证明与 Proposal 池对策略文件和验收记录的读取，以及 `mainline-policy-invalid`、
  `acceptance-attestation-invalid` 这两类诊断
- 晋级证明对"晋级提交必须同时带 Spec 与 Plan"的要求

历史发布记录、`docs/acceptance/` 与其他 `tasks/` 历史材料保持原样，只作为历史证据。两份已退役模块的原始 Spec 与 Plan 已逐字节移至：

- 主链裁决：[Spec](proposal-mainline-review/spec.md)、[Plan](proposal-mainline-review/plan.md)
- 边界提醒：[Spec](proposal-boundary-guidance/spec.md)、[Plan](proposal-boundary-guidance/plan.md)

这四份文件不属于当前能力图的模块产物；旧路径和旧设计见 Git 历史。

## 保留的内容

- 已有的 `spec/proposal-mainline-policy.json` 与 `spec/proposal-acceptances/*.json` 可以留在原处：插件不再读取，
  存在（即使内容无效）也不报错、不参与判断。
- `scripts/check-acceptance-immutable.py` 继续保护已有验收记录不被修改。
- Proposal 池的隔离行为与 `skippedProposals` 输出不变。

## 现在的接受与收尾

- 接受 = 已发布的 v2 Proposal + Issue 标签 `proposal-stage:accepted` + 评审新鲜（基线未漂移、模块还不在能力图中、
  依赖齐全、锚点有效）。v1 Proposal 仍返回 `legacy-revision-required`。
- 预检：基线漂移返回 `stale` 与评审的诊断；只有标签为 accepted 且新鲜时才是 `ready`，并给出 `baseCommit`。
- 证明：Issue 阶段为 accepted 或 promoted 均可；从 Proposal 的基线提交起沿远端默认分支 first-parent 找第一个纳入该模块的
  提交，在它的父提交上判断新鲜度，`reviewCommit` 为该父提交。新增状态 `stale`。

## 迁移

- 已在 accepted 阶段的 Proposal：确认 Issue 标签为 `proposal-stage:accepted`，直接运行
  `/spec-guard:proposal-promotion-preflight`。
- 策略文件与验收记录：可保留，也可自行删除；插件不再读取。
- `integration/mainline` 分支及其保护规则：不再有用，可自行处理。
- 原先用 mainline-candidates 在模块边界查看候选的：改用 `/spec-guard:proposal-review` 逐个查看。
