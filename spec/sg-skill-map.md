# Spec: sg-skill-map

<!-- spec-guard: flow v2 tier=normal -->

<!-- spec-guard: review pending -->

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
   | 需求确认停点（新流程需求等用户确认） | interview-me（重要需求必用，其余在信息不全时用）、idea-refine（想法还粗时）、spec-driven-development |
   | 需求文档先审一轮（还没有审查记录） | delegate 的 review（`delegate:review`） |
   | 总体技术方案关卡 | source-driven-development、api-and-interface-design、documentation-and-adrs；画图用 artifact-diagramming |
   | 写技术方案（`NEEDS_DESIGN`）与技术方案送审（命中三种高风险） | security-and-hardening（送审时）、doubt-driven-development（关键假设）；数据迁移加 deprecation-and-migration |
   | 构建（`BUILDING`） | incremental-implementation、test-driven-development；前端加 frontend-ui-engineering |
   | 最终验收（最终 gate） | 回归里有 `ai-operate` 用例时 browser-testing-with-devtools；有性能要求时 performance-optimization；提交与合并 git-workflow-and-versioning、ci-cd-and-automation |

3. 同一位置只出一行；行里只放与本位置有关的 skill，不附整张对照表。

**对不上阶段的写进规则（Q3 A）**

4. 能力图（planning-and-task-breakdown）、质量底线（constraint-driven-development，项目还没有质量底线文件时）、出事自动修（debugging-and-error-recovery）、发版与安装验证（shipping-and-launch）、上线之后（observability-and-instrumentation）写进共享规则新增的「skill 对照」一节；「出事处理」一节与发版相关的段落各补一句指向它。能力图审阅的节点规则也补一句。
5. 情境触发（不限关卡）：画图、数据迁移、登录与权限、浏览器验证、性能、文档。规则写明：碰到这些时先在所有已装插件里找对应的 skill，找到就用；找不到记「没有现成的 skill，按常规做法来」。构建阶段的点名那一行末尾提一句。
6. 不进主流程：code-review-and-quality、code-simplification（照总体技术方案 7.1）。

**记录写在 todo（Q1 A）**

7. 记录写在 `tasks/<id>/todo.md` 的 `## Skill 使用记录`（英文 `## Skill log`）一节，每行一条列表项：`- <关卡或情境>：<skill>[、<skill>…]`；找不到时写 `- <情境>：没有现成的 skill，按常规做法来`（英文 `no existing skill, done the usual way`）。中英文冒号与顿号、逗号都认。
8. 各档位的新流程模块都有 todo（bug、small 也走 Plan 与 todo），所以记录一律写在 todo，不写进需求文档（需求文档在批准指纹里）。
9. 不判断记录是否属实、不核对 skill 是否真的装着。

**`/map --json` 解析给 hub（Q1 A）**

10. `/map --json` 每个模块加 `skillLog`：老流程模块为 `null`；新流程模块为列表，每条 `{"place", "skills", "none"}`——`place` 是冒号前的文字，`skills` 是冒号后按分隔符拆开的 skill 名（`none` 为真时为空列表），`none` 表示这一条写的是「没有现成的 skill」。没有这一节时为空列表。写不成「位置：内容」的行跳过，不报错。
11. `interface.json` 升次版本，写明 `skillLog` 的含义、格式与位置。

**最终验收时查一遍，缺了提醒（Q2 A）**

12. 新流程模块到最终 gate（阶段提示的最终验收停点）时，记录一节缺失或没有一条有效记录，阶段提示多一行提醒、verify-artifacts 出**警告**，不判失败、不挡合并。
13. 模块已完成（todo 全部勾选）而记录为空时，verify-artifacts 同样警告；本模块之前已完成的新流程模块不追补，只警告。

**兼容**

14. 老流程模块的阶段提示、verify-artifacts、`/map --json`（除新增的 `skillLog: null`）逐字不变。
15. 新流程模块的阶段提示多出点名那一行，状态码不因这一行变化（行的内容只取决于阶段与档位，二者已在状态码里）。

## 不做什么

- 不做汇报本身（模块 8，hub）。
- 不重做「连着做之前先说一句」（模块 4 已做）。
- 不判断 skill 是否真的用过、是否装着；不自动加载 skill。
- 不改老流程模块。
- 不把 code-review-and-quality、code-simplification 放进主流程。
- 不改送审判定、批准人、技术方案章节（模块 5、6）。

## 成功标准

- S1：新流程模块在第 2 条表里的每个位置，阶段提示有且只有一行「- Skill：…」，写着该位置的 skill 与「记进 todo 的 Skill 使用记录」；不在这些位置时没有这一行；老流程模块从不出现这一行。
- S2：`workflow-checkpoints.md` 有「skill 对照」一节，写全第 4～6 条（对不上阶段的关卡、情境触发、不进主流程），「出事处理」与发版段落、能力图审阅的节点规则各有一句指向；规则测试钉住，`node-rules.md` 每节不超过 `NodeRulesTests` 的字节上限。
- S3：todo 里 `## Skill 使用记录`／`## Skill log` 的列表项被 `/map --json` 的 `skillLog` 解析成 `{place, skills, none}`；「没有现成的 skill」写法 `none` 为真；中英文写法、全半角分隔符都认；写坏的行跳过；没有这一节为空列表；老流程为 `null`。
- S4：bug、small 模块同样在 todo 里记，需求文档的批准指纹不受影响。
- S5：新流程模块到最终 gate 而记录为空时，阶段提示多一行提醒、verify-artifacts 警告不判失败；有记录时不提醒；已完成而记录为空的模块 verify-artifacts 警告。
- S6：`interface.json` 升次版本并写明 `skillLog`；全部现有回归通过，老流程模块输出除 `skillLog: null` 外不变。
- S7：技术方案批准后，把记录的位置与格式回告 ecosystem-lead，转 hub 模块 8。

## 待定问题

无。四处待定已在需求确认时定下：Q1 A（写在 todo，`/map` 解析给 hub）、Q2 A（最终验收时查，缺了提醒）、Q3 A（能对上阶段的点名，其余写进规则）、Q4 A（只对新流程模块）。
