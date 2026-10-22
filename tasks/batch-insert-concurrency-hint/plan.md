# Plan: batch-insert-concurrency-hint

<!-- spec-guard: review pending -->

依据 [`spec/batch-insert-concurrency-hint.md`](../../spec/batch-insert-concurrency-hint.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-22
单独批准（用户批准事项 C139，Q1 选 A：看本会话可用技能判断 module-crew，不写探测脚本），本 Plan 单独交审。分支
`batch-insert-concurrency-hint`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/batch-insert-concurrency-hint`。
不改版本号、不推送、不开 PR；合并由模块协调按用户原话做。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

只改规则文字与回归：先在 `test_workflow_checkpoints.py` 的 `ConcurrencyAssessmentTests` 写断言并确认是红的，再改共享检查点规则的
「并行评估」一节，然后给 `add-module` 的两处说明各加一句指引，最后做改坏验证、同步集成分支跑完整检查。

## Architecture Decisions

- **规则正文只写在「并行评估」一节里。** 新加一小段「**批量插入之后**」，放在「这些都只是建议」一段之前；`add-module.md` 与
  `SKILL.md` 的 add-module 一节只放一句条件句指过去。这样开关不是 `on` 的项目读到的停点规则、约定块、阶段提示都不变。
- **按用户对重叠的答复只追加、不动别的行。** `quiet-injection` 独占 `references/workflow-checkpoints.md` 与 `hooks/test_workflow_checkpoints.py`；
  本模块在前者只改「并行评估」一节（时机一句改写、加一小段），在后者只在 `ConcurrencyAssessmentTests` 里加用例。后合入的一方先 `module-crew sync`。
- **断言测关键短语，不测整段原文**；「插入单个模块不算能力图审阅」改写后用一条「不含」断言锁住，防止新旧两句并存。
- **module-crew 一句按 Q1 A 写**：条件是本会话可用技能里有 `crew-coordinator` 且 checkout 没标角色；拿不准当没装，只给 Build order 建议。
- `docs/design.md` 没有讲批量插入的段落，不改；CHANGELOG 由模块协调整批写，更新说明记在 todo 末尾。

## Task List

### Task 0：提交 Plan 与 todo

Plan 交审时标 `pending`，和 todo 一起提交。收到开工类【协调通知】后单独执行 `module-crew sync`，把集成分支带批准标记的 Spec、Plan 合进来，
确认 Spec 标记是批准版。

- 验收：`verify-and-commit.sh` 快档通过；sync 后 `spec/batch-insert-concurrency-hint.md` 带 `approved` 标记。

### Task 1：「并行评估」一节加批量插入时机（先红后绿，AC1～AC3）

先在 `ConcurrencyAssessmentTests` 加用例，确认是红的：
- 节内含「2 个及以上」「同一个需求」「最后一个」「只评估一次」「不建议并行」「批量插入之后」「插入单个模块不评估」；
- 节内含「module-crew」「crew-coordinator」「协调会话」「只给 Build order 建议」「角色」；
- 节内不含「插入单个模块不算能力图审阅」；
- `references/node-rules.md` 不出现 `moduleConcurrency` 与「module-crew」。

再按 Spec 改动 1 改这一节：时机一句改成三个时机，单个插入一句改写，加「批量插入之后」一小段（假设 1～6）。

- 验收：`test_workflow_checkpoints.py` 全绿；`check-no-parallel-surface.py` 通过。

### Task 2：`add-module` 两处说明加指引（先红后绿，AC4）

先加用例并确认是红的：`commands/add-module.md` 与 `SKILL.md` 的 add-module 一节各含「2 个及以上」「moduleConcurrency」「批量插入之后」，
Claude 侧含 `/spec-guard:config`，Codex 侧含「spec-guard-ops」的 config。再按 Spec 改动 2 各加一句，位置在「等用户明确确认后才加 `--confirm`」那段之后。

- 验收：`test_workflow_checkpoints.py` 全绿；`validate.sh --quick` 通过。

### Checkpoint 1（report）：改坏验证与 off 不变（AC5、AC6）

在 scratchpad 里 `git archive HEAD` 建的副本上各改一处，跑 `test_workflow_checkpoints.py`：
- 删掉「批量插入之后」里「只评估一次」一句 → 对应断言变红；
- 往 `node-rules.md` 写一句 module-crew → 「停点规则不出现」一例变红。

另确认 hook、模板、`node-rules.md` 未改（`git diff --stat crew/fix-batch` 只落在并行边界所列文件）。结果记进 todo，继续。

### Task 3：合入集成分支并跑完整检查

单独执行 `module-crew sync`；然后跑 Spec 的 Commands 全部五条，`module_scope.py check --module batch-insert-concurrency-hint --base crew/fix-batch`
核对越界。sync 冲突在共享检查点规则或测试文件里时以集成分支为底，只把本模块那两处追加放回去。

- 验收：五条命令全绿；越界检查为 0 个，或只有 Spec 已列出的文件。

### 最终验收（gate）

交最终验收【交审】：按 AC1～AC6 逐条给证据，附改动统计与越界检查。不含推送与开 PR。

## Risks and Mitigations

| 风险 | 影响 | 应对 |
|---|---|---|
| `quiet-injection` 同时改共享检查点规则和测试文件 | sync 冲突 | 只在「并行评估」一节和 `ConcurrencyAssessmentTests` 里改；冲突以集成分支为底手工放回两处追加 |
| 规则文字能不能让 agent 在真实批量插入后评估一次 | 单元测试证明不了 | 照 Spec 写明未验证，留到下一次真实批量插入时观察 |
| 改写「插入单个模块不算能力图审阅」影响已有断言 | 旧用例变红 | 现有 `test_section_covers_gates_references_and_advice` 不含这句；如有别的用例命中，按新句同义改写并在 todo 记明 |

## 未决问题

无。
