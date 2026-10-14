# Spec: doc-suggestion-at-handoff

<!-- spec-guard: review pending -->

## Objective

实地使用里暴露了两处与文档有关的缺口：

1. **没人问，就没人提文档。** 一个项目的十几份底座文档（标准、术语表、时序图、状态机、安全边界、总览等），都是用户问了
   “该出哪些文档”之后才出的；用户不问时，参与的几个会话都没有主动提过。这些文档大多是跨模块的，单看一个模块想不到。
   文档基线、影响、核验三个工具只在显式调用时运行，阶段钩子不调用它们，规则里也没有一处提醒 agent 主动提文档。
2. **Spec 阶段的影响检查必然报错，被误读成故障。** `documentation_impact.py` 先校验 Spec 里的影响表，再校验 Plan；
   只要影响表里有 `update` 或 `create`，就要求 `tasks/<id>/plan.md` 是普通文件。Spec 交审时 Plan 还没写，所以一定报
   `module plan must be a regular file`。实地里有一个会话因此向用户报告了不存在的“启用基线被阻断”。

本模块只改规则与说明文字补上这两处，不加命令、钩子或文件格式，文档基线、影响、核验三个工具的行为不变。

登记：2026-10-14 经 `/spec-guard:add-module` 插入能力图。需求来自一个审查会话，用户在此基础上补充了提醒位置与建议范围，
已确认范围与取舍。

## Assumptions

用户已于 2026-10-14 确认：

1. **文档建议在三个位置各问一次**，对应三个层次：
   - **能力图评审**（写完或大改能力图、交用户确认模块拆分时）：跨模块、开工前就该有的文档，例如总览、术语表、架构边界、
     关键技术选型的 ADR。它们决定各个模块按什么约定写，做完再补时前面的模块已经各写各的。
   - **Spec 交审**（每个模块）：本模块自己的文档，例如接口契约、状态机、模块内的取舍。
   - **能力图全部完成**（最后一个模块最终验收的那次停顿）：收尾文档，按实际做出来的东西更新总览、使用说明、交接文档，
     并核对能力图评审时定下的文档是否已与实际脱节。这是整个需求的最后一个检查点，之后没人再问。
2. **建议前先想范围，不用清单。** 先想这个项目是什么、给谁用（看能力图的目标、README 与已有文档）；再想这类项目的
   使用者和维护者分别要看什么，参考文档基线已有的类别（产品方向、架构、开发入口、使用说明、接口契约），项目建了基线就
   以基线为准；最后想已有文档里哪些会因这次的工作过时。不按项目类型列文档清单：列不全、会被照抄、要维护。
3. **README 默认在候选里。** 能力图评审与全部完成这两处一定要对 README 表态（新建、更新或不用改）；单个模块的 Spec 交审
   只在这个模块改变了使用方式时才提它。
4. **写法一致**：每条建议说清写什么、为什么现在写、解决什么问题；没有就写“无”，多数模块应当是“无”。
5. **采纳与拒绝**：能力图评审与 Spec 交审时采纳的，写进相应模块的 Plan 成为普通任务；全部完成时采纳的，另开一个收尾模块
   按正常流程写，不在已完成的模块里补；拒绝的不再就同一层次重复提。不卡验收，不新增决定表；是否先查资料由 agent 判断。
6. **ADR 询问收窄**：“Spec 没覆盖的决策”停下时，只在这个决策会影响以后的设计时，才顺带问是否记一份 ADR。
7. **不加的位置**：每个模块的最终验收（采纳的文档已是 Plan 任务，验收时自然核对）、阶段提示里“全部完成”那一行
   （全部完成后每轮都出现，且要改钩子输出）、插入新模块与 Proposal 晋级（新模块照样过 Spec 交审）。
8. **影响检查的时序只写说明，不改代码。**
9. 不要求已完成的模块补文档建议；不自动生成文档或 ADR。约定块模板不改。
10. 版本 0.60.2，一个 PR。

核对代码得到的一处更正：影响表里没有 `update`、`create` 时直接得到 `valid`，这包括 `follow`、`pending`、`not-applicable`
三种决定（需求原文只写了 `follow` 与 `not-applicable`）。另外，Plan 不存在、是符号链接或不是普通文件时报的是同一句错误，
说明里要区分预期与异常。

