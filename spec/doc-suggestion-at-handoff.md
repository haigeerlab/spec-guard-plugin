# Spec: doc-suggestion-at-handoff

<!-- spec-guard: review pending -->

## Objective

实地使用里暴露了两处与文档有关的缺口：

1. **没人问，就没人提文档。** 一个项目的十几份底座文档，都是用户问了“该出哪些文档”之后才出的；用户不问时，参与的几个会话
   都没有主动提过。文档基线、影响、核验三个工具只在显式调用时运行，阶段钩子不调用它们，规则里也没有一处提醒 agent
   主动提文档。
2. **Spec 阶段的影响检查必然报错，被误读成故障。** `documentation_impact.py` 先校验 Spec 里的影响表，再校验 Plan；
   只要影响表里有 `update` 或 `create`，就要求 `tasks/<id>/plan.md` 是普通文件。Spec 交审时 Plan 还没写，所以一定报
   `module plan must be a regular file`。实地里有一个会话因此向用户报告了不存在的“启用基线被阻断”。

本模块只改规则与说明文字补上这两处，不加命令、钩子或文件格式，文档基线、影响、核验三个工具的行为不变。

登记：2026-10-14 经 `/spec-guard:add-module` 插入能力图。需求来自一个审查会话，用户已确认范围与取舍。

## Assumptions

用户已于 2026-10-14 确认：

1. **文档建议只挂在 Spec 交审这一处。** 这是每个模块必经、用户一定会看的时候。默认对所有项目生效，不依赖文档基线。
2. **允许写“无”**，多数模块应当是“无”。每条建议说清写什么、为什么现在写、解决什么问题。
3. **不卡验收。** 用户采纳的建议写进 Plan，成为普通任务；用户拒绝的不再就本模块重复提。不新增决定表；
   提建议前是否先查资料由 agent 自己判断。
4. **ADR 询问收窄。** 原提议是每次在“Spec 没覆盖的决策”停下时都问是否记 ADR；这类停点很多是小决策，每次都问会成为噪音。
   改为：这个决策会影响以后的设计时，才顺带问是否记一份 ADR。
5. **影响检查的时序只写说明，不改代码。**
6. 不要求已完成的模块补文档建议；不自动生成文档或 ADR。
7. 版本 0.60.2，一个 PR。

写说明时核对代码得到的一处更正：影响表里没有 `update`、`create` 时直接得到 `valid`，这包括 `follow`、`pending`、
`not-applicable` 三种决定（需求原文只写了 `follow` 与 `not-applicable`）。另外，Plan 不存在、是符号链接或
不是普通文件时报的是同一句错误，说明里要区分预期与异常。

## Contract

### 文档建议

`references/workflow-checkpoints.md`「评审状态标记」一节的 Spec 交审清单末尾加一项“文档建议”，并在清单后加一段说明：

> 文档建议：本模块做的事是否值得新增或更新文档（包括 ADR）。每条建议说清写什么、为什么现在写、解决什么问题；没有就写
> “无”。用户采纳的写进 Plan 成为任务；用户拒绝的不再就本模块重复提。

`commands/review-mark.md` 与 `spec-guard-ops` 里列出 Spec 交审内容的那两处，同样加上“文档建议”，措辞与上面一致，
细则指向共享检查点规则。

### ADR 询问

`references/workflow-checkpoints.md`「Plan 检查点分级」里的异常停点“Spec 没覆盖的决策”后加半句：
这个决策会影响以后的设计时，停下的同时问是否记一份 ADR。`docs/workflow.md` 里同一串停点同步。

### 影响检查的 Spec 阶段说明

`references/documentation-impact.md` 的「模块 Plan」一节与 `commands/documentation-impact.md` 的结果说明各加一段：

> 在 Spec 阶段、Plan 还没写时，影响表里只要有 `update` 或 `create`，检查就会报 `module plan must be a regular file`。
> 这是预期结果：报到这一句说明 Spec 里的影响表已通过校验，只是 Plan 交付还没检查，不能当作完整的 `valid`。影响表里
> 没有 `update`、`create`（全部为 `follow`、`pending` 或 `not-applicable`）时直接得到 `valid`。Plan 获批后要再跑一次，
> 必须得到完整的 `valid`。Plan 已经写了还报这一句（例如它是符号链接），才是异常。

### 文档

`CHANGELOG.md` 新增 `[0.60.2]`；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.60.2。约定块模板不改。

### 不变

`documentation_impact.py` 等代码、阶段判定、阶段提示、`verify-artifacts` 与所有命令的行为都不变。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 -B plugins/spec-guard/hooks/test_documentation_impact.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- 先加断言并确认失败，再改文字：`test_workflow_checkpoints.py` 新增一例，检查三处 Spec 交审清单都有“文档建议”、
  共享检查点规则有那段说明的关键词（写什么、为什么现在写、“无”、写进 Plan、不再就本模块重复提）、异常停点带 ADR 询问。
- 影响检查说明的关键词由同一个测试文件或影响检查的测试检查（两处说明都有 `module plan must be a regular file`、
  “预期结果”、“再跑一次”）。说明与代码一致：在临时项目里实跑一次，Spec 有 `create`、Plan 不存在时得到这句错误；
  影响表只有 `follow`、`pending`、`not-applicable` 时得到 `valid`。
- 其余回归不改，全部通过即证明行为未变。
- 发版后在两边宿主各用一个临时项目跑一次 Spec 交审（提示里不提文档），看交审内容里是否出现“文档建议”一项。

## Boundaries

- Always：规则只有一个出处，命令文件与技能只放要点和指向；三处交审清单措辞一致。
- Ask first：文档建议扩到 Spec 交审以外的位置；让它卡验收；为它加决定表、命令或钩子输出；改影响检查的代码。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 三处 Spec 交审清单都有“文档建议”，措辞一致；共享检查点规则写明它的写法与采纳、拒绝后怎么办。
- “Spec 没覆盖的决策”停点带上收窄后的 ADR 询问。
- 影响检查的两处说明写清 Spec 阶段的预期结果，与代码实测一致。
- 全套检查通过。
- 发版后两边宿主各有一次真实会话在 Spec 交审时给出“文档建议”；做不到时如实记为未验证。

## Open questions

- 无。
