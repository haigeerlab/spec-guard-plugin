# Plan: delegate-review-hint

<!-- spec-guard: review approved -->

依据 [`spec/delegate-review-hint.md`](../../spec/delegate-review-hint.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-17 单独批准，
本 Plan 单独交审。分支 `claude/delegate-review-hint`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `ac04c7b` 开出。
草稿 PR #339 已开，含能力图两行与两份已批准的 Spec。本模块在同一个 PR 里完成，版本号 0.65.0；plugin-interface 另开 PR。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先做测试隔离，让本机装的插件影响不到回归结果；再加只读的安装判断、外部审查状态的判定和阶段提示里那一行；最后补规则文字、
文档、CHANGELOG 和版本号。

## Architecture Decisions

- **安装判断放在新文件 `hooks/sibling_plugins.py`。** Claude 侧把 `agent_relay_probe.claude_root` 的记录读取与 settings 合并
  抽成 `sibling_plugins.claude_plugin_root(project, plugin)`，`agent_relay_probe` 改为调用它，自身输出不变。Codex 侧按行扫描
  `config.toml`，不调 `codex plugin list`。
- **外部审查状态的判定放在 `module_stage.py`。** 新增 `external_review_state(root, module) -> "none"|"recorded"|"declined"`，
  plugin-interface 之后直接复用。这里只读两个文件：Spec 和 todo。
- **检查点判断复用现有函数：** `review_hint` 已经算出的 Spec、Plan 标记，加上 `at_final_gate`，不再另写一套。
- **提示行加在 `describe` 里 Review 行之后。** 它不改 `review_hint` 的返回值，也不改建议的下一步。
- **测试隔离用环境变量。** 让 `CLAUDE_CONFIG_DIR`、`CODEX_HOME` 指向空的临时目录，不给产品代码加「测试模式」开关。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后，用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：测试隔离（先做，行为不变）

在 `test-phase-guard.sh` 开头和所有会走到 `module_stage.describe` 的 Python 测试里（构建时用 grep 列全），把
`CLAUDE_CONFIG_DIR`、`CODEX_HOME` 指向临时空目录。

- 验收：三套核心回归全绿，用例数与改动前相同。

### Task 2：`sibling_plugins.py` 安装判断（先红后绿）

先写 `test_sibling_plugins.py`，覆盖 Spec 测试策略里列出的 Claude 四例、Codex 四例，确认它们是红的；再实现新文件，并把
`agent_relay_probe` 改为调用共享函数。

- 验收：新测试全绿；`test_agent_relay_probe.py` 不改断言、全绿；`test_python_compat.py` 通过（兼容 3.9）；新测试登记进
  `validate.sh` 的测试清单（test-registration-check）。

### Task 3：外部审查状态判定与阶段提示行（先红后绿）

先在 `test-phase-guard.sh` 加正反例，确认它们是红的：
- 正例：三个检查点各一例，Claude 和 Codex 的入口命令各断言一次；
- 反例：没装；Spec 或 todo 里有记录；有拒绝标记；小节为空时仍出现；英文标题 `## External review` 也认；构建中段不出现。

再实现 `external_review_state` 和 `describe` 里的那一行。测试里的「装了」用临时目录伪造插件记录，不依赖本机。

- 验收：phase-guard 回归全绿；没装时，现有用例的输出逐字不变。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并在草稿副本上做一次改坏验证

把拒绝标记的判断删掉，或把 Codex 的入口命令改错，确认相应断言变红，再复原；结果记进 todo。

### Task 4：规则、文档、CHANGELOG 与版本号

- `references/workflow-checkpoints.md` 补「外部审查意见」一段，内容按 Spec：引用哪些字段、不写严重程度、拒绝标记、跑不起来时
  只记一行原因、只作参考；
- `docs/design.md` 的部件表加 `sibling_plugins.py`，数据流里注明阶段提示会只读本机插件记录；
- CHANGELOG `[0.65.0]` 记一条「新增」；
- 两份 `plugin.json` 改为 0.65.0，README 中英的 `--ref` 改为 v0.65.0。

- 验收：`validate.sh` 全档通过（含 workflow-checkpoints 相关断言）。

### Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行

在正文列出这些内容：
- 实际改动的文件，取自版本库；
- 提示行原文：Claude、Codex 各一份；
- 验证结果和未验证项；
- 文档建议；
- 拟回告：对象是 spec-guard-monitor，经「Codex LIVE-SAAS 前端基础架构监测」（`local_4f410de8-418e-440c-90d8-436a73edcc6b`）
  转达，渠道是宿主会话消息，时机是 0.65.0 装上之后。

在这里也提议一次用 delegate 对本模块做只读审查，本模块正好用来实地验证这个提示（只提议，用户同意才发起）。

- 验收：用户验收通过。

### 发版后的验证

- 两边升级到 0.65.0；
- 在装了 delegate 的 Claude Code 与 Codex 临时项目里各走一次 Spec 交审，确认出现这一行、agent 只提议不自行发起；
- 在没装 delegate 的临时项目里，确认阶段提示与 0.64.2 逐字相同；
- 回告来源。

## 影响面

- 新增：`hooks/sibling_plugins.py`、`hooks/test_sibling_plugins.py`；
- 修改：`hooks/module_stage.py`、`hooks/agent_relay_probe.py`、`hooks/test-phase-guard.sh`、走到 describe 的若干 Python 测试、
  `scripts/validate.sh`（测试清单）、`references/workflow-checkpoints.md`、`docs/design.md`、CHANGELOG、两份 `plugin.json`、
  README 中英；
- 本模块的 Plan 与 todo。

## Risks and Mitigations

- **本机装的插件让回归结果随机器变化。** Task 1 先做隔离；CI 机器上没装 delegate，正好当作「没装」的对照。
- **抽出共享函数时改变了 agent-relay 探测的行为。** `test_agent_relay_probe.py` 不改断言，它就是护栏。
- **Codex 的 `config.toml` 格式和预想不同**（比如 inline table）。认不出就按没装处理，不出提示；发版后的 Codex 实测会暴露这类问题。
- **每轮都多读几个文件。** 只在检查点才读，读的是本机小文件，开销可以忽略。

## Open Questions

- 无。
