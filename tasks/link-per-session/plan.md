# Plan: link-per-session

<!-- spec-guard: review approved -->

依据 [`spec/link-per-session.md`](../../spec/link-per-session.md)。本仓库评审节奏为合并审：Spec 与本 Plan 一起评审、一次批准
（2026-10-13，内容先在对话里给出，用户批准后写成文件）。分支 `claude/link-per-session`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`，从 `6d0590f`（v0.59.0 验证记录合并）开出。本模块一个 PR，含 0.60.0 版本号；
合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先实测会话标识的稳定性，再扩展 `project_link.py` 的解析，然后是钩子、命令、文档。命令文件已存在，不会出现引用未建命令的问题。

## Architecture Decisions

- **解析仍只有一处。** `project_link.resolve` 增加候选标识参数并返回来源；钩子与命令都调用它。
- **候选标识在 Python 里从 hook 输入取**，bash 只把已读到的那一行输入转交过去，不在 bash 里解析 JSON。
- **目录级路径不动。** 不带候选标识调用时，返回值与现行相同；版本 1 的全部用例是不变性的回归。

## Task List

### Task 1：实测会话标识的稳定性

在两边宿主上各测：恢复同一会话后标识是否不变；能测到的话，压缩后是否不变；Codex 的 hook 输入里有没有 `session_id` 字段
（没有直接证据时照实记“未实测”，设计已不依赖它）。把方法与结果写进 todo。

- 验收：todo 里有每一项的结果或“未实测”及原因。**若标识在会话生命期内会变，停下来找用户。**
- 验证：实测命令及输出摘要。
- 文件：`tasks/link-per-session/todo.md`。

### Task 2：解析支持会话登记（先红）

`test_project_link.py` 加解析表每一行与版本 2 的无效写法并确认失败；再改 `resolve`。

- 验收：单测全绿，原有用例不改。
- 验证：`python3 -B plugins/spec-guard/hooks/test_project_link.py`。
- 文件：`hooks/project_link.py`、`hooks/test_project_link.py`。

### Task 3：钩子按会话查找（先红）

`test-phase-guard.sh` 加 Spec「Testing strategy」列出的用例并确认失败；再改 `phase-guard.sh` 与 `project_link.py resolve` 子命令。
变异：不优先查会话登记、没登记时也用别人的登记。

- 验收：phase-guard 回归全绿；目录级用例逐字不变；两处变异各有断言变红。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`。
- 文件：`hooks/phase-guard.sh`、`hooks/project_link.py`、`hooks/test-phase-guard.sh`。

### Checkpoint 1（report）：核心回归全绿，ShellCheck 无警告

### Task 4：命令支持 `--session`（先红）

`test_project_link.py` 加命令用例并确认失败；再实现。临时目录里实跑：两个会话各自登记，钩子各给各的项目。

- 验收：单测全绿；实跑结果记入 todo。
- 验证：同 Task 2 的命令；实跑输出摘要。
- 文件：`hooks/project_link.py`、`hooks/test_project_link.py`。

### Task 5：命令文件、技能、文档、那句规则、CHANGELOG 与版本号

- 验收：`validate.sh` 通过。
- 验证：`/bin/bash scripts/validate.sh`。
- 文件：`commands/link-project.md`、`skills/spec-guard-ops/SKILL.md`、`references/workflow-checkpoints.md`、
  `hooks/test_workflow_checkpoints.py`、`docs/commands.md`、`docs/troubleshooting.md`、`docs/design.md`、`CHANGELOG.md`、两份
  `plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 2（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`，一个任务做完并提交后再开始下一个。展示验证结果与未验证项。推送本分支与开 PR 在
这个检查点由用户确认；合并由用户进行。

## 影响面

指向解析、钩子的一段、命令脚本、一个命令文件、一份技能、一条规则、三份文档。只用目录级指向的项目不受影响。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| 会话标识在压缩或恢复后变化，登记失效 | Task 1 先测；会变就停下找用户 |
| 文件里积累失效的登记 | `show` 列出每条登记；不自动清理是有意的 |
| 旧版本插件读到版本 2 的文件 | 它按格式无效给诊断，不会误用别人的登记；CHANGELOG 写明 |

## Open Questions

- 压缩或恢复后会话标识是否变化：Task 1 实测。
