# Plan: concurrency-assessment

<!-- spec-guard: review approved -->

依据 [`spec/concurrency-assessment.md`](../../spec/concurrency-assessment.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-18
单独批准（用户决定不做外部审查，Spec 里已写拒绝标记），本 Plan 单独交审。分支 `claude/module-concurrency`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`。按批量发版约定，本模块不改版本号、不推送、不开 PR，验收后直接进入下一个模块
`module-scope-boundary`。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

只改共享检查点规则 `references/workflow-checkpoints.md`：先在 `test_workflow_checkpoints.py` 写断言并确认是红的，再写新的一节并让
「文档建议」指向它，最后记 CHANGELOG。

## Architecture Decisions

- **新一节放在「文档建议」与「按需求批量前置审」之间**，标题 `## 并行评估（moduleConcurrency 为 on 时）`，节首第一句写明开关不是 `on`
  时整节不适用、交审内容与以前相同。
- **「文档建议」一节只加一句指引**，加在「能力图评审」那一条的末尾，不动其他两条。
- **断言测关键短语，不测整段原文**，以后措辞调整不会牵连太多；但节首的适用条件、两条硬门槛、「只在这里算」这几处必须精确命中。
- **约定块模板不出现 `moduleConcurrency`**：用一条断言锁住，证明写进用户项目的约定块不因本批改动而变。
- `docs/design.md` 没有讲能力图评审停点的段落，按 Spec「如有」不改。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：共享规则新增「并行评估」一节（先红后绿）

先在 `test_workflow_checkpoints.py` 新增一个测试类，确认是红的：
- 有 `## 并行评估（moduleConcurrency 为 on 时）` 一节，节内第一段含「不是 `on`」「不适用」；
- 节内含两条硬门槛（「同时开工」「2 个」、「集成基线」）、三项参考（「文件分区」「共享接口」「热点文件」）、「逗号组」「往前挪」、
  「关键路径」「只在这里算」、「未核实」、「/spec-guard:config」、「能粗就粗」；
- 「文档建议」一节的能力图评审一条提到「并行评估」；
- `templates/*-block-*.md` 里都不出现 `moduleConcurrency`；
- 新一节不含 `parallel-`／`parallel_`。

再按 Spec 假设 1～6 写这一节，并在「文档建议」加指引。

- 验收：`test_workflow_checkpoints.py` 全绿；`check-no-parallel-surface.py` 通过。

### Checkpoint 1（report）：三套核心回归全绿，并做两次改坏验证

- 删掉节首「不适用」那一句，确认对应断言变红；
- 在 `templates/claude-block-local.md` 加一个 `moduleConcurrency`，确认「模板里不出现」一例变红。

两处都复原；`git diff --stat` 确认改动只在共享规则、测试和本模块流程文件里。结果记进 todo。

### Task 2：CHANGELOG

在「未发布」小节的「新增」下加一条：开关为 `on` 时，能力图评审给出并行评估。

- 验收：`verify-and-commit.sh` 通过。

### Checkpoint 2（gate）：模块验收

在正文列出：
- 实际改动的文件（取自版本库），标出超出预计的；
- 新一节的全文（篇幅短，直接贴）；
- 验证结果和未验证项（规则能否让 agent 写出合格评估，留到第 7 关实测）；
- 文档建议。

用户验收后勾选并提交，直接进入 `module-scope-boundary`。

- 验收：用户验收通过。

## 影响面

- 修改：`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、CHANGELOG；
- 本模块的 Plan 与 todo。

## Risks and Mitigations

- **共享规则是两个宿主都读的文件，改了 off 项目的 agent 也会读到这一节。** 节首适用条件写在第一句，并有断言锁住；行为上 off 项目
  不受影响。
- **规则写了，agent 实际评估不合格。** 单元测试证明不了，Spec 已写明留到第 7 关在样本项目实测。

## Open Questions

- 无。
