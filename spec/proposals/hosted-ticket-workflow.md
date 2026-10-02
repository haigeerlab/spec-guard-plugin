# Proposal: 按需处理 GitHub/GitLab 日常缺陷事项
<!-- spec-guard-proposal:v2 id=hosted-ticket-workflow revision=sha256:153aeed18a31e3200b92d869b69f87727a1274acc44cbc01c83ea374fdcdad7f -->

## Summary

当前项目审查可以收束发现并交给 Local 事项账本，但选择 GitHub/GitLab 普通 Issue 时只会留下待外部交接清单。增加一个独立的按需托管事项能力：明确目标后查重、创建或复用 Issue、读回身份、记录修复与验证，并在 PR/MR 交付后逐项核对关闭条件。Local 继续使用既有 Epiq 入口；代码托管位置不决定事项目标。三者共享用户可理解的处理语义，不恢复已退役的远端 tracker bridge。设计与精简审查见 `docs/research/2026-10-02-hosted-ticket-workflow-design.md`。

## Integration intent

| Field | Value |
| --- | --- |
| Problem | 审查已确认的缺陷在 GitHub/GitLab 事项目标下无法由 Spec Guard 原生入账、读回和交付对账，反复“继续”只能停在外部清单；旧 bridge 已退役，不能用旧状态推断工作流。 |
| In scope | 每批审查或直接事项明确选择 Local/GitHub/GitLab 目标；GitHub/GitLab 普通 Issue 的完整查重、精确预览、授权创建、读回、讨论留痕与交付后逐项关闭对账；不确定写入用稳定标记和最小私有意图恢复。 |
| Out of scope | 项目级 Tracker 模式配置、旧 bridge 的投影/取任务/工作树绑定、自动迁移、双向同步、常驻合并监听、替代 Local Epiq、修改 Proposal Issue 或阶段 hook。 |
| Safety boundaries | 不凭 Git remote 或旧 `.agent/state.json` 选托管目标；只读审查不写 Issue；外部发布前展示目标、可见性与脱敏后的精确内容并取得授权；分页不完整、写入结果未知或标记冲突时不盲建第二条；PR/MR 合并不自动等于事项已关闭。 |
| Initial dependency assumptions | 依赖 `audit-handoff` 的发现项与交接语义；现有 Local 移交的 GitHub/GitLab 传输代码可作安全校验参考，但不得引入 Epiq 运行时依赖，也不调用移交发布或其映射日志。 |
| Acceptance intent | Local 现有流程无回归；GitHub/GitLab 各能对已确认缺陷查重、创建并读回稳定身份、记录验证与安全关闭；失败/重复/权限/分页/部分合并/平台自动关闭场景不虚报成功或重复创建；受控真实目标与双宿主入口分别验证，退役 bridge 与 Proposal 只读回归通过。 |

## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | origin |
| Default branch | main |
| Commit | 334a722bf96c4ed4e103620844dcee945aacedb2 |
| Capability map | spec/CAPABILITY-MAP.md |
| Goal digest | 03cd446c69f5 |
| Build order | proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-promotion-proof → collaboration-messaging → collaboration-safe-defaults → local-ticket-ledger → ledger-dependency-lock → local-convention → phase-and-verification → module-insert → capability-history → documentation-baseline → documentation-impact → documentation-verification → audit-remediation → done-stage-split → module-interrupt → plan-without-todo → proposal-pool-isolation → proposal-label-acceptance → proposal-add-module-promotion → proposal-submit → promotion-proof-diagnostics → insert-existing-spec → ledger-worktree-owner → done-unmerged-hint → git-fixture-template → local-ticket-portability → retired-module-separation → audit-handoff |

### Module digests

| Module id | Row digest |
| --- | --- |
| proposal-contract | f84b24340ec2 |
| proposal-publication | e563ad8b3b2b |
| proposal-tracker-read | 7e155de3579e |
| proposal-review | f8e8cdcfb46b |
| proposal-promotion-proof | 6d0cdfcf3656 |
| collaboration-messaging | 2a091b441012 |
| collaboration-safe-defaults | fa11d17d3934 |
| local-ticket-ledger | 75ed35684de9 |
| ledger-dependency-lock | bc3f8bbc3b88 |
| local-convention | bd5ffdd20fdf |
| phase-and-verification | 299bdf8b6c4f |
| module-insert | 4cc89d8f78a4 |
| capability-history | 83a5c722e8ac |
| documentation-baseline | 80dbe13f6626 |
| documentation-impact | 866e51ab31da |
| documentation-verification | 8cdc2b63fb9b |
| audit-remediation | 256eb0614aee |
| done-stage-split | d67afc026e5b |
| module-interrupt | 3e3e44278a97 |
| plan-without-todo | 21280242c951 |
| proposal-pool-isolation | 32cee16b8f9d |
| proposal-label-acceptance | 53184b625ccc |
| proposal-add-module-promotion | 97861b18bdf8 |
| proposal-submit | 10b6be5202b3 |
| promotion-proof-diagnostics | 20ab47b3f8e0 |
| insert-existing-spec | 4cdf90f9133d |
| ledger-worktree-owner | 49f7ed5e6610 |
| done-unmerged-hint | 062ea6636717 |
| git-fixture-template | db1c3f2cc74a |
| local-ticket-portability | cdfd994a5018 |
| retired-module-separation | 67deaf21283a |
| audit-handoff | 73d62ca69073 |

## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | hosted-ticket-workflow |
| Responsibility | 按需把已确认缺陷受理到明确选择的 GitHub/GitLab 普通 Issue，并在代码交付后逐项读回与收尾，不恢复旧 tracker bridge。 |
| Depends on | audit-handoff |
| Build-order anchor | end |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | hosted-ticket-workflow |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
