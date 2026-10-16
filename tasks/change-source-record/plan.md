# Plan: change-source-record

<!-- spec-guard: review approved -->

依据 [`spec/change-source-record.md`](../../spec/change-source-record.md)。本仓库评审节奏为分开审：Spec 已单独批准，本 Plan 单独交审。
分支 `claude/change-source-record`，worktree `.claude/worktrees/spec-guard-plugin-owner-a42afa`，从 `7803862`（v0.63.0 验证记录合并）
开出。本模块一个 PR，含 0.63.1 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

规则文件新增一节「需求来源与回告」（变更记录、回告、接收回告三段），两份约定块模板各新增两行，约定块文档同步，
`verify-artifacts` 加一例不干扰回归，文档与版本号。不新增命令、钩子或检查，不改阶段判定。

## Architecture Decisions

- **规则只有一个出处。** 细则只写在共享检查点规则，模板那两行只指向它。
- **模板只新增行。** 现有行一字不改，升级项目的 `setup-convention --replace` 不会被拒。
- **记录行不写批准，回告结果不进 Spec。** 批准由评审标记表达；Spec 的标记绑定全文，批准后的任何改动都会触发复审，所以
  记录先于复审写好，回告结果写在 `todo.md`。

## Task List

### Task 0：提交已批准的产物

把能力图（新行与「变更记录」）、`.agent/config.json`（评审节奏改为分开审）、已批准的 Spec、本 Plan 与 todo 提交一次，
让后续任务从干净的工作区开始。

- 验收：`verify-and-commit.sh` 快档通过并提交。
- 验证：`/bin/bash scripts/verify-and-commit.sh -- -m "<信息>"`。
- 文件：`spec/CAPABILITY-MAP.md`、`.agent/config.json`、`spec/change-source-record.md`、`tasks/change-source-record/plan.md`、
  `tasks/change-source-record/todo.md`。

### Task 1：规则「需求来源与回告」与模板行（先红）

`test_workflow_checkpoints.py` 加 Spec「Testing strategy」列出的断言并确认失败；再改 `references/workflow-checkpoints.md`、
两份模板与 `docs/convention-block.md`。

- 验收：`test_workflow_checkpoints.py` 通过；`validate.sh --quick` 通过；`git diff` 显示两份模板只有新增行。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`/bin/bash scripts/validate.sh --quick`。
- 文件：`references/workflow-checkpoints.md`、`templates/claude-block-local.md`、`templates/codex-block-local.md`、
  `docs/convention-block.md`、`hooks/test_workflow_checkpoints.py`。

### Task 2：带「变更记录」的能力图照常通过校验

`test-verify-artifacts.sh` 加一例：能力图末尾带「变更记录」一节时，校验结果与不带时相同。预期不需要改代码；若变红，停下报告，
不在本模块扩大范围。

- 验收：verify-artifacts 回归全绿。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`。
- 文件：`hooks/test-verify-artifacts.sh`。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告

### Task 3：文档、CHANGELOG 与版本号

`docs/workflow.md` 一段（记录来源、回告来源、收到回告先核对）；CHANGELOG `[0.63.1]`；两份 `plugin.json` 改为 0.63.1，
中英 README 的 `--ref` 改为 v0.63.1。

- 验收：`validate.sh` 通过。
- 验证：`/bin/bash scripts/validate.sh`。
- 文件：`docs/workflow.md`、`CHANGELOG.md`、两份 `plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 2（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`，一个任务做完并提交后再开始下一个。在对话里列出实际改动的文件、验证结果与未验证项，
并按新规则列「拟回告」（本模块由用户本人提出，预期为“无”）。推送本分支与开 PR 在这个检查点由用户确认；合并由用户进行。

## 影响面

一份规则文件新增一节；两份约定块模板各新增两行，约定块文档同步；一份测试新增断言、一份测试新增一例；两份文档、CHANGELOG、
版本号。已有项目升级后运行 `setup-convention --replace` 才会看到新的模板行；不运行也不影响其余行为。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| agent 在复审批准后才补记录，Spec 再次被判为已修订 | 规则写明先记录再复审，记录行不写批准 |
| 回告结果被写进 Spec，触发复审 | 规则写明回告结果写在 `todo.md` 最后一项 |
| 改动了模板的现有行，升级项目被拒 | 只新增行；Task 1 验收时看 `git diff` |
| 有通信工具时 agent 跳过批准直接回告 | 规则写明回告随最终 gate 批准，到用得上时按批准的内容发 |
| 规则写了但真实会话不照做 | 发版后两边宿主各跑一次真实会话观察，如实记录 |

## Open Questions

- 无。
