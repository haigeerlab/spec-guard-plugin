# Spec: rework-scope-baseline

<!-- spec-guard: review approved d2f4068442c3 -->

## Objective

越界检查（takeover-scope-check、plan-auto-approve 的 T4 检查）拿「第一次加入这个模块 Spec 的那个提交的父提交」当基线（`module_scope.default_base`），比较从基线到 HEAD 改过的所有文件。
模块第一次开工时这没有问题；但按 rework-in-place 在已完成的老模块上返工（往它的 todo 追加任务）时，基线和现在之间夹着别的模块合进 main 的提交，这些提交改过的文件全被算到这个模块头上。
2026-11-26 regression-doc-check 返工（#505）时，阶段提示报「16 个文件超出并行边界」，实际 #505 只改了边界内的 9 个文件；agent 因此停在中途 gate，要用户逐个解释。返工越晚、中间合并的模块越多，误报越多。

本模块让返工时的越界检查从返工开始的提交算起；第一次开工的模块判定完全不变。

给谁用：在老模块上返工的 agent；被误报打扰的用户；读越界结果的 autopilot、module-crew（经 `module_scope.py check`）。

登记：用户 2026-11-26「修，先写需求」「说完了」（需求复述：只检查返工开始之后的改动；返工自己越界照样报；第一次开工的模块不变；不改边界、预先声明、T4 规则本身与返工写法）。不属于任何用法草案。2026-11-26 用户回「批准；Q1 A」（同时确认能力图新行）。

**返工（2026-11-26，0.96.2 之后）**：0.96.2 留下一个已知边界：返工期间别的模块合进默认分支，返工分支再同步它之后，别人的改动仍会算进来。功能盘点把它列为缺口；用户经 ecosystem-lead 转达「按你的建议做」，在本会话回「两件都做，Claude 写码」；Spec 修订 2026-11-26 用户回「批准；Q2 A；Q3 A」。
写 Spec 前在临时仓库实测：
- **rebase 不误报**：返工提交被改写到新的默认分支之上，返工基线跟着移上去，别人的文件不在比较范围里。
- **merge 误报**：把默认分支 merge 进返工分支后，返工基线还停在旧位置，别的模块合入的文件被算成越界。
所以这次修的是 merge（以及返工分几个 PR 合并、中间夹着别的模块的情况，见假设 8），rebase 补回归锁住现状。

## Assumptions

1. **「正在返工」与「返工开始」怎么认**（Q1，推荐 A）：
   - 模块 todo 在某个提交上全部勾完（没有未勾选项；正式延期不算未勾选，同阶段判定），之后又出现了未勾选项，就是在返工。
   - 返工开始 = 最近一次「全部勾完」之后，第一个让 todo 重新出现未勾选项的提交；基线取它的父提交。还没提交（只在工作区加了任务）时，基线取 HEAD。
   - 从没全部勾完过的模块（第一次开工）：基线照旧是 `default_base`。
   - 只看 `tasks/<id>/todo.md` 的提交历史，读最近 200 个提交；读不到 git、todo 没有历史时退回 `default_base`（与现在一致，不会更松）。
2. **哪些地方用新基线**：问「这一轮改了什么」的五处——阶段提示的越界检查（`scope_overreach`）、T4 路径检查（`t4_hits`）、`module_scope.py check` 命令的默认基线、Codex 最终验收的审查范围起点（`acceptance_step`）与它的越界判定（`review_mark._outside`）。
   新函数 `module_scope.scope_base(root, module)` 统一给出，五处都改调它。
