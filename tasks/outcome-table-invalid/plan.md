# Plan: outcome-table-invalid

<!-- spec-guard: review approved -->

依据 [`spec/outcome-table-invalid.md`](../../spec/outcome-table-invalid.md)（2026-11-04 用户在本会话批准：「批准」，能力图新行同时确认写入）。
分支 `claude/outcome-table-invalid`（从 `origin/main` `4b2abcce` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.86.6。

## Overview

先在 `test_documentation_verification.py` 写四种坏表与命令行入口的用例，确认在 0.86.5 上失败；再在 `_outcomes` 里把 `ImpactError`
转成 `VerificationError`。随后改版本号与 CHANGELOG，交最终验收。

## Architecture Decisions

1. **只在 `_outcomes` 转换**：`_table(...)` 的调用包在 `try` 里，`except ImpactError as error: raise VerificationError(str(error))`，
   与 `verify_documentation` 对 `parse_impact` 的转换写法一致。`main` 不改。
2. **报错文字不改**：保留 `_table` 原文（如 `Documentation outcome table has no entries`），命令行 JSON 的 `error` 即这句。
3. **不动** `documentation_impact.py`、判定、JSON 字段、退出码约定、`interface.json`；命令说明已写 `invalid` 表示表格结构无效，不用改文档。
4. **发版**照 0.86.5：合并后核对、打 tag（我这边推 tag 遇 500 就改在你的终端推）、打包、Release、两个宿主核对（Codex 在新开 CLI 的提示里批 hook，
   我先展示终端面板）、证据收尾 PR。需求来自你本人，无回告。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：坏的 outcome 表报 invalid（假设 1–3）

- 文件：`hooks/documentation_verification.py`、`hooks/test_documentation_verification.py`。
- 用例：只有表头、缺分隔行、分隔行写错、某行格数不对，各抛 `VerificationError`；`main` 对只有表头的表输出 `state: invalid` 的 JSON 并返回 1。
- 验证：新用例在 0.86.5 上失败（抛 `ImpactError`）、改后通过；该文件全部通过。

### Task 2：版本号与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、README 中英 `--ref`、`CHANGELOG.md`（0.86.6：修复）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；`evals/codex-plugin-smoke.sh --selftest`。
- 变异（草稿副本）：去掉这次的转换，测试要变红；临时项目从命令行跑一次只有表头的表。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、成功标准证据、改动表、提交表、Spec 中途改动（如有）。通过即同时授权：推送、开 PR；你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对合并、打 `v0.86.6`、打包、Release、比对 SHA-256；刷新并核对 Claude 与 Codex 安装副本；收尾扫描、证据收尾 PR。任一步失败就停下说明。

## Files likely touched

- 插件包：`hooks/documentation_verification.py`、`hooks/test_documentation_verification.py`、两份 `plugin.json`
- 仓库：`README.md`、`README.en.md`（只改 `--ref`）、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.86.6-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/outcome-table-invalid.md`、本 Plan、`tasks/outcome-table-invalid/todo.md`
- 新增依赖、锁文件改动：无。不碰 `documentation_impact.py`、`phase-guard.sh`、`interface.json`。

## 风险

- **既有用例依赖 `ImpactError`**：先 grep 测试里有没有断言 outcome 表抛 `ImpactError`；有就在 todo 写明原因再改。
- **重复的 outcome 表**：已由 `_outcomes` 自己报 `VerificationError`，不受影响；用例保持通过即可。