## Contract

### 文档建议（共享检查点规则新增一节）

`references/workflow-checkpoints.md` 新增「文档建议」一节，写明：

- 三个位置与各自问什么（Assumptions 1）；
- 建议前怎么想范围（Assumptions 2），以及 README 默认在候选里（Assumptions 3）；
- 每条建议的写法与“无”（Assumptions 4）；
- 采纳与拒绝后怎么办，含全部完成时采纳的另开收尾模块（Assumptions 5）。

「评审状态标记」一节的 Spec 交审清单末尾加一项“文档建议”，指向这一节。`commands/review-mark.md` 与 `spec-guard-ops` 里列出
Spec 交审内容的那两处同样加上“文档建议”，措辞一致；`spec-guard-ops` 另用一句话指出能力图评审与全部完成时也问，细则见共享
检查点规则。

### ADR 询问

「Plan 检查点分级」里的异常停点“Spec 没覆盖的决策”后加半句：这个决策会影响以后的设计时，停下的同时问是否记一份 ADR。
`docs/workflow.md` 里同一串停点同步，并补一句三个文档建议位置的说明。

### 影响检查的 Spec 阶段说明

`references/documentation-impact.md` 的「模块 Plan」一节与 `commands/documentation-impact.md` 的结果说明各加一段：

> 在 Spec 阶段、Plan 还没写时，影响表里只要有 `update` 或 `create`，检查就会报 `module plan must be a regular file`。
> 这是预期结果：报到这一句说明 Spec 里的影响表已通过校验，只是 Plan 交付还没检查，不能当作完整的 `valid`。影响表里
> 没有 `update`、`create`（全部为 `follow`、`pending` 或 `not-applicable`）时直接得到 `valid`。Plan 获批后要再跑一次，
> 必须得到完整的 `valid`。Plan 已经写了还报这一句（例如它是符号链接），才是异常。

### 文档

`CHANGELOG.md` 新增 `[0.60.2]`；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.60.2。

### 不变

`documentation_impact.py` 等代码、阶段判定、阶段提示、`verify-artifacts`、约定块模板与所有命令的行为都不变。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 -B plugins/spec-guard/hooks/test_documentation_impact.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- 先加断言并确认失败，再改文字：`test_workflow_checkpoints.py` 新增一例，检查「文档建议」一节含三个位置、范围的三个问题、
  README、“无”、另开收尾模块、不再重复提等关键词；三处 Spec 交审清单都有“文档建议”；异常停点带 ADR 询问。
- 影响检查说明的关键词由影响检查的测试检查（两处说明都有 `module plan must be a regular file`、“预期结果”、“再跑一次”）。
  说明与代码一致：在临时项目里实跑，Spec 有 `create`、Plan 不存在时得到这句错误；影响表只有 `follow`、`pending`、
  `not-applicable` 时得到 `valid`。
- 其余回归不改，全部通过即证明行为未变。
- 发版后在两边宿主各用临时项目跑真实会话（提示里不提文档）：一次 Spec 交审，看是否出现“文档建议”；一次能力图全部完成的
  最终验收，看是否给出收尾文档建议并对 README 表态。能力图评审那一处靠 agent-skills 的 `/spec` 流程，真实会话成本高，
  发版后如实记为未验证或另找机会观察。

## Boundaries

- Always：规则只有一个出处，命令文件与技能只放要点和指向；三处交审清单措辞一致。
- Ask first：增加文档建议的位置；让它卡验收；按项目类型列文档清单；为它加决定表、命令或钩子输出；改影响检查的代码。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 共享检查点规则有「文档建议」一节，写明三个位置、范围怎么想、README 默认在候选里、写法与采纳拒绝。
- 三处 Spec 交审清单都有“文档建议”，措辞一致。
- “Spec 没覆盖的决策”停点带上收窄后的 ADR 询问。
- 影响检查的两处说明写清 Spec 阶段的预期结果，与代码实测一致。
- 全套检查通过。
- 发版后的真实会话按 Testing strategy 观察；做不到的如实记为未验证。

## Open questions

- 无。
