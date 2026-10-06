# Plan: session-handoff

依据 [`spec/session-handoff.md`](../../spec/session-handoff.md)（2026-10-06 用户评审通过）。分支
`claude/spec-guard-plugin-planning-82c482`，worktree `.claude/worktrees/hello-226c46`。

## Overview

新增只读的 `hooks/session_handoff.py` 拼交接文本；`phase-guard.sh` 在整条提示词恰好是触发词时输出宿主专属的拦截 JSON，
其余情况逐字不变；Module boundary 行指向新命令；补上 Claude 命令与 Codex 操作作为未拦截时的退路。先实测第 12 条
（worktree 会话里 `CLAUDE_PROJECT_DIR` 指向哪里），成立再改 phase-guard 的根目录判定。task 串行，每个 task 一条提交，
测试先红后绿并记录失败输出。

## Architecture Decisions

- **拼装与拦截分开。** `session_handoff.py` 只负责文本与 `is_trigger`，不知道宿主；宿主判别与 JSON 形状只在
  `phase-guard.sh`（经一个小的 python 发射函数），使命令行退路与 hook 共用同一份文本。
- **复用而不复制。** 阶段与计数取 `module_stage.describe` 用的同一判定函数，未合并提交取 `unmerged_commits`，位置取
  `session_context.location_line`；不新增 git 判据。
- **标准输入只读一次。** `session_context.py` 已在 1 秒 / 1 MiB 上限内读 hook 输入；扩展它多输出一行 `prompt` 是否为触发词
  （第三行 `1` / 空），不再另读标准输入。
