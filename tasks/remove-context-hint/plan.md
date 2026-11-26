# Plan: remove-context-hint

<!-- spec-guard: review pending -->

Spec：[spec/remove-context-hint.md](../../spec/remove-context-hint.md)（2026-11-26 批准，Q1 A、Q2 A）。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 架构决定

- **`module_stage.py`**：
  - 删 `thresholds`、`boundary_line`、只给它们用的 `_k`，`COMMANDS`／`COMMANDS_ZH` 各宿主的 `free-next` 一项，以及只为 `free-next` 存在的常量（`FREE_BOUNDARY`，`CODEX_COMPACT`、`CARRIES_OVER_ZH` 等；`NO_PASTE`、`SLASH_BLOCK` 等若别处仍用就留）。删之前逐个 `grep`，有别的读取方的不删。
  - `_describe_body` 去掉 `boundary_note_line` 及三处追加（MODULE_DONE、DONE、NEEDS_SPEC 分支）；`describe` 去掉状态码没变时附带边界行的逻辑（`info["boundary"]`），一行模式只剩那一行。
  - 去掉参数 `--context-tokens`、`--context-window`、`--window-estimated`、`--unattended`，`describe`／`_describe_body` 的对应形参一并去掉；`--host` 留着（其他命令的写法要用）。
- **`session_context.py`**：删 `_usage`、`_window`、`context_tokens`、`context_usage`、`STANDARD_WINDOW`、`over_standard_window`、`unattended`。`_compacted` 改成只判断「是不是压缩记录」的谓词 `_is_compaction`，不再读 `postTokens`；`_count` 随之没有用处，一并删除（R1-1）。`_first_record`、`FIRST_RECORD_LIMIT`（宿主判断用）、`tail_lines`、`_records`、`last_state` 留着。模块开头的说明改为「位置、宿主与上一次 spec-guard 注入的状态码」（R1-4）。`main` 的普通模式输出从七行改为三行：位置行、宿主、上一次的状态码（Spec 假设 3）。
- **普通模式只有一个读取方**（R1-2，已核对）：全仓 `git grep session_context.py`，普通模式只有 `phase-guard.sh` 第 301 行读；`--resolve-root`（第 109 行）与 `--received`（第 154 行）各有自己的输出，不受影响；`test_session_context.py` 直接调脚本；七个兄弟插件仓库没有引用。Task 1 实现后再 `git grep` 一次确认。
- **`phase-guard.sh`**：会话事实按新的三行解析；删 `TOKENS`、`WINDOW`、`OVER`、`WINDOW_ESTIMATED`、`UNATTENDED` 与 SessionStart 时把 `TOKENS` 置 0 的那段；调 `module_stage.py` 时不再传那四个参数。`LOCATION`、`FACT_HOST`→`HOST`、`LAST`（SessionStart 时清空）照旧。
- **测试**：
  - 新增「再也不出这一行」的回归：`test-phase-guard.sh` 用会话记录夹具造出原来一定会出这一行的情形——Claude 读数 800k（超过 200k，原来按 1M 估算、过 70%）、Codex 带 `model_context_window` 且过 70%——分别在 MODULE_DONE、DONE、NEEDS_SPEC 与状态码没变的一行模式下断言没有「模块边界: 本会话上下文约」与 "Module boundary: this session's context"（AC1）。一行模式那例另做精确断言：输出恰好是原来那一行 brief（`spec-guard: …`），状态码与低读数时相同（R1-3）。
  - 原来断言出这一行、断言阈值与窗口估算、断言无人值守时不出的场景删除或改成断言不出；`test_session_context.py` 删读数、窗口、over-200k、无人值守的用例，加一例 `main` 只输出三行且顺序为位置、宿主、状态码。
  - `test_flow_v2.py` 里如有构造 `describe(..., context_tokens=...)` 的调用一并改掉。
  - `evals/hint-english-diff.sh` 去掉比对这一行的部分。
- **文档**（Spec 假设 4）：`docs/commands.md`（第 68 行附近）、`docs/workflow.md`（第 80、181 行附近）、`docs/design.md`（第 42 行 `session_context.py` 的说明改为「位置、宿主与上一次注入的状态码」）、`commands/phase.md`（第 68、83 行附近）。CHANGELOG「未发布」加「移除」一条，如实写数字从哪来、为什么删。

## 外部审查意见

- 第一轮（Codex）：R1-1 `_count` 与 `postTokens` 只为读数存在 → 采纳；R1-2 三行协议的读取方未核对 → 采纳，已核对；R1-3 高读数一行模式缺精确断言 → 采纳；R1-4（建议）模块说明 → 采纳。

## 任务

- **Task 0**：提交 Spec 批准、能力图新行、本 Plan 与 todo。验证：快档。
- **Task 1**：先写会红的回归：`test-phase-guard.sh` 的 AC1 场景（实现前这几例会因为出了边界行而失败）；`test_session_context.py` 的三行输出一例。再改 `module_stage.py`、`session_context.py`、`phase-guard.sh`，删掉旧用例。验证：`test-phase-guard.sh`、`test_session_context.py`、`test_flow_v2.py`。
- **Task 2**：文档、`evals/hint-english-diff.sh`、CHANGELOG。验证：快档，`git grep -n -e boundary_line -e context_tokens -e context_window -e window_estimated -e over-200k -e postTokens -e '上下文约' -e 'Module boundary: this session'` 在历史目录与 CHANGELOG 旧条目之外为空（AC4）。
- **Checkpoint 1（report）**：完整档三条全绿；变异（临时副本）：在 `_describe_body` 里加回一行固定的边界文字 → AC1 用例变红；还原后全绿。已安装的 0.96.2 与本分支比对（AC2、AC3）：本仓库与几种老流程夹具在没有读数或读数低于 70% 时的阶段提示与状态码逐字相同；高读数的一行模式下，0.96.2 的输出去掉边界行后与本分支逐字相同（R1-3）；SessionStart（compact）那次注入逐字相同；带收件包装的提示词，收件记账那行逐字相同。
- **Checkpoint 2（gate）**：推送、开 PR；最终验收与合并合成一问；发 0.97.0 另取授权，发之前先告诉 ecosystem-lead（agent-relay 同步发版）。拟回告：给 ecosystem-lead「上下文边界提示已删，数字来源的核实结果见 Spec」。

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=3 sha256=c1e4f76f5d10 -->
