# Spec: sg-skill-map

<!-- spec-guard: flow v2 tier=normal -->

<!-- spec-guard: review approved de17fb6f2c48 -->

## 目标

自动驾驶第一版的模块 7「skill 对照」。需求 R8「已装的 skill 必须用上」：到了固定的关卡用固定的 skill（对照表在总体技术方案 7.1 节）；做到具体情境时先在已装的插件里找 skill，找到就用并写进汇报；真的没有就明说「这件事没有现成的 skill，按常规做法来」。

讨论记录「实例：拷问没有触发」说明：固定位置的 skill 必须由工具强制触发，不能靠 AI 记得。现在 spec-guard 的阶段提示只在需求确认时点名 interview-me，其他关卡不点名，也没有地方记用了哪些 skill，autopilot-hub 的汇报（模块 8）读不到。

本模块让新流程模块的阶段提示在能对上的关卡点名 skill，在 todo 里留一节记录，`/map --json` 解析给 hub，最终验收时查一遍有没有记。

## 给谁用

- 在新流程模块里干活的 agent：每到一个关卡，阶段提示告诉它该用哪些 skill、用完记在哪。
- autopilot-hub 的汇报（模块 8）：从 `/map --json` 读每个模块用了哪些 skill、哪些情境没有现成的 skill。
- 用户：最终验收时看到这份记录。

## 使用场景

- 新流程模块到了需求确认停点：阶段提示点名 interview-me（重要需求必用）、idea-refine、spec-driven-development。
- 写技术方案、做实现、到最终验收：阶段提示各点名对应的 skill。
- 构建中要画架构图、做数据迁移、碰登录权限：先在已装插件里找 skill，找到就用，记一行；找不到记「没有现成的 skill，按常规做法来」。
- 到最终验收时，todo 里还没有记录：阶段提示与 verify-artifacts 提醒补上。
- hub 生成汇报时读 `/map --json` 的 `skillLog`。

## 业务规则和异常情形

**只对新流程模块（Q4 A）**

1. 只对带流程标记的新流程模块生效（各档位都算，bug、small 也点名它们会经过的关卡）；老流程模块的阶段提示与检查逐字不变。

**能对上阶段的关卡在阶段提示里点名（Q3 A）**

2. 阶段提示在下面这些位置多一行「- Skill：…」，点名本关卡的 skill（对照总体技术方案 7.1；agent-skills 的写裸名，其他插件写「插件名:skill」或插件名），并说明用完记进 todo 的「Skill 使用记录」：

   | 位置（阶段提示能判断的） | 点名的 skill |
   |---|---|
   | 需求文档先审一轮（需求等确认、档位要审、还没有审查记录） | 装了 delegate 时用 `delegate:review`；没装就宿主全新子会话审，都不行写明没有审查者（这一步本身不是 skill 时，记录写「没有现成的 skill，按常规做法来」） |
   | 需求确认停点（需求等确认，已有审查记录或档位不要审） | interview-me（重要需求必用，其余在信息不全时用）、idea-refine（想法还粗时）、spec-driven-development |
   | 总体技术方案关卡 | source-driven-development、api-and-interface-design、documentation-and-adrs；画图用 artifact-diagramming |
   | 写技术方案与技术方案送审（`NEEDS_DESIGN`，以及 `NEEDS_REGRESSION` 时技术方案还在等审或等批） | security-and-hardening（技术方案要送审时）、doubt-driven-development（关键假设）、deprecation-and-migration（涉及数据迁移时） |
   | 构建（`BUILDING`，还没到最终 gate） | incremental-implementation、test-driven-development、frontend-ui-engineering（改前端时） |
   | 最终验收（`BUILDING` 的最终 gate 停点） | browser-testing-with-devtools（回归里有 `ai-operate` 用例时）、performance-optimization（有性能要求时）、git-workflow-and-versioning、ci-cd-and-automation |

