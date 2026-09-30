# Spec: promotion-proof-diagnostics

## Objective

`/spec-guard:proposal-promotion-proof` 被拒时只报 `promotion-invalid`，用户看不出该改能力图还是改 Proposal。
2026-09-30 在一个消费者项目的只读快照上，证明返回 `invalid`，要写脚本逐项比对才发现：晋级那一行的职责文字与声明
不同、依赖从 6 个减到 3 个。

自 v0.33.0 起，`add-module --proposal` 写入前已用 `_matches` 自检，所以证明被拒的真实来源只剩两类：旧方式手工晋级
的行与声明不符，以及晋级 PR 顺手改了其他模块行。本模块只为这两类给出具体诊断码与定位信息。

登记：2026-09-30 经 `/spec-guard:add-module` 插入能力图。用户评审时认为首版（为 8 处 `invalid` 各设诊断码）
过度设计：其余 6 处在当前算法下几乎不会发生或已被上游拦下，保持 `promotion-invalid`。

## Assumptions

用户已于 2026-09-30 确认：

1. `state` 仍为 `invalid`；只有以下两处的 `diagnostic` 改为具体码：
   - 晋级行的职责、依赖或位置与 Proposal 声明不符 → `promotion-row-mismatch`；
   - 晋级提交改动了其他模块行或它们的顺序 → `promotion-other-rows-changed`。
2. 这两种结果额外带 `promotionCommit`（找到的晋级提交）；`promotion-row-mismatch` 另带 `mismatchedFields`，取值为
   `responsibility`、`dependsOn`、`position` 的子集，按此顺序。
3. 其余 `invalid` 分支、`proved`／`not-promoted`／`not-accepted`／`stale`／`unknown` 与预检输出逐字不变；
   `as_json` 仍只输出符合短码格式的诊断。
4. 只改 `proposal_promotion_proof.py` 及其测试、`references/proposal-promotion-proof.md`、
   `commands/proposal-promotion-proof.md` 与 `CHANGELOG.md`；不改 `add-module --proposal`。
5. 一个 task：代码、测试与文档；随下一版发布。

## Contract

- 在证明找到晋级提交 C、父提交 P 之后：
  1. P 已含该模块 → 维持 `invalid`（不改）；
  2. 行不符：计算 `mismatchedFields`——`responsibility`（行职责 ≠ 声明）、`dependsOn`（行依赖 ≠ 声明，按顺序比较，
     与 `_matches` 一致）、`position`（位置不满足锚点，与 `_matches` 一致）；非空 → `invalid`、
     `promotion-row-mismatch`、`promotionCommit` = C、`mismatchedFields`；
  3. 否则若 `_only_adds` 为假 → `invalid`、`promotion-other-rows-changed`、`promotionCommit` = C。
  判断顺序与现有代码一致（先行是否相符，再看其他行），`_matches` 为真当且仅当 `mismatchedFields` 为空。
- `Proof` 新增可选的 `mismatched_fields`；`as_json` 仅在非空时输出 `mismatchedFields`（列表）。
- 不复制 `_matches` 的判断：由同一个函数给出不符字段，`_matches` 改为基于它返回布尔值，保证两者不会分叉。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py
python3 -B plugins/spec-guard/hooks/test_module_insert.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
```

## Testing strategy

- 先写测试并确认它在当前代码上失败，再修改；沿用现有临时远端与 tracker 夹具。
- 职责与依赖都与声明不符的晋级（模拟消费者项目的情况）→ `promotion-row-mismatch`，`promotionCommit` 为该提交，
  `mismatchedFields == ["responsibility", "dependsOn"]`；
- 只有位置不符（锚点要求紧跟而实际不是）→ `mismatchedFields == ["position"]`；
- 行相符但顺手改了另一个模块的职责 → `promotion-other-rows-changed`，带 `promotionCommit`，无 `mismatchedFields`；
- 已有 `_matches` 单测（锚点变体）与全部证明／预检测试保持通过；`test_module_insert.py`（依赖 `_matches`）保持通过。
- 两种 Python 下三条最小验证与上述测试都通过。

## Boundaries

- Always：先红后绿；hook 只读；状态值与成功路径输出不变；诊断只输出短码。
- Ask first：新增状态；改变其他 `invalid` 分支的诊断；改动 `add-module --proposal`。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 上述三类被拒情况分别给出对应诊断码与定位字段，用户不需要额外排查就能知道改哪里。
- 其余结果逐字不变；`_matches` 与 `mismatchedFields` 同源。
- 三条最小验证与 `check-command-parity.py` 在两种 Python 下都通过。

## Open questions

- 无。