3. **哪些地方不改**：问「模块最初开工前是什么样」的两处保持原基线——`review_mark._merge_at_base`（开工前合并是否就是自动的，防止补丁靠改配置给自己放宽档位）与 `module_stage.module_baseline`（技术方案「碰了老文件」的判定）。
4. **提示写明基线**：返工时越界一行写明「从返工开始的提交 `<sha 前 12 位>` 算起」，让用户知道比的是哪一段；第一次开工的模块提示文字不变。
5. **返工自己越界照样报**：返工开始之后本模块改了边界外的文件，照现在的规则报出、停在中途 gate。
6. **规则与文档**：共享检查点规则「返工与小模块」一条补一句「返工时越界检查从返工开始的提交算起」；CHANGELOG「未发布」加一条；版本 0.96.1 → 0.96.2（两份 plugin.json、两份 README 的 `--ref`）。
7. **不做**：改并行边界、预先声明、T4 路径的判定规则；改返工写法（rework-in-place）；改 `/map --json` 的字段；改 autopilot、module-crew。
8. **返工分支同步过默认分支时**（返工，Q2 A）：
   - 返工时，再算一个「HEAD 与默认分支的 merge-base」。它比返工基线新（返工基线是它的祖先、两者不同），而且当前分支不是默认分支的本地分支，就改用它当基线；否则照旧用返工基线。
   - 效果：只比较还没进默认分支的改动。merge 进来的别的模块的提交都在默认分支上，不再算；返工分几个 PR 合并时，已经合进默认分支的那几段也不再算（它们合并前已过越界检查和验收）。
   - 默认分支沿用 `verification.default_branch`：`refs/remotes/origin/HEAD` 指向的分支，读不到用本地 `main`，再读不到就不做这一步（照旧）。
   - 「当前分支不是默认分支」这一条，是为了直接在默认分支上返工时不把已提交的返工改动漏掉（远端跟踪分支停在返工中途时也一样）；这种情况照旧用返工基线。从默认分支新开的续做分支还没提交时，merge-base 就是 HEAD，照样扣除，只比较工作区（2026-11-26 Plan 第二轮审查后修订，用户「按改法改，批准」）。
   - 只会收窄、不会放宽：新基线一定是返工基线的后代，被排除的只有已经在默认分支上的提交。远端跟踪分支没 fetch 时，merge-base 偏旧，最坏退回现在的结果（误报），不会漏报。
   - 第一次开工的模块不变（Q3）。
9. **提示写明基线**（返工）：用了 merge-base 时，越界一行的返工说明改为「；返工：从提交 `<12>` 起算（已扣除默认分支上的提交）」；没用时文字不变（假设 4）。
10. **版本**（返工）：与同批的「删除退役接口」一起发 0.97.0（删接口按次版本号升）；本模块把两份 plugin.json、两份 README 的 `--ref` 改为 0.97.0，CHANGELOG「未发布」加一条。

## Contract

- **C1** `hooks/module_scope.py`：新增 `scope_base(root, module)`（假设 1）；`check` 命令不给 `--base` 时用它。
- **C2** `hooks/module_stage.py`：`scope_overreach`、`t4_hits`、`acceptance_step` 改用 `scope_base`；越界一行在返工时写明基线（假设 2、4）。
- **C3** `hooks/review_mark.py`：`_outside` 改用 `scope_base`，`_merge_at_base` 不变（假设 2、3）。
- **C4** `references/workflow-checkpoints.md`、CHANGELOG、版本号（假设 6）。

## Acceptance criteria