3. 任一时刻最多出一行：上表的位置互不重叠——需求等确认时，「先审一轮」与「确认停点」二选一（看有没有审查记录）；`BUILDING` 时，到了最终 gate 就只出「最终验收」那一行，不再出「构建」那一行。行里只放与本位置有关的 skill，不附整张对照表。
3a. 括号里的条件（「技术方案要送审时」「涉及数据迁移时」「改前端时」「回归里有 `ai-operate` 用例时」「有性能要求时」）只是写在行里的文字，由 agent 按实际情况取舍；spec-guard 不解析任何产物来判断这些条件，所以这些 skill 总是列出、带着条件文字。

**对不上阶段的写进规则（Q3 A）**

4. 能力图（planning-and-task-breakdown）、质量底线（constraint-driven-development，项目还没有质量底线文件时）、出事自动修（debugging-and-error-recovery）、发版与安装验证（shipping-and-launch）、上线之后（observability-and-instrumentation）写进共享规则新增的「skill 对照」一节；「出事处理」一节与发版相关的段落各补一句指向它。能力图审阅的节点规则也补一句。
5. 情境触发（不限关卡）：画图、数据迁移、登录与权限、浏览器验证、性能、文档。规则写明：碰到这些时先在所有已装插件里找对应的 skill，找到就用；找不到记「没有现成的 skill，按常规做法来」。构建阶段的点名那一行末尾提一句。
6. 不进主流程：code-review-and-quality、code-simplification（照总体技术方案 7.1）。

**记录写在 todo（Q1 A）**

7. 记录写在 `tasks/<id>/todo.md` 的 `## Skill 使用记录`（英文 `## Skill log`）一节，每行一条列表项：`- <关卡或情境>：<skill>[、<skill>…]`；找不到时写 `- <情境>：没有现成的 skill，按常规做法来`（英文 `no existing skill, done the usual way`）。
7a. **写 todo 之前的关卡**（需求确认、需求文档审查、总体技术方案、技术方案）还没有 todo：这几处用过的 skill 在写 Plan 与 todo 时一并补进这一节，不另找地方存；阶段提示在需求确认到技术方案那几处的点名行里写「写 todo 时补进 Skill 使用记录」，到构建阶段写「记进 todo 的 Skill 使用记录」。
8. 各档位的新流程模块都有 todo（bug、small 也走 Plan 与 todo），所以记录一律写在 todo，不写进需求文档（需求文档在批准指纹里）。
9. 不判断记录是否属实、不核对 skill 是否真的装着。

**`/map --json` 解析给 hub（Q1 A）**

10. `/map --json` 每个模块加 `skillLog`：老流程模块为 `null`；新流程模块为列表，每条 `{"place", "skills", "none"}`。解析规则（按顺序）：
   1. 只看这一节里不在代码块中、以 `- ` 开头的行；
   2. 用行里**第一个**中文冒号「：」或英文冒号「:」切开，前面去掉首尾空白是 `place`，后面是内容；`place` 或内容为空的行跳过（skill 名里的冒号，如 `delegate:review`，在第一个冒号之后，不受影响）；
   3. 内容去掉首尾空白与句末标点后，若等于「没有现成的 skill，按常规做法来」或 `no existing skill, done the usual way`（英文不分大小写），`none` 为真、`skills` 为空列表；
   4. 否则按「、」「，」「,」「；」「;」拆开，去掉空项与重复项（保留先出现的顺序）作 `skills`，`none` 为假。
   没有这一节时为空列表；todo 读不了时为空列表，不报错。
11. `interface.json` 升次版本，写明 `skillLog` 的含义、格式与位置。

**最终验收时查一遍，缺了提醒（Q2 A）**

12. 新流程模块到最终 gate（阶段提示的最终验收停点）时，记录一节缺失或没有一条有效记录，阶段提示多一行提醒、verify-artifacts 出**警告**，不判失败、不挡合并。
13. 模块已完成（todo 全部勾选）而记录为空时，verify-artifacts 同样警告；本模块之前已完成的新流程模块不追补，只警告。

**兼容**

14. 老流程模块的阶段提示、verify-artifacts、`/map --json`（除新增的 `skillLog: null`）逐字不变。
15. 点名那一行的内容只取决于阶段、停点与档位，不额外进状态码；最终 gate 的提醒取决于记录是否为空，「记录为空」这件事进状态码，空与非空互相转换时阶段提示重新给全文。

