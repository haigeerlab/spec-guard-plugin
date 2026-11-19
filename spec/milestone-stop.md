# Spec: milestone-stop

<!-- spec-guard: review approved 36d3b3a8a510 -->

## 目标

多模块需求按用法草案的里程碑分段验证：一个里程碑的模块全部完成后，阶段提示停下，要求按本里程碑的典型用法实际跑一遍、
摆证据，由用户判定；用户判定通过后用 `milestone-mark` 记下确认，阶段提示才转到下一个模块（总账 S89 第二个里程碑 M2；
用户 2026-11-19 选 B1，并在本会话判定 M1 停点通过）。

现状：0.87.0 起用法草案里有里程碑表，但阶段提示不读它；一个里程碑做完，提示直接指向下一个模块的 Spec，分段验证只能靠
agent 自觉（本仓库 M1 停点就是在 todo 里手写一项 gate 实现的）。

给谁用：批准与验收多模块需求的人（在停点看实跑证据、判定通过与否），以及照阶段提示推进的 agent。

## 假设

1. **何时算停点**：某份草案的某个里程碑 Mk，其所有模块在阶段判定里都是已完成（只剩正式延期项也算完成），且 Mk 没有有效的确认记录。
   同时有几个停点时只报第一个（草案文件名排序，草案内按里程碑表顺序）。最后一个里程碑同样停（整个需求做完，要跑全部典型用法）。
   挂起的模块不算完成。里程碑里有模块不在能力图上，或草案读不了，不判停点，只在提示里写一行「用法草案读不了，里程碑停点未判定」
   （探测失败降级，不拦路）；结构错误仍由 verify-artifacts 报。
2. **确认记录（B1）**：写在草案里、`## Milestones` 表之后，一行一个里程碑：
   `<!-- spec-guard: milestone M1 confirmed store, add-cmd, list-cmd -->`，列出确认时该里程碑的模块（按表里的顺序）。
   确认后里程碑表里该行的模块变了（例如 add-module 后归进来一个新模块），记录失效：新模块做完后会再停一次。
   不记日期与人名（与 review-mark 的批准标记一致，时间与人看 git 历史）。
3. **`/spec-guard:milestone-mark`（新命令）**：`milestone_mark.py --project <dir> --draft spec/usage/<需求>.md --milestone M<n>`，
   默认只读预览，`--confirm` 才写。预览列出：草案、里程碑、它的模块与各自阶段、要跑的典型用法、将写入的那一行、写入后阶段提示
   会转到哪。拒绝：里程碑不存在；有模块未完成；前面还有未确认的里程碑；已有有效确认（报「已确认」，退出 0 不写）。旧的失效记录
   在确认时替换为新行，不留两行。只改这一份草案，不提交、不改 todo 与 state.json。命令文档写明：只在用户明确说本里程碑通过之后才
   `--confirm`，「看起来还行」不算；用户说不通过时不调用本命令，按「返工与小模块」规则在本里程碑的模块 todo 里追加任务，或回头改
   草案与后面还没开工的模块。
4. **阶段提示**：有停点时，「当前阶段」一行和计数不变（不新增阶段名，避免牵动状态码之外的读取方），在计数后加一行
   「- 里程碑停点: `spec/usage/x.md` 的 M1（模块 a、b、c 已全部完成，未确认）」，「建议下一步」换成：先不开下一个模块，按 M1 的
   典型用法 U1… 实际跑一遍、把命令与输出摆给用户判定；通过后用 milestone-mark 预览、确认后记下。并附「里程碑停点」的停点规则
   （取自 node-rules.md，经 module_stage.py，同现有节点规则的接法）。没有草案或没有停点的项目，提示逐字不变。
5. **共享检查点规则**：`references/workflow-checkpoints.md` 的「用法草案」一节补「里程碑停点」：停下时摆什么（本里程碑的每个典型
   用法：怎么跑的、命令与输出、和草案描述是否一致；跑不了的写明原因）、用户判定后怎么做（通过→milestone-mark；不通过→追加任务
   或改草案），与最终验收的关系（最终验收照旧逐模块；里程碑停点在该里程碑最后一个模块验收并合并、发版之后，用安装后的版本跑）。
   `node-rules.md` 加「里程碑停点」一节。
6. **verify-artifacts**：确认记录也由 `usage_draft.py` 解析：记录指向不存在的里程碑或格式坏判失败；记录的模块与表里不一致只提醒
   「M1 确认后改过，模块做完后会再停一次」。
7. **`/map` 的 JSON（用户 2026-11-19 定：加）**：加一个顶层字段 `milestoneStop`（无停点为 `null`，有则 `{file, milestone, modules, usages}`），
   interface 升到 1.13（纯新增，其他字段不变）。理由：并行开关打开时由模块协调按 `/map --json` 派活，只改阶段提示的话协调会绕过
   停点。不加的代价：并行项目里停点只对看阶段提示的会话生效。文字版 `/map` 在有停点时多一行。
