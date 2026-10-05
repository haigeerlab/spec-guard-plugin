# Plan: module-cost-report

依据 [`spec/module-cost-report.md`](../../spec/module-cost-report.md)。分支 `claude/module-cost-report`。

## Overview

一个只读脚本 `hooks/module_cost_report.py`（只用 python3 标准库与 git），离线读取 Claude transcript 与 Codex rollout，
按模块、按 task 汇总主代理与子代理的 token、派活与返工信号；外加 Claude 命令与 Codex skill 路由。六个 task 串行，
每个 task 一条提交，先写能在当前代码上失败的测试并记录失败输出。

## Architecture Decisions

- **单文件、纯函数为主**：读取层（Claude / Codex 各一个 reader）→ 归属层（task 时间窗）→ 汇总层 → 输出层。
  reader 只产出「带时间戳、模型、类别用量、角色（main / sub / guardian）、派活与改动事件」的统一记录，后续各层与宿主无关。
- **夹具全部合成**：测试在临时目录构造假的 `~/.claude/projects`、`~/.codex/sessions` 与 git 仓库，通过参数
  `--claude-home` / `--codex-home` 注入路径（默认取真实目录），不读本机真实会话。
- **口径与 tier-guard 一致**：Claude 按（文件, message.id）取 usage 最大的一行；Codex 取累计值之差、非缓存输入 =
  input − cached、推理含在输出内。联调时与 tier-guard `tier_report.py` 的 `_usage_groups` 交叉核对。
