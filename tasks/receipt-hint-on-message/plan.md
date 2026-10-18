# Plan: receipt-hint-on-message

<!-- spec-guard: review approved -->

依据 [`spec/receipt-hint-on-message.md`](../../spec/receipt-hint-on-message.md)。本模块按用户要求 Spec 与 Plan 合并交审一次（项目配置不变）。
分支 `claude/receipt-hint-on-message`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `207218d`（0.71.1 发版收尾）开出。
本模块一个 PR，含 0.72.0 版本号；发版后另开一个收尾 PR 放证据。

所需工具：无 UI 改动；发版后的真实会话复测用 tmux 起交互会话、用 SendMessage 发真实跨会话消息。

## Overview

`session_context.py` 多输出一行「这一轮是不是转来的消息、对方是谁」；`phase-guard.sh` 在有账本时据此在建议下一步前加一行提醒。其余输出不变。

## Architecture Decisions

- **判定放在 session_context.py。** 它已经解析 hook 输入、并有 `safe_fragment`；phase-guard 只读它的第 5 行，不自己解析提示词。
- **提醒放在建议下一步之前**，和上下文行同一位置规则，模型读到建议之前先看到它。
- **不改规则文字与模板。** 规则已写明收到即记，本模块只补「到达那一刻」的提示。

## Task List

### Task 0：提交已批准的 Spec、Plan 与 todo

- 验收：`review-mark` 记两份为 approved；`verify-and-commit.sh` 快档通过并提交。

### Task 1：回归先红

`test-phase-guard.sh` 新增一段，覆盖 Spec Testing strategy 的五种情形（中英文、正文中段提及、无账本、属性不合格、SessionStart）。先确认失败。

- 验收：新断言失败，原有用例通过。
- 文件：`hooks/test-phase-guard.sh`。

### Task 2：实现

- `session_context.py`：读 `prompt`，判定包装，输出第 5 行；
- `phase-guard.sh`：按 Contract 拼提醒行。

- 验收：phase-guard 回归全绿；`validate.sh` 通过。
- 文件：`hooks/session_context.py`、`hooks/phase-guard.sh`。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警

### Task 3：CHANGELOG 与 0.72.0 版本号

CHANGELOG `[0.72.0]`；两份 `plugin.json` 改为 0.72.0，中英 README 的 `--ref` 改为 v0.72.0。

- 验收：`validate.sh` 通过。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

列出实际改动、验证结果与未验证项；拟回告：无（需求来自用户本人）。

### 发版后的验证

PR 合并后按 `docs/release-process.md` 发 0.72.0：tag、发布包、Release、两边宿主升级与 Codex smoke、证据 JSON。
然后按 Spec 假设 4 复测 3 次 Claude 交互会话，记录每次是否当场记账；3 次都记才算达标，不达标如实记下并回来找用户。
