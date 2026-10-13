# Spec: rework-in-place

<!-- spec-guard: review approved ddfdc7063458 -->

## Objective

已完成的模块需要返工或修订时，约定里没有写它该放在哪。2026-10-13 的实地使用里，agent 在 `tasks/<id>/` 下自造了几种带清单的
文件来承载评审修正、主题扩展与跟随修订。阶段判定只数 `todo.md`，`verify-artifacts` 也不看这些文件：模块显示完成时，旁路清单里
还有没做的项不会被报告，修正期间的阶段显示一直是错的。

同一批观察里的另一件事：在已写好的实现上补建能力图时，许多模块只是对既有功能的盘点，产出只有几十行，却各自走完 Spec、Plan
与多个检查点的全套闸门，用户被要求反复点头。能收敛它的手段（合并审、按需求批量前置审）早已存在，但没有任何文字告诉 agent
这种模块该收敛。

本模块不引入新机制：返工回到原模块的 `todo.md`，阶段判定因此自然如实；`verify-artifacts` 多一条警告指出旁路清单；规则补一条
小模块的收敛指引。

登记：2026-10-13 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-13 确认：

1. 返工或修订已完成的模块：在它的 `todo.md` 追加任务，在 `plan.md` 补一节说明；不另建带清单的文件。给模块加新能力另开模块。
2. `plan.md` 补了一节后，把 Plan 的评审标记改回 `pending`，交用户看过再继续。
3. `verify-artifacts` 多一条警告：`tasks/<id>/` 下除 `plan.md`、`todo.md` 外的文件里有未勾选项时，列出文件与未勾数；只有已勾选项
   或没有清单项的文件不输出。警告不做成失败。
4. 小模块指引：模块只盘点或接收既有实现、不新增行为时，并成相邻模块的一个任务，或批量交审，Plan 里只留最后一个 `gate`。
5. 重新打开已完成的模块会改变“当前模块”（它在 Build order 里靠前，有未勾选项后重新成为当前模块，后面进行中的模块显示为
   暂停）。这是如实报告，按现有判定即可，不做特殊处理。
6. 不做：钩子统计旁路文件里的清单项；规定返工那一节的格式或标题；为“模块边界上的待办”单独建机制（写成上一个模块追加的
   任务或下一个模块的第一个任务即可）；接入时列出全部可选能力。
7. 版本 0.59.0，一个 PR。约定块模板不改。

## Contract

### `verify-artifacts`

对每个 `tasks/<id>/` 目录下直接包含的 `*.md` 文件，除 `plan.md` 与 `todo.md` 外：文件里有未勾选的清单项（与阶段判定同一条
`UNCHECKED` 正则）时输出一条警告，写明文件路径、未勾选项数，以及这些项不计入阶段、返工应写进该模块的 `todo.md`。

- 没有这样的文件、或它们没有未勾选项时，不输出这一项，其余输出逐字不变。
- 子目录里的文件不看；不是 `.md` 的文件不看。
- 检查没有正常运行时报“未验证”，不报通过也不报失败。读不了的文件报未验证并指出文件。
- 只读；判据从 `module_stage.py` 导入，不复制正则。

### 规则文字

`references/workflow-checkpoints.md` 新增一节「返工与小模块」：

- 返工或修订已完成的模块：在该模块的 `tasks/<id>/todo.md` 追加未勾选的任务，在 `plan.md` 补一节说明改什么、为什么；模块因此
  回到进行中，阶段提示如实显示。不在 `tasks/<id>/` 下另建带清单的文件——阶段判定只数 `todo.md`，旁路清单里的未完成项没人看得见。
- `plan.md` 补了一节后，把 Plan 的评审标记改回 `pending` 并交用户审核（按「评审状态标记」的交审要求）。
- 给模块加新能力不是返工：另开模块（`add-module`），或走 Proposal。
- 两个模块之间必须做的事，写成上一个模块追加的任务，或下一个模块的第一个任务。
- 小模块：模块只盘点或接收既有实现、不新增行为时，优先并成相邻模块的一个任务；确需各自成模块时用「按需求批量前置审」
  一次交审，Plan 里只留最后一个 `gate`，其余检查点标 `report`。

`commands/add-module.md` 与 `spec-guard-ops` 的 add-module 一节各补一句指向这两点（返工不开新模块；盘点类小模块先考虑合并或批量）。

### 文档与版本

`docs/workflow.md` 一段；`docs/troubleshooting.md` 一行（新警告的含义与处理）；CHANGELOG `[0.59.0]`；版本号 0.59.0。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先写测试并确认在现有代码上失败，再实现。
- `test-verify-artifacts.sh`：旁路文件有未勾选项时警告并含路径与项数；只有已勾选项不输出；没有清单项不输出；`plan.md`／`todo.md`
  里的未勾选项不触发；子目录里的文件不触发；没有 `tasks/` 时输出逐字不变；检查没跑成报未验证；退出码仍为 0。
- `test_workflow_checkpoints.py`：「返工与小模块」一节的关键词在场；`add-module` 的命令文件与技能各含指向。
- `test-phase-guard.sh` 不改，全部通过即证明阶段判定未变。
- 在本仓库运行 `verify-artifacts`：两份既有的旁路文件全是已勾选项，不应出现新警告。
- 发版后在两份安装副本上各跑一次带旁路清单的临时项目。固定输出，不另做真实 agent 会话。

## Boundaries

- Always：`verify-artifacts` 只读；新检查只警告；阶段判定与完成判据不变；判据不复制。
- Ask first：让钩子统计旁路文件；把警告升级为失败；规定返工一节的格式。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 规则里能读到返工的去处、Plan 补节后须复审、新能力另开模块、小模块的收敛指引。
- 旁路清单有未勾选项时 `verify-artifacts` 警告并列出文件；否则输出不变。
- 阶段判定与其余输出不变；三条最小验证与 ShellCheck 全部通过。

## Open questions

- 无。
