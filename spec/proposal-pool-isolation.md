# Spec: proposal-pool-isolation

## Objective

`hooks/proposal_publication.py` 的 `read_published_pool` 从远端默认分支的一个快照读取 `spec/proposals/*.md`，
逐个解析、核对基线并校验。任何一个 Proposal 校验失败，循环内立即 `return PublicationPool("invalid", ...)`
（基于 `main` 的 `33b2d7f` 评估：第 222–239 行），整个池失效。池的使用方——主链候选与裁决
（`proposal_mainline_review.py`）、晋级预检与证明（`proposal_promotion_proof.py`）——随之全部返回
`proposal-pool-invalid`。

2026-09-29 在一个消费者项目中实际发生：仓库迁移后，一个早已晋级的历史 Proposal 仍留在 `spec/proposals/`，
它记录的基线提交只存在于迁移前的仓库，于是新仓库里所有后续 Proposal 的预检、晋级与证明都无法进行。
用 `main` 的 `33b2d7f` 在该项目的只读快照上复现：`read_published_pool` 返回
`invalid`（`Proposal baseline commit is not on remote default branch`），晋级预检返回 `proposal-pool-invalid`。

本模块让"已经晋级、自身又校验失败"的历史 Proposal 不再拖累整个池。

登记：2026-09-29 按用户决定经 `/spec-guard:add-module` 快速插入能力图；方案经用户选定为 A。

## Assumptions

用户已于 2026-09-29 确认（方案 A）：

1. 已晋级的 Proposal（其声明的 `Module id` 已在远端默认分支的能力图中）若基线核对或 `validate_proposal` 失败，
   从池中排除，不再使整个池失效。

以下为本 Spec 提出、待评审确认的细节：

2. 只容忍"解析成功之后"的失败：`parse_proposal` 本身失败时无法得知模块 id，仍使整个池失效（行为不变）。
3. 已晋级且校验通过的 Proposal 仍留在池中，行为逐字不变——否则刚晋级的模块无法再做晋级证明。
4. 未晋级的 Proposal 校验失败、重复 id、能力图缺失或无效、池超过上限等情况，行为不变。
5. 被排除的 Proposal 记录在池结果的新字段 `skipped`（`(proposal id, diagnostic)` 列表，按路径排序）；命令的
   JSON 输出只在 `skipped` 非空时附加该字段，否则输出逐字不变。
6. 验收记录（attestation）的内容、路径与 `policy_digest` 不受影响；被排除的 Proposal 不参与 attestation 查找。
7. 只改 `read_published_pool`；单个读取的 `read_published`（`/spec-guard:proposal-review` 使用）行为不变：对那个
   历史 Proposal 单独评审时，仍如实报告它无效。
8. 与已批准的 Proposal 流程精简（四步）互不冲突：精简后仍需读取 Proposal 池，本模块的行为保留。

## Contract

### P1 池读取（`hooks/proposal_publication.py`）

- `read_published_pool` 在循环开始前，从 `observed_commit` 的能力图（已解析）取得模块 id 集合。
- 对每个 Proposal：
  - `parse_proposal` 失败 → 与现在相同，整个池 `invalid`；
  - 解析成功后，基线 remote/branch 不一致、基线提交不在默认分支上、基线能力图缺失或 `validate_proposal` 失败：
    - 若 `proposal.change.module_id` 在上述模块 id 集合中 → 记入 `skipped`，继续下一个 Proposal；
    - 否则 → 与现在相同，整个池 `invalid`；
  - 其余逻辑（重复 id、attestation、review commit、publication map）不变。
- `PublicationPool` 增加 `skipped` 属性（默认空元组），不改变已有字段与 `state` 取值。

### P2 输出（`hooks/proposal_mainline_review.py`、`hooks/proposal_promotion_proof.py`）

- 两个命令的 JSON 结果在 `skipped` 非空时附加 `"skippedProposals": [{"proposalId": ..., "diagnostic": ...}]`；
  为空时输出逐字不变。
- `diagnostic` 沿用现有 JSON 只输出短码、不外露原始报错的约定（用户 2026-09-29 确认）：基线 remote／默认分支
  不一致 → `proposal-baseline-remote-mismatch`；基线提交不在默认分支上或基线能力图缺失 →
  `proposal-baseline-unavailable`；其余 → `proposal-invalid`。池结果的 `skipped` 内部保留原始诊断。
- 被排除的 Proposal 若正是本次查询的对象：预检／证明／主链裁决返回与"池中不存在该 Proposal"相同的现有结论
  （预检 `publication-absent`、证明 `absent`、裁决 `proposal-not-published`），不新增状态。

### P3 文档

- `references/proposal-publication.md`（或池读取所在的参考文档）、`references/proposal-promotion-proof.md`、
  `references/proposal-mainline-review.md`：说明被排除的条件与 `skippedProposals` 字段。
- `CHANGELOG.md` Unreleased。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_proposal_publication.py
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py
python3 -B plugins/spec-guard/hooks/test_proposal_mainline_review.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Project structure

```text
plugins/spec-guard/hooks/proposal_publication.py       -> P1
plugins/spec-guard/hooks/test_proposal_publication.py  -> P1 回归
plugins/spec-guard/hooks/proposal_mainline_review.py,
  proposal_promotion_proof.py 及其测试                -> P2
plugins/spec-guard/references/proposal-*.md, CHANGELOG.md -> P3
```

## Testing strategy

- 每项先写测试并确认它在当前代码上失败，再修改。
- `test_proposal_publication.py`（沿用现有的临时 Git 仓库与远端夹具）：
  - 正例：池中一个已晋级 Proposal 的基线提交不在默认分支上，另一个 Proposal 正常 → 池 `published`（或现有的
    正常状态），正常 Proposal 在池中，`skipped` 含前者及其诊断；
  - 反例：同样的坏基线，但该 Proposal 的模块不在能力图中 → 整个池 `invalid`（行为不变）；
  - 反例：`parse_proposal` 失败 → 整个池 `invalid`；
  - 已晋级且健康的 Proposal 仍在池中、`skipped` 为空；
  - 没有坏 Proposal 时，池结果与现在逐字相同。
- `test_proposal_promotion_proof.py`、`test_proposal_mainline_review.py`：坏的历史 Proposal 存在时，预检／证明／候选
  对其他 Proposal 正常工作；JSON 在有 `skipped` 时带 `skippedProposals`，无时逐字不变；查询被排除的那个 Proposal 时
  得到 `publication-absent`。
- 已有的 attestation／policy digest 测试全部保留并通过。
- 两种 Python（默认 `python3` 3.10 与 `/usr/bin/python3` 3.9）下三条最小验证都通过；在该消费者项目的只读快照上
  复现：预检不再返回 `proposal-pool-invalid`。

## Boundaries

- Always：先红后绿；只读远端默认分支快照；不改 attestation／policy 的格式与摘要。
- Ask first：容忍未晋级 Proposal 的失败（方案 B）；新增池状态；改动 `read_published` 的行为。
- Never：写文件或远端；把被排除的 Proposal 当作有效发布；在 Spec、代码、测试、提交信息中写入消费者项目的名称、
  模块或编号。

## Success criteria

- 一个已晋级、基线失效的历史 Proposal 不再让整个池失效；其余 Proposal 的预检、晋级与证明照常。
- 未晋级 Proposal 的失败、解析失败等现有行为不变；没有坏 Proposal 时所有输出逐字不变。
- 已有验收记录与 policy 摘要不受影响。
- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过。
