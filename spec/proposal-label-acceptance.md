# Spec: proposal-label-acceptance

## Objective

Proposal 流程目前有 9 步，其中"主链裁决 → 人工写验收记录"这一层（主链策略文件、`spec/proposal-acceptances/*.json`、
`--authority-id`／`--boundary`／`--current-module-id`、受保护的 `integration/mainline` 分支、两个 mainline 命令与
`proposal_boundary_guidance`）是使用中摩擦最大的部分：一个消费者项目的主链策略文件失效后，预检只能报
`mainline-policy-invalid`，所有 Proposal 都无法晋级。

用户已于 2026-09-29 批准把流程精简为四步（提交、接受、晋级、收尾），拆成三个模块。本模块是第一个：
**接受只看 Issue 标签与评审新鲜度，删除主链授权层**，并修好删除后会失效的晋级证明。晋级方式
（`add-module --proposal`，模块 `proposal-add-module-promotion`）与提交命令、四步文档（模块 `proposal-submit`）
不在本模块范围。

登记：2026-09-29 按用户决定经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-09-29 确认：

1. **接受** = 已发布的 v2 Proposal + Issue 阶段标签 `proposal-stage:accepted` + 评审新鲜（基线未漂移、模块未在图中、
   依赖齐全、锚点有效）。不再读取主链策略文件与验收记录。v1 Proposal 仍返回 `legacy-revision-required`。
2. **收尾（证明）** 以 Proposal 的**基线提交**为起点，沿远端默认分支的 first-parent 寻找第一个把该模块加进能力图、
   且该行与 Proposal 声明一致的提交；不再要求该提交同时包含 Spec 与 Plan。通过后由人打 `proposal-stage:promoted`。
3. **旧数据保持可读、不再需要**：已有的策略文件与验收记录留在原处，存在时不报错、不参与判断；
   `scripts/check-acceptance-immutable.py` 继续保护已有验收记录。
4. 两个 mainline 命令与 `proposal_boundary_guidance` **直接删除**，不设过渡版本；CHANGELOG 与退役说明写明替代方式。
5. 发版流程中快进 `integration/mainline` 的步骤由模块 `proposal-submit` 移除；分支本身与其保护规则不在本仓库改动范围。
6. `proposal-pool-isolation` 的隔离行为保留；`skippedProposals` 随 mainline 命令从其输出中消失，预检／证明中保留。

本 Spec 提出、用户于 2026-09-29 批准的细节：

7. 晋级之后模块已在当前能力图中，拿当前图做评审必然得到 `proposal-module-already-present`。所以证明的新鲜度
   在**晋级提交的父提交**的能力图上判断（等价于"晋级那一刻的预检"），而不是当前图。
8. 证明对 Issue 阶段接受 `proposal-stage:accepted` **或** `proposal-stage:promoted`：打上 promoted 标签后重跑证明
   仍能得到 `proved`，收尾可重复执行。预检只接受 `accepted`。
9. 证明不再限制晋级提交改动的路径（原先要求恰好是能力图 + Spec + Plan）：以 PR 合并时 first-parent 提交会带上
   PR 的全部改动，只要求能力图中该模块是新增的、且行内容与位置与 Proposal 声明一致，与父提交相比没有其他模块行
   被改动。
10. 证明 JSON 的 `reviewCommit` 保留字段名，值改为晋级提交的父提交（判断新鲜度所用的快照）。其余字段不变。
11. 本模块只把已失效的文档改正确（删掉 mainline 步骤与一次性准备里的策略文件／主链分支）；四步流程的完整改写在
   `proposal-submit`。

## Contract

### C1 接受（`hooks/proposal_promotion_proof.py`）

- `accepted(publication, tracker, platform, target)` 移入本文件（`proposal_mainline_review.py` 删除后唯一使用者），
  去掉 `policy`／`attestation` 参数：
  - v1 或缺 revision → `legacy-revision-required`（不变）；
  - `review()` 结果为 `accepted` → `accepted`；否则原样返回 review 的状态与诊断（不变）。
