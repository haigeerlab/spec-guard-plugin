# Plan: quick-tier-doc-regressions

<!-- spec-guard: review approved -->

依据 [`spec/quick-tier-doc-regressions.md`](../../spec/quick-tier-doc-regressions.md)（2026-10-28 用户在本会话批准：「Spec 批准；Q1 A；Q2 A」）。
批准节奏为分开审，本 Plan 单独交审。分支 `claude/quick-tier-doc-regressions`（从 `origin/main` `dcbf9da6` 开出），worktree `distracted-morse-46ef70`。
串行，在本会话做。不改插件包、不改版本号、不发版。

## Overview

先写复现漏洞的回归（红），再把三个读仓库文档的测试移进快档（绿）；然后加「漏列」检查器，先写它的正反例（红）再实现（绿）；
最后改维护者文档。每个 task 单独提交（`scripts/verify-and-commit.sh`；这些改动含 `.sh`／`.py`，走全套）。

## Architecture Decisions

1. **快档清单是 `validate.sh` 里的一个 bash 数组 `DOC_REGRESSIONS`**，在快档部分（`if [ "$QUICK" = false ]` 之前）新开一节
   `═══ 读仓库文档的回归 ═══` 逐个跑；三个测试从全套回归段里删掉，全套照样会经过快档这一节，不重复跑。`check-tests-registered.py` 只认 `validate.sh` 与 CI 里出现的测试，新位置仍在 `validate.sh` 里，Task 1 实跑确认它不报漏注册。
2. **检查器 `scripts/check-doc-regressions-listed.py`**：读 `validate.sh` 里 `DOC_REGRESSIONS` 的条目；扫 `plugins/spec-guard/hooks/test*`、`scripts/test*`，
   按 Spec 假设 2 的写法（Python `parents[N] / "docs"`、`parents[N] / "README…"`、`/ "CHANGELOG.md"` 这类从仓库根拼路径的写法；shell 里
   `"$ROOT/docs/…"`、`"$ROOT/README…"`、`"$ROOT/CHANGELOG.md"`）找出读仓库文档的测试，不在清单里就报错并列出文件；
   `scripts/test-checkers.sh` 本身是检查器回归，不扫它（它把坏样本当数据）。挂在快档的「用户可见输出里的命令名」那组检查之后，零成本。
3. **AC1 的复现回归**照 `test_validate_quick.py` 现有「复制仓库、改坏一处、跑 `--quick`」的写法加一个用例：删掉副本 `docs/workflow.md` 里的
   `rootCauseReviewRequired`，断言 `--quick` 失败。`QUICK_SECTIONS` 加新一节的名字。
4. **耗时**：改动前后在本机各跑三次 `validate.sh --quick` 取中位数，写进 todo。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：快档跑读仓库文档的回归（AC1、AC2，先红后绿）

- 文件：`scripts/test_validate_quick.py`、`scripts/validate.sh`。
- 先加 AC1 用例与 `QUICK_SECTIONS` 新名 → 红（快档放行坏文档、没有新一节）；再加 `DOC_REGRESSIONS` 与新一节、从全套删掉三行 → 绿。
- 变异：草稿副本里清空数组，AC1 用例变红。耗时前后实测记进 todo。

### Task 2：漏列检查器（AC3、AC4，先红后绿）

- 文件：`scripts/check-doc-regressions-listed.py`（新）、`scripts/test-checkers.sh`、`scripts/validate.sh`。
- 先在 `test-checkers.sh` 加用例：漏列被拦（fail）；夹具路径（临时目录里的 `docs/`）不报（pass）；已列入的不报（pass）；当前仓库通过（pass）→ 检查器不存在，红。
- 实现检查器并接进 validate → 绿。它在现有测试里多找出的，按 AC4 加进清单或在清单旁写原因；多出耗时超过 2 秒先停下问你。

### Checkpoint 1（report）：三套核心回归与 ShellCheck

- `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全过；CI 同版 `npx --yes shellcheck@4.1.0 -S warning` 跑 hooks、scripts、evals 的全部 `.sh` 无告警；
  `git diff --stat origin/main -- scripts/verified_trees.py .github plugins/spec-guard` 为空；记入 todo。

### Task 3：维护者文档（AC6）

- 文件：`docs/maintainer-workflow.md`，必要时 `CLAUDE.md` 讲快档的那句。写明快档也跑读仓库文档的回归、新增这类测试要列进 `DOC_REGRESSIONS`（漏列会被检查器拦下）。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC1～AC7 逐条证据、耗时前后、文档改动表与提交表、Spec 中途改动（如有）。通过后推送并开本模块 PR（批准本 Plan 即授权推送与开 PR），
  合并由用户进行。

## Files likely touched

- 脚本：`scripts/validate.sh`、`scripts/check-doc-regressions-listed.py`（新增）
- 测试：`scripts/test_validate_quick.py`、`scripts/test-checkers.sh`
- 文档：`docs/maintainer-workflow.md`，可能 `CLAUDE.md`
- 记录：`spec/CAPABILITY-MAP.md`（已写入新行与变更记录）、`spec/quick-tier-doc-regressions.md`、`tasks/quick-tier-doc-regressions/plan.md`、`tasks/quick-tier-doc-regressions/todo.md`
- 不碰：`scripts/verified_trees.py`、`scripts/verify-and-commit.sh`、`.github/`、`plugins/spec-guard/`。新增依赖、锁文件改动：无。

## 风险

- **检查器误报夹具路径。** 只认从仓库根拼路径的写法（决定 2），反例用例锁住「临时目录里的 `docs/` 不报」。
- **检查器漏报其他写法。** Spec 假设 2 已接受；正例覆盖本仓库现有的三种写法。
- **快档变慢。** 实测前后耗时；超过 2 秒按 Spec「先问」。
- **`test_validate_quick` 自身变慢**：复制仓库的用例已有一个，新用例共用同样做法，约多几秒，只在全套里跑。
