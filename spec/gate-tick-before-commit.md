# Spec: gate-tick-before-commit

<!-- spec-guard: review approved 4f972ea42788 -->

## Objective

一个消费者项目连续三个模块都出现同一个问题：用户在最终 gate 批准“验收通过，并批准这份精确文件清单的本地提交”，agent 按清单
提交；提交之后才勾上这个 gate、更新 `.agent/state.json`，而这两处改动不在清单里，就一直留在工作区。结果是已提交的版本把三个
已验收的模块显示成没做完；之后要挂起一个模块、另开工作位时，这些残留不能整体提交、不能暂存、不能删，让每一步多了一层判断。

之前的模块没有这个问题：那时 Plan 带本地提交授权，验收后会补一个记录验收的提交。问题从“每次提交都要用户单独批准精确文件
清单”开始出现。

本模块在共享检查点规则里加一句，让提交本身记录模块完成。

登记：2026-10-15 经 `/spec-guard:add-module` 插入能力图。问题由观测会话报告，插件所有者只读核对过现场，用户已确认做法。

## Assumptions

用户已于 2026-10-15 确认：

1. **批准包含提交时，先勾再提交。** 先勾上这个 gate、更新状态记录（`.agent/state.json`，以及项目惯例里要更新的其他状态记录），
   把它们列进待批准的提交清单，一并提交。
2. **批准不含提交时，照实说明。** 说明勾选与状态记录留在工作区、尚未提交。
3. 只加在「Plan 检查点分级」里“最终验收列出实际改动的文件”那一条之后；约定块已有一行指向那条规则，模板不改。
4. 不给 `verify-artifacts` 加“已提交版本与工作区阶段不一致”的提示：那是新机制，这一句规则已消除问题的来源。
5. 版本 0.60.4，一个 PR。

## Contract

`references/workflow-checkpoints.md`「Plan 检查点分级」一节，在“最终验收列出实际改动的文件”那一条之后新增一条：

> **最终验收的提交包含勾选与状态记录。** 最终 gate 的批准包含提交时，先勾上这个 gate、更新 `.agent/state.json` 以及项目
> 惯例里要更新的其他状态记录，把它们列进待批准的提交清单，一并提交，这样提交本身就记录了模块完成。批准不含提交时，照实说明
> 这些改动留在工作区、尚未提交。

`CHANGELOG.md` 新增 `[0.60.4]`；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.60.4。阶段判定、阶段提示、`verify-artifacts`、
约定块模板与所有命令的行为都不变。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- 先加断言并确认失败：`test_workflow_checkpoints.py` 的最终验收用例补关键词（先勾上这个 gate、`.agent/state.json`、
  列进待批准的提交清单、批准不含提交时）。
- 其余回归不改，全部通过即证明行为未变。
- 发版后两边宿主各跑一次：临时项目里唯一的模块做到最终 gate，在批准里同时批准提交，看提交是否包含 gate 勾选与状态记录。

## Boundaries

- Always：规则只有一个出处；模板不改。
- Ask first：为它加检查或钩子提示；规定提交的分法。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 规则写明批准含提交时先勾、更新状态记录、一并提交，不含提交时照实说明。
- 全套检查通过。
- 发版后的真实会话按 Testing strategy 观察，结果如实记录。

## Open questions

- 无。
