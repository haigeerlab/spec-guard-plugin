# Spec: proposal-submit

## Objective

Proposal 流程精简为四步（提交、接受、晋级、收尾）的第三个、也是最后一个模块：**提交由命令生成 Proposal 文档**，
并把使用文档改写为四步。

现在写 Proposal 全靠手工按格式规范：基线表里远端 main 的提交、Goal digest、Build order 与每个模块的行摘要要用
`hooks/spec-digest.py` 逐个算；首行标记里的 revision 要把自身置零后再算整篇 SHA-256；开 Issue 时正文要放同一行
标记并打两个标签。任何一处算错，评审时就是 `invalid`。本模块让 agent 只起草文字字段，其余全部由命令从远端
默认分支的固定快照算出，并在写入前用现有的解析与校验把关。

接受（`proposal-label-acceptance`，v0.32.0）与晋级（`proposal-add-module-promotion`，v0.33.0）已完成；
本模块完成后四步流程闭合。

登记：2026-09-29 与前两个模块一同经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-09-30 确认（按推荐方案）：

1. 新增 `/spec-guard:proposal-submit`（Codex `spec-guard-ops` 同步入口），背后是新 hook `hooks/proposal_submit.py`。
   输入是一个 JSON 文件（`--input <path>`，`-` 表示标准输入），字段由 agent 从对话起草：标题、Summary、
   Integration intent 六项、模块 id、职责、依赖、锚点。
2. 基线从远端默认分支的固定快照计算（`--remote`，默认 `origin`），复用 `proposal_publication.fixed_snapshot`：
   Remote、Default branch、Commit、Goal digest、Build order、各模块行摘要全部自动填入，摘要只用
   `spec-digest.py` 的 `compute`；revision 用 `proposal_contract.compute_revision` 计算。本地能力图不参与。
3. 写入前校验，任一不通过即拒绝且不写：生成的文档经 `parse_proposal` 解析、经 `validate_proposal` 对照基线能力图
   校验（模块 id 未存在、依赖都在图中、锚点不排在依赖之前）；远端池中已有同 id 的 Proposal，或本地已有
   `spec/proposals/<id>.md`；锚点落在 Build order 并行段中（与 add-module 同一规则：插入后无法被证明）。
4. 先预览后确认：默认只打印生成的文档；`--confirm` 才写入 `spec/proposals/<id>.md`，只写这一个文件。
5. 插件不做远端操作：发布 = 用户通过 PR 把该文件合进默认分支；命令最后输出开 Issue 的现成命令
   （GitHub `gh issue create`／GitLab `glab issue create`，正文含标记，标签 `proposal` 与
   `proposal-stage:published`），并附标签不存在时的创建命令；这些命令由用户或 agent 确认后执行。
6. 只生成 v2；文档写完要改，改输入 JSON 后重新生成（本地已有同名文件时会被拒绝，需先由用户删除旧文件）；
   不提供单独的 revision 重算命令，文档中手工计算 revision 的片段删除。
7. 四步文档完整改写：`docs/workflow.md` 的 Proposal 一节改为 提交（生成 → 合进 main → 开 Issue）、
   接受（评审 → 标签改 accepted）、晋级（`add-module --proposal`）、收尾（证明 → 标签改 promoted）；
   README 与 `docs/concepts.md` 同步；`docs/release-process.md` 删除快进 `integration/mainline` 的步骤
   （分支本身与其保护规则不在本模块范围）。
8. 三个 task：生成器 hook 与测试 → 命令与 Codex 入口 → 四步文档、发版流程与 CHANGELOG。

## Contract

### S1 生成器（`hooks/proposal_submit.py`）

- CLI：`--project`（默认 `.`）、`--input <path|->`（必填）、`--remote`（默认 `origin`）、
  `--platform {github,gitlab}`（必填，只影响输出的 Issue 命令）、`--confirm`。
- 输入 JSON（UTF-8 对象，未知键或缺键即报错）：
  `id`、`title`、`summary`、`problem`、`inScope`、`outOfScope`、`safetyBoundaries`、`dependencyAssumptions`、
  `acceptanceIntent`、`moduleId`、`responsibility`、`dependsOn`（字符串数组，可为空）、`anchor`（`end` 或
  `after:<module-id>`）。`id` 须满足 `PROPOSAL_ID`；表格单元内的文字字段须为单行、不含 `|`（否则报错，
  不静默改写）；`summary` 可多行。
- 生成：按 `references/proposal-contract.md` 的 v2 语法输出（标题、标记、Summary、Integration intent、
  Capability map baseline 含 Module digests、Change、Tracker contract），标记先以 64 个 `0` 占位，写入临时文件后
  用 `compute_revision` 计算并替换，得到最终文本。
- 校验（S3 中的全部拒绝条件）通过后：预览打印最终文本与"下一步"；`--confirm` 以原子方式写入
  `spec/proposals/<id>.md`（目录不存在则创建），不改其他任何文件。
