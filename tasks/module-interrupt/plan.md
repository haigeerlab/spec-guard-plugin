# Plan: module-interrupt

依据 [`spec/module-interrupt.md`](../../spec/module-interrupt.md)。四个 task 串行，每个 task 一条提交；先写能在当前
代码上失败的测试并记录失败输出，再修改到通过。全部在临时项目上测试，不访问网络。

每个 task 完成时都运行三条最小验证，并用 `/usr/bin/python3` 再跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

依赖关系：Task 1 把"做到一半"的判据移进 `module_stage.py`，Task 2 复用它；Task 3 与前两者独立；Task 4 描述最终行为。

## Task 1：被暂停的模块与 Paused 行（I1）

- 把 `module-insert.py` 的 `_half_done` 判据（todo 同时有已勾与未勾项）移到 `module_stage.py`，作为唯一实现；
  module-insert 改为从 `module_stage` 导入，行为不变。
- `module_stage.py`：当前模块以外、做到一半的模块记为被暂停；`NEEDS_SPEC`／`NEEDS_PLAN`／`BUILDING`／`MODULE_DONE`
  在计数行后加 `Paused` 行；`MODULE_DONE` 有被暂停模块时点名它（Build order 中第一个）。
- `test-phase-guard.sh`：上述各阶段的 `Paused` 行、`MODULE_DONE` 指回被暂停模块；没有被暂停模块时已有 37 个用例不变。
- **验收：** 新断言在当前代码上失败、修改后通过；`test_module_insert.py` 全部通过。
- **文件：** `module_stage.py`、`module-insert.py`（仅导入）、`test-phase-guard.sh`。

## Task 2：add-module 的 `--interrupt`（I2）

- `module-insert.py`：新增 `--interrupt`，按 Spec I2 放行、拒绝第二层插队、在预览中写明被暂停模块与进度，以及何时需要改
  `activeModule`；不带它时仅在拒绝信息中提到 `--interrupt`。`--confirm` 重新执行全部校验，只写能力图。
- `commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`：`--interrupt` 的用法与确认要求。
- `test_module_insert.py`：Spec 测试策略中 module-insert 的全部场景，包括端到端（插队 → Paused → 完成 → 指回）。
- **验收：** 新测试在当前代码上失败、修改后通过；`check-command-parity.py` 通过。
- **文件：** `module-insert.py`、`test_module_insert.py`、`add-module.md`、`spec-guard-ops/SKILL.md`。

## Task 3：主链评审接受 `module-interrupt` 边界（I3）

- `proposal_mainline_review.py`（第 222、334、410 行三处）与 `proposal_boundary_guidance.py`：加入 `module-interrupt`；
  确认 boundary 不进入 attestation 与 policy 摘要。
- `commands/proposal-mainline-review.md`、`commands/proposal-mainline-candidates.md`、`references/proposal-mainline-review.md`、
  `references/proposal-boundary-guidance.md`：边界取值。
- 测试：`module-interrupt` 与 `module-advance` 结论相同；未知取值仍为 `mainline-boundary-invalid`；边界提醒同样给出。
- **验收：** 新测试在当前代码上失败、修改后通过；已有 Proposal 测试全部通过。
- **文件：** 两个 hook、两个测试文件、四份文档。

## Task 4：文档（I4）

- `docs/workflow.md`：检查点规则加上"显式插队"；新增"插队"一节（何时用、预览、改 `activeModule`、完成后回到被暂停
  模块、Proposal 晋级同样适用）。
- `commands/phase.md`：`Paused` 行。
- `CHANGELOG.md` Unreleased。
- **验收：** 全仓不再有把"只在检查点插入"写成无例外规则的用户文档；`validate.sh` 与 `check-command-parity.py` 通过。
- **文件：** `docs/workflow.md`、`phase.md`、`CHANGELOG.md`。

## Checkpoint：完成

- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过；逐条核对 Spec 的成功标准（含按 pwa-platform 形状复现的
  端到端场景）；检查点勾选随模块 PR 一起提交，由分支保护的两项必需 CI 把关合并；阶段变为 DONE。