- **AC1** 第一次开工的模块：越界检查的基线与结果和现在完全一样（现有 takeover-scope-check、plan-auto-approve 的回归全绿）。
- **AC2** 已完成的模块之后有别的模块合入、再返工：只改边界内文件时不报越界；返工里改了边界外的文件照样报出该文件，且不报别的模块的文件。
- **AC3** 返工只在工作区（还没提交）时基线取 HEAD；返工提交之后基线取返工第一个提交的父提交；返工两次时取最近一次。
- **AC4** 正式延期不算未勾选：只剩正式延期的 todo 视为全部勾完。
- **AC5** git 读不到、todo 没有历史时退回原基线，不报「无基线」以外的新错误。
- **AC6** `_merge_at_base` 与技术方案「碰了老文件」的判定仍用原基线（各有一例）。
- **AC7** 返工时越界一行写明返工开始的提交；第一次开工的模块提示文字逐字不变。
- **AC8** 本机 `validate.sh`、phase-guard、verify-artifacts 全绿；合并前头提交的 `CI required` 通过。
- **AC9**（返工）复现 11-26 的情形：已完成的模块在分支上返工，期间别的模块合进默认分支，再把默认分支 merge 进返工分支——只改边界内文件时不报越界，返工自己改了边界外的文件照样报，且不报别的模块的文件。
- **AC10**（返工）同一情形改用 rebase：结果与现在一样（不报别人的文件，返工越界照报），锁住现状。
- **AC11**（返工）返工分两个 PR：第一段已合进默认分支，之后别的模块合入，再从默认分支开新分支续做——只比较第二段；直接在默认分支上返工、默认分支读不到时，结果与 0.96.2 一样。
- **AC12**（返工）第一次开工的模块（含 merge 过默认分支的）越界结果与 0.96.2 逐字相同；用了 merge-base 时越界一行写明「已扣除默认分支上的提交」。

## Boundaries

- **会做**：C1～C4 及正反回归。
- **先问再做**：超出假设 1～7 的改动；并行边界外的文件；合并；发版。
- **不做**：假设 7 列出的事。

## 并行边界

- 独占：`spec/rework-scope-baseline.md`、`tasks/rework-scope-baseline/`、`plugins/spec-guard/hooks/module_scope.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/test_module_scope.py`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/references/workflow-checkpoints.md`、`CHANGELOG.md`、`README.md`、`README.en.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、`spec/CAPABILITY-MAP.md`
- 公共：无

## Open questions

- **Q1 「返工开始」怎么认？**（2026-11-26 用户选 A）
  - A（推荐）：从 todo 历史机械算出——最近一次全部勾完之后、第一个让 todo 重新出现未勾选项的提交，基线取它的父提交（假设 1）。不用多写任何东西；返工时追加任务本来就要改 todo。
    代价：如果有人在同一个提交里既合进了别的模块的改动、又追加了返工任务，那个提交里别的模块的文件仍会算进来（极少见，比现在好得多）。
  - B：写一行显式的返工标记（如 `<!-- spec-guard: rework from <sha> -->`），从标记写的提交算起。代价：多一条要记得写的规矩，忘了写就退回现在的误报；返工规则与 add-module 的提示都要改。
  - C：以最近一次「全部勾完」的提交为基线。代价：全部勾完之后、返工开始之前合进来的别的模块的改动仍会误报（#505 那次 #501～#504 都在这一段里），只解决了一部分。
- **Q2 返工分支同步过默认分支时，怎么排除别人的改动？**（返工，2026-11-26 用户选 A）
  - A（推荐）：取 HEAD 与默认分支的 merge-base，比返工基线新、又不等于 HEAD 时用它（假设 8）。一行 git 命令，只会收窄；顺带解决「返工分几个 PR」。
    代价：没 fetch 时 origin 偏旧，退回现在的误报；直接在默认分支上返工、中间又有别的模块提交，仍会误报（这种做法本仓不用）。
  - B：按补丁内容判断：逐个文件看改动是否来自 merge 进来的提交（`git log --first-parent` 只取返工分支自己的提交）。代价：要处理冲突解决时写在 merge 提交里的改动，规则复杂，测试多一倍。
- **Q3 第一次开工的模块要不要一起改？**（返工，2026-11-26 用户选 A）
  - A（推荐）：不改。这次的需求只说返工；第一次开工 merge 过默认分支而误报，至今没碰到过。
  - B：一起改。代价：动到 AC1「第一次开工完全不变」的承诺，回归面变大。

## 文档建议

共享检查点规则「返工与小模块」一条补一句即可（C4）；`docs/commands.md` 讲 `module_scope.py check` 的地方没有写基线细节，不用改。项目没有文档基线。
