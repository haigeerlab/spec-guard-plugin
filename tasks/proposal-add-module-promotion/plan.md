# Plan: proposal-add-module-promotion

依据 [`spec/proposal-add-module-promotion.md`](../../spec/proposal-add-module-promotion.md)。三个 task 串行，每个 task
一条提交。代码类 task 先写能在当前代码上失败的测试并记录失败输出，再修改到通过。测试沿用现有的临时 Git 远端与
tracker 夹具，不访问网络；测试与提交信息只用通用夹具名，不写任何消费者项目的名称、模块或编号。

顺序的理由：Task 1 先提供 add-module 需要的"预检结果 + baseCommit 能力图"，Task 2 才能在其上实现 `--proposal`；
文档最后统一改。

每个 task 完成时，在默认 `python3` 与 `PATH=/usr/bin:/bin` 下各跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

以及该 task 相关的 `python3 -B plugins/spec-guard/hooks/test_*.py`；动到命令或文档时加
`python3 scripts/check-command-parity.py`。

## Task 1：预检复用（P1）

- `proposal_promotion_proof.py`：新增只读函数，返回预检结果，`ready` 时附带 `baseCommit` 上能力图原文与 Proposal；
  复用 `read_published_pool` 与 `_preflight`，`preflight()` 与 CLI 输出不变；支持注入 `tracker_reader`。
- `test_proposal_promotion_proof.py`：ready 时返回原文与 Proposal、非 ready 时只返回结果、与 `preflight()` 结果一致。
- **验收：** 新测试在当前代码上失败、修改后通过；已有测试全部通过。
- **文件：** `proposal_promotion_proof.py`、`test_proposal_promotion_proof.py`。

## Task 2：`add-module --proposal`（P2）

- `module-insert.py`：新增 `--proposal`／`--platform`／`--target`；字段互斥；预检 ready → 本地图与 `baseCommit` 一致 →
  现有 `preview()` 校验 → `_matches` 自检 → 预览输出加 Proposal id／revision／baseCommit、不提示同名 Proposal →
  `--confirm` 沿用 `write()`。
- `test_module_insert.py`：Spec 测试策略中的正例、端到端（写入 → 推到临时远端 → `proved`）与全部反例；不带
  `--proposal` 的已有测试保持通过且输出不变。远端与 tracker 夹具如需共享，抽到测试可复用的 helper，不改
  `test_proposal_promotion_proof.py` 的断言。
- **验收：** 新测试在当前代码上失败、修改后通过；已有测试全部通过。
- **文件：** `module-insert.py`、`test_module_insert.py`（及可能的共享测试 helper）。

## Task 3：入口与文档（P3）

- `commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`、`commands/proposal-promotion-preflight.md`、
  `references/proposal-promotion-proof.md`、`docs/workflow.md`、`CHANGELOG.md`（Unreleased `### 新增`）。
- **验收：** `validate.sh`、`check-command-parity.py` 通过；文档与实际参数、拒绝条件一致；不含消费者项目信息。

## Checkpoint：完成

- 两种 Python 下三条最小验证、`test_module_insert.py`、`test_proposal_promotion_proof.py` 全部通过；逐条核对 Spec
  的成功标准。
- 检查点勾选随模块 PR 一起提交；阶段推进到下一个模块 `proposal-submit`。
