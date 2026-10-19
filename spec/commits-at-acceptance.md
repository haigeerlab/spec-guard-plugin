# Spec: commits-at-acceptance

<!-- spec-guard: review approved 99edaf76bec8 -->

## Objective

模块最终验收已经列出实际改动的文件，但看不出这些改动分几次、各做了什么。一份「提交号＋一句话」的清单一眼就能看清模块做了
什么，用户希望在切模块（最终验收）和准备提 PR 的时候看到它。

本模块在共享检查点规则「最终验收列出实际改动的文件」一条里补一句：再列出本模块的提交；随后推送或开 PR 时，推上去的提交与这份
清单不一致的单独列出差异。

登记：2026-10-19 经 `module-insert.py` 插入能力图。来源是用户在接入协调会话做的决定 69，经协调人自查去掉过度设计后转来；
插件所有者交审方案，用户已确认，并确认了「待提交」一处补充。

## Assumptions

用户已于 2026-10-19 确认：

1. **只补一句，不加新条目。** 写进「最终验收列出实际改动的文件」那一条，紧接新增依赖那一行之后。
2. **提交清单取自版本库，不凭记忆。** 每条提交号和一句话；多时按任务归并，不写死条数阈值。
3. **验收批准后才做的提交写作待提交。** 按 `gate-tick-before-commit`，勾选最终 gate 与状态记录的提交在批准之后才做，验收时的
   清单里没有它；写作待提交，免得推送时被当成不一致。
4. **推送或开 PR 时只报不一致。** 推上去的提交和清单不一致的单独列出差异；不在推送前再完整列一遍。
5. **不做**：挂起时列提交、多模块合 PR 分组、进度汇报规则、条数阈值；module-crew、decision-inbox 不改。
6. 与「任务做完的结果带上文件数与提交号」不重复：那条是每个任务报一个号，这里是最终验收时整个模块的汇总。
7. **不改版本号、不发版。** 阶段丙期间版本冻结（决定 68），0.79.0 不变；CHANGELOG 写进顶部「[未发布]」段，排到下一版。

## Contract

`references/workflow-checkpoints.md`「Plan 检查点分级」一节，「最终验收列出实际改动的文件」一条末尾新增：

> 再列出本模块的提交：取自版本库的提交记录，不凭记忆，每条写提交号和一句话，多时按任务归并；最终验收批准后才做的那次提交
> （勾选与状态记录）写作待提交。随后推送或开 PR 时，推上去的提交和这份清单不一致的，单独列出差异。

两份 `templates/*-block-local.md` 的最终验收摘要行与 `docs/convention-block.md` 的同一句改为：

> 模块最终验收时在对话里列出实际改动的文件（新增、修改、删除与行数，取自版本库）、本模块的提交（提交号＋一句话）及新增依赖与
> 锁文件改动（不含工作区自己的包），推送或开 PR 时与这份提交清单不一致的单独列出；任务做完的结果带文件数与提交号；

`CHANGELOG.md` 顶部新增 `## [未发布]` 段。阶段判定、阶段提示、`verify-artifacts`、命令行为与版本号都不变。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- 先加断言并确认失败：`test_workflow_checkpoints.py` 的最终验收用例补关键词（本模块的提交、提交号和一句话、待提交、不一致），
  模板与 `docs/convention-block.md` 补「本模块的提交」。
- 其余回归不改，全部通过即证明行为未变。
- 发版后两边宿主各跑一次真实会话：做到最终 gate，看是否列出提交清单并标出待提交；推送时是否只在不一致时列差异。

## Boundaries

- Always：规则只有一个出处；摘要行只指向它。
- Ask first：为它加检查或钩子提示；规定条数阈值或提交的分法。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号；本模块里改版本号。

## Success criteria

- 规则写明列提交清单（取自版本库、提交号＋一句话、多时归并、待提交）与推送或开 PR 时只列不一致。
- 两份模板与 `docs/convention-block.md` 的摘要行同步。
- 全套检查通过，版本号不变。

## Open questions

- 无。