- 远端不可达、默认分支读取失败：报错并退出非零，不写文件。
- 只依赖 bash／git／python3；保留 `from __future__ import annotations`；除 `--confirm` 写入的那一个文件外只读。

### S2 下一步输出

- 预览与写入成功后都打印：
  1. 把 `spec/proposals/<id>.md` 通过 PR 合进默认分支（发布）；
  2. 合并后开 Issue 的现成命令（按 `--platform`），标题 `Proposal: <title>`，正文首行为完整标记，
     标签 `proposal`、`proposal-stage:published`；
  3. 标签不存在时的创建命令；
  4. 之后用 `/spec-guard:proposal-review` 评审，人工改标签为 `proposal-stage:accepted` 即为接受。
- 命令本身不执行其中任何一条。

### S3 拒绝条件（均不写文件，退出非零，给出原因）

- 输入 JSON 无效、缺键／多键、字段不合规；
- 远端池中已有同 id 的 Proposal（读 `read_published_pool`；池不可用时报错而不是跳过）；本地已有
  `spec/proposals/<id>.md`；
- `validate_proposal` 失败（模块已在图中、依赖缺失、锚点不存在或排在依赖之前）；
- 锚点模块在 Build order 的并行段中且不是段内最后一个（新模块会被插到整段之后，与 `_matches` 要求不符）。

### S4 入口与文档

- `commands/proposal-submit.md`（Claude）与 `skills/spec-guard-ops/SKILL.md`（Codex）；
  `scripts/check-command-parity.py`、`evals/test-codex-command-roots.sh` 通过（新命令加入命令根清单）。
- `docs/workflow.md` Proposal 一节改写为四步；删除手工计算 revision 的片段；README、`docs/concepts.md` 同步；
  `references/proposal-contract.md` 说明文档由 `proposal-submit` 生成（格式规范保留）。
- `docs/release-process.md` 删除快进 `integration/mainline` 的步骤。
- `CHANGELOG.md` Unreleased：`### 新增`（proposal-submit）与 `### 变更`（四步文档、发版流程）。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_proposal_submit.py
python3 -B plugins/spec-guard/hooks/test_proposal_publication.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
/bin/bash evals/test-codex-command-roots.sh
```

## Project structure

```text
plugins/spec-guard/hooks/proposal_submit.py, test_proposal_submit.py, scripts/validate.sh -> S1–S3
plugins/spec-guard/commands/proposal-submit.md, skills/spec-guard-ops/, evals/            -> S4 入口
docs/, plugins/spec-guard/references/, README.md, CHANGELOG.md                            -> S4 文档
```

## Testing strategy

- 先写测试并确认它在当前代码上失败（新文件不存在即失败），再实现。
- `test_proposal_submit.py`（沿用临时 bare 远端与消费者克隆的夹具方式，不访问网络）：
  - 预览：生成的文本通过 `parse_proposal`；基线 Commit 为远端默认分支提交，摘要与 `compute` 一致；
    revision 与 `compute_revision` 一致；不写任何文件；输出含 Issue 命令（github 与 gitlab 各一次）；
  - `--confirm`：只新增 `spec/proposals/<id>.md`，内容与预览相同；
  - 端到端：`--confirm` → 提交并推到临时远端默认分支 → `read_published(<id>)` 为 `published`，且在池中；
  - 反例（不写文件、非零）：JSON 无效／缺键／多键；表格字段含 `|` 或换行；id 不合规；远端已有同 id；本地已有同名
    文件；模块 id 已在图中；依赖不存在；锚点不存在；锚点排在依赖之前；锚点在并行段中（非段内最后一个）；
    远端不可达。
- `validate.sh` 加入新测试；两种 Python（默认 `python3` 3.10 与 `PATH=/usr/bin:/bin` 下的 3.9）下三条最小验证与
  上述测试都通过。

## Boundaries

- Always：先红后绿；除 `--confirm` 写入的单个文件外只读；摘要只用 `spec-digest.py`、revision 只用
  `compute_revision`、解析与校验只用 `proposal_contract`，不复制算法；输出宿主可读的文本或 JSON。
- Ask first：执行 `gh`／`glab` 写操作；创建分支或提交；支持 v1 或 new-module 以外的变更类型；删除
  `integration/mainline` 分支或改其保护规则。
- Never：静默改写用户输入（例如把 `|` 替换掉）；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或
  编号。

## Success criteria

- 由 JSON 输入生成的 Proposal 经 `--confirm` 写入、合进远端默认分支后，`read_published` 为 `published`，
  可直接进入评审（端到端测试覆盖）。
- S3 列出的每种情况都拒绝且不写文件。
- `docs/workflow.md` 的 Proposal 一节是四步流程，不再含手工计算 revision 的片段；发版流程不再要求快进
  `integration/mainline`。
- 三条最小验证、`check-command-parity.py` 与 Codex 命令根测试在两种 Python 下都通过。

## Open questions

- 无。
