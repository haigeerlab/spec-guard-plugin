# Plan: fresh-session-hint

依据 [`spec/fresh-session-hint.md`](../../spec/fresh-session-hint.md)。分支 `claude/fresh-session-hint`，主检出目录。

## Overview

阶段提示新增三类行：模块完成时建议开新会话（第 9 条）、主会话上下文超过 200k 时报告大小（第 2、8、9 条）、每个阶段的
分支与 worktree 位置行（第 11 条）。新增只读的 `hooks/session_context.py`（标准库 + git），`module_stage.describe()`
多一个可选参数，`phase-guard.sh` 调一次 `session_context.py` 再拼输出。五个 task 串行，每个 task 一条提交，先写能在当前
代码上失败的测试并记录失败输出。

## Architecture Decisions

- **位置行在 `phase-guard.sh` 拼，不进 `describe()`。** `IDLE`、`MAP_ONLY`、`UNKNOWN` 由 `phase-guard.sh` 直接输出、不经
  `describe()`，只有在外层插行才能覆盖全部阶段；`describe()` 的文本（`module-insert`、清洗测试依赖它）因此只多出第 9 条
  两行。
- **模块完成与上下文两行在 `describe()` 里。** 它们依赖阶段判定，放在 `Suggested next step` 之前的事实列表末尾，模块完成
  在前。`context_tokens=None` 时上下文行永不出现。
- **一次 python 调用拿全部会话事实。** `phase-guard.sh` 运行 `python3 session_context.py .`，读两行：token 数、位置行。
  标准输入的 1 秒 / 1 MiB 上限在 python 里用 `select` 实现（bash 3.2 的 `read -t` 处理不了大输入），标准输入是终端时
  `phase-guard.sh` 改喂 `/dev/null`。任何失败 → 两行空，阶段照常注入。
- **不改阶段判据。** 阶段取值与完成判据不变，所以 `verify-artifacts` 不需要改；只跑它的回归证明不受影响。
- **夹具全部合成。** 会话记录在临时目录构造，不读本机真实 transcript / rollout；位置行用临时 git 仓库与
  `git worktree add`。
