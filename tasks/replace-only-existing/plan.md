# Plan: replace-only-existing

<!-- spec-guard: review approved -->

依据 [`spec/replace-only-existing.md`](../../spec/replace-only-existing.md)（2026-11-02 用户在本会话批准：「批准」，能力图新行同时确认写入）。
分支 `claude/replace-only-existing`（从 `origin/main` `1861f012` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.86.1。

## Overview

先在 `test-setup-teardown.sh` 写三种「没有块却带 `--replace`」的用例（带与不带 `--dry-run`），确认在 0.86.0 上失败；再在
`setup-convention.sh` 里、建任何目录之前加一个拒绝分支。随后改命令说明与文档的说法，最后改版本号与 CHANGELOG，交最终验收。

## Architecture Decisions

1. **拒绝放在 C3 检查的同一位置**：`echo '═══ Spec Guard local convention ═══'` 之后、`mkdir -p` 之前，新增
   `if [ "$REPLACE" = true ] && [ "$HAS_BLOCK" != true ]`。这样带不带 `--dry-run` 都在同一处拒绝，不会先打印「create spec/…」
   之类的预览行。
2. **另一侧的判定写成一个小函数** `other_side`：按 `HOST` 取另一侧的文件名与标记（Claude 侧看 `AGENTS.md` 的
   `spec-guard-codex-convention`，Codex 侧看 `CLAUDE.md` 的 `agent-skills-convention`），用与 `marker_lines` 相同的独占一行判据
   （`grep -Ec`，`|| true`，不用 `| grep -q`）。不校验另一侧块的结构，只决定提示哪一句。
3. **三种提示**照 Spec 原文写到 stderr，`exit 1`。`install_block` 里没有块的分支不改：不带 `--replace` 时它照旧新建；带 `--replace`
   已在前面被拒，走不到它。
4. **既有回归核对**：先 grep `test-setup-teardown.sh` 与 `test-phase-guard.sh`、`evals/` 里在没有块的项目上用 `--replace` 并期望成功的用例；
   有的话按新行为改写并在 todo 里列出，没有就写「无」。
5. **文档**：`commands/setup-convention.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md` 写明没有块时 `--replace` 拒绝并提示哪一侧；
   README 中英「已经装过旧版约定块的项目」与 `docs/workflow.md:74` 补「在块所在的一侧运行，两侧都有就各跑一次」；
   CHANGELOG 0.86.0 升级须知那一行改成同样说法，0.86.1 的「修复」写本模块并注明更正了 0.86.0 的说法。
6. **发版**照 0.86.0：合并后核对、打 tag、打包、Release、两个宿主核对（Codex 先请你重新批准 hook）、证据收尾 PR，最后告诉总负责人。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：拒绝分支（成功标准 1–4）

- 文件：`hooks/setup-convention.sh`、`hooks/test-setup-teardown.sh`。
- 用例：只有 `AGENTS.md` 有块时 Claude 侧 `--replace` 与 `--replace --dry-run`；只有 `CLAUDE.md` 有块时 `--host=codex --replace`；两侧都没有块时
  `--replace`。每例核对退出 1、提示文字、`snapshot` 前后相同（不建 `spec/`、`tasks/`、`.agent/`，不建 `CLAUDE.md`）。回归：两侧都有块时
  两边各自 `--replace` 成功。
- 验证：新用例在 0.86.0 上失败、改后通过；`test-setup-teardown.sh` 全部通过；ShellCheck 无告警。

### Task 2：文档

- 文件：`commands/setup-convention.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/workflow.md`、`README.md`、`README.en.md`。
- 验证：`validate.sh --quick` 通过（含命令对照、README 同步与读文档的回归）。

### Task 3：版本号与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、README 中英 `--ref`、`CHANGELOG.md`（0.86.1，并改 0.86.0 升级须知那一行）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；ShellCheck；`evals/codex-plugin-smoke.sh --selftest`。
- 变异（草稿副本）：去掉拒绝分支、把它挪到 `mkdir -p` 之后，两处都要让 `test-setup-teardown.sh` 变红。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、成功标准证据、文档与改动表、提交表、Spec 中途改动（如有）、拟回告。通过即同时授权：推送、开 PR；你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对合并、打 `v0.86.1`、打包、Release、比对 SHA-256；刷新并核对 Claude 与 Codex 安装副本（Codex 先请你在命令行版 `codex` 的 `/hooks` 重新批准再跑 smoke）；
  收尾扫描、证据收尾 PR；按批准的原文回告总负责人。任一步失败就停下说明。

## Files likely touched

- 插件包：`hooks/setup-convention.sh`、`hooks/test-setup-teardown.sh`、`commands/setup-convention.md`、`skills/spec-guard-ops/SKILL.md`、两份 `plugin.json`
- 仓库：`docs/commands.md`、`docs/workflow.md`、`README.md`、`README.en.md`、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.86.1-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/replace-only-existing.md`、本 Plan、`tasks/replace-only-existing/todo.md`
- 新增依赖、锁文件改动：无。不碰 `managed-block.py`、`teardown-convention.sh`、阶段判定。

## 风险

- **既有用例依赖旧行为**：决定 4 的 grep 兜住；有就改写并列出。
- **改历史 CHANGELOG**：只改 0.86.0 升级须知那一行的说法，并在 0.86.1 注明；GitHub 上 v0.86.0 的 Release 说明不改。
- **`.sh` 改动**：按 CI 参数跑 ShellCheck；`grep` 计数不用管道 `-q`，变量后接中文写 `${VAR}`。
