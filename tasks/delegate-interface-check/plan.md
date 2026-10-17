# Plan: delegate-interface-check

<!-- spec-guard: review pending -->

依据 [`spec/delegate-interface-check.md`](../../spec/delegate-interface-check.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-17
单独批准（用户决定不做外部审查，Spec 里已写拒绝标记），本 Plan 单独交审。分支 `claude/delegate-interface-check`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`，从 v0.66.0 的证据分支 `15a7b4b` 开出（#342 尚未合并，合并后自动对上）。
本模块一个 PR，含 0.67.0 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先在 `sibling_plugins.py` 加读取并校验 delegate 接口说明的函数，再让阶段提示用它的结果决定出不出提示、用什么命令名，最后补文档、
CHANGELOG 和版本号。

## Architecture Decisions

- **新函数 `delegate_review_entry(project, host)` 放在 `sibling_plugins.py`。** 它负责找安装目录、读 interface.json、校验版本和
  命令名，返回 None 或 `{"review", "doctor", "source"}`。现有的 `delegate_enabled` 保留。
- **安装目录：** Claude 侧复用 `claude_plugin_root` 的返回值；Codex 侧把 `codex_plugin_enabled` 里已取得的市场名带出来，在
  `cache/<市场>/delegate/` 下恰好只有一个子目录时取它。
- **命令名只认 `^/delegate:[a-z][a-z-]*$`。** 不合规的项单独回落到默认值，不影响另一项。
- **提示措辞改成带占位的模板。** `COMMANDS` 里 Claude 和未知宿主的 `delegate-review` 改为带 `%(review)s`、`%(doctor)s` 占位的模板，
  默认值仍是 `/delegate:review`、`/delegate:doctor`；Codex 的那条不变。这样默认情况下输出与 0.66.0 逐字相同。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：`delegate_review_entry`（先红后绿）

先在 `test_sibling_plugins.py` 写失败用例，覆盖 Spec 测试策略里列的 Claude 8 例、Codex 4 例，确认它们是红的；再实现函数。

- 验收：新用例和原有用例全绿；`test_agent_relay_probe.py` 不变、全绿；兼容 Python 3.9。

### Task 2：阶段提示改用 `delegate_review_entry`（先红后绿）

先在 `test-phase-guard.sh` 第 17 段写 3 例并确认是红的：
- 夹具 delegate 带 interface 1.0、命令名改为 `/delegate:review2`，提示里出现它；
- interface 2.0 时不出提示；
- 没有 interface.json 时，输出与改动前逐字相同。

再改 `external_review_hint` 和 `COMMANDS` 模板。

- 验收：phase-guard 回归全绿，原有 23 例不变。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并做一次改坏验证

把版本上限放宽到 `<3.0`，确认「2.0 不出提示」变红，再复原。结果记进 todo。

### Task 3：文档、CHANGELOG 与版本号

- `references/workflow-checkpoints.md`「外部审查意见」补一句：装了 delegate 但它的接口主版本不兼容时，不出提示；
- `docs/design.md` 的 `sibling_plugins.py` 一行补上：读 delegate 的 interface.json，按 `>=1.0,<2.0` 校验；
- CHANGELOG `[0.67.0]` 记一条「变更」；
- 两份 `plugin.json` 改为 0.67.0，README 中英的 `--ref` 改为 v0.67.0。

- 验收：`validate.sh` 全档通过。

### Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行

在正文列出这些内容：
- 实际改动的文件，取自版本库；
- 四种情况各自的提示原文或「不出提示」；
- 验证结果和未验证项；
- 文档建议；
- 拟回告：对象是 delegate 负责人（`local_2f967122-2c46-4c17-abf4-6b283516a8c7`），渠道是宿主会话消息，时机是 0.67.0 装上之后。

- 验收：用户验收通过。

### 发版后的验证

- 两边升级到 0.67.0；
- 本机 Claude 侧把 delegate 升到 0.5.3，这一步要先问用户；在已安装副本上看检查点提示的命令取自 interface.json；
- Codex 侧按缓存目录的实际情况记录走的是哪条路径；
- 回告 delegate 负责人。

## 影响面

- 修改：`hooks/sibling_plugins.py`、`hooks/test_sibling_plugins.py`、`hooks/module_stage.py`、`hooks/test-phase-guard.sh`、
  `references/workflow-checkpoints.md`、`docs/design.md`、CHANGELOG、两份 `plugin.json`、README 中英；
- 本模块的 Plan 与 todo。

## Risks and Mitigations

- **delegate 的 interface.json 被改成恶意内容。** 只取两个经过正则校验的命令名，其余文字一律不进注入。
- **Codex 缓存里留了旧版本目录，导致一直读不到。** 只是回落到现有提示，不会出错；发版后的验证会记录本机实际是哪种情况。
- **主版本不兼容时用户想不起外部审查。** 这是 Spec 里的取舍，用户仍可直接调用 delegate。

## Open Questions

- 无。
