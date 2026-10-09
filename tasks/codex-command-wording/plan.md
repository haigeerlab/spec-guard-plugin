# Plan: codex-command-wording

依据 [`spec/codex-command-wording.md`](../../spec/codex-command-wording.md)（用户 2026-10-09 批准 Spec）。分开审：本 Plan
单独批准。分支 `claude/codex-command-wording`；提交一律走 `scripts/verify-and-commit.sh`。

## Task List

### Task 1：实测两边宿主给 hook 的信号

在临时消费者项目里（不改用户自己的配置）各跑一次真实宿主：Claude Code 用 `claude -p` 加临时 settings 里的
UserPromptSubmit hook，Codex 用 `codex exec`（`</dev/null`）加临时插件或沿用 `evals/codex-plugin-smoke.sh` 的做法。
记下两边 hook 进程的环境变量名（只记名字，不记值）与 hook 输入里 `transcript_path` 指向的记录首条类型。据此选定假设 1
的环境变量；结果写进 todo。

### Task 2：判断宿主

回归先行：`test-phase-guard.sh` 新增用例——会话记录首条为 Codex `session_meta`、为 Claude 记录、读不到记录时分别看
环境变量、两者都判断不了。再改 `session_context.py`（从会话记录判断）与 `phase-guard.sh`（环境兜底，把结果以
`--host` 传给 `module_stage.py`）。变异：把 codex 判成 claude；忽略环境兜底。

### Task 3：按宿主写命令

回归先行：
- Codex：各阶段建议、挂起、缺 todo、配置无效、MAP_INVALID 各行用 `$` 写法，不含 `/spec-guard:`、`/build`、`/plan`；
  `/compact` 行不带参数；
- Claude：模块完成行与上下文行改为"把命令单独放进代码块、`/compact` 带填好的聚焦说明"；其余逐字不变；
- 拿不准：与改前逐字相同。

再改 `module_stage.py`（命令写法集中在一处按宿主取）与 `phase-guard.sh` 的兜底行。变异：漏改一处 `/spec-guard:`；
Codex 的 `/compact` 带上参数；Claude 其余行改动一处。

### Task 4：文档与全量验证

改文档里引用这些提示原文的地方。跑 `/bin/bash` 3.2 下的三条最小验证、CI 同版本 ShellCheck，经 verify-and-commit 全档提交。

### Task 5：真实宿主核验

本机 Claude Code 与 Codex 各开一次真实会话（临时消费者项目），看注入原文与 agent 的转述：Codex 不再出现斜杠写法，
Claude 在模块边界给出一行可复制的 `/compact …`。结果写进 todo，用户做最终确认。

### Checkpoint 1（gate）：模块评审

全部回归通过，ShellCheck 无告警，真实宿主核验通过。本 Plan 获批即授权推送本分支并开本模块 PR，合并由用户进行。

### Task 6：随下次发版发出

改的是插件发布包：下次发版时 CHANGELOG 写进"修复"，发版证据里在两边安装副本上各看一次注入。
