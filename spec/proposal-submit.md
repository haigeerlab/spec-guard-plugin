# Spec: proposal-submit

## Objective

Proposal 流程精简为四步（提交、接受、晋级、收尾）的第三个、也是最后一个模块：**提交时由命令补全并校验
Proposal 草稿**，并把使用文档改写为四步。

现在写 Proposal 全靠手工按格式规范：基线表里远端 main 的提交、Goal digest、Build order 与每个模块的行摘要要用
`hooks/spec-digest.py` 逐个算；首行标记里的 revision 要把自身置零后再算整篇 SHA-256；开 Issue 时正文要放同一行
标记并打两个标签。任何一处算错，评审时就是 `invalid`。文字部分（Summary、Integration intent、Change、Tracker
contract）本来就由人或 agent 写，命令不接管。

本模块只做机器该做的部分：agent 照格式直接写 Markdown 草稿，命令从远端默认分支的固定快照算出基线表与
revision 填回草稿，用现有解析与校验把关，并给出开 Issue 的现成命令。接受（`proposal-label-acceptance`，
v0.32.0）与晋级（`proposal-add-module-promotion`，v0.33.0）已完成；本模块完成后四步流程闭合。

登记：2026-09-29 与前两个模块一同经 `/spec-guard:add-module` 插入能力图。2026-09-30 用户评审时认为
首版（由 13 键 JSON 生成整篇文档）过度设计，改为本版"补全草稿 + 校验"。

## Assumptions

用户已于 2026-09-30 确认：

1. 新增 `/spec-guard:proposal-submit`（Codex `spec-guard-ops` 同步入口），背后是新 hook
   `hooks/proposal_submit.py`，输入是一个 Markdown 草稿：`--draft spec/proposals/<id>.md`。
2. 草稿由 agent 按 `references/proposal-contract.md` 的 v2 语法写好标题、v2 标记（id 正确，revision 可为 64 个 `0`）、
   Summary、Integration intent、Change、Tracker contract；`## Capability map baseline` 一节可以省略或留占位，
   命令会整节替换。
3. 命令从远端默认分支的固定快照（`--remote`，默认 `origin`，复用 `proposal_publication.fixed_snapshot`）生成基线
   一节（Remote、Default branch、Commit、Capability map、Goal digest、Build order 与 Module digests，摘要只用
   `spec-digest.py` 的 `compute`），再用 `proposal_contract.compute_revision` 算出 revision 写回标记。
   本地能力图不参与。
4. 校验：补全后的文本必须通过 `parse_proposal` 与对照基线能力图的 `validate_proposal`；草稿路径必须是
   `spec/proposals/<id>.md`（id 取自标记）；远端池中**另一个文件**声明了同一 id → 拒绝（重复 id 会使整个池
   失效）；远端同一路径已有该 Proposal → 视为修订，允许并在输出中提示"将替换已发布版本"。池不可用时报错，
   不跳过检查。锚点在并行段中不在此重复检查（晋级时 `add-module --proposal` 会拒绝）。
5. 先预览后确认：默认只打印补全前后的差异与新 revision，不写文件；`--confirm` 才原子写回草稿这一个文件。
   草稿修改后重跑即重新计算 revision，因此不需要单独的 revision 重算命令；文档中手工计算 revision 的片段删除。
6. 插件不做远端操作：发布 = 用户通过 PR 把该文件合进默认分支；命令最后输出开 Issue 的现成命令（按
   `--platform github|gitlab`，正文首行为完整标记，标签 `proposal` 与 `proposal-stage:published`），并附标签不存在
   时的创建命令；这些命令由用户或 agent 确认后执行。
7. 四步文档完整改写：`docs/workflow.md` 的 Proposal 一节改为 提交（写草稿 → `proposal-submit` → 合进 main → 开
   Issue）、接受（评审 → 标签改 accepted）、晋级（`add-module --proposal`）、收尾（证明 → 标签改 promoted）；
   README 与 `docs/concepts.md` 同步；`references/proposal-contract.md` 补一份可直接复制的草稿模板；
   `docs/release-process.md` 删除快进 `integration/mainline` 的步骤（分支本身与其保护规则不在本模块范围）。
8. 三个 task：补全与校验 hook 及测试 → 命令与 Codex 入口 → 四步文档、发版流程与 CHANGELOG。

## Contract

### S1 补全与校验（`hooks/proposal_submit.py`）

- CLI：`--project`（默认 `.`）、`--draft <path>`（必填，相对 `--project`）、`--remote`（默认 `origin`）、
  `--platform {github,gitlab}`（必填，只影响输出的 Issue 命令）、`--confirm`。