- 共同验证命令（每个 task 都跑，并在 `PATH=/usr/bin:/bin` 的 python3 3.9 下再跑一次 python 测试）：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_session_context.py
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  python3 -B plugins/spec-guard/hooks/test_module_insert.py
  python3 -B plugins/spec-guard/hooks/test_module_stage_sanitization.py
  ```

## Task List

### Task 1: 会话记录读取（第 2、8 条）

**Description:** 新建 `hooks/session_context.py` 与 `hooks/test_session_context.py`。实现 `context_tokens(path)`：从文件
末尾向前按块读、最多 4 MiB，逐行解析；Claude 取最后一条非 `isSidechain` 的带 `message.usage` 的 assistant 消息三项相加，
Codex 取最后一条 `info` 非 null 的 `token_count` 的 `last_token_usage.input_tokens`。实现
`transcript_path_from_hook_input(text)`。在 `scripts/validate.sh` 登记新测试。

**Acceptance criteria:**
- [ ] Claude：末尾是 user / 无用量行时向前找；末尾是 sidechain assistant 时跳过；三项相加正确
- [ ] Codex：取最后一条 `token_count`；`info: null` 跳过
- [ ] 末尾 4 MiB 内无记录（记录在更前面）、坏行、空文件、不存在、空路径 → `None`；坏行不影响找到更早的有效记录
- [ ] hook 输入：正常 / 非 JSON / 缺字段 / `null` / 非字符串 → 对应结果

**Verification:**
- [ ] 测试先红（模块不存在）后绿：共同验证命令
- [ ] Manual check：对本会话真实 transcript 运行一次，数值与最后一条 assistant 用量手算一致（只看数字，不贴内容）

**Dependencies:** None

**Files likely touched:** `plugins/spec-guard/hooks/session_context.py`、`plugins/spec-guard/hooks/test_session_context.py`、
`scripts/validate.sh`

**Estimated scope:** Medium: 3 files

### Task 2: 模块完成行（第 1、9、10 条的模块完成部分）

**Description:** `describe(root, context_tokens=None)` 在 `MODULE_DONE`、`DONE` 时于事实列表末尾追加模块完成行（含
`DONE` 的 push-first 分支与 `MODULE_DONE` 的暂停分支）。这一步不依赖标准输入，`phase-guard.sh` 不改。

**Acceptance criteria:**
- [ ] `MODULE_DONE`（普通 / 有暂停模块 / 有未合并提交）与 `DONE`（普通 / 有未合并提交 / 无 todo）都恰好一行模块完成行，
      位于 `Suggested next step` 之前
- [ ] `NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MAP_INVALID`、`IDLE`、`MAP_ONLY` 没有这一行
- [ ] 现有 MODULE_DONE / DONE 断言按新输出更新；其他阶段输出逐字不变

**Verification:**
- [ ] 测试先红后绿：共同验证命令

**Dependencies:** None（可与 Task 1 交换顺序）

**Files likely touched:** `plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`

**Estimated scope:** Small: 2 files

### Task 3: 上下文行与 phase-guard 接线（第 7、8、9 条的上下文部分）

**Description:** `describe()` 在 `context_tokens > 200000` 且阶段为 `NEEDS_SPEC` / `NEEDS_PLAN` / `BUILDING` /
`MODULE_DONE` / `DONE` 时追加上下文行（N = 四舍五入到千）；命令行加 `--context-tokens N`。`session_context.py` 加命令行
入口（`select` 等 1 秒、读 1 MiB，输出两行，第二行此时留空）。`phase-guard.sh` 激活后调用它（终端时喂 `/dev/null`），
把 token 数传给 `module_stage.py`。

**Acceptance criteria:**
- [ ] `BUILDING` + 25 万 → 只有上下文行；`DONE` + 25 万 → 两行，模块完成在前；`BUILDING` + 15 万 → 与现在逐字相同；
      恰好 200000 不提示
- [ ] 标准输入为 `/dev/null`、非 JSON、记录不存在 → 只按阶段决定模块完成行
- [ ] 一直不关闭的管道作标准输入 → 2 秒内照常输出
- [ ] 运行前后项目文件与会话记录文件的 mtime 不变
- [ ] 输出仍是合法 hook JSON；不用 `cmd | grep -q`；phase-guard 只依赖 bash、git、python3

**Verification:**
- [ ] 测试先红后绿：共同验证命令
- [ ] Manual check：`CLAUDE_PROJECT_DIR=. phase-guard.sh` 喂本会话 hook 输入，看到上下文行（本会话已超 200k 时）

**Dependencies:** Task 1、Task 2

**Files likely touched:** `module_stage.py`、`session_context.py`、`phase-guard.sh`、`test-phase-guard.sh`、
`test_session_context.py`

**Estimated scope:** Medium: 5 files

### Checkpoint 1: 两类建议行端到端可用

- [ ] 共同验证命令两种 python 下全绿；`/bin/bash scripts/validate.sh` 后台跑满
- [ ] 手工改坏一处判据（如阈值比较写成 `>=`、跳过 sidechain 的条件删掉），确认对应断言变红后还原
- [ ] 向用户展示本仓库实际注入的阶段文本，确认措辞

### Task 4: 位置行（第 11 条）

**Description:** `session_context.location_line(root)`：`git rev-parse --abbrev-ref HEAD` 与 `--show-toplevel`，分离 HEAD
时用 `detached at <短 sha>`，两个值过 `module_stage.safe_fragment`；命令行第二行输出它。`phase-guard.sh` 把位置行插到所有
阶段（含 `IDLE`、`MAP_ONLY`、`UNKNOWN`、`MAP_INVALID`）的标题与 `当前阶段` 之间。

**Acceptance criteria:**
- [ ] 单元：普通分支、分离 HEAD、linked worktree 报告自己的根目录、非 git 目录 → `None`、含控制字符的分支名被清洗
- [ ] phase-guard：git 夹具中每个阶段都有位置行且位置在标题与 `当前阶段` 之间；非 git 夹具没有这一行、其余逐字不变
- [ ] 位置行含"State this location to the user whenever you ask them to review or confirm."
- [ ] Codex 路径（不设 `CLAUDE_PROJECT_DIR`、从子目录运行）报告仓库根目录

**Verification:**
- [ ] 测试先红后绿：共同验证命令
- [ ] Manual check：在本仓库与一个 linked worktree 里各跑一次 phase-guard，位置正确

**Dependencies:** Task 3

**Files likely touched:** `session_context.py`、`phase-guard.sh`、`test_session_context.py`、`test-phase-guard.sh`

**Estimated scope:** Medium: 4 files

### Task 5: 文档与变更记录

**Description:** `CHANGELOG.md` 最上面的 `## [未发布]` 记三项新增（只改最上面那一个）；`grep` 仓库中描述阶段输出行的
文档（README、commands/phase.md、skills 路由），有就同步；记录 Codex `transcript_path` 尚待真实会话核对。

**Acceptance criteria:**
- [ ] CHANGELOG 三项新增，措辞与 spec 第 9、11 条一致
- [ ] 列出阶段输出行的文档已同步，或说明无需同步

**Verification:**
- [ ] `/bin/bash scripts/validate.sh`

**Dependencies:** Task 4

**Files likely touched:** `CHANGELOG.md`，可能 `plugins/spec-guard/commands/phase.md`

**Estimated scope:** Small: 1–2 files

### Checkpoint 2: 交付

- [ ] 最小验证三条 + 共同验证命令，两种 python 全绿；validate.sh 跑满
- [ ] 代码审查（五维），处理发现
- [ ] 开 PR，由用户合并；合并后按发版流程走 tag → Release → 宿主升级
- [ ] 安装版实测：真实 Claude Code 与真实 Codex 会话各一次，记录实际注入的行；Codex 若 `transcript_path` 为空，如实记
      "Codex 只有模块完成一条"
- [ ] 提醒用户开新会话

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| 宿主没有关闭标准输入，hook 挂住 | 每轮卡住 | python `select` 1 秒上限 + 终端时喂 `/dev/null`；挂起管道用例 |
| Claude 记录格式变化，读不到用量 | 上下文行消失 | 按设计静默；Checkpoint 2 实测会暴露 |
| Codex `transcript_path` 实际为空 | Codex 没有上下文行 | spec 已接受；如实记录 |
| 位置行每轮多约 30 token | 轻微成本 | 已接受 |
| 转告用户是软约束 | 偶尔不说位置 | 已接受；不做强制 |

## Open Questions

- 无。