- **宿主判别。** 有 `CLAUDE_PROJECT_DIR` 视为 Claude，否则 Codex；Codex 输出里不得出现 `hookSpecificOutput`。
- **失败即放行。** 拼装非零退出、超时或输出为空 → 走原有阶段注入。
- 共同验证命令（每个 task 都跑，并在 `PATH=/usr/bin:/bin` 的 python3 3.9 下再跑一次 python 测试）：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_session_handoff.py
  python3 -B plugins/spec-guard/hooks/test_session_context.py
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  python3 -B plugins/spec-guard/hooks/test_module_insert.py
  ```

## Task List

### Task 1: 实测 worktree 会话的项目目录（第 12 条）

**Description:** 在本 worktree 临时加 `.claude/settings.local.json`，注册一个只把 `CLAUDE_PROJECT_DIR`、hook 输入的 `cwd`
与 `pwd` 写到 scratchpad 的 UserPromptSubmit hook；发一轮提示后读结果，再删除该文件。**改动前先征得用户同意**（属于宿主
配置改动，即使是项目本地、临时的）。结论写回 Spec 第 12 条。

**Acceptance criteria:**
- [ ] 记录到三个值，并判定 `CLAUDE_PROJECT_DIR` 是否为主仓路径
- [ ] 临时文件已删除，`git status` 无残留

**Verification:**
- [ ] Spec 第 12 条改为"已实测"并附数值（路径用占位描述，不写其他项目信息）

**Dependencies:** None

**Files likely touched:** `spec/session-handoff.md`

**Estimated scope:** Small

### Task 2: 根目录以会话 cwd 为准（第 12 条，仅当 Task 1 证实）

**Description:** `phase-guard.sh` 在 hook 输入带 `cwd` 且 `git -C <cwd> rev-parse --show-toplevel` 成功时以它为项目根，
否则保持现有逻辑。为避免两次读标准输入，根目录解析移到 `session_context.py` 读完输入之后（第一行起输出顺序固定）。
Task 1 不成立则跳过本 task，在 todo 中注明原因。

**Acceptance criteria:**
- [ ] linked worktree 夹具：`CLAUDE_PROJECT_DIR` 指向主仓、`cwd` 指向 worktree → 报告 worktree 的分支、目录与阶段
- [ ] 子目录启动（`cwd` 为仓库子目录）→ 根目录仍为仓库根，与现在相同
- [ ] 无 `cwd`、`cwd` 不是 git 仓库、无标准输入 → 与现在逐字相同
- [ ] 未启用项目仍静默

**Verification:**
- [ ] 测试先红后绿：共同验证命令

**Dependencies:** Task 1

**Files likely touched:** `plugins/spec-guard/hooks/phase-guard.sh`、`plugins/spec-guard/hooks/session_context.py`、
`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test_session_context.py`

**Estimated scope:** Medium

### Task 3: 交接文本（第 1、2、10、11 条）

**Description:** 新建 `hooks/session_handoff.py` 与 `hooks/test_session_handoff.py`：`handoff_text(root)` 按 Spec 的格式
拼文本，取不到的项写"未知"；命令行入口打印文本。在 `scripts/validate.sh` 登记新测试。

**Acceptance criteria:**
- [ ] 各阶段（IDLE、MAP_ONLY、NEEDS_SPEC、BUILDING、DONE）文本正确，末行恰为 `下一步：____`
- [ ] 分离 HEAD、linked worktree（报告自身根目录）
- [ ] 未合并提交：有 / 无 / 无远端（"未知"）
- [ ] 发布证据：取最大版本（`v0.10.0` > `v0.9.0`）、同版本多文件合并、无 not-verified → "无"、目录缺失、坏 JSON 跳过该文件
- [ ] 不读 `transcript_path`；运行前后文件修改时间不变

**Verification:**
- [ ] 测试先红（模块不存在）后绿：共同验证命令
- [ ] Manual check：对本 worktree 运行一次，与手查的 git / 发布证据一致

**Dependencies:** None（可与 Task 2 独立）

**Files likely touched:** `plugins/spec-guard/hooks/session_handoff.py`、`plugins/spec-guard/hooks/test_session_handoff.py`、
`scripts/validate.sh`

**Estimated scope:** Medium

### Task 4: 触发词拦截（第 7、8、9 条）

**Description:** `is_trigger(prompt)`；`session_context.py` 输出第三行触发标记；`phase-guard.sh` 激活后若触发且
`session_handoff.py` 成功，按宿主输出拦截 JSON，否则走原逻辑。

**Acceptance criteria:**
- [ ] `is_trigger` 正例：`/spec-guard:handoff`、`  spec-guard handoff\n`；反例：带参数、`继续 /spec-guard:handoff`、大小写不同、空串
- [ ] Claude 环境：`decision`=`block`、`reason` 为交接文本、`suppressOriginalPrompt` 为 true
- [ ] Codex 环境（无 `CLAUDE_PROJECT_DIR`）：只有 `decision` 与 `reason`
- [ ] 拼装脚本失败（夹具里替换为非零退出）→ 原有阶段注入，逐字相同
- [ ] 非触发词、无标准输入、非 JSON 输入、未启用项目 → 与现在逐字相同；挂起管道约 1 秒内返回

**Verification:**
- [ ] 测试先红后绿：共同验证命令
- [ ] Manual check：`claude -p "/spec-guard:handoff" --plugin-dir <工作区插件>` 在临时启用项目里 `total_cost_usd` 为 0

**Dependencies:** Task 3

**Files likely touched:** `plugins/spec-guard/hooks/session_handoff.py`、`plugins/spec-guard/hooks/session_context.py`、
`plugins/spec-guard/hooks/phase-guard.sh`、对应测试

**Estimated scope:** Medium

### Checkpoint 1: 本地作答端到端

- [ ] 共同验证命令两种 python 全绿
- [ ] 牙齿检查：在草稿副本里把 Codex 输出加回 `hookSpecificOutput`、把 `is_trigger` 改成包含匹配，各自看到断言变红
- [ ] 向用户展示 `claude -p` 实测输出与费用

### Task 5: 命令、Module boundary 行与文档（第 3 条）

**Description:** 新增 `commands/handoff.md`（运行 `session_handoff.py` 并原样输出）与 `spec-guard-ops` 的 `handoff` 操作；
`MODULE_BOUNDARY` 改为 Spec 中的新文本，同步 `test-phase-guard.sh` 断言与 `commands/phase.md`；CHANGELOG `[未发布]`。

**Acceptance criteria:**
- [ ] 新命令与 Codex 操作都只运行同一脚本、不写文件
- [ ] Module boundary 行与 Spec 逐字一致，其余阶段输出不变
- [ ] `scripts/validate.sh` 的清单一致性检查通过（新命令登记到需要登记的位置）

**Verification:**
- [ ] 最小验证三条

**Dependencies:** Task 4

**Files likely touched:** `plugins/spec-guard/commands/handoff.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、
`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/commands/phase.md`、
`CHANGELOG.md`

**Estimated scope:** Medium

### Checkpoint 2: 交付

- [ ] 最小验证三条 + 共同验证命令，两种 python 全绿；validate.sh 跑满
- [ ] 代码审查（五维），处理发现
- [ ] 开 PR，由用户合并；"已合并"后先用 gh 核实；按发版流程走 tag → Release → 宿主升级
- [ ] 安装版实测：Claude CLI、桌面版 Code 标签页、Codex TUI 各一次，记录拦截后用户实际看到的内容；定下 Codex 触发词；
      桌面版若显示为错误样式，交用户决定是否取消本地作答（Spec Open questions）
- [ ] 提醒用户开新会话

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| 误拦截正常提示词 | 用户的话被吞 | 只精确匹配两个触发词；反例用例；拦截失败即放行 |
| Codex 输出混入未知字段 | hook 判 Failed，提示词照常送模型 | 单独的 Codex 输出用例 + 牙齿检查 |
| 改根目录判定影响非 worktree 会话 | 阶段读错目录 | 仅 Task 1 证实才做；子目录、无 cwd 用例保持逐字相同 |
| 桌面版拦截消息像报错 | 体验差 | Checkpoint 2 实测，用户决定 |
| Codex 新 hook 需信任 | 安装后首次不生效 | 插件 hook 已被信任，hash 变化会再次提示；发版说明写明 |

## Open Questions

- Codex 触发词定稿（Checkpoint 2）。
- 桌面版显示效果是否可接受（Checkpoint 2，用户决定）。
