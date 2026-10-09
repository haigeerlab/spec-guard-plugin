# Plan: agent-relay-interface-2

依据 [`spec/agent-relay-interface-2.md`](../../spec/agent-relay-interface-2.md)（用户 2026-10-09 批准 Spec；假设 1 已由
agent-relay 负责会话确认并经本会话核对）。分开审：本 Plan 单独批准。分支 `claude/v0.56.0`；提交一律走
`scripts/verify-and-commit.sh`。本模块是 0.56.0 的最后一个模块，PR 里同时带上发版改动。

## Task List

### Task 1：放宽接口范围

回归先行：`test_agent_relay_probe.py` 里"范围外判 incompatible"的取值改为 `0.9、3.0、3.1`，新增 `2.0`、`2.4` 判 `ready`，
两处范围断言改为 `>=1.0,<3.0`；改代码前确认变红。再改 `agent_relay_probe.py` 的 `REQUIRED`、`MAX_VERSION` 与文件头说明。
变异：上限改回 `(2, 0)`；上限改为 `(4, 0)`。系统 Python 3.9 通过。

### Task 2：文档

`docs/collaboration-interface.md:15`、`docs/migrations/2026-10-07-collaboration-split.md:29` 改为新范围，迁移说明"接口 1.x
内各自升级即可"改为"接口 1.x、2.x 内"。

### Task 3：0.56.0 发版改动

- 两份清单版本号与中英 README 的 `--ref` 改为 0.56.0；
- CHANGELOG `[0.56.0]`：修复（codex-command-wording）、兼容（本模块）、维护者工具（validate-parallel-files、
  verify-and-commit-untracked-warning、phase-guard-test-parallel）；
- 已拣入 `a54ecdc`；
- 勾掉四个模块已合并的 Checkpoint 1 与写 CHANGELOG 的项。

按 docs/release-process.md"发布前"：macOS `/bin/bash` 下跑完整 validate、两套 hook 回归，`evals/codex-plugin-smoke.sh --selftest`
（改了 hook 与技能）；经 verify-and-commit 全档提交。

### Checkpoint 1（gate）：模块与发版评审

全部回归通过，ShellCheck 无告警。本 Plan 获批即授权推送本分支并开 PR（含 0.56.0 发版改动），合并由用户进行。

### Task 4：发版后

用户合并后按发布流程一次做完：tag、发布包与 GitHub Release（下载回来核对摘要）、Codex 与 Claude 安装副本升级与核验（探针、
新的 phase-guard 回归、两边各看一次注入）、证据写入并开收尾 PR（勾掉各模块剩下的项）。
