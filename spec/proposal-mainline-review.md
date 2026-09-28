# Spec: proposal-mainline-review

## Objective

将已发布 Proposal 的共享远端事实与主链的有限本地架构观察明确分离。只有经远端默认分支策略验证的单一主链，才能在显式模块边界发现候选、输入人工裁决，并产生可审计但不自动写入 tracker 的主链评审结果。

本模块不读取其他 worktree、未提交源文件或 .agent/state.json；不创建或修改 Proposal、能力图、Issue、标签、任务、PR 或分支；不调用或依赖已退役的 tracker bridge。

## Contract

### Revision-bound shared facts

- 新 Proposal 使用 proposal-contract v2 的完整 identity marker，其中含 proposal id 与 revision digest。Issue 的完整 marker 必须与已发布文档完全相同。
- 所有共享 Proposal、能力图、策略和 acceptance attestation 都只从同一次固定远端默认分支 snapshot 读取。GitHub/GitLab Issue 只提供已核验的唯一阶段事实。
- 已发布 v1 Proposal 仍可被发现和读取，但结果必须标为 legacy-revision-required；不得产生 accepted-candidate、accepted 或 promotion preflight。

### Mainline authority

- 远端默认分支中的 spec/proposal-mainline-policy.json 是唯一 authority policy。它定义 schema version、authority id、remote 名称、唯一 review ref 与 workflow id。
- 调用方只能显式声明 authority id、boundary、current module id、受限 observation 和 decision。当前 branch、upstream、local HEAD 与 remote review commit 由工具读取并验证，不能由调用方文本替代。
- 合法上下文要求：当前 branch 精确匹配 policy review ref；其 upstream 精确匹配 policy remote/ref；local HEAD 包含固定 review commit；current module id 在 review map 中存在。
- Git 元数据不能证明操作者身份。policy 的 review ref 和 acceptance attestation 路径必须由仓库保护规则、CODEOWNERS 或同等外部授权机制保护；本模块只验证可观察的仓库/分支/工作流上下文，绝不伪称认证人类身份。
- 本仓库的 review ref `integration/mainline` 自 2026-09-28 起受 GitHub 分支保护（禁止 force push 与删除），通过快进与 `main` 保持一致：主链评审前、以及每次发布后快进（见 `docs/release-process.md`）。acceptance attestation 路径尚未单独保护。

### Candidate discovery and local observations

- 仅在显式 module-deliver 或 module-advance 且主链上下文有效时，枚举固定 snapshot 中 spec/proposals/ 下的 Proposal。候选按 proposal id 排序；候选数超过固定上限、snapshot 变化、解析失败或任一必需分页无法证实完整性时，返回 blocked 或 unknown，不能返回部分完整列表。
- 可评审候选必须同时是 v2 published Publication、verified TrackerRead，且阶段为 proposal-stage:published 或 proposal-stage:in-review。发现不自动产生接受结论。
- local observation 是本地主链评审输入，不是共享事实。每条只能含固定 kind（package-boundary-conflict、public-contract-conflict、anchor-conflict、unmerged-public-contract-change、dependency-suggestion 或 anchor-suggestion）和关联 module ids；module id 只能是当前模块、Proposal 自身、其声明的依赖或锚点。不接受代码片段、路径、Issue/评论正文、token、自由文本或其他 worktree 身份。
- 硬冲突 kind（package-boundary-conflict、public-contract-conflict、anchor-conflict）强制输出 needs-revision。其他架构或优先级判断须由显式 decision 决定，绝不从发布状态或边界自动推断。

### Human decision and acceptance attestation

- mainline review 的合法 decision 是 accept、needs-revision、defer 或 reject。结果分别为 accepted-candidate、needs-revision、deferred 或 rejected-candidate；所有结果保留 review commit、Proposal revision、Issue identity、policy authority 与本地观察的稳定 reason codes。
- accepted-candidate 不是 Issue 阶段，也不是 promotion authorization。它只表示有效主链上下文中有一次明确的人工 accept 输入。
- 只有受保护流程人工写入 spec/proposal-acceptances/<proposal-id>-<revision>.json 后，才存在 acceptance attestation。它是不可变授权证据，记录 proposal id、revision、review commit、policy digest、authority id 和 accept；不存储本地观察正文，也不是第二个可变阶段状态。
- Issue 的 proposal-stage:accepted 仍由另一个明确、可审计的人工操作写入。promotion preflight 必须同时验证最新 Issue accepted 标签和匹配 attestation。

## Result model

安全结果只能包含 state、proposal id、revision、review commit、Issue platform/target/id/stage、authority id、当前模块、稳定 observation/reason codes 和诊断码。它不包含能力图、Proposal、Issue、评论、远端 URL、临时路径、代码、自由文本或原始异常。

允许状态：

- candidate-list、accepted-candidate、accepted、needs-revision、deferred、rejected-candidate；
- stale、legacy-revision-required、blocked、invalid、unknown。

accepted 只能由新鲜远端事实、accepted Issue stage 与匹配 acceptance attestation 共同得出。任何普通支路调用、缺失 policy、分支/上游不匹配、未认证的 revision 或不完整候选池均不得产生 accepted-candidate 或 accepted。

## Commands

~~~text
proposal-boundary --boundary module-deliver|module-advance
proposal-mainline-candidates --authority-id <id> --boundary <boundary>
proposal-mainline-review --proposal-id <id> --decision <decision>
proposal-promotion-preflight --proposal-id <id>
python3 -B plugins/spec-guard/hooks/test_proposal_mainline_review.py
/bin/bash scripts/validate.sh
~~~

这些是未来显式入口。UserPromptSubmit hook 不得自动调用它们或访问网络。

## Testing strategy

- 使用 local bare remote、linked worktree、fixture policy、stubbed tracker transport 与纯结果对象；不访问真实服务，不依赖旧 bridge。
- 覆盖非主链、detached branch、错误 upstream、review commit 非祖先、缺/错 policy、v1 Proposal、v2 revision 变更、过大/不完整候选池和脏 sibling worktree。
- 覆盖 accept 不自动写标签、接受证明与 Issue/revision/authority/review commit 全部匹配才返回 accepted、硬冲突强制 needs-revision，以及 no-write assertions。
- 每一新增 fail-closed 判据都需要正反测试；focused suite 接入 scripts/validate.sh。

## Boundaries

- Always: 固定远端 snapshot；区分 remote facts、local observations 与人工 decisions；要求显式边界、唯一 policy、revision 和 acceptance attestation。
- Ask first: 新增 observation kind、变更 policy schema、接受多主链、缓存候选、变更 candidate 上限、允许写 tracker 或改变授权证据存放位置。
- Never: 从其他 worktree 扫描内容；把 branch 名当人类身份；自动接受、写 Issue 标签、创建 Proposal/能力图/分支/任务，或恢复旧 bridge/state 选择逻辑。

## Success criteria

- 普通 Proposal 作者能发布和读取候选，但不能借由普通 review、同名分支或旧标签得到 accepted-candidate、accepted 或 promotion。
- 主链能在模块边界基于完整远端候选池和受限本地观察给出人工决策，而本地观察绝不成为共享事实。
- 每个 accepted 结论可回指唯一 Proposal revision、远端 review commit、policy authority、acceptance attestation 和唯一 Issue stage。
