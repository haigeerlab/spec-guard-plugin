# Plan: context-hint-thresholds

依据 [`spec/context-hint-thresholds.md`](../../spec/context-hint-thresholds.md)（2026-10-06 用户评审通过）。分支
`claude/context-hint-thresholds`，worktree `.claude/worktrees/hello-226c46`。

## Overview

`session_context.py` 多读一个窗口大小并在命令行输出第三行；`module_stage.describe()` 用窗口（或 Claude 的固定数）按两档决定
Module boundary 行与上下文行；`phase-guard.sh` 把第三行传进去。三个 task 串行，每个 task 一条提交，测试先红后绿。

## Architecture Decisions

- **窗口与 token 来自同一条记录。** `context_usage()` 在找到最后一条有效用量记录时一并取窗口，避免跨记录拼接。
- **阈值计算集中在 `module_stage`。** 新增 `thresholds(window) -> (boundary, mid, boundary_text, mid_text)`，测试与输出共用，
  不在 bash 里算数。
- **兼容旧调用。** `context_tokens()` 签名不变；`describe()` 新参数有默认值；`verify-artifacts`、`module-insert` 调用不变。
- 共同验证命令（每个 task 都跑，并在 `PATH=/usr/bin:/bin` 的 python3 3.9 下再跑一次 python 测试）：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_session_context.py
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  python3 -B plugins/spec-guard/hooks/test_module_insert.py
  ```

## Task List

### Task 1: 读出窗口大小（第 3、6 条）

**Description:** `session_context.context_usage()`；`context_tokens()` 改为取其第一项；命令行输出第三行窗口。

**Acceptance criteria:**
- [ ] Codex 记录返回 `(tokens, model_context_window)`；窗口缺失、0、负数、非整数 → 窗口 `None`
- [ ] Claude 记录窗口为 `None`；`context_tokens()` 现有用例全部不变
- [ ] 命令行恰好三行，前两行与现在相同

**Verification:** 测试先红后绿：共同验证命令

**Dependencies:** None

**Files likely touched:** `plugins/spec-guard/hooks/session_context.py`、`plugins/spec-guard/hooks/test_session_context.py`

**Estimated scope:** Small

### Task 2: 两档判定与输出（第 1、2、6、7 条）

**Description:** `module_stage.thresholds()`、`describe(..., context_window=None)`、`--context-window`；`phase-guard.sh` 读第三行。

**Acceptance criteria:**
- [ ] BUILDING：Claude 799,999 无 / 800,000 有；Codex 窗口 258,400 时 206,719 无 / 206,720 有；文字与 Spec 第 7 条逐字一致
- [ ] DONE、MODULE_DONE：Claude 499,999 无 Module boundary 行 / 500,000 有且带大小；Codex 129,199 无 / 129,200 有；
      不再出单独的上下文行
- [ ] 读不到记录、无标准输入、非 JSON 输入 → Module boundary 行与现行逐字相同，其余输出不变
- [ ] 依赖 200k 单档的旧断言按新规则更新；位置行、阶段判定用例不变

**Verification:** 测试先红后绿：共同验证命令；validate.sh

**Dependencies:** Task 1

**Files likely touched:** `plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/phase-guard.sh`、
`plugins/spec-guard/hooks/test-phase-guard.sh`

**Estimated scope:** Medium

### Checkpoint 1（report）: 两档端到端

- [ ] 共同验证命令两种 python 全绿
- [ ] 牙齿检查：草稿副本里把 `>=` 改成 `>`、把 0.8 改成 0.5，各自看到断言变红
- [ ] 结果记入 todo 后直接继续，不停下等确认

### Task 3: 文档与变更记录

**Description:** `commands/phase.md`、`docs/workflow.md` 中提醒条件的描述；CHANGELOG `[未发布]`。

**Acceptance criteria:**
- [ ] 文档描述与 Spec 第 1、2、3、7 条一致，不再出现"超过 200k"
- [ ] validate.sh 通过

**Dependencies:** Task 2

**Files likely touched:** `plugins/spec-guard/commands/phase.md`、`docs/workflow.md`、`CHANGELOG.md`

**Estimated scope:** Small

### Checkpoint 2（gate）: 交付

- [ ] 最小验证三条 + 共同验证命令，两种 python 全绿；validate.sh 跑满
- [ ] 代码审查（五维），处理发现
- [ ] 推送、开 PR（本 Plan 获批即授权），由用户合并；"已合并"后先用 gh 核实
- [ ] 发版与宿主核对按 release-process；Checkpoint：安装版在真实 Claude Code 会话里确认模块进行中低于 800k 不再出现上下文行

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Claude 200k 窗口模型永远不提醒 | 小窗口用户失去提醒 | Spec 已接受；CHANGELOG 写明 |
| Codex 某些版本不写 `model_context_window` | 退回固定数，Codex 阈值偏高 | 按第 6 条退回；测试覆盖缺失字段 |
| 命令行多一行破坏旧解析 | 位置行错位 | phase-guard 只取第二行的首行；用例覆盖 |

## Open Questions

- 无。