8. **M1 停点观察的收敛**：同一模块归两个里程碑时，`usage_draft.py` 只报重复那条，不再连带报 Build order 顺序（M1 停点时看到的
   双报）。
9. 只改 spec-guard；发 0.88.0；仓库里不出现消费项目的名字、模块或编号；上游 agent-skills 不改。发版回告 ecosystem-lead，S89 至此
   完成；手册第 6 章由他改。

## 命令

```text
python3 -B -m unittest plugins/spec-guard/hooks/test_milestone_mark.py
python3 -B -m unittest plugins/spec-guard/hooks/test_usage_draft.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## 项目结构

- `hooks/usage_draft.py`：加确认记录的解析与 `stop(project, states)`（停点判定的唯一位置，阶段提示、milestone-mark、map_view 都调它）。
- 新增 `hooks/milestone_mark.py` 与 `hooks/test_milestone_mark.py`；新增 `commands/milestone-mark.md`；`skills/spec-guard-ops/SKILL.md`
  补 Codex 入口一句。
- `hooks/module_stage.py`：停点行、建议下一步与停点规则；`references/node-rules.md`、`references/workflow-checkpoints.md`。
- 假设 7：`hooks/map_view.py`、`interface.json`、`spec/map-view.md`。
- 文档：`docs/commands.md`（milestone-mark、verify-artifacts 一行）、`docs/workflow.md`、`docs/concepts.md`（里程碑停点）、README 中英命令表。
  能力图这次全部完成，按收尾规则另提 README 建议：从用法草案 `spec/usage/usage-milestones.md` 展开。

## 测试策略

- 先写测试并确认在 0.87.0 上失败，再实现。
- `test_usage_draft.py`：停点判定（里程碑全完成未确认→停；确认后不停；确认后加模块且做完→再停；挂起模块不算完成；只剩延期项算完成；
  多个停点报第一个；草案坏→不判并给原因）；确认记录的失败与提醒项；重复归属只报一条。
- `test_milestone_mark.py`：预览只读；四种拒绝；`--confirm` 写一行、替换失效记录、二次确认退出 0 不写；只改那份草案。
- `test-phase-guard.sh`：有停点时多停点行、建议下一步换成跑典型用法、带停点规则；确认后提示回到原样；没有草案时逐字不变。
- `test_map_view.py` 的 `milestoneStop` 正反例，接口契约回归。
- 变异（草稿副本）：去掉「确认后模块变了则失效」、去掉阶段提示的停点分支、去掉 milestone-mark 的「未完成拒绝」，都要让测试变红。

## 边界

- Always：先红后绿；停点判定只在 `usage_draft.py`；没有草案的项目输出不变；milestone-mark 先预览后确认。
- Ask first：新增阶段名；让停点改变 `startable` 或阻止 add-module；milestone-mark 自动提交；判断典型用法的内容是否跑通。
- Never：agent 未经用户明确判定就 `--confirm`；改上游 agent-skills；在 Spec、代码、测试、提交信息或 PR 中写入消费项目的名称、模块或编号。

## 并行边界

- 独占：`plugins/spec-guard/hooks/usage_draft.py`、`plugins/spec-guard/hooks/milestone_mark.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/commands/milestone-mark.md`、`plugins/spec-guard/references/node-rules.md`、`plugins/spec-guard/references/workflow-checkpoints.md`
- 公共：无

## 成功标准

- AC1：里程碑全部完成且未确认时，阶段提示出停点行、建议下一步改为按该里程碑典型用法实跑并交用户判定，并带停点规则；没有草案、
  没有停点时提示逐字不变。
- AC2：milestone-mark 预览只读；`--confirm` 写入一行确认记录；四种拒绝情形各自说明原因；确认后阶段提示转到下一个模块。
- AC3：确认后里程碑的模块变了，记录失效，新模块完成后再停；verify-artifacts 对坏记录判失败、对失效记录只提醒。
- AC4：草案读不了时不判停点、提示写明原因，不让阶段提示失败。
- AC5：共享检查点规则与节点规则写明停点时摆什么、通过与不通过各怎么做；命令文档写明只在用户明确判定通过后确认。
- AC6：`/map --json` 有顶层 `milestoneStop`（无停点为 `null`），interface 1.13 且只新增；文字版 `/map` 有停点时多一行；既有回归全部通过。
- AC7：同一模块归两个里程碑只报一条失败。
- AC8：文档同步，版本 0.88.0；能力图全部完成，收尾 README 建议从用法草案展开。

## 文档建议

- 本模块：commands.md 加 milestone-mark；concepts.md 加「里程碑停点」；workflow.md 在能力图审阅之后一步加停点；README 命令表加一行。
- 能力图全部完成（S89 收尾）：README 的功能介绍加一段「多模块需求：用法草案与里程碑停点」，从 `spec/usage/usage-milestones.md`
  的 U1–U3 展开，随本模块一起改。

## 待定问题

- 无（假设 7 已定：加 `milestoneStop`，interface 1.13）。
