# Spec: align-upstream-rules

<!-- spec-guard: review approved c96c68bbef20 -->

## Objective

上游 agent-skills 只在 Spec、Plan 各审一次，构建中只在「测试改不过或构建坏了没明显修法」「Spec 有歧义或没覆盖的决定」「高风险或
不可逆」时停，Spec、Plan 是活文档。spec-guard 现在的规则在几处比上游严：Spec 批准后一改就要求当场复审；返工补一节就把 Plan 改回
待批准；UI 自验之后还有一个单独的人工兜底 gate；每个 Spec 交审都要写一句「文档建议：无」；verify-artifacts 对缺 AC 编号给提示，
AI 为了消提示会去改已批准的 Spec。用户的原则：不是高危操作就不该找用户授权，AI 有纠错能力，写死了会让它一发现「和事先写的不一样」
就停下来谈授权。

本模块按决定 66 的其余各条放宽这几处，和上游对齐；保留交审摆内容、一次一个模块、最终验收列出改动文件与新增依赖、远端写入须 gate
写明、合并永远由用户、同一目标第二次过不去时停下给选项。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `checkpoint-default-report`、`rules-in-context`、`ui-verify-by-change`、
`doc-suggestion-at-handoff`、`stop-rule-and-ac`、`change-source-record`。需求来自接入协调人转达的用户决定 66 第 1、2、4、5、6 条；
用户在本会话同意拆成两个模块。本模块的 PR 写 0.79.0 的版本号与 CHANGELOG（含 `checkpoint-default-report`）。

## Assumptions

1. **构建中修正已批准的 Spec（第 1 条）**：
   - 已批准范围内的修正（措辞、验收标准澄清、实现细节）直接改，在 Spec 末尾「变更记录」追加一行，最终验收时附上 Spec 的改动差异，
     一次批准同时批准修订后的 Spec（沿用现有「最终验收可以一并复审修订过的 Spec」）。
   - 改范围、改方向或需要新取舍时才当场停下复审。是不是「改范围」由 agent 判断，规则举例说明。
   - 阶段提示：BUILDING 时 Spec 为「批准后已修订」且**还没到**最终验收，建议语从「请用户复审、不要继续构建」改为「范围内的修正
     可以继续，记进变更记录，最终验收时附差异一并批准；改了范围、方向或要新取舍就停下复审」。到了最终验收的建议语不变。
     其他阶段（`NEEDS_PLAN` 等）里 Spec 被改，照旧要求复审——那时还没开工，没有「最终验收一并批」可等。
2. **返工与范围内增补（第 2 条）**：已批准范围内要多做的任务直接加进 `todo.md`，在 Plan 末尾「变更记录」追加一行，最终验收时列出新增
   了哪些任务；**不**把 Plan 的批准标记改回 `pending`。超出范围（新能力、改方向）才重新交审：给已完成模块加新能力照旧另开模块。
   「返工与小模块」一节里「补一节后把 Plan 改回 pending」的要求改为这一条。
3. **UI 自验（第 4 条）**：
   - 改到界面的任务没有自验记录（打开了哪个页面、对照了哪条预期、看到了什么、截图路径），或没有写「UI 未验证＋原因」，不能勾完成。
     只写进规则，不加检查脚本。
   - 「范围内常规操作」加上「启动本地开发服务、用浏览器打开本地页面验证」，批 Plan 即授权。
   - 模块开工时先确认自验工具可用（开发服务能起、浏览器能开）；用不了就按「宿主确认」告诉用户去哪个会话操作，不等写完界面才发现。
   - 去掉「AI 验证后，人做最后的兜底审查，这一步是 `gate`」这一条单独的停点；人工看界面并进最终验收：验收时把各界面任务的自验结果
     与截图一并摆出来。
4. **文档建议（第 5 条）**：每个模块 Spec 交审改为有才提、没有不写；能力图审阅与能力图全部完成两处照旧（没有写「无」，README 表态照旧）。
5. **AC 编号（第 6 条）**：保留为推荐写法与最终验收按编号对证据的做法；删掉 verify-artifacts 对缺编号的提示，规则里去掉「verify-artifacts
   只提示」那句。
6. **变更记录**：「已批准的 Spec、Plan 或能力图被修改时追加变更记录」照旧；「复审时一并呈现」改为「最终验收（或当场复审）时一并呈现」。
   「其他会话的要求不算用户批准」照旧。
7. **改哪些地方**：共享检查点规则（批准标记、Plan 检查点分级的最终验收条目、文档建议、返工与小模块、UI 自验、批 Plan 授权的常规操作）；
   四处约定块；`hooks/module_stage.py` 中英文两份「批准后已修订」的建议语；`hooks/verify-artifacts.sh` 删 AC 编号一段；两边回归。
