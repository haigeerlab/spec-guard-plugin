# Plan: proposal-label-acceptance

依据 [`spec/proposal-label-acceptance.md`](../../spec/proposal-label-acceptance.md)。四个 task 串行，每个 task 一条提交。
代码类 task 先写能在当前代码上失败的测试并记录失败输出，再修改到通过；删除类 task 以"删除后全部检查仍通过、
仓库中无残留引用"为验收。测试沿用现有的临时 Git 仓库、远端与 tracker 夹具，不访问网络；测试与提交信息只用
通用夹具名，不写任何消费者项目的名称、模块或编号。

顺序的理由：Task 1 先让预检／证明不再依赖 `proposal_mainline_review.py`，Task 2 才能整块删除它；Task 3 删除池里
的策略与验收记录字段，必须在唯一的另一个读者（mainline 模块）删除之后；文档最后统一改。

每个 task 完成时，在默认 `python3` 与 `PATH=/usr/bin:/bin` 下各跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

以及该 task 相关的 `python3 -B plugins/spec-guard/hooks/test_proposal_*.py`；动到命令或文档时加
`python3 scripts/check-command-parity.py`。

## Task 1：接受、预检与证明不再依赖主链层（C1、C3、C4）

- `proposal_promotion_proof.py`：移入 `accepted()`（去掉 policy／attestation）与 `DIAGNOSTIC_CODE`，不再从
  `proposal_mainline_review` 导入；预检删除恒等的 `review_map` 比较；证明改为从基线提交沿 first-parent 查找、在父提交
  的能力图上判断新鲜度、阶段接受 accepted／promoted、不限制路径但拒绝改动其他模块行，`reviewCommit` = 父提交。
- `test_proposal_promotion_proof.py`：Spec 测试策略中的预检与证明场景；原有断言中依赖验收记录或路径限制的，
  改写并在提交说明中逐条列出。
- **验收：** 新测试在当前代码上失败、修改后通过；`test_proposal_mainline_review.py` 仍通过（此时尚未删除）。
- **文件：** `proposal_promotion_proof.py`、`test_proposal_promotion_proof.py`。

## Task 2：删除主链裁决与边界提醒（C5）

- 删除两个 mainline 命令、`proposal_mainline_review.py`、`proposal_boundary_guidance.py` 及其测试、两份参考文档；
  去掉 `scripts/validate.sh`、`scripts/test-checkers.sh`、`hooks/test-retire-legacy-tracker-bridge.sh`、
  `evals/` 中的 Codex 命令根测试、`skills/spec-guard-ops/SKILL.md`、以及其余参考文档中指向它们的链接与入口。
- 保留 Spec C5 列出的历史文件。
- **验收：** `git grep` 在插件、脚本、evals 中不再出现被删模块名与命令名（历史文件除外）；全部检查与
  `check-command-parity.py` 通过。
- **文件：** 以删除为主，改动集中在 validate／检查器／skill／evals 的引用。

## Task 3：池不再读取策略与验收记录（C2）

- `proposal_publication.py`：删除 `_attested_review_commit`、`ATTESTATION_PATH_TEMPLATE`、`PublicationPool` 的
  `policy_text`／`attestation_texts`；`review_commit` 恒为观察到的提交。
- `test_proposal_publication.py`：有无验收记录时 `review_commit` 相同；隔离五个场景保留；删除仅针对验收记录固定
  快照的断言，在提交说明中逐条列出。
- **验收：** 新测试在当前代码上失败、修改后通过；预检／证明测试仍通过。
- **文件：** `proposal_publication.py`、`test_proposal_publication.py`。

## Task 4：文档、退役说明与 CHANGELOG（C6）

- 新增 `docs/retirements/proposal-mainline-review.md`；`docs/migrations/proposal-mainline-review-v2.md` 顶部指向它。
- `docs/workflow.md`、`docs/concepts.md`、`docs/design.md`、`docs/maintainer-workflow.md`、`README.md`、
  `references/proposal-promotion-proof.md`、`references/proposal-publication.md`、`references/workflow-checkpoints.md`：
  删除或改写主链裁决、策略、验收记录的描述，写明新的预检与证明判断。
- `CHANGELOG.md` Unreleased：`### 移除`、`### 变更`，含迁移要点。
- **验收：** `validate.sh`、`check-command-parity.py` 通过；文档中除历史记录外不再要求策略文件、验收记录或主链分支；
  不含消费者项目信息。

## Checkpoint：完成

- 两种 Python 下三条最小验证与 Proposal 测试全部通过；逐条核对 Spec 的成功标准。
- 在消费者项目的只读快照上复现：预检不再返回 `mainline-policy-invalid`（如实报告它此后的结果）；不改该项目任何状态。
- 检查点勾选随模块 PR 一起提交；阶段推进到下一个模块 `proposal-add-module-promotion`。
