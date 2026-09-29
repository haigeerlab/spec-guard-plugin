# Plan: proposal-pool-isolation

依据 [`spec/proposal-pool-isolation.md`](../../spec/proposal-pool-isolation.md)。三个 task 串行，每个 task 一条提交；先写能在
当前代码上失败的测试并记录失败输出，再修改到通过。测试沿用现有的临时 Git 仓库与远端夹具，不访问网络。测试与提交信息
只用通用夹具名，不写任何消费者项目的名称、模块或编号。

每个 task 完成时都运行三条最小验证，并用 `/usr/bin/python3` 再跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Task 1：池读取隔离已晋级的坏 Proposal（P1）

- `proposal_publication.py`：`read_published_pool` 在循环前取 `observed_commit` 能力图的模块 id 集合；解析成功后的基线与
  校验失败，若模块已在图中则记入 `skipped` 并继续，否则整池 `invalid`（不变）。`PublicationPool` 增加 `skipped`（默认空元组）。
- `test_proposal_publication.py`：Spec 测试策略中的五个场景（隔离正例、未晋级反例、解析失败反例、健康已晋级仍在池中、
  无坏 Proposal 时结果不变）。
- **验收：** 新测试在当前代码上失败、修改后通过；已有 Proposal 测试（含 attestation／policy digest）全部通过。
- **文件：** `proposal_publication.py`、`test_proposal_publication.py`。

## Task 2：命令输出与查询被排除的 Proposal（P2）

- `proposal_promotion_proof.py` 的 `preflight_as_json`／`as_json`、`proposal_mainline_review.py` 的 `as_json`：`skipped` 非空时
  附加 `skippedProposals`；为空时输出逐字不变。查询的正是被排除的 Proposal 时，得到现有的 `publication-absent`。
- 两个测试文件：坏的历史 Proposal 存在时其他 Proposal 的预检／证明／候选正常；有无 `skipped` 时的 JSON；被排除者的查询结果。
- **验收：** 新测试在当前代码上失败、修改后通过；已有测试全部通过。
- **文件：** 两个 hook、两个测试文件。

## Task 3：文档（P3）

- `references/proposal-publication.md`、`references/proposal-promotion-proof.md`、`references/proposal-mainline-review.md`：
  被排除的条件、`skippedProposals` 字段、单个评审仍如实报告。
- `CHANGELOG.md` Unreleased。
- **验收：** `validate.sh` 与 `check-command-parity.py` 通过；文档不含消费者项目的任何信息。
- **文件：** 三份参考文档、`CHANGELOG.md`。

## Checkpoint：完成

- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过；在触发问题的消费者项目的只读快照上复现：预检不再返回
  `proposal-pool-invalid`；逐条核对 Spec 的成功标准；检查点勾选随模块 PR 一起提交，由分支保护的两项必需 CI 把关合并；
  阶段变为 DONE。