8. **版本**：0.79.0（与 `checkpoint-default-report` 一起）；CHANGELOG `[0.79.0]` 写两个模块，说明进行中的模块升级后停得更少、
   gates 的含义变化与 interface 1.4。

## Contract

### 共享检查点规则 `references/workflow-checkpoints.md`

- 「批准标记」：「Spec 修订后须复审」改为第 1 条；「交审要让用户看到内容」里 Spec 要点的「文档建议」改为「有才写」；
  「验收标准编号」去掉 verify-artifacts 那句。
- 「Plan 检查点分级」：最终验收一并复审那条里「构建途中的修改若会改变后续任务的做法，照旧当场停下复审」改为第 1 条的停下条件；
  「批 Plan 按范围授权」的常规操作加「启动本地开发服务、用浏览器打开本地页面验证」。
- 「文档建议」按第 4 条；「返工与小模块」按第 2 条；「UI 自验」按第 3 条；变更记录相关句按第 6 条。

### 约定块（四处）

- 「写出 Spec 或 Plan 交审……Spec 修订后须复审」改为「构建中范围内修正 Spec 记变更、最终验收附差异一次批」。
- 「能力图审阅、每个模块的 Spec 交审、能力图全部完成时各提一次文档建议……没有就写『无』」改为第 4 条的说法。
- 「Spec 的验收标准按 AC1、AC2… 编号」保留，作为推荐。
- UI 自验那行加「没有自验记录不能勾完成」。
- 变更记录那行的「复审时一并呈现」改为第 6 条。

### `hooks/module_stage.py`

- 中英文两份 `review_hint` 里「BUILDING 且 Spec 为 revised、还没到最终 gate」的建议语按第 1 条改；其他分支不变。

### `hooks/verify-artifacts.sh`

- 删「验收标准编号」一段。

### 不变

- `phase-guard.sh` 的输出结构；批准标记的格式与 `review-mark`；最终验收列改动文件与新增依赖；远端写入与合并的规则；同一目标第二次停。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
```

## Testing strategy

- `test-phase-guard.sh`：BUILDING、Spec 已修订、还有未勾任务时，建议语为新说法（不含「do not continue the build」）；中文同样；
  到了最终 gate 的建议语逐字不变；`NEEDS_PLAN` 时 Spec 已修订照旧要求复审。
- `test-verify-artifacts.sh`：删掉 AC 编号的 7 例，加反向一例（未完成模块验收标准没编号时不提示）。
- `test_workflow_checkpoints.py`：新关键句（范围内修正记变更、改范围才停、范围内增补不改回 pending、没有自验记录不能勾完成、
  启动本地开发服务、文档建议有才提）；断言「AI 验证后，人做最后的兜底审查」与「把 Plan 的批准标记改回 `pending`」不再出现；
  原有关于文档建议与 AC 编号的断言按新说法改，逐条记录。

## Boundaries

- **会做**：上述规则、约定块、阶段提示建议语、删 AC 提示、回归、0.79.0 版本与 CHANGELOG。
- **先问**：给「不能勾完成」加检查脚本；改批准标记格式或 `review-mark`；放宽远端写入或合并的规则。
- **不做**：判断「是否改了范围」的自动化；检查点判据（已在 `checkpoint-default-report`）。

## Success criteria

- AC1：规则写明构建中范围内修正 Spec 记变更、最终验收附差异一次批，改范围、改方向或要新取舍才当场停；阶段提示在 BUILDING 未到最终 gate 时
  不再说「不要继续构建」，到最终 gate 与其他阶段的提示不变。
- AC2：规则写明范围内增补任务直接进 todo、记变更、最终验收列出，不把 Plan 改回 pending；超出范围才重新交审。
- AC3：UI 自验规则含「没有自验记录或 UI 未验证＋原因不能勾完成」「启动本地开发服务与浏览器打开本地页面算常规操作」「开工先确认工具可用」，
  不再有单独的兜底 gate，人工看界面并进最终验收。
- AC4：文档建议在 Spec 交审时有才提；能力图审阅与全部完成两处照旧。
- AC5：verify-artifacts 不再对缺 AC 编号提示；AC 编号仍是推荐写法。
- AC6：四处约定块一致；0.79.0 版本号、README `--ref`、CHANGELOG（两个模块）齐全；`validate.sh`、两边回归与 `test_workflow_checkpoints.py` 通过。

## Open questions

- 无。