- 步骤：
  1. 读取草稿；找到唯一的 v2 标记（沿用 `proposal_contract.V2_MARKER` 语法；revision 任意 64 位十六进制），取出 id；
     草稿路径不是 `spec/proposals/<id>.md` → 拒绝；
  2. 读取远端固定快照；生成基线一节并替换草稿中的 `## Capability map baseline` 整节（到下一个 `## ` 为止）；
     没有该节时插在 `## Change` 之前；
  3. 以 64 个 `0` 暂置 revision，用 `compute_revision` 算出并写回标记，得到最终文本；
  4. 对最终文本运行 `parse_proposal` 与 `validate_proposal`（对照快照中的能力图）；
  5. 读 `read_published_pool`：池不可用 → 报错；另一个文件声明同一 id → 拒绝；同一路径已发布 → 标注为修订。
- 输出：预览打印草稿与最终文本的 unified diff、revision、是否为修订，以及 S2 的下一步；`--confirm` 在全部检查通过
  后原子写回草稿文件（保留原文件权限），不改其他任何文件。
- 只依赖 bash／git／python3；保留 `from __future__ import annotations`；除 `--confirm` 写回草稿外只读；
  不复制摘要、revision、解析或校验算法。

### S2 下一步输出

- 预览与写回成功后都打印：
  1. 把草稿通过 PR 合进默认分支（发布）；
  2. 合并后开 Issue 的现成命令（按 `--platform`），标题取自文档标题，正文首行为完整标记，标签 `proposal`、
     `proposal-stage:published`；修订时改为"在原 Issue 更新正文中的标记"的提示；
  3. 标签不存在时的创建命令；
  4. 之后用 `/spec-guard:proposal-review` 评审，人工改标签为 `proposal-stage:accepted` 即为接受。
- 命令本身不执行其中任何一条。

### S3 拒绝条件（均不写文件，退出非零，给出原因）

- 草稿不存在或无法读取；没有或有多个 v2 标记；路径与 id 不符；
- 远端不可达、默认分支或能力图读取失败、池不可用；
- `parse_proposal`／`validate_proposal` 失败（缺节、字段不合规、模块已在图中、依赖缺失、锚点不存在或排在依赖之前、
  Tracker contract 与标记不符）；
- 远端另一个文件声明了同一 id。

### S4 入口与文档

- `commands/proposal-submit.md`（Claude）与 `skills/spec-guard-ops/SKILL.md`（Codex）；
  `scripts/check-command-parity.py`、`evals/test-codex-command-roots.sh` 通过（新命令加入命令根清单）。
- `docs/workflow.md` Proposal 一节改写为四步；删除手工计算 revision 的片段；README、`docs/concepts.md` 同步；
  `references/proposal-contract.md` 补草稿模板并说明基线与 revision 由命令填写。
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
  - 预览：省略基线一节、revision 为全 `0` 的草稿 → 输出的最终文本通过 `parse_proposal`；基线 Commit 为远端默认分支
    提交，摘要与 `compute` 一致；revision 与 `compute_revision` 一致；草稿文件不变；输出含 Issue 命令
    （github 与 gitlab 各一次）；
  - 带旧占位基线一节的草稿 → 整节被替换，其余内容逐字不变；
  - `--confirm`：只改草稿文件，内容与预览的最终文本相同；再次运行预览无差异（幂等）；
  - 修订：远端同一路径已发布旧 revision → 允许，输出标注为修订；
  - 端到端：`--confirm` → 提交并推到临时远端默认分支 → `read_published(<id>)` 为 `published`，且在池中；
  - 反例（不写文件、非零）：草稿不存在；没有／多个标记；路径与 id 不符；缺少必需节或字段；模块已在图中；依赖不存在；
    锚点不存在；锚点排在依赖之前；远端另一个文件声明同一 id；远端不可达。
- `validate.sh` 加入新测试；两种 Python（默认 `python3` 3.10 与 `PATH=/usr/bin:/bin` 下的 3.9）下三条最小验证与
  上述测试都通过。

## Boundaries

- Always：先红后绿；除 `--confirm` 写回草稿外只读；摘要只用 `spec-digest.py`、revision 只用
  `compute_revision`、解析与校验只用 `proposal_contract`；草稿中基线一节以外的内容逐字保留。
- Ask first：执行 `gh`／`glab` 写操作；创建分支或提交；支持 v1 或 new-module 以外的变更类型；删除
  `integration/mainline` 分支或改其保护规则。
- Never：改写草稿中基线一节与标记 revision 以外的任何文字；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目
  的名称、模块或编号。

## Success criteria

- 按模板写的草稿经 `proposal-submit --confirm` 补全、合进远端默认分支后，`read_published` 为 `published`，可直接
  进入评审（端到端测试覆盖）；草稿修改后重跑即得到新的正确 revision。
- S3 列出的每种情况都拒绝且不写文件；同一路径的修订被允许并标注。
- `docs/workflow.md` 的 Proposal 一节是四步流程，不再含手工计算 revision 的片段；发版流程不再要求快进
  `integration/mainline`。
- 三条最小验证、`check-command-parity.py` 与 Codex 命令根测试在两种 Python 下都通过。

## Open questions

- 无（第 4 条"同一路径视为修订"已于 2026-09-30 经用户确认）。
