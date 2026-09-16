# Plan: Proposal v2 mainline review and guarded promotion

## Overview

将现有 read-only Proposal lifecycle 升级为 revision-bound、mainline-authorized 的流程。实现仍保持默认只读：标签、Issue、分支、能力图和 acceptance attestation 的写入均由显式受治理的人类流程完成，插件只验证并拒绝错误顺序。

Spec: spec/proposal-mainline-review.md

## Architecture decisions

- Proposal v2 的 SHA-256 revision digest 绑定文档内容；同一 proposal id 的内容修订不能复用旧 Issue marker、旧 accepted 标签或旧 acceptance evidence。
- Issue stage 是唯一可变远端阶段事实；远端默认分支上的 acceptance attestation 是不可变、受保护的 accept 授权证据，而非第二状态机。
- 主链上下文验证仓库、policy、branch、upstream、workflow 和 commit 拓扑，但不把它误表述为人类身份认证。
- Candidate discovery 与 preflight 均使用一次固定远端 bare snapshot；不完整、移动或超限的数据一律 fail closed。
- Promotion proof 对 first-parent diff 使用最小 allowlist：只允许能力图、Proposal module Spec、Proposal module Plan 和必要 acceptance evidence，并要求 map 只插入该 Proposal 的一行。

## Implementation slices

### Slice 1: Proposal v2 revision contract and stage extension

**Acceptance criteria:**

- proposal-contract 同时解析 v1 与严格 v2；v2 验证 canonical revision digest、结构化 intent/safety fields 和完整 revision marker。
- tracker validation 接受 needs-revision 与 deferred 阶段，并以完整 revision marker 匹配 Issue。
- v1 保持可读，但不能产生新的 acceptance 或 promotion eligibility。

**Verification:** Contract regressions覆盖 digest mutation、marker/Issue revision mismatch、v1 compatibility、每个新阶段与无写入断言。

**Likely files:** spec/proposal-contract.md, plugins/spec-guard/hooks/proposal_contract.py, plugins/spec-guard/hooks/test_proposal_contract.py, plugins/spec-guard/references/proposal-contract.md.

**Dependencies:** None.

### Slice 2: Fixed-snapshot candidate pool and revision-aware tracker facts

**Acceptance criteria:**

- publication 在单一 remote-default snapshot 中安全枚举、排序和验证 Proposal pool，不返回部分列表。
- tracker reader 对 v2 marker 维持完整分页、唯一性和只读 transport；候选过限、分页/快照不完整均不伪装为完整候选。

**Verification:** Local bare remote 与 linked-worktree fixtures 证明未合并 Proposal/代码不可发现；分页、上限、tip 移动和 revision mismatch 分别 fail closed。

**Likely files:** spec/proposal-publication.md, plugins/spec-guard/hooks/proposal_publication.py, plugins/spec-guard/hooks/test_proposal_publication.py, plugins/spec-guard/hooks/test_proposal_tracker_read.py, spec/proposal-tracker-read.md.

**Dependencies:** Slice 1.

### Slice 3: Separate remote fact review from authorization

**Acceptance criteria:**

- proposal-review 输出 revision-aware freshness facts，保留既有无关模块不造成假 stale 的规则。
- accepted Issue label 本身不成为 promotion authorization；缺 v2 revision、缺 attestation 或 map drift 都不能形成 accepted。

**Verification:** In-memory fixtures覆盖旧 accepted 标签对应新 revision、anchor/dependency drift、无关新增与 Issue/Git 非原子读取。

**Likely files:** spec/proposal-review.md, plugins/spec-guard/hooks/proposal_review.py, plugins/spec-guard/hooks/test_proposal_review.py, plugins/spec-guard/references/proposal-review.md.

**Dependencies:** Slices 1-2.

### Slice 4: Mainline policy, local observation and decision evaluation

**Acceptance criteria:**

- 新模块只在有效 policy/mainline context/explicit boundary 下发现候选并输出主链人工决策。
- observation 使用有限 schema；硬冲突确定为 needs-revision；accept 必须显式输入且不写 tracker。
- acceptance attestation 的 revision、review commit、policy digest 与 authority id 必须完整匹配。

**Verification:** Fixtures覆盖普通支路、伪造同名 branch、detached HEAD、错 upstream、非祖先 commit、无效 observation、v1 Proposal、错误 attestation 和 no-write paths。

**Likely files:** spec/proposal-mainline-review.md, plugins/spec-guard/hooks/proposal_mainline_review.py, plugins/spec-guard/hooks/test_proposal_mainline_review.py, plugins/spec-guard/references/proposal-mainline-review.md.

**Dependencies:** Slice 3.

### Checkpoint: Acceptance cannot be self-issued

- 普通支路只能看见 published facts，不能得到 accepted-candidate 或 accepted。
- 主链 accept 不会修改 Issue、标签、能力图或分支。
- accepted 同时绑定 Proposal revision、Issue stage、attestation 和固定远端事实。

