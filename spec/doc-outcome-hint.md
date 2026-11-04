# Spec: doc-outcome-hint

<!-- spec-guard: review approved 53ab2fe8a915 -->

## 目标

启用文档基线的项目里，模块 Plan 写了 `Documentation delivery` 表（计划交付哪些文档），最终验收前还要在同一份 Plan 里补
`Documentation outcome` 表（实际交付了什么），核验才会判 `ready`。0.86.4 的文档没说这一步：`references/documentation-impact.md`
只说「实际交付证据由后续核验模块处理」，文档链的 Plan 交审、最终验收两步也没提；而 `documentation-verification` 读不到这张表时，
对每个关注点各报一行 `<concern> has no declared documentation outcome`，与表里只漏一行时一模一样。

2026-11-04 一个使用方项目实测（S80）：四份文档都改过，核验却报四项 attention，只好在 Plan 里临时加一个任务补表。本模块让文档写清这一步，
并让核验在整张表都没有时直接点出来。

给谁用：启用了文档基线的项目，以及替用户跑核验、转述结果的 agent。

## 假设

用户已于 2026-11-04 确认（「说完了，开模块」，针对本会话的需求总结）：

1. **文档**：
   - `references/documentation-impact.md` 的 `Documentation delivery` 一节写明：表里有 `update` 或 `create` 时，最终验收前要在同一份 Plan 里补
     `## Documentation outcome` 表，否则核验判 `attention`；附一张空模板（列 `Concern | Outcome | Evidence | Rationale`），并链接
     `documentation-verification.md` 的格式说明。
   - `references/workflow-checkpoints.md` 文档链第 2 步（Plan 交审）补：outcome 表在最终验收前补，可作为 Plan 最后一个普通任务；
     第 3 步（最终验收）补：跑核验前先补表。
   - `docs/optional-features.md` 核验那一条补同样一句。
2. **行为**：`documentation_verification.py` 在 Plan 里**整张** `Documentation outcome` 表都没有、且有需交付的关注点时，`attention` 列表的
   **第一行**写明 `tasks/<id>/plan.md has no Documentation outcome table; add one before final acceptance (format: references/documentation-verification.md)`；
   原来每个关注点各一行的 `<concern> has no declared documentation outcome` 照旧跟在后面。
3. **不变**：表存在但只漏了某一行时，输出与 0.86.4 相同；`attention`／`ready`／`invalid`／`absent` 的判定条件不变；JSON 字段不变；
   `interface.json` 不变；不自动生成 outcome 表。
4. 既有用例 `test_missing_outcome_is_attention_not_invalid` 断言 `attention[0]` 含关注点名，因为新的一行排在最前，这条断言要改成看后面的逐项行；
   这是本模块有意的输出变化，改动写进 todo。
5. 发 0.86.5；仓库里不出现消费项目的名字、模块或编号。

## 命令

```text
python3 -B -m unittest plugins/spec-guard/hooks/test_documentation_verification.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## 测试策略

- 先写测试并确认在 0.86.4 上失败，再实现。
- `test_documentation_verification.py`：
  - Plan 里没有 outcome 表、有 `update` 关注点：`state` 为 `attention`，`attention[0]` 含 `has no Documentation outcome table` 与 Plan 路径，
    后面仍有该关注点的 `has no declared documentation outcome`；
  - outcome 表存在、只漏一个关注点：不出现缺表那一行，只有漏掉的那一项；
  - 影响表里没有 `update`／`create`（不要求 outcome）时：不出现缺表那一行；
  - 其余既有用例全部通过。
- 变异（草稿副本）：去掉缺表那一行、把条件改成「表里漏任意一行」，两处都必须让测试变红。

## 边界

- Always：先红后绿；只加一行提示，判定与 JSON 结构不变。
- Ask first：改判定条件；去掉逐项提示；改 `interface.json`；自动生成或改写 Plan。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费项目的名称、模块或编号。

## 成功标准

- Plan 没有 outcome 表时，核验输出第一行点出缺表、给出 Plan 路径与格式出处。
- 表里只漏一行、或不需要 outcome 时，输出与 0.86.4 相同。
- 三处文档写明最终验收前补 outcome 表，`documentation-impact.md` 带空模板。
- 既有回归全部通过（含改过断言的那一条）。

## 待定问题

- 无。
