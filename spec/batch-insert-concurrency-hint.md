# Spec: batch-insert-concurrency-hint

<!-- spec-guard: review pending -->

## Objective

`concurrency-assessment` 只在能力图审阅时做并行评估，并且明确写了「用 `add-module` 插入单个模块不算能力图审阅」
（`references/workflow-checkpoints.md`「并行评估」一节）。可是已有能力图的项目，新需求几乎都是用 `add-module` 一个一个插进去的：
2026-10-22 一次插入 12 个修复模块，评估一次都没被触发，逗号组是手工排的。决定 D20 定下：

1. `moduleConcurrency` 为 `on`、且一次插入 2 个及以上模块后，按现有「并行评估」规则评估一次，把可同时开发的模块、理由与缺的条件交用户选；
2. 本机装了 module-crew 时，提示可以用它的协调会话并行开发；没装只给 Build order 建议；
3. 只出一次，不在之后每轮重复；
4. 开关不是 `on` 时一切不变。

本模块只改规则文字（共享检查点规则、`add-module` 命令说明与 Codex 侧同一节）和对应回归，不改脚本、不改阶段注入、不改约定块与停点规则。

登记：2026-10-22 修复批次 12 个模块之一，经用户批准事项 C136 开模块会话；能力图依赖 `rules-at-nodes`（已合入，改过共享检查点规则与
停点规则）、`concurrency-assessment`（已完成，提供「并行评估」一节）。依据：`docs/reports/2026-10-22-feature-inventory/decisions.md` D20。

## Assumptions

以下是写 Spec 时定下的前提，请在批准时一并确认：

1. **「一次插入」按需求算，不按命令算。** `module-insert.py` 一次只插一个模块，脚本不知道前后几次是不是同一批。所以「一次插入 2 个及以上」
   定义为：为同一个需求（同一次需求确认、同一轮预览交审）连续用 `add-module` 确认插入的模块，至少 2 个。不同需求、隔了几轮各插一个，
   不累计、不评估。这由 agent 按规则判断，不加状态文件、不改脚本（与 `concurrency-assessment` 假设 8「不写计算脚本」一致）。
2. **时机：这一批最后一个模块 `--confirm` 写入成功之后，评估一次。** 评估写在那一轮的回复里；如果紧接着就是新模块的 Spec 交审，就放在交审
   正文里、小项之前单列一段「并行评估」，不占 Spec 的小项。只评估一次：用户采纳、拒绝或不表态之后，这一批不再提；同一批后来又补插一个，
   不重新评估（用户明确要求评估除外，那属于现有第二个时机）。
3. **评估内容沿用「并行评估」一节，不另立判据。** 两条硬门槛、三项参考、逗号组与前移建议、关键路径只在这里算、能粗就粗，全部照原节。
   评估范围是这一批新模块，加上 Build order 里与它们相邻、还没完成的模块（新模块可能和已有的待做模块并排）；已完成的模块只当依赖看。
4. **交用户选，写成选项。** 结论之后给选项与后果：A 采纳建议，按「需求来源与回告」改 Build order、追加变更记录、交用户复审；B 维持现有顺序串行做。
   硬门槛不满足时只写「不建议并行」与缺什么，不出 A。改 Build order 仍是改能力图，评估本身不改任何文件。
5. **module-crew 装没装：看本会话可用的技能，不写探测脚本。** 本会话可用技能里有 `module-crew:crew-coordinator`（Codex 侧是 module-crew 插件的
   `crew-coordinator` 技能）就算装了；看不到或拿不准就当没装。装了：在选项 A 后加一句「本机装了 module-crew，可以用它的协调会话并行开发这些模块
   （协调会话由 module-crew 开启，spec-guard 不开会话）」；没装：只给 Build order 建议，不推荐安装。选「看技能列表」而不是读插件记录，
   理由：插件记录要新增一个命令行入口（`sibling_plugins.py` 现在只被 hook 内部调用），而模块会话、协调会话本来就靠这个技能工作，
   技能可见与「这个会话能用协调会话」是同一件事。见「未决问题」Q1。
6. **已经在并行中就不提 module-crew。** 当前 checkout 已标了角色（`/spec-guard:checkout-role` 标为 `module` 或 `coordinator`）时，说明已经在
   用运行时并行，评估照做，module-crew 那一句不出。
7. **开关不是 `on` 时逐字不变。** `add-module` 说明与 Codex 侧同一节只加一句条件句，指向共享检查点规则；规则正文都写在「并行评估」一节里，
   那一节本来就以「不是 `on` 时本节不适用」开头。不改 hook、模板、`node-rules.md`，所以阶段注入、约定块、停点规则对所有项目逐字不变。
   不放进停点规则的理由：停点规则对每个串行项目都会注入，加一行就会让 off 的项目也多一行（与 `concurrency-assessment` 假设 7 同理）。
8. **单个插入照旧不评估。** 原句「用 `add-module` 插入单个模块不算能力图审阅」保留，改成「插入单个模块不评估；一次插入 2 个及以上时见下」。
9. **CHANGELOG 与版本号不在本模块改**，由模块协调整批合完后统一改；更新说明记在 todo 末尾。

## Contract

### 改动 1 共享检查点规则（`plugins/spec-guard/references/workflow-checkpoints.md`「并行评估」一节）

- 「只在两个时机评估」一句改为三个时机：能力图审阅；**一次插入 2 个及以上模块之后**（按假设 1 的定义）；中途接手的项目、用户明确要求评估时。
  「用 `add-module` 插入单个模块不算能力图审阅」改为「用 `add-module` 插入单个模块不评估」。
