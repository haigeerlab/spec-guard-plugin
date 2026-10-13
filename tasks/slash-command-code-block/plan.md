# Plan: slash-command-code-block

<!-- spec-guard: review approved -->

依据 [`spec/slash-command-code-block.md`](../../spec/slash-command-code-block.md)（2026-10-13 用户评审通过，批准标记已写入）。
本仓库评审节奏为分开审：本 Plan 单独评审。分支 `claude/slash-command-code-block`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`，叠在 `claude/review-marker-legacy-projects`（#290）之上：两个模块一起随 0.57.1
发出，版本号由本模块的 PR 带。#290 先合并，本模块的 PR 再对 `main` 开出。合并后的 tag、Release、两边宿主同步与验证记录按
`docs/release-process.md` 另走。

所需工具：无 UI 改动。发版后的显示核对涉及 Claude 桌面应用自身，电脑操作不能用于它，由用户查看。

## Overview

`module_stage.py` 加一份常量说明，接进三句提示；更新硬编码这几行的测试；规则与排障文档各补一处；版本号 0.57.1。

## Architecture Decisions

- **说明只有一份常量。** 三句提示拼接同一个常量，避免两边宿主的写法漂移。
- **插在“in its own code block”所在的那一句里**，放在命令说明之后、`do not paste handoff text` 之前，保持每行仍是一行。
- **宿主判断不了的路径不碰。** `FREE_BOUNDARY` 与默认的 `free-current` 不引用这个常量。
- 共同验证命令：

  ```bash
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  ```

## Task List

### Task 1：三句提示加斜杠命令说明（先红）

`test-phase-guard.sh`：把硬编码的模块完成行、上下文行（Claude 与 Codex）期望更新为带说明的文字，并加三条要点断言
（不是 shell 命令、不标 shell 语言、发到消息输入框）；加“宿主判断不了时两行逐字不变”的断言。确认失败后改 `module_stage.py`。

- 验收：phase-guard 回归全绿；`validate.sh` 里的自观测报告与 Codex smoke 判决器自检仍通过。
- 文件：`hooks/module_stage.py`、`hooks/test-phase-guard.sh`。

### Task 2：规则与文档（先红）

`test_workflow_checkpoints.py` 先加断言并确认失败；再改 `references/workflow-checkpoints.md` 那半句、`docs/troubleshooting.md`
一行、CHANGELOG（把 `[未发布]` 下补上本模块的条目）。

- 验收：`test_workflow_checkpoints.py` 通过。
- 文件：上述三个文件与测试。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告

### Task 3：版本号

两份 `plugin.json` 改为 0.57.1，中英 README 的 `--ref` 改为 v0.57.1，CHANGELOG 标题 `[0.57.1]`，概述写明本版两个模块。

- 验收：`validate.sh` 的清单一致性通过。
- 文件：两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。

### Checkpoint 2（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`，pre-push 钩子兜底。展示全部验证结果与未验证项。
批准本 Plan 即授权推送本分支并开本模块的 PR；合并由用户进行。发版后的宿主行为验证与用户对桌面应用显示的查看属于
合并后的步骤。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| 提示变长后 agent 反而漏掉 `/compact` 本身 | 说明放在命令说明之后；发版后在真实会话里看 agent 的实际输出 |
| 自观测报告或 smoke 判决器按整行匹配这些提示 | Task 1 即跑 `validate.sh`；匹配失败就一并更新并写进 todo |
| #290 未合并时本 PR 的 diff 含两个模块 | 等 #290 合并后再对 `main` 开本 PR |

## Open Questions

- 无。
