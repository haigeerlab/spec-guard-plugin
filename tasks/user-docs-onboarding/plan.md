# Plan: user-docs-onboarding

<!-- spec-guard: review approved -->

依据 [`spec/user-docs-onboarding.md`](../../spec/user-docs-onboarding.md)（2026-10-28 用户在本会话批准：「Spec 批准；Q1 A；Q2 A；Q3 A；Q5 A」）。
批准节奏为分开审，本 Plan 单独交审。分支 `claude/docs-onboarding`（从 `origin/main` `8765b363` 开出），worktree `distracted-morse-46ef70`。
串行，在本会话做。只改文档，不改版本号、不发版。

## Overview

先在临时目录里把例子项目真实走一遍、存下每一步的输出，再据此写上手文档；然后补术语、Codex 话术与 README；最后整体检查，
并让一个不知道背景的子代理重做新手测试。每个 task 单独提交（`scripts/verify-and-commit.sh`）；因为快档不跑文档回归
（user-docs-align 踩过），每次提交前另跑一次完整 `validate.sh`。

## Architecture Decisions

1. **例子项目建在 scratchpad 的临时目录里，不进仓库。** `git init` 后用插件自己的脚本安装约定（`setup-convention` 对应的脚本），
   逐步写能力图、Spec、Plan、todo，每一步用 `phase-guard.sh` 取阶段提示、用 `verify-artifacts.sh` 校验，输出存成文件；用到的命令记进 todo。
2. **输出原样贴入，只替换一处。** 阶段提示里的 `位置:` 一行带临时目录的绝对路径和分支名，贴入时把路径换成 `<项目目录>`，其余一字不改；
   页内写明这一处替换。
3. **例子以 0.85.0 的输出为准。** 页首写明「以下输出取自 0.85.0」；插件以后改了提示文字，例子可能和实际略有出入，以实际为准。
   不为此新增自动检查（超出范围）。
4. **每样内容只放一处**（Spec 假设 4）：对照表、选用指引在上手文档；术语在 `concepts.md`；Codex 话术在 `commands.md` 命令对照；
   README 只放入口、功能一览与分工说明。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：实跑例子项目并存下输出（AC2、AC4 的证据）

- 在 scratchpad 建 `note-*` 例子项目，按 `MAP_ONLY` → `NEEDS_SPEC` → `NEEDS_PLAN` → `BUILDING` → 最终验收前 → `MODULE_DONE` 逐步推进，
  每步存 `phase-guard.sh` 输出；能力图写完后存 `verify-artifacts.sh` 输出（须 0 失败）；顺带存一份 `/map` 输出。
- 验证：每个阶段的输出文件都在、阶段名对得上；todo 记下命令与文件名。只是取证，不提交文件到仓库（todo 一行除外）。

### Task 2：写 `docs/getting-started.md`（AC1 的文档部分、AC2～AC6）

- 内容：适合谁与前置条件一句带过并链到 README；`/spec` 与能力图格式的关系；例子项目逐步走第一个模块（能力图、最小 Spec、带
  `gate`／`report` 的 plan 与 todo、每步阶段提示）；「你做什么／agent 自动做什么」对照表；功能选用指引与「只用 agent-skills 时会碰到什么」。
- 核对：`docs/upstream-analysis.md` 3.3 节、`templates/CAPABILITY-MAP.md`、`references/workflow-checkpoints.md`、各命令说明。

### Task 3：`docs/concepts.md` 术语（AC7）

- 补 11 个术语；已有条目不改。核对：`workflow-checkpoints.md`（检查点分级、预先声明、并行边界、自治档位）、`node-rules.md`、
  `teardown-convention`（零足迹）、`local-ticket-ledger-runtime.md`（Epiq）。

### Task 4：`docs/commands.md` 的 Codex 话术（AC8）

- 命令对照的 Codex 一列改为可直接说的一句；每句对着 `skills/*/SKILL.md` 的小节名核对。

### Task 5：README 中英（AC1、AC9）

- 「快速开始」末尾加上手文档入口；新增「功能一览」（6 组）；文档导航加上手文档；多模块并行一节写 module-crew 的分工。

### Checkpoint 1（report）：整体检查

- `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全过；改过的文档无断链；`git diff --stat origin/main -- plugins/spec-guard` 为空；记入 todo。

### Task 6：新手测试复跑（AC10）

- 派一个不知道背景的只读子代理，只给 README 路径与「只读使用者文档」的限制，让它照上手文档写一份能力图并说出读完的结论；
  我把它写的能力图放进临时项目跑 `verify-artifacts`。结论与新发现原样记进 todo，新问题只列出、不在本模块处理。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC1～AC11 逐条证据、文档改动表与提交表、Spec 中途改动（如有）、新手测试结论。通过后推送并开本模块 PR
  （批准本 Plan 即授权推送与开 PR），合并由用户进行。

## Files likely touched

- 文档：`docs/getting-started.md`（新增）、`docs/concepts.md`、`docs/commands.md`、`README.md`、`README.en.md`
- 记录：`spec/CAPABILITY-MAP.md`（已写入新行与变更记录）、`spec/user-docs-onboarding.md`、`tasks/user-docs-onboarding/plan.md`、`tasks/user-docs-onboarding/todo.md`
- 仓库外：scratchpad 里的临时例子项目与输出文件（不提交）。
- 不碰：`plugins/spec-guard/`、CHANGELOG、历史记录目录、维护者文档。新增依赖、锁文件改动：无。

## 风险

- **例子输出以后会过时。** 页首写明版本（决定 3）；不加自动检查。
- **README 中英结构检查。** `check-readme-sync.py` 核对部分结构；新增一节两版同时加，逐段对照。
- **新手测试结论不如预期。** AC10 只要求如实记录；新问题列出交你决定是否另开模块，不在本模块里扩大范围。
- **快档漏跑文档回归。** 每次提交前另跑完整 `validate.sh`（见 Overview）。