- **未知即未知**：无法归属、无记录的派活、未定价，一律显式报告，不填 0。
- 共同验证命令（每个 task 都跑，并在 `PATH=/usr/bin:/bin` 的 python3 3.9 下再跑一次）：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_module_cost_report.py
  /bin/bash scripts/validate.sh
  ```

## Task List

### Task 1: task 时间窗（C1）

**Description:** 新建脚本骨架与测试文件。解析 `tasks/<模块>/todo.md` 的勾选项，用 `git log` 逐提交比对该文件，得到每项首次
被勾选的提交时间，切出（上一项完成, 本项完成] 的时间窗；未勾选项为「进行中」，终点为运行时刻。脚本先只输出时间窗（内部数据），
供后续 task 使用。在 `scripts/validate.sh` 登记新测试。

**Acceptance criteria:**
- [ ] 两项依次勾选的夹具得到两个正确时间窗，第一项起点是 todo.md 首次出现的提交
- [ ] 未勾选项窗口终点为运行时刻
- [ ] todo.md 未提交或没有 git 历史 → 「无法归属」并说明原因，退出 2，不报 0

**Verification:**
- [ ] Tests pass: 共同验证命令
- [ ] Manual check: 对本仓库 `build-task-dispatch` 运行，时间窗与 `git log -p tasks/build-task-dispatch/todo.md` 手查一致

**Dependencies:** None

**Files likely touched:**
- `plugins/spec-guard/hooks/module_cost_report.py`
- `plugins/spec-guard/hooks/test_module_cost_report.py`
- `scripts/validate.sh`

**Estimated scope:** Medium: 3 files

### Task 2: Claude 用量读取与归属（C2 的 Claude 部分）

**Description:** 定位项目目录（realpath 后把 `/`、`.`、`_` 换成 `-`，并以 `cwd` 复核）；读主会话文件，按（文件, message.id）
取 usage 最大的一行、无 id 的行逐行计入、按消息自己的模型分列；主会话的 Agent 调用经 `subagents/*.meta.json` 的 `toolUseId`
关联子代理文件，整份文件只计一次，计到发起它的 task；找不到子代理文件的派活计为「无记录」。

**Acceptance criteria:**
- [ ] 同一 message.id 三行（output 逐行增长）只计最大的一行；无 id 的行逐行计入
- [ ] 子代理经 toolUseId 计到发起 task；续派追加的文件只计一次；缓存写 5m / 1h 分列
- [ ] 会话中途换模型按消息各自分列；无子代理文件的派活计入「无记录」并降低覆盖率
- [ ] 含 `.`、`_` 的路径与 `/var` → `/private/var` 能找到正确目录

**Verification:**
- [ ] Tests pass: 共同验证命令
- [ ] Manual check: 对本会话（本仓库 transcript）抽一个窗口，与手工按 message.id 去重的结果一致

**Dependencies:** Task 1

**Files likely touched:**
- `plugins/spec-guard/hooks/module_cost_report.py`
- `plugins/spec-guard/hooks/test_module_cost_report.py`

**Estimated scope:** Medium: 2 files

### Task 3: Codex 用量读取与归属（C2 的 Codex 部分）

**Description:** 按 `session_meta.cwd` 选出本项目 rollout；主线程用量取窗内最后一条与窗前最后一条 `total_token_usage` 之差；
子线程（`session_id` 等于主线程、`id` 不同）取最后一条累计值，计到发起它的 `spawn_agent` 所在 task；`source.other == guardian`
单列；非缓存输入 = input − cached，推理单列不另计。

**Acceptance criteria:**
- [ ] 累计值求差而非相加；子线程只取最后一条
- [ ] guardian 单列、不算派活；`spawn_agent` 计数正确
- [ ] 非缓存输入 = input − cached；推理不重复计入输出

**Verification:**
- [ ] Tests pass: 共同验证命令
- [ ] Manual check: 对 scratchpad 里 Codex A/B 验收项目运行，派活次数与之前 grade.py 的结果一致

**Dependencies:** Task 1

**Files likely touched:**
- `plugins/spec-guard/hooks/module_cost_report.py`
- `plugins/spec-guard/hooks/test_module_cost_report.py`

**Estimated scope:** Medium: 2 files

### Checkpoint: 两种会话都能读、能归属
- [ ] 共同验证命令通过；Task 1–3 的手查一致

### Task 4: 返工信号（C2）

**Description:** 每个 task 计算派活次数、重派（次数减一）、收回（Agent 调用的错误结果含「第二次失败后的收回」）、子代理交回后
主代理改动的不同文件数（最后一次派活结束后至窗口结束，Edit / Write / MultiEdit 或 Codex `apply_patch`，排除该模块 todo.md）。

**Acceptance criteria:**
- [ ] 两次派活 → 重派 1；收回原因 → 收回 1
- [ ] 交回后改两个文件（其中一个是 todo.md）→ 计 1
- [ ] 不统计「测试是否一次通过」

**Verification:**
- [ ] Tests pass: 共同验证命令

**Dependencies:** Task 2, Task 3

**Files likely touched:**
- `plugins/spec-guard/hooks/module_cost_report.py`
- `plugins/spec-guard/hooks/test_module_cost_report.py`

**Estimated scope:** Small: 2 files

### Task 5: 价格、输出与隐私（C3–C5）

**Description:** `--prices` 折算等价金额（缺价标「未定价」，总额注明不含未定价部分）；默认人读表格、`--json`；多模块对照按
「有派活 / 没派活的 task」分组给每 task 平均值并注明只能看趋势；「无法统计的部分」一节；退出码按 spec。

**Acceptance criteria:**
- [ ] 有价折算正确；缺价标「未定价」；无价格文件只出 token
- [ ] 夹具中的 prompt、回复、工具参数与代码字符串不出现在人读或 `--json` 输出中
- [ ] 多模块对照分组平均正确并带趋势说明；没有会话数据时如实报告为空、不报错

**Verification:**
- [ ] Tests pass: 共同验证命令

**Dependencies:** Task 4

**Files likely touched:**
- `plugins/spec-guard/hooks/module_cost_report.py`
- `plugins/spec-guard/hooks/test_module_cost_report.py`

**Estimated scope:** Medium: 2 files

### Task 6: 命令、skill 路由与文档（C6）

**Description:** 新增 `commands/cost-report.md`；`skills/spec-guard-ops/SKILL.md` 增加 cost-report 路由；`docs/workflow.md`
在实验性派活一段后加「怎么看省没省钱」；`CHANGELOG.md` 未发布节。

**Acceptance criteria:**
- [ ] `check-command-parity.py` 通过（命令引用的脚本在 skill 中有路由）
- [ ] 文档写明只读、口径、无法统计的部分与「对照只能看趋势」

**Verification:**
- [ ] Tests pass: 共同验证命令与 `python3 scripts/check-command-parity.py`

**Dependencies:** Task 5

**Files likely touched:**
- `plugins/spec-guard/commands/cost-report.md`
- `plugins/spec-guard/skills/spec-guard-ops/SKILL.md`
- `docs/workflow.md`
- `CHANGELOG.md`

**Estimated scope:** Medium: 4 files

### Checkpoint: Complete
- [ ] 两种 Python 与系统 `/bin/bash` 3.2 下全量通过
- [ ] 本仓库 `build-task-dispatch` 与 Codex A/B 项目实跑，结果与手查一致
- [ ] 牙齿检查：改坏去重规则与累计求差，对应断言变红
- [ ] 代码审查；推分支、开 PR 等 CI，不自行合并
- [ ] 联调：与 tier-guard 的对照实验数据交叉核对（tier-guard 实验完成后）

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| 宿主 transcript 格式随版本变化 | Med | 只依赖实测字段；读不到的字段报「未提供」，不崩溃 |
| 并行会话被计入同一时间窗 | Med | 报告列出贡献会话与各自用量，提示用户 |
| 大量会话文件读得慢 | Low | 先按文件修改时间与时间窗粗筛再解析 |

## Open Questions

- 无
