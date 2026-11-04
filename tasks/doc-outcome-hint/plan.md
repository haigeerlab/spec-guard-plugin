# Plan: doc-outcome-hint

<!-- spec-guard: review approved -->

依据 [`spec/doc-outcome-hint.md`](../../spec/doc-outcome-hint.md)（2026-11-04 用户在本会话批准：「批准」，能力图新行同时确认写入）。
分支 `claude/doc-outcome-hint`（从 `origin/main` `7c67d8ed` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.86.5。

## Overview

先在 `test_documentation_verification.py` 写缺整张表、只漏一行、不需要 outcome 三个用例，确认在 0.86.4 上失败；再在
`documentation_verification.py` 里加缺表那一行。随后补三处文档，改版本号与 CHANGELOG，交最终验收。

## Architecture Decisions

1. **只看表有没有**：`_outcomes` 已经用 `_has_outcome_table` 数表的个数；`verify_documentation` 在 `required` 非空且表数为 0 时，
   先往 `attention` 放缺表那一行，再走原来的逐项循环。表数为 0 的判断复用现有函数，不另写解析。
2. **文字**：`tasks/<id>/plan.md has no Documentation outcome table; add one before final acceptance (format: references/documentation-verification.md)`，
   路径用模块 id 拼出，与项目根无关；和其他 attention 一样是英文。
3. **其余不动**：判定（`attention` 非空即 attention）、JSON 字段、退出码、`interface.json` 都不改。
4. **文档**：`documentation-impact.md` 的空模板放在 `Documentation delivery` 说明之后，放在 ```` ```markdown ```` 围栏里
   （核验会跳过围栏里的示例表，既有用例 `test_fenced_example_outcome_table_is_ignored` 已覆盖）。
5. **发版**照 0.86.4：合并后核对、打 tag、打包、Release、两个宿主核对（Codex 升级后在新开的 CLI 里批 hook，批完先看一眼再跑 smoke）、
   证据收尾 PR、回告 ecosystem-lead。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：核验缺整张 outcome 表时点名（假设 2–4）

- 文件：`hooks/documentation_verification.py`、`hooks/test_documentation_verification.py`。
- 用例：缺整张表（第一行点名缺表与 Plan 路径，后面仍有逐项行）；表在只漏一项（不出缺表行）；不需要 outcome（不出缺表行）；
  既有 `test_missing_outcome_is_attention_not_invalid` 的断言改看逐项行。
- 验证：新用例在 0.86.4 上失败、改后通过；`test_documentation_verification.py` 全部通过。

### Task 2：文档（假设 1）

- 文件：`references/documentation-impact.md`、`references/workflow-checkpoints.md`、`docs/optional-features.md`；
  `commands/documentation-verification.md` 讲输出的地方补一句缺表时的第一行。
- 验证：`validate.sh --quick` 通过；空模板放在围栏里，不被核验当成真表。

### Task 3：版本号与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、README 中英 `--ref`、`CHANGELOG.md`（0.86.5：修复、文档）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；`evals/codex-plugin-smoke.sh --selftest`。
- 变异（草稿副本）：去掉缺表那一行、把条件改成「表里漏任意一行」，两处都要让测试变红。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、成功标准证据、改动表、提交表、Spec 中途改动（如有）。通过即同时授权：推送、开 PR；你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对合并、打 `v0.86.5`、打包、Release、比对 SHA-256；刷新并核对 Claude 与 Codex 安装副本；收尾扫描、证据收尾 PR；回告 ecosystem-lead。
  任一步失败就停下说明。

## Files likely touched

- 插件包：`hooks/documentation_verification.py`、`hooks/test_documentation_verification.py`、`references/documentation-impact.md`、
  `references/workflow-checkpoints.md`、`commands/documentation-verification.md`、两份 `plugin.json`
- 仓库：`docs/optional-features.md`、`README.md`、`README.en.md`（只改 `--ref`）、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.86.5-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/doc-outcome-hint.md`、本 Plan、`tasks/doc-outcome-hint/todo.md`
- 新增依赖、锁文件改动：无。不碰 `phase-guard.sh`、`module_stage.py`、`interface.json`。

## 风险

- **别处依赖 attention 的顺序或条数**：先 grep 读 `attention` 的代码与测试（阶段提示只给命令名，不读结果）；有用例变红就在 todo 写明原因再改。
- **空模板被当成真表**：模板放在围栏里；Task 2 后用一份临时项目跑一次核验确认。
