# Plan: codex-hook-reapproval-docs

<!-- spec-guard: review approved -->

依据 [`spec/codex-hook-reapproval-docs.md`](../../spec/codex-hook-reapproval-docs.md)（2026-10-28 用户在本会话批准：「能力图 批准。Spec 批准；Q1 A；Q2 A」）。
分支 `claude/codex-hook-reapproval-docs`（从 `origin/main` `00e497e0` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
不改插件包、不改版本号、不发版。

## Overview

先改面向用户的 README 中英与故障排查，再改维护者的发布流程、维护者流程和 smoke 提示行；最后跑完整检查，交最终验收。
验收通过后推送、开 PR，合并由你进行。

## Architecture Decisions

1. **一处写全，其他处引用**：完整批准步骤（命令行版 `codex` 启动 → 提示「Hooks need review」→ `/hooks` 里批准 spec-guard 的 3 个 hook
   → 开新会话）写在 README「更新」一节；安装表只写一句并指向它；故障排查写现象与原因，步骤也指向 README，避免几处说法走样。
2. **措辞**：「Codex 0.164 起」开头；桌面版写「可能不提示」（Spec 假设 1）；旧版 Codex 那句（只有新增的 hook 要信任一次）保留并标「0.164 之前」。
3. **smoke 提示行**（Q1 A）：在第 182 行之后、`raise SystemExit(2)` 之前加一行 `print`，返回 2 时总是打印；不碰判决与退出码。
   selftest 只断言退出码，不改；改完跑 `--selftest` 与 ShellCheck。
4. **不新增测试**：这是说明文字，不是判据。改完用 `grep` 确认「原有的 `UserPromptSubmit` 一项不受影响」在仓库文档里为 0 次。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：README 中英（AC1）

- 文件：`README.md`、`README.en.md`（安装表 Codex 一栏、「更新」一节、排查小表「阶段提示没有出现」一行）。
- 验证：`check-readme-sync.py` 通过；两份说法一致。

### Task 2：故障排查（AC2）

- 文件：`docs/troubleshooting.md`（原因列表加 Codex 一条、第 41 行改正、第 143 行排查表补「重新批准」）。
- 验证：读仓库文档的回归（`DOC_REGRESSIONS`）通过；`grep` 原错误说法为 0 次。

### Task 3：发布流程、维护者流程与 smoke 提示（AC3、AC4）

- 文件：`docs/release-process.md` 第 5 步、`docs/maintainer-workflow.md` 第 118～132 行、`evals/codex-plugin-smoke.sh`。
- 验证：`evals/codex-plugin-smoke.sh --selftest` 通过；ShellCheck 无新告警。

### Checkpoint 1（report）：完整检查（AC4）

- 在本机 macOS 用系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh`；
  `git diff --stat origin/main -- plugins/spec-guard` 为空。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC1～AC4 证据、文档表、提交表、Spec 中途改动（如有）。通过后推送、开 PR，合并由你进行。

## Files likely touched

- 文档：`README.md`、`README.en.md`、`docs/troubleshooting.md`、`docs/release-process.md`、`docs/maintainer-workflow.md`
- 评估脚本：`evals/codex-plugin-smoke.sh`
- 记录：`spec/CAPABILITY-MAP.md`（已写入新行与变更记录）、`spec/codex-hook-reapproval-docs.md`、本 Plan、`tasks/codex-hook-reapproval-docs/todo.md`
- 插件包、新增依赖、锁文件：无。

## 风险

- **smoke 改的是 `.sh`**：提交走完整档（不是快档），加跑 ShellCheck（CI 会跑，本机 validate 不跑）。
- **0.164 的界面文字以后可能变**：文档里引用「Hooks need review」时写成「提示有 hook 需要审查（Hooks need review）」，界面变了也能对上意思。
