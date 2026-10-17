# Plan: concurrency-rule-wording

<!-- spec-guard: review approved -->

依据 [`spec/concurrency-rule-wording.md`](../../spec/concurrency-rule-wording.md)。本仓库评审节奏为分开审：Spec 经 delegate 只读审查、按六条发现
修订后，于 2026-10-18 获批（`2cf8fb6`），本 Plan 单独交审。分支 `claude/module-concurrency`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`。
按批量发版约定不改版本号、不推送、不开 PR；验收后回到 `map-startable` 写 Plan（它的 Spec 已批准）。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

只改共享规则 `references/workflow-checkpoints.md`：先写断言并确认是红的，再写新的一节和三句指引；用一次整份比对证明除此之外一字未改；最后记 CHANGELOG。

## Architecture Decisions

- **整份比对分两层做，和 Spec 的写法有一处出入，请留意。** Spec 测试策略写的是「测试从当前文件去掉新增内容后与原文逐字节相同」。如果把原文存成长期测试夹具，
  后面的 `checkout-role`、`crew-interface` 只要合规地改这个文件（它们大概率会改），这条测试就会失败，只能连夹具一起改，测试也就失去意义。所以：
  - **一次性的整份比对**（本模块的 Checkpoint 1）：用一个临时脚本，从当前文件里去掉新的一节和三句指引，与改动前提交（`2cf8fb6`）里的原文逐字节比对；两份约定块模板
    用 `git diff 2cf8fb6 -- plugins/spec-guard/templates/` 确认为空。结果记进 todo。改坏验证也在这一层做：改动原文任意一个字，确认比对报差异。
  - **长期断言**（留在 `test_workflow_checkpoints.py`）：三句原文逐字存在；新一节的全部要点；三句指引各指向新一节；约定块模板不出现 `moduleConcurrency`。这些在以后的模块
    合规改动时不会误报，又能拦住删改原句、删掉关键底线。
- **新一节的位置**：「并行边界」之后、「按需求批量前置审」之前，标题 `## 协调会话的批准与合并（moduleConcurrency 为 on 时）`。
- **断言测关键短语**，但「唯一例外」「远端」「不自动重试」「重新取得」这几处底线必须精确命中。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：共享规则新增一节与三句指引（先红后绿）

先在 `test_workflow_checkpoints.py` 加 `CoordinatorApprovalTests`，确认是红的：
- 三句原文逐字存在（「`approved` 只在用户于当前对话明确批准」那一句的开头、「合并永远由用户进行，任何 Plan 都不能授权 agent 合并。」、「两种节奏下人工闸门都在，合并永远由用户进行。」）；
- 新一节存在，位于「并行边界」之后、「按需求批量前置审」之前，节首写明不是 `on` 时不适用；
- 新一节含：唯一例外、三个条件、同一时刻只有一个、集成基线、核对内容与交审版本一致、不能凭转达、模块分支的提交与集成分支的提交、重新确认、一次只合一个、
  Build order、不改写历史（不变基、不压缩、不强推）、新提交撤回、不 reset、停止后续合并、不自动重试、不算完成、冲突退回、替换后重新取得、推送和远端合并仍只由用户；
- 「评审状态标记」的 `approved` 一条、「Plan 检查点分级」的合并句之后、「评审节奏」的合并句之后，三处都提到新一节；
- 约定块模板仍不出现 `moduleConcurrency`；新一节不含 `parallel-`／`parallel_`。

再按 Spec 假设 3～6 写新一节，加三句指引。

- 验收：用例全绿；`check-no-parallel-surface.py` 通过。

### Checkpoint 1（report）：整份比对、三套核心回归与改坏验证

- 一次性整份比对（见 Architecture Decisions）：去掉新增内容后与 `2cf8fb6` 的原文逐字节相同；约定块模板 `git diff` 为空；
- 改坏验证：改动原文任意一个字，整份比对报差异；删掉新一节「远端」那句、删掉「不自动重试」那句，对应断言变红。都复原；
- 三套核心回归全绿（本模块不改 hook 代码）。

结果记进 todo。

### Task 2：CHANGELOG

「未发布」小节加一条「变更」：开关为 on 时，协调会话的批准与本地合并规则。

- 验收：`verify-and-commit.sh` 通过。

### Checkpoint 2（gate）：模块验收

在正文列出：实际改动的文件（标出超出预计的）；新一节全文与三句指引原文；整份比对结果；验证结果与未验证项；文档建议。

用户验收后勾选并提交，回到 `map-startable` 写 Plan。

- 验收：用户验收通过。

## 影响面

- 修改：`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、CHANGELOG；
- 本模块的 Plan 与 todo。不改约定块模板、hook 代码与 `review-mark`。

## Risks and Mitigations

- **长期断言比整份比对弱。** 以后有人在新一节外悄悄改了别处原文，长期断言拦不住；这是为了不让后续合规改动误报而做的取舍。缓解：三句关键原文逐字锁住；整份比对的结果记在本模块 todo 里，可复查。
- **规则写了，真实协调会话不一定守得住。** 留给第 7 关实测，Spec 已写明。

## Open Questions

- 无。