- `DIAGNOSTIC_CODE` 一并移入。`accepted_from_pool` 删除。

### C2 发布与池（`hooks/proposal_publication.py`）

- 删除 `_attested_review_commit`：`Publication.review_commit` 与池中每个 publication 的 `review_commit` 都是本次
  观察到的远端默认分支提交，`review_map` 是该提交的能力图。
- `PublicationPool` 删除 `policy_text`、`attestation_texts`；`read_published_pool` 不再读取策略文件与验收记录。
  `ATTESTATION_PATH_TEMPLATE` 删除（`check-acceptance-immutable.py` 自有目录常量，不受影响）。
- 解析、基线校验、隔离（`skipped`）、重复 id、池上限等其余行为不变。

### C3 预检

- 池不可用 → `proposal-pool-invalid`／`proposal-pool-unknown`（不变）；Proposal 不在池中 → `absent`／
  `publication-absent`（不变）。
- 删除 `publication.review_map != pool.review_map` 的 `stale` 分支（两者现在恒等）；新鲜度由 `review()` 给出，
  漂移时返回 review 的 `stale` 与其诊断（如 `proposal-baseline-drifted`）。
- 接受 → `ready`，`baseCommit` 为观察到的远端默认分支提交（不变）。其他状态沿用 C1 的结果。

### C4 证明

- 先要求 Issue 阶段为 `accepted` 或 `promoted`（否则 `not-accepted`，诊断沿用 review／tracker 的诊断）。
- 在远端默认分支快照上 `rev-list --first-parent --reverse <baseline>..<observed>`，找第一个能力图含该模块的提交 C，
  其 first-parent 为 P：
  - P 的图已含该模块、或 C 的行内容／依赖／位置与 Proposal 声明不一致（现有 `_matches`）、或 C 与 P 相比有其他
    模块行被改动 → `invalid`；
  - 以 P 的能力图重跑 `review()` 的新鲜度判断（阶段按第 1 条放宽为 accepted/promoted）；不新鲜 → 返回其 `stale`
    与诊断；
  - 否则 `proved`，`reviewCommit` = P，`promotionCommit` = C。
- 基线到当前之间没有任何提交含该模块 → `not-promoted`／`promotion-not-found`（不变）。
- 删除 `_promotion_paths`、`_has_module_artifacts` 的路径与产物要求。

### C5 删除

- `commands/proposal-mainline-candidates.md`、`commands/proposal-mainline-review.md`；
  `skills/spec-guard-ops/SKILL.md` 中对应入口；命令对照与 Codex 命令根测试中的对应项。
- `hooks/proposal_mainline_review.py`、`hooks/test_proposal_mainline_review.py`、
  `hooks/proposal_boundary_guidance.py`、`hooks/test_proposal_boundary_guidance.py`，以及它们在
  `scripts/validate.sh`、`scripts/test-checkers.sh`、`hooks/test-retire-legacy-tracker-bridge.sh` 中的引用。
- `references/proposal-mainline-review.md`、`references/proposal-boundary-guidance.md`；其他参考文档中指向它们的链接。
- 不删除：本仓库的 `spec/proposal-mainline-policy.json` 与 `spec/proposal-acceptances/`（历史证据）、
  `scripts/check-acceptance-immutable.py`、能力图中 `proposal-mainline-review`／`proposal-boundary-guidance` 两行及其
  Spec／Plan（历史）、`docs/acceptance/`、`docs/releases/`、`tasks/` 下的历史记录。

### C6 文档与迁移

- 新增 `docs/retirements/proposal-mainline-review.md`（照 `claude-desktop-mcpb.md` 的结构）：退役了什么、为什么、
  移除的内容、迁移（已接受的 Proposal：确认 Issue 标签为 `accepted` 即可继续预检；已有策略文件与验收记录可保留
  或自行删除，插件不再读取；`integration/mainline` 分支可自行处理）。
- `docs/migrations/proposal-mainline-review-v2.md` 顶部加一行指向该退役说明。
- `docs/workflow.md`：Proposal 表格删掉主链裁决一步，"人工接受"改为只改 Issue 标签；一次性准备删掉策略文件与
  主链分支；命令对照删掉两个 mainline 命令。
