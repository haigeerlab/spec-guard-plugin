# Plan: promotion-proof-diagnostics

依据 [`spec/promotion-proof-diagnostics.md`](../../spec/promotion-proof-diagnostics.md)。一个 task、一条提交：先写能在当前
代码上失败的测试并记录失败输出，再修改到通过；测试沿用临时远端与 tracker 夹具，只用通用夹具名。

## Task 1：两个诊断码与定位字段

- `proposal_promotion_proof.py`：抽出返回不符字段的函数，`_matches` 基于它；证明在行不符时返回
  `promotion-row-mismatch` + `promotionCommit` + `mismatchedFields`，在改动其他行时返回
  `promotion-other-rows-changed` + `promotionCommit`；`Proof`／`as_json` 支持 `mismatchedFields`。
- `test_proposal_promotion_proof.py`：Spec 测试策略中的三个场景。
- `references/proposal-promotion-proof.md`、`commands/proposal-promotion-proof.md`：两个诊断码与字段；
  `CHANGELOG.md` Unreleased `### 变更`。
- **验收：** 新测试在当前代码上失败、修改后通过；已有测试全部通过；两种 Python 下三条最小验证、
  `test_module_insert.py` 与 `check-command-parity.py` 通过。

## Checkpoint：完成

- 逐条核对 Spec 成功标准；在该消费者项目的只读快照上复现，证明应返回 `promotion-row-mismatch`，
  `mismatchedFields` 含 `responsibility` 与 `dependsOn`（只读，不改该项目任何状态，结果写进 PR 时只写"消费者项目快照"）。
- 检查点勾选随模块 PR 一起提交；阶段回到 DONE。