### Slice 5: Fresh promotion preflight and strict proof

**Acceptance criteria:**

- preflight 固定最新 remote main，验证 accepted evidence 后输出唯一 promotion base commit。
- proof 验证 first-parent map diff 只新增声明 module，存在对应 Spec/Plan，且没有夹带 map/module/文件变更。

**Verification:** Remote fixtures覆盖 main 在接受后漂移、错误 base、缺 Spec/Plan、第二 module、既有 map 行变更、错 anchor、额外文件和成功 merge。

**Likely files:** spec/proposal-promotion-proof.md, plugins/spec-guard/hooks/proposal_promotion_proof.py, plugins/spec-guard/hooks/test_proposal_promotion_proof.py, plugins/spec-guard/references/proposal-promotion-proof.md.

**Dependencies:** Slice 4.

### Slice 6: Boundary guidance, public references and E2E specification

**Acceptance criteria:**

- 非主链边界继续只得到非阻断通用提醒；有效主链上下文才展示 candidate/mainline-review/preflight 入口。
- Reference、design 和 E2E acceptance 文档不再描述独立 reviewer 可以接受 Proposal，也不引入已退役命令。

**Verification:** Boundary tests覆盖有/无/无效主链上下文；source audit、focused suites与 retirement regression 均通过。

**Likely files:** spec/proposal-boundary-guidance.md, plugins/spec-guard/hooks/proposal_boundary_guidance.py, plugins/spec-guard/hooks/test_proposal_boundary_guidance.py, plugins/spec-guard/references/proposal-boundary-guidance.md, docs/acceptance/v0.15-proposal-github-e2e-spec.md.

**Dependencies:** Slices 4-5.

### Slice 7: Validation wiring and end-to-end regression

**Acceptance criteria:**

- 所有 focused suites接入 repository validation；完整 v2 journey 有本地、无真实外部写入的覆盖。
- 旧 bridge/state/static-surface negative regression仍证明不依赖退役流程。

**Verification:** /bin/bash scripts/validate.sh; all Proposal focused suites; /bin/bash plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh; /bin/bash evals/codex-plugin-smoke.sh --selftest.

**Likely files:** scripts/validate.sh, docs/maintainer-workflow.md, relevant focused test files.

**Dependencies:** Slices 1-6.

## Dependency graph

~~~text
v2 revision contract
        ↓
fixed pool snapshot + verified Issue facts
        ↓
revision-aware remote fact review
        ↓
mainline context + acceptance evidence
        ↓
fresh promotion preflight + strict proof
        ↓
boundary guidance, documentation and full validation
~~~

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| An accepted label is reused for edited Proposal text | Bind every review, Issue match and attestation to v2 revision digest. |
| Branch naming is mistaken for authorization | Require policy topology plus externally protected attestation; document the authentication boundary honestly. |
| Candidate discovery omits a Proposal | Fixed snapshot, sorted enumeration and fail-closed limit/pagination behavior. |
| Promotion carries unrelated capability-map work | Compare first-parent map/diff against a strict allowlist and exact insertion relation. |
| Local observations become hidden shared truth | Restrict schema and prohibit paths, snippets and free text in shared outputs. |
| The change revives old tracker orchestration | Retain negative static regression and prohibit bridge/state imports in every Proposal focused suite. |

## Current checkpoint

**Type:** Slices 1--5 complete; user-facing command markdown remains to be wired.

**Reviewable artifacts:** spec/CAPABILITY-MAP.md, spec/proposal-mainline-review.md and this plan.

**Completed:** Slice 1 added revision-bound v2 parsing, strict Integration intent fields,
revision-matched Issue identity, new non-terminal decision stages and v1 read compatibility.
Slice 2 added fixed-snapshot, sorted remote Proposal pool reading without worktree
fallback. It now carries policy and revision-addressed attestation text from that
same snapshot. Slice 3 carries a Proposal revision through remote fact review.
Slice 4 parses the remote policy, derives branch/upstream/topology from only the
current worktree, and adds a deliberately transport-free candidate/decision kernel:
ordinary branch context is blocked, hard structured conflicts override accept, and
no result writes remote state. Slice 5 rejects v1 and label-only acceptance, requires
attested mainline acceptance, module Spec/Plan and a strict promotion-diff allowlist.
It also has a fresh read-only preflight that returns a base commit only after the
current pool, Issue and attestation agree.

**Next step:** Add explicit user-facing read-only command adapters. Keep policy,
attestation and tracker reads joined to one snapshot where their consistency is
required; do not add a tracker writer.

**Stop condition:** Any request to permit automatic tracker writes, accept an unprotected attestation, add a second integration authority, read other worktrees, relax strict promotion diff rules or reuse the retired bridge requires a new explicit design decision.
