# Plan: autonomy-tier

<!-- spec-guard: review approved -->

依据 [`spec/autonomy-tier.md`](../../spec/autonomy-tier.md)（2026-10-26 用户在本会话批准：「批准 autonomy-tier 的 Spec」）。评审节奏为分开审，
本 Plan 单独交审。分支 `claude/s32-autonomy-tier`，worktree `distracted-morse-46ef70`，叠在 `claude/s32-interface-1.11`（PR #414）之上；
#414 合并后先把本分支同步到 `main` 再开 PR。串行，在本会话做。本模块改版本号到 0.85.0，打 tag 与发 Release 不在本 Plan 里。

## Overview

先做配置项（先红后绿），再做接口条目、规则与说明文字，最后改版本号与 CHANGELOG。每个 task 单独提交（`scripts/verify-and-commit.sh`）；
代码 task 在草稿副本里把修复改坏一处，确认新用例变红（手工变异，不入库）。

## Architecture Decisions

1. **配置只加常量与校验器**：`project_config.py` 加 `TIERS`，`VALIDATORS` 与 `DEFAULTS` 各加 `autonomyTier`；`load`／`summary`／`set`／`unset`
   已经按 `VALIDATORS` 通用处理，不写新的读写代码。
2. **阶段提示不注入**：`module_stage.config_lines` 只认识 `artifactLanguage`、`reviewCadence`（逐键判断），新键天然不出行；用单测锁住这一点，
   不改 `config_lines`。
3. **接口条目照 `moduleConcurrency` 的形状**，`readFrom` 写 `project_config.py show --format json`；`check-interface.py` 的 `ENTRIES` 加它，
   并核对 `values` 等于 `project_config.TIERS`。先改检查器（现有 interface.json 变红），再加条目（变绿）。
4. **底线一段放在「批准节奏」与「批准标记」之间**，标题「## 自治档位与底线」；不进节点规则（Spec 假设 6）。
5. **CHANGELOG**：把顶部「未发布」段标题改为 `## [0.85.0] - <发版日>`，开头加一句本版范围（两个模块、interface 1.11），补本模块条目与「升级须知」；
   发版日先写本模块提交当天，发版时若跨日再更正（发布流程里核对）。

## Task List

### Task 0：提交已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：配置项 `autonomyTier`（C1，AC1、AC2，先红后绿）

- 文件：`hooks/project_config.py`、`hooks/test_project_config.py`。
- 用例：三档各 `set --confirm` 后读回；未设置时 `summary` 为 `strict`／`default`；`set --value fast` 退出 2、文件不变；文件里写 `"autonomyTier": "fast"`
  时只这个键回默认、`check` 退出 1、`reviewCadence` 照常生效；`unset --confirm` 去掉；`module_stage.config_lines` 设与不设三档输出相同。
- 变异：草稿副本里 `TIERS` 删掉 `relaxed`，对应用例变红。

### Task 2：接口条目（C3，AC3，先红后绿）

- 文件：`interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`docs/design.md`。
- 先改检查器 → 现有 interface.json 报缺 `autonomyTier`（红）；加条目（绿）；`test-checkers.sh` 加「缺条目」「少一档」两例。`docs/design.md` 1.11 一段补一句。

### Task 3：底线规则与说明（C2、C4，AC4）

- 文件：`references/workflow-checkpoints.md`、`commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`hooks/test_workflow_checkpoints.py`。
- 断言：「自治档位与底线」一段含三项批准、三种必停、「不联动」「原话」「项目规则更严以项目为准」；`config.md` 表格一行与例外句、SKILL.md config 一节含
  `autonomyTier`、「不联动」、旧版本兼容。先红后绿。

### Checkpoint 1（report）：三套核心回归

- `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿，CI 同版 ShellCheck 无告警；结果记入 todo。

### Task 4：版本号 0.85.0 与 CHANGELOG（C5，AC5）

- 文件：两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。`check-readme-sync.py` 通过；`interface.json` 版本不动。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC 逐条证据、改动文件与提交表、Spec 中途改动（如有）。通过后：#414 已合并则把本分支同步到 `main`（合并基线，不改写已推送历史），
  推送并开本模块 PR（批准本 Plan 即授权推送与开 PR），合并由用户进行；#414 未合并则先停下告诉用户。打 tag 前先告诉 ecosystem-lead 影响面。

## Files likely touched

- 代码：`plugins/spec-guard/hooks/project_config.py`、`scripts/check-interface.py`
- 测试：`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`scripts/test-checkers.sh`
- 说明：`plugins/spec-guard/interface.json`、`plugins/spec-guard/commands/config.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、
  `plugins/spec-guard/references/workflow-checkpoints.md`、`docs/design.md`、`CHANGELOG.md`、`README.md`、`README.en.md`
- 版本：`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`
- 新增依赖、锁文件改动：无。

## 风险

- **旧版本读到新键**：0.68.0～0.84.2 只忽略并警告，0.67.1 及更早整份判无效。说明与 CHANGELOG 提醒团队升级后再设；默认不写这个键，不设就没有影响。
- **分支叠在 #414 上**：#414 若在合并前又改动，本分支同步时可能冲突；冲突只会在共用的 `interface.json`、`docs/design.md`、`CHANGELOG.md`，按两边都保留解决。
- **CHANGELOG 发版日期**：写的是提交当天，发版若跨日要更正；发布流程核对时一并检查。
