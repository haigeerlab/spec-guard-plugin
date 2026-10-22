# Plan: cost-slim-link-follow

<!-- spec-guard: review approved -->

依据 [`spec/cost-slim-link-follow.md`](../../spec/cost-slim-link-follow.md)（2026-10-22 批准，事项 C84／C85），假设 1～13 全部按原文认可。
同一答复要求把并行边界里 `commands/`、`skills/` 两个整目录收窄到具体文件：已在 Spec 的「并行边界」一节改好（只改这一行，随本 Plan 一并交审）；
与 `sibling-rules-out` 重叠的文件等它合入、`module-crew sync` 之后再改。

分支 `cost-slim-link-follow`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/cost-slim-link-follow`，从集成分支 `crew/fix-batch` 开出。
module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调整批合完后统一改，
本模块把拟写的更新说明记在 todo 末尾。

所需工具：无 UI 改动，不需要浏览器或电脑操作；不访问远端，不新增依赖。

## 实现要点

- **成本报告（C1）**：`_claude_events` 只返回 `{tool_use_id: is_error}` 与用户提问时间；`_codex_thread` 去掉 `edits`。`build_report` 里
  删掉 `HOOK_DENIAL`／`RECLAIM_MARK` 分支、`handbacks`／`edited` 与 `redispatches`／`reclaims`／`edits_after_handback`；Agent 调用结果
  `is_error` 为真时跳过（不计 `subagents`），否则 `subagents += 1`，无子代理文件时 `subagents_unrecorded += 1`。`comparison()` 与多模块对照
  输出整段删除。`render` 的列与「无法统计的部分」按 Spec C1 改；`_wrap_up`、价格、去重、时间窗不动。
- **派活规则退役（C2）**：`setup-convention.sh` 参数解析把 `--dispatch|--no-dispatch` 改为与 tracker 模式相同的「已退役，未改动任何文件」退出 2；
  删 `DISPATCH`／`DISPATCH_SOURCE`／`dispatch_status`，`block_content` 只 `cat "$TEMPLATE"`；保留 `dispatch_in_block`，只用来在 `--replace` 的预览
  与实际输出里多打一行「已退役的派活规则段会被移除」；`--known "$RULE"` 照旧传。`project_config.py` 删 `dispatch` 项。两份规则模板文件头加注释。
- **跟随（C3）**：`project_link.py` 加 `follow` 子命令，复用 `resolve_for`、`enabled()` 与现有路径清洗；失效诊断的措辞与 `phase-guard.sh` 现有三种
  一致（抽成 `project_link.py` 里的常量，`phase-guard.sh` 不改调用方式）。会话目录自身已启用时直接打印会话目录。
- **命令入口（C4/C5）**：25 个命令文件里取根的写法统一换成 Spec C4 的两行；没有取根代码的命令（`ticket`、`local-ticket-portability`）在说明里写
  「项目根取 `follow` 的输出」；`local-ticket-ledger` 给 `local_ledger_runtime.py` 传 `--project-dir "$PROJECT"`。Codex 四个 skill 同样改，`--session`
  传 `CODEX_THREAD_ID`。「除 link-project 外都经 follow 取根」的检查写进 `test_project_link.py`（扫描 `commands/*.md` 与四个 `SKILL.md`，
  不新增测试文件、不改 `validate.sh` 登记）。
- **阶段注入（C6）**：只改「关联项目」／「Linked project」四段文字与 `test-phase-guard.sh` 对应断言。

## Task List

### Task 0：提交已批准的 Spec 标记、Plan 与 todo

Plan 获批后由模块协调带批准标记提交到集成分支，`module-crew sync` 合入。

- 验收：sync 退出码 0；`verify-and-commit.sh` 快档通过。

### Task 1：成本报告瘦身（C1）

先改 `test_module_cost_report.py`：返工信号用例改为断言人读与 `--json` 都没有派活、重派、收回、交回后改与对照；新增报错的 Agent 调用不计入
`subagents`、无文件的计入 `subagents_unrecorded`、结果正文含「第二次失败后的收回」「hook error」时输出不变。确认在现有代码上红，再改实现。

- 验收：`python3 -B plugins/spec-guard/hooks/test_module_cost_report.py` 全过，默认 `python3` 与 `/usr/bin/python3` 3.9 各跑一次；去重、时间窗、Codex、
  收尾、价格、隐私用例原样通过；同一夹具改前改后主代理、子代理 token 与轮次一致。

### Task 2：派活规则退役（C2）

先改 `test-setup-teardown.sh` 与 `test_project_config.py`（`--dispatch`／`--no-dispatch` 退出 2 且文件不变；旧块带派活段时 `--replace` 不加
`--accept-removals` 也能移除整段且预览有退役行；新建块不含派活标记；teardown 仍能移除带派活段的旧块；`config show` 无 `dispatch`），确认红，再改实现。

- 验收：两份测试全过；`shellcheck plugins/spec-guard/hooks/setup-convention.sh` 无告警。

### Task 3：跟随解析（C3）

先在 `test_project_link.py` 加 `follow` 用例（Spec Testing strategy 的七种情况），确认红，再实现。

- 验收：`python3 -B plugins/spec-guard/hooks/test_project_link.py` 全过；`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh` 全过（钩子解析未受影响）。

### Checkpoint 1（report）：变异核对

在 scratchpad 里 `mktemp -d` 建的副本上分别：`follow` 不优先查会话登记；`follow` 失效时退回会话目录；成本报告把报错的 Agent 调用计入 `subagents`；
`--replace` 不再把规则模板当 `--known`。每种都应让对应断言变红，结果记进 todo。

### Task 4：Claude 命令入口（C4，不含 `config.md`、`review-mark.md`）

改除 `config.md`、`review-mark.md` 外的 23 个命令文件（`link-project.md` 只改第 67 行的跟随说明）；在 `test_project_link.py` 加入口扫描检查（此时
`config.md`、`review-mark.md` 与四个 `SKILL.md` 暂列例外，Task 6 去掉例外）。

- 验收：`test_project_link.py`、`python3 scripts/check-command-parity.py`、`/bin/bash scripts/validate.sh --quick` 通过。

### Task 5：等 `sibling-rules-out` 合入后同步

它合入前发【等待其他会话】给模块协调，不动 `config.md`、`review-mark.md`、`SKILL.md`、`docs/commands.md`、`docs/workflow.md`；收到同步类通知或确认它已合入后，单独执行
`module-crew sync`，冲突按 sync 规则处理。

- 验收：sync 退出码 0；本分支能看到 `sibling-rules-out` 的提交。

### Task 6：重叠文件与 Codex 入口（C4 `config.md`、`review-mark.md`、C5）

改 `commands/config.md`（取根两行、去掉 dispatch 一行）、`commands/review-mark.md`（取根两行；用户批准 C87 时要求与 `config.md` 一起等 sync 后再改）、四个 `SKILL.md`（取根、link-project 一节、setup 的 `--dispatch` 说明、config 一节的 dispatch）。
去掉 Task 4 里的例外。

- 验收：`test_project_link.py`（无例外）、`check-command-parity.py`、`validate.sh --quick` 通过。

### Task 7：阶段注入措辞（C6）

改 `phase-guard.sh` 四段「关联项目」文字与 `test-phase-guard.sh` 对应断言；若 `rules-at-nodes` 已合入，先 sync 再改。

- 验收：`test-phase-guard.sh` 全过；ShellCheck 无告警。

### Task 8：文档（C7）

README 中英两份「统计与上传」与可能提到 `--dispatch` 的地方；`commands/cost-report.md`、`commands/setup-convention.md`、`docs/commands.md`、
`docs/workflow.md`、`docs/design.md`、`docs/troubleshooting.md`；新增 `docs/retirements/build-task-dispatch.md`；`spec/build-task-dispatch.md`、
`spec/module-cost-report.md`、`spec/link-per-session.md` 各追加修订节。

- 验收：`python3 scripts/check-readme-sync.py` 通过；`grep -rn -- "--dispatch\|返工信号\|交回后改\|作为项目传入" README*.md docs/commands.md docs/workflow.md
  docs/design.md docs/troubleshooting.md plugins/spec-guard/commands plugins/spec-guard/skills` 只剩退役说明。

### Task 9：公共文件实查（C8）

`grep -n -i "dispatch\|返工\|rework" plugins/spec-guard/interface.json`；有命中就发【公共变更请求】（列出要改的字段与新文字），按答复处理；没有就照实记进 todo。

- 验收：结果记进 todo。

### Task 10：端到端跟随核对

在 scratchpad 里建一个临时启用项目与一个指向它的会话目录，按命令文件里的写法（工作区源码）跑 `map`、`review-mark` 预览与 `cost-report`：输出写明被指向的项目；
把目标改成未启用后命令退出 2 并给诊断；删掉指向文件后操作会话目录本身。

- 验收：三种情况的输出摘要记进 todo。

### Task 11：合入集成分支并跑完整检查

先提交实现，再单独执行 `module-crew sync`，然后走 `verify-and-commit.sh` 全套（validate、phase-guard、verify-artifacts，含 ShellCheck）。

- 验收：sync 退出码 0；全套通过；`module_scope.py check --module cost-slim-link-follow --base crew/fix-batch` 越界 0。

### Checkpoint 2（gate）：模块最终验收

发最终验收【交审】：按 Spec Success criteria 逐条给证据、变异核对结果、改动统计与越界检查、新增依赖（无）、提交表、拟写的更新说明。
不推送、不开 PR，合并由模块协调按用户原话做。

## 风险

| 风险 | 影响 | 处理 |
| --- | --- | --- |
| 有脚本或测试仍依赖成本报告的旧 JSON 字段 | 调用方读不到字段 | Task 1 前全仓 `grep` `redispatches`／`reclaims`／`edits_after_handback`（排除 `evals/dispatch-cost/results/` 历史结果与 `docs/reports/`） |
| 命令里 `|| exit 2` 在宿主执行代码块时的表现 | 跟随失败时命令继续往下跑 | Task 10 按命令文件原样实跑失效情况；必要时改为 `[ -n "$PROJECT" ] || exit 2` |
| 与 `sibling-rules-out`、`rules-at-nodes` 改同一文件 | sync 冲突 | 重叠文件放到 Task 5 之后改；只改本模块相关段落，冲突以集成分支为底手工合并 |
| Spec 并行边界那一行在批准后改过 | 批准标记的指纹与正文不符 | 随本 Plan 一起交审，由模块协调按用户答复重新标记 |