- 在「这些都只是建议」一段之前加一小段「**批量插入之后**」，按假设 1～6 写：怎样算一次插入、什么时候评估、只评估一次、评估范围、
  选项 A／B 与「不建议并行」时不出 A、module-crew 一句的条件（技能可见、没标角色）与原文、没装只给 Build order 建议。
- 节首「不是 `on` 时本节不适用」不动；新内容不出现 `parallel-`／`parallel_` 字样。
- 其他小节不动（「文档建议」一节的能力图审阅一条已指向本节，不改）。

### 改动 2 `add-module` 说明（`plugins/spec-guard/commands/add-module.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md` 的「add-module」一节）

两处各加一句，位置在「等用户明确确认后才加 `--confirm`」那段之后：
「为同一个需求一次插入 2 个及以上模块时，最后一个写入成功后先用 config 看 `moduleConcurrency`：是 `on` 就按共享检查点规则「并行评估」一节的
「批量插入之后」评估一次；不是 `on` 不用管。」Claude 侧写 `/spec-guard:config`，Codex 侧写 `spec-guard-ops` 的 config。

### 改动 3 回归（`plugins/spec-guard/hooks/test_workflow_checkpoints.py`）

在 `ConcurrencyAssessmentTests` 加用例（先写、先红）：

- 「并行评估」一节含「2 个及以上」「同一个需求」「最后一个」「只评估一次」「不建议并行」「module-crew」「crew-coordinator」「协调会话」「只给 Build order 建议」
  「插入单个模块不评估」，不含「插入单个模块不算能力图审阅」；
- `commands/add-module.md` 与 `SKILL.md` 的 add-module 一节各含「2 个及以上」「moduleConcurrency」「批量插入之后」；
- 现有的「约定块不出现 `moduleConcurrency`」一例照旧通过；另加一例：`references/node-rules.md` 不出现 `moduleConcurrency` 与「module-crew」。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 scripts/check-no-parallel-surface.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- 改动 3 的用例先写、确认变红，再改规则文字到全绿。
- **off 时逐字不变：** 不改 hook、模板、`node-rules.md`；`test-phase-guard.sh`、`test-verify-artifacts.sh` 原样全绿，`git diff --stat` 只落在
  并行边界所列文件。
- **改坏验证：** 删掉「批量插入之后」里「只评估一次」一句、把 module-crew 一句写进 `node-rules.md`，对应断言各自变红；复原。
- **未验证：** 规则文字能不能让 agent 在真实的批量插入后给出合格评估、技能列表判断 module-crew 是否可靠，单元测试证明不了；
  留给下一次真实批量插入时观察。

## Acceptance criteria

- **AC1** 「并行评估」一节写明三个时机，含「批量插入之后」一小段：一次插入的定义（同一个需求、2 个及以上）、最后一个写入后评估、只评估一次、
  评估范围、选项 A／B、不满足硬门槛时只写「不建议并行」。
- **AC2** 同一小段写明 module-crew 一句的条件（本会话可用技能里有 `crew-coordinator`、checkout 没标角色）与原文，以及没装时只给 Build order 建议。
- **AC3** 单个插入照旧不评估：节内有「插入单个模块不评估」。
- **AC4** `add-module.md` 与 `SKILL.md` 的 add-module 一节各有改动 2 那一句，Claude、Codex 各按宿主写 config 入口。
- **AC5** 开关不是 `on` 时逐字不变：约定块模板与 `node-rules.md` 不出现 `moduleConcurrency`、module-crew；hook 未改；
  `test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿。
- **AC6** 改动 3 的用例全绿；`check-no-parallel-surface.py`、`scripts/validate.sh` 通过；改坏验证两处各自变红。

## 未决问题

- **Q1：怎么判断本机装了 module-crew（假设 5）。** A（推荐）：看本会话可用技能里有没有 `crew-coordinator`，拿不准当没装；只改规则文字。
  B：给 `sibling_plugins.py` 加一个只读命令行入口（读 Claude 的插件记录与 Codex 的 config），规则让 agent 跑它；更准，但多一个脚本入口和它的回归，
  而且模块会话自己看不到这一点也照样没法用协调会话。

## Boundaries

- **总是做**：开关不是 `on` 时规则不生效；评估只出建议，改 Build order 仍要用户批准并记变更记录；没核实的门槛写「未核实」；只评估一次。
- **先问再做**：要加探测脚本或状态文件（Q1 选 B 时按批准的范围做）；发现要改 hook、约定块或停点规则才能做到。
- **不做**：自动改 Build order；替用户开协调会话或 worktree；推荐安装 module-crew；在阶段提示里每轮提醒；改 `module-insert.py`；
  改 `concurrency-assessment` 等已完成模块的 Spec；改 module-crew 仓库；改版本号与 CHANGELOG。

## 并行边界

- 独占：`spec/batch-insert-concurrency-hint.md`、`tasks/batch-insert-concurrency-hint/plan.md`、`tasks/batch-insert-concurrency-hint/todo.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/commands/add-module.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`
- 公共：无

## 与在开模块的重叠

- `quiet-injection`（与本模块并列）改阶段注入（`phase-guard.sh`、`module_stage.py`），可能也动 `test_workflow_checkpoints.py` 或共享检查点规则。
  本模块在这两个文件里只改「并行评估」一节和 `ConcurrencyAssessmentTests`；后合入的一方先 `module-crew sync`，冲突以集成分支为底手工合并。
  它若独占了这两个文件，请模块协调告知，我改成只在这两处追加、不动别的行。
