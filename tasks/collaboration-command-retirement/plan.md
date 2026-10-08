# Plan: collaboration-command-retirement

依据 [`spec/collaboration-command-retirement.md`](../../spec/collaboration-command-retirement.md)（用户 2026-10-08 确认发 0.54.0 并先做本模块）。
本仓库 `reviewCadence` 为 `combined`：Spec 与本 Plan 一起评审、一次批准。分支 `claude/collaboration-command-retirement`，
从 `d1f2b09`（`runtime-state-layout` 合并）开出。本模块是本批最后一个，版本号改动在本 PR 内。

## Task List

### Task 1：退役扫描加入该名字（先红）

`test-retire-legacy-tracker-bridge.sh` 的能力图名单与插件现行文件扫描加入 `spec-guard:collaboration`，确认因命令文件与
现行文字仍在而失败。

- 验收：扫描失败并指出命令文件等位置。
- 文件：`plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh`。

### Task 2：删除命令并改写现行文字

删除 `commands/collaboration.md`、`hooks/test_collaboration_handoff.py`（及其在 `validate.sh` 的调用）；改写 `docs/workflow.md`、
`README.md`、`docs/optional-features.md`、`docs/collaboration-interface.md`、两个检查器的说明与清单（命令名检查器的外部命令项以实测为准）。

- 验收：退役扫描转绿；命令名、命令表、README 同步、协作边界检查器与检查器回归全部通过；`ticket` skill 与
  `test_agent_relay_probe.py`、`test_ticket_entry.py` 不变且通过。变异：放回命令文件、在能力图写回该名字，扫描都变红。
- 文件：上述文件。

### Checkpoint 1（report）：validate.sh 通过，两套 hook 断言通过，ShellCheck 无警告

### Task 3：0.54.0 版本与 CHANGELOG

两份 `plugin.json` 改为 `0.54.0`，README `--ref v0.54.0`；CHANGELOG `## [未发布]` 改为 `## [0.54.0] - <日期>`，补"移除"一节；
运行清单一致性、README 同步与 `evals/codex-plugin-smoke.sh --selftest`。

- 验收：上述检查通过。
- 文件：两份 `plugin.json`、`README.md`、`CHANGELOG.md`。

### Checkpoint 2（gate）：模块评审与发版

推送前在同一条 `&&` 链里，于 macOS `/bin/bash` 跑 `validate.sh`、两套 hook 断言与 ShellCheck；pre-push 钩子兜底。
批准本 Plan 即授权推送本分支并开本模块的 PR；合并由用户进行。**合并后**按 `docs/release-process.md` 一次走完：
核实合并 → 打 `v0.54.0` tag 并推送 → 创建 GitHub Release → 升级 Claude 与 Codex 两边宿主 → 证据 PR；只在出错时停下，
证据 PR 同样由用户合并。

## 风险

| 风险 | 应对 |
|---|---|
| 漏改某处现行文字，用户仍被引向已删除的命令 | 退役扫描覆盖插件现行文件与能力图；命令名检查器拦下不存在的命令 |
| 误删 `ticket` 依赖的探针 | 探针与其回归明确保留，`test_ticket_entry.py` 守住调用方式 |
| 发版步骤中途失败 | 按发版流程逐步读回；失败即停、照实报告，不跳步 |