## 不做什么

- 不做汇报本身（模块 8，hub）。
- 不重做「连着做之前先说一句」（模块 4 已做）。
- 不判断 skill 是否真的用过、是否装着；不自动加载 skill。
- 不改老流程模块。
- 不把 code-review-and-quality、code-simplification 放进主流程。
- 不改送审判定、批准人、技术方案章节（模块 5、6）。

## 成功标准

- S1：新流程模块在第 2 条表里的每个位置，阶段提示有且只有一行「- Skill：…」，写着该位置的 skill（含括号里的条件文字）与记录要求（写 todo 之前的位置写「写 todo 时补进」）；需求等确认时按有无审查记录二选一，最终 gate 只出「最终验收」那一行；不在这些位置时没有这一行；老流程模块从不出现这一行。
- S2：`workflow-checkpoints.md` 有「skill 对照」一节，写全第 4～6 条（对不上阶段的关卡、情境触发、不进主流程），「出事处理」与发版段落、能力图审阅的节点规则各有一句指向；规则测试钉住，`node-rules.md` 每节不超过 `NodeRulesTests` 的字节上限。
- S3：todo 里 `## Skill 使用记录`／`## Skill log` 的列表项按第 10 条的解析规则得到 `skillLog`：只用第一个冒号切 `place`（`- 审查：delegate:review` 得到 `skills: ["delegate:review"]`）；「没有现成的 skill，按常规做法来」与英文写法 `none` 为真；五种分隔符都认、去空项与重复；代码块里的行、没有冒号或一边为空的行跳过；没有这一节为空列表；老流程为 `null`。
- S4：bug、small 模块同样在 todo 里记，需求文档的批准指纹不受影响。
- S5：新流程模块到最终 gate 而记录为空时，阶段提示多一行提醒、verify-artifacts 警告不判失败；有记录时不提醒；空与非空互相转换时状态码变化；已完成而记录为空的模块 verify-artifacts 警告。
- S6：`interface.json` 升次版本并写明 `skillLog`；全部现有回归通过，老流程模块输出除 `skillLog: null` 外不变。
- S7：技术方案批准后，经 agent-relay 给 ecosystem-lead（线程 `autopilot-m5-7`）发一条消息，写明 `skillLog` 的位置（`/map --json` 每个模块）、字段（`place`、`skills`、`none`）与 todo 里的写法；投递成功的消息编号记进 todo。

## 待定问题

无。四处待定已在需求确认时定下：Q1 A（写在 todo，`/map` 解析给 hub）、Q2 A（最终验收时查，缺了提醒）、Q3 A（能对上阶段的点名，其余写进规则）、Q4 A（只对新流程模块）。

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=7 sha256=44f486db1e89 -->

第 1 轮（Codex，gpt-5.6-sol high，7 条阻断），逐条对照现有阶段流程核实，全部采纳：
1. 写 todo 之前的关卡没地方记 → 采纳：那几处用过的 skill 在写 Plan 与 todo 时补进记录一节（第 7a 条），点名行里写明「写 todo 时补进」。
2. 没装 delegate 时仍点名 `delegate:review` → 采纳：先审一轮那一行写成装了才用、没装走宿主子会话或写明没有审查者。
3. 位置重叠时出几行没说 → 采纳：任一时刻最多一行；需求等确认时按有无审查记录二选一，最终 gate 只出最终验收那一行（第 3 条）。
4. 条件式 skill 没有判据 → 采纳：条件只作行里的文字，spec-guard 不解析产物判断，总是列出（第 3a 条）。
5. 记录的解析有歧义 → 采纳：写明按第一个冒号切、先认「没有现成的 skill」、五种分隔符、去空项与重复、跳过代码块（第 10 条、S3）。
6. 最终 gate 的提醒没进状态码 → 采纳：「记录为空」进状态码（第 15 条、S5）。
7. 回告 lead 没有可验证的证据 → 采纳：写明渠道、线程、内容与「消息编号记进 todo」（S7）。