- `references/proposal-promotion-proof.md`、`references/proposal-publication.md`、`references/workflow-checkpoints.md`、
  `docs/concepts.md`、`docs/design.md`、`docs/maintainer-workflow.md`、`README.md`：删除或改写对主链裁决、策略、
  验收记录的描述，写明 C3／C4 的新判断。
- `CHANGELOG.md` Unreleased：`### 移除` 与 `### 变更`，含迁移要点。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_proposal_publication.py
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py
python3 -B plugins/spec-guard/hooks/test_proposal_review.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
```

## Project structure

```text
plugins/spec-guard/hooks/proposal_publication.py, test_proposal_publication.py     -> C2
plugins/spec-guard/hooks/proposal_promotion_proof.py, test_proposal_promotion_proof.py -> C1, C3, C4
plugins/spec-guard/commands/, skills/spec-guard-ops/, hooks/*mainline*, *boundary_guidance*,
  scripts/validate.sh, scripts/test-checkers.sh, evals/                           -> C5
docs/, plugins/spec-guard/references/, README.md, CHANGELOG.md                     -> C6
```

## Testing strategy

- 每项先写测试并确认它在当前代码上失败，再修改；沿用现有的临时 Git 仓库、远端与 tracker 夹具，不访问网络。
- `test_proposal_promotion_proof.py`：
  - 预检：Issue 为 accepted、新鲜、**没有**策略文件与验收记录 → `ready`；存在旧策略文件（含无效内容）与验收记录时
    结果相同；阶段为 in-review／promoted → 非 ready；基线漂移 → `stale`／`proposal-baseline-drifted`；v1 →
    `legacy-revision-required`。
  - 证明：晋级提交只改能力图 → `proved`，`reviewCommit` 为父提交；晋级 PR 合并提交同时带 Spec／Plan／其他文件 →
    `proved`；标签已改为 promoted → 仍 `proved`；晋级时顺带改了其他模块行 → `invalid`；行内容或位置与声明不符 →
    `invalid`；晋级前基线已漂移（父提交上不新鲜）→ `stale`；尚未晋级 → `not-promoted`；无验收记录不影响以上结果。
  - 已有 `skippedProposals` 相关断言保留。
- `test_proposal_publication.py`：池与单个读取不再依赖验收记录（有无验收记录时 `review_commit` 都是观察到的提交）；
  隔离相关的五个场景保留。删除仅针对验收记录固定快照的断言时，在提交说明中逐条列出。
- 删除 `test_proposal_mainline_review.py`、`test_proposal_boundary_guidance.py` 整个文件；`validate.sh` 与检查器
  用例同步去掉。
- 两种 Python（默认 `python3` 3.10 与 `PATH=/usr/bin:/bin` 下的 3.9）下三条最小验证与上述测试都通过。

## Boundaries

- Always：先红后绿；hook 只读、只输出宿主 JSON；只依赖 bash／git／python3；保留 `from __future__ import annotations`；
  删除有退役说明与迁移要点。
- Ask first：删除本仓库的策略文件或历史验收记录；改动 `check-acceptance-immutable.py`；新增 Issue 阶段；
  让插件写标签或远端。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号；把删除混进无关文件的改写。

## Success criteria

- 没有策略文件和验收记录的项目，Issue 标签为 accepted 且新鲜时，预检返回 `ready`；晋级后证明返回 `proved`。
- 存在旧策略文件（即使无效）或旧验收记录不影响任何结果。
- 只改能力图的晋级提交与带 Spec／Plan 的 PR 合并提交都能被证明；改动其他模块行或与声明不符的会被拒绝。
- 仓库中不再有 mainline 命令、`proposal_mainline_review.py`、`proposal_boundary_guidance.py` 及其参考文档；
  `check-command-parity.py` 与 `validate.sh` 通过；文档不再要求策略文件、验收记录或主链分支。
- 三条最小验证在两种 Python 下都通过。

## Open questions

- 无（第 7–11 条已于 2026-09-29 经用户批准）。
