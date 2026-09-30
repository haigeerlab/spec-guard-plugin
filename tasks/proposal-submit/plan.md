# Plan: proposal-submit

依据 [`spec/proposal-submit.md`](../../spec/proposal-submit.md)（精简版：补全草稿 + 校验）。三个 task 串行，每个 task
一条提交。代码类 task 先写能在当前代码上失败的测试并记录失败输出，再修改到通过。测试沿用现有的临时 Git 远端夹具，
不访问网络；测试与提交信息只用通用夹具名，不写任何消费者项目的名称、模块或编号。

顺序的理由：Task 1 的 hook 是命令与文档的前提；命令入口单独一个 task，便于 command parity 与 Codex 命令根测试
独立验收；文档最后统一改写为四步。

每个 task 完成时，在默认 `python3` 与 `PATH=/usr/bin:/bin` 下各跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

以及该 task 相关的测试；动到命令或文档时加 `python3 scripts/check-command-parity.py` 与
`/bin/bash evals/test-codex-command-roots.sh`。

## Task 1：补全与校验 hook（S1–S3）

- 新增 `hooks/proposal_submit.py`：读取草稿与唯一 v2 标记、路径与 id 一致、从远端固定快照生成并替换基线一节、
  计算 revision、`parse_proposal` + `validate_proposal`、远端池同 id 检查（另一文件拒绝、同一路径标注修订）、
  预览 diff 与下一步输出、`--confirm` 原子写回草稿。
- 新增 `hooks/test_proposal_submit.py`：Spec 测试策略中的全部正例、修订、幂等、端到端与反例；`scripts/validate.sh`
  加入该测试。
- **验收：** 新测试在当前代码上失败、实现后通过；已有测试全部通过。
- **文件：** `proposal_submit.py`、`test_proposal_submit.py`、`scripts/validate.sh`。

## Task 2：命令与 Codex 入口（S4 入口）

- `commands/proposal-submit.md`：前提（先按模板写草稿）、预览命令、原样转述 diff／revision／修订标注／下一步、
  被拒时如何处理、确认后 `--confirm`、不做远端操作。
- `skills/spec-guard-ops/SKILL.md`：同步 Codex 入口；`evals/test-codex-command-roots.sh` 的命令清单加入新命令。
- **验收：** `check-command-parity.py`、Codex 命令根测试、`validate.sh` 通过。
- **文件：** 上述三个文件（及检查脚本要求同步的清单，如有）。

## Task 3：四步文档、发版流程与 CHANGELOG（S4 文档）

- `docs/workflow.md` Proposal 一节改写为四步（提交／接受／晋级／收尾），删除手工计算 revision 的片段；README、
  `docs/concepts.md` 同步；`references/proposal-contract.md` 补可复制的草稿模板并说明基线与 revision 由命令填写。
- `docs/release-process.md` 删除快进 `integration/mainline` 的步骤。
- `CHANGELOG.md` Unreleased：`### 新增`、`### 变更`。
- **验收：** `validate.sh`、`check-command-parity.py`、`check-readme-sync.py` 通过；文档中不再出现手工计算 revision
  或快进 `integration/mainline` 的要求（历史记录除外）；不含消费者项目信息。

## Checkpoint：完成

- 两种 Python 下三条最小验证、`test_proposal_submit.py`、`test_proposal_publication.py`、command parity 与 Codex
  命令根测试全部通过；逐条核对 Spec 的成功标准。
- 只读演示：在本仓库的临时克隆里对真实远端默认分支写一份假设的新草稿，只跑预览，基线 Commit、Goal digest 与各模块
  行摘要应与远端能力图一致（不写本仓库任何文件）。原计划用已发布的 Proposal 演示不可行：它的模块已在能力图中，
  按当前远端补全必然被拒。
- 检查点勾选随模块 PR 一起提交；阶段变为 DONE（Proposal 精简三个模块全部完成）。
