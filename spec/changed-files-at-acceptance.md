# Spec: changed-files-at-acceptance

<!-- spec-guard: review approved fcf58afe5e1f -->

## Objective

用户在模块最终验收时批准的是一批改动，但整个流程没有任何一处在对话里告诉用户实际改了哪些文件：Spec 交审讲的是范围，
Plan 列的是“预计”会动的文件，检查点展示的是验证结果。实地使用里，三个会话的最终验收都是这样，用户只能自己去翻差异。

本模块在共享检查点规则里补两条要求：

1. 模块最终验收的那次停顿，在对话里列出本模块实际改动的文件。
2. 报告一个任务做完时，带上它改动的文件数与提交号。

只改规则文字与约定块模板里的一行，不加命令、不加钩子输出、不改任何判定。

登记：2026-10-13 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-13 确认范围与排期（单独一个小模块，0.60.1）。以下是写规则时还需要定下来的几点：

1. **“最终验收”指模块 Plan 里最后一个 `gate` 检查点。** 途中的其他 `gate` 不要求列清单；`report` 检查点不停，也不要求。
2. **清单取自版本库。** 相对模块开始前的状态（通常是模块分支的起点）取差异统计，不凭记忆写。规则不规定具体命令。
3. **呈现方式只定内容，不定格式。** 必须有：新增、修改、删除三类及各自的行数，合计的文件数。文件多时可以按目录归并，
   只展开关键文件。用表格还是列表由 agent 按数量决定。
4. **单独标出超出 Plan 预计影响面的文件**，并说明为什么动了它；没有就写“无”。
5. **任务结果只多半句话**：“改动 N 个文件，提交号”。不展开清单，也不规定任务结果的其他写法。
6. **项目不按任务提交时**：任务结果里只说文件数；最终验收列相对上次提交的全部未提交改动，并照实说明这是未提交的改动、
   分不到各个任务。不为此加机制。
7. **项目不在版本库里时**：照实说明清单不是取自版本库，按已知的改动列出。
8. **不加的位置**：Spec 交审、`report` 检查点、发版报告。
9. 约定块模板只新增一行，不改已有的行（改已有行会让升级的项目在 `setup-convention --replace` 时被拒绝）。

## Contract

### 规则文本

`references/workflow-checkpoints.md` 的「Plan 检查点分级」一节新增两条：

- **最终验收列出实际改动的文件。** 模块 Plan 的最后一个 `gate` 检查点，除开头的五件事外，还要在对话里列出本模块相对
  开始前实际改动的文件：分新增、修改、删除并带行数，取自版本库的差异统计，不凭记忆；文件多时按目录归并、只展开关键文件；
  单独标出超出 Plan 预计影响面的文件并说明原因，没有就写“无”。项目没有按任务提交时，列相对上次提交的全部未提交改动并
  照实说明；项目不在版本库里时，说明清单不是取自版本库。只给链接或只说“见差异”不算。
- **任务做完的结果带上文件数与提交号。** 向用户报告一个任务做完时，带上它改动了几个文件和对应的提交号；没有提交时只说
  文件数。不展开清单。

### 模板与文档

- 两份约定块模板（`templates/claude-block-local.md`、`templates/codex-block-local.md`）各新增一行，指向共享检查点规则。
- `docs/convention-block.md` 同步这一行；`docs/workflow.md` 在讲检查点的地方补一句；`CHANGELOG.md` 新增 `[0.60.1]`。
- 本仓库 `AGENTS.md` 的约定块用工作区源码更新（先预览，只应新增一行）。
- 版本号 0.60.1：两份 `plugin.json`、中英 README 的 `--ref`。

### 不变

阶段判定、阶段提示的文字、`verify-artifacts` 的检查与输出、所有命令的行为都不变。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- 先加断言并确认失败，再改规则：`test_workflow_checkpoints.py` 新增一例，检查「Plan 检查点分级」一节含两条规则的关键词
  （最终验收、新增、修改、删除、差异统计、超出 Plan、文件数、提交号），以及两份模板各有指向它的一行。
- `test-setup-teardown.sh` 全部通过，证明新增的模板行不破坏接入与移除。
- 阶段钩子与 `verify-artifacts` 的回归不改，全部通过即证明输出未变。
- 静态测试只证明文字在场。agent 是否照做，发版后在两边宿主各用一个临时小模块跑到最终验收，看对话里是否列出文件清单。

## Boundaries

- Always：规则只有一个出处，模板与文档只放要点和指向；模板只新增行。
- Ask first：把清单要求扩到其他检查点、Spec 交审或发版报告；规定清单的固定格式；让钩子或命令生成清单。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 共享检查点规则写明最终验收要列出实际改动的文件，以及任务结果带文件数与提交号。
- 两份约定块模板各多一行，已有的行逐字不变；升级的项目 `setup-convention --replace` 不需要 `--accept-removals`。
- 三条最小验证与 ShellCheck（如有 `.sh` 改动）全部通过。
- 发版后两边宿主各有一次真实会话在最终验收时列出了文件清单；做不到时如实记为未验证。

## Open questions

- 无。
