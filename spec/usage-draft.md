# Spec: usage-draft

<!-- spec-guard: review approved 80cb6f17746b -->

## 目标

多模块需求在开工前就能看清「做出来怎么用」，并为分段验证定好里程碑（总账 S89，2026-11-19 经 ecosystem-lead 转来，用户在本会话确认需求）。

现状：能力图按「怎么造」组织（模块表 + Build order），对外用法要到能力图全部完成、写 README 时才第一次成形；模块之间也没有
「做完这几个能演示什么」的划分。本模块补上前一半与里程碑的定义：

1. **用法草案**：同一次需求确认拆出 2 个及以上模块时，能力图审阅同一轮默认给出 `spec/usage/<需求>.md`：入口清单、两三个典型用法、
   里程碑表。顺带核对拆分：有入口找不到模块是拆漏了，有模块不对应任何入口可能拆多了。
2. **一致性**：属于某份草案的模块，Spec 交审时标出对外接口与草案是否一致；收尾 README 从草案展开。
3. **结构校验**：`verify-artifacts` 检查草案的结构与它和能力图的对应关系，不判断内容。
4. **插入提醒**：`add-module` 在项目有草案时，预览提醒把新模块归进里程碑。

里程碑停点（阶段提示停下、用户确认通过与否、确认记录命令）是下一个模块 `milestone-stop` 的事，本模块不做。

给谁用：批准与验收多模块需求的人（看草案、验里程碑），以及照规则出草案、维护里程碑的 agent。

## 假设

用户已于 2026-11-19 确认（「说完了，按推荐」，针对本会话的需求总结与 A1、C1 等推荐项）：

1. **命名**：段叫「里程碑」（Milestone），草案叫「用法草案」（Usage draft）；不用「阶段」，避免与阶段提示的 IDLE、BUILDING 等撞名。
   插件里「里程碑」目前没有别的用法。
2. **多模块门槛**：同一次需求确认（同一轮预览交审）拆出 2 个及以上模块，与「批量插入」的算法一致；单模块需求不出草案。
3. **文件位置（A1）**：每个需求一份，`spec/usage/<需求>.md`，文件名建议 kebab-case。`spec/usage/` 是子目录，现有的模块 Spec 对应检查
   只扫 `spec/*.md`，不受影响。
4. **能力图格式不改**：不加列、不加节，Build order 仍然只有一行；`capability_map.py`、`spec-digest.py`、`proposal_contract.py`、
   `module-insert.py` 的能力图读写都不动。里程碑归属只写在草案里。
5. **草案格式**（结构关键字用英文，正文按项目产物语言）：

   ```markdown
   # Usage draft: <需求>

   ## Entry points

   | Entry | Does | Module |
   |---|---|---|
   | `/foo bar` | 做什么 | module-a |

   ## Typical usage

   ### U1: <标题>
   用户怎么输入或调用、得到什么。

   ## Milestones

   | Milestone | Usage | Modules |
   |---|---|---|
   | M1 | U1 | module-a, module-b |
   | M2 | U1, U2 | module-c |
   ```

   入口按项目类型写：插件是命令、skill 与自动触发的行为；库或服务是 API 与参数；网页是页面与主要操作；命令行是子命令与参数。
6. **结构校验（失败项）**：缺任一节或表格写坏；典型用法没有 `### U<n>:` 标题；里程碑引用了不存在的用法；有用法没被任何里程碑引用；
   最后一个里程碑没有列出全部用法；里程碑里的模块不在能力图上；同一模块在一份或几份草案里归了不止一个里程碑；入口归属的模块
   不在本草案的里程碑里；Build order 里后一个里程碑的模块排在前一个里程碑的模块之前或同一逗号组。
   **提醒项（不判失败）**：里程碑里的模块没有对应任何入口（可能拆多了，也可能是基础设施模块）。
   能力图里不属于任何草案的模块不检查（旧模块、单模块需求都是这样）。
7. **已在开发中的项目（C1）**：新来的多模块需求照样出草案，已有模块不补。没有 `spec/usage/` 的项目，`verify-artifacts` 不出这一项，
   其他输出与 0.86.7 相同；`add-module` 预览与 0.86.7 逐字相同。
8. **add-module 提醒**：项目有草案时，预览在 Build order 之后多一段：列出草案文件；锚点模块属于某个里程碑时写明是哪份草案的哪个
   里程碑；提醒「新模块属于其中某个需求时，把它加进那份草案的里程碑表，verify-artifacts 会检查顺序」。不自动改草案，`--confirm`
   仍只写能力图。
9. **规则文本**：共享检查点规则与节点规则的「能力图审阅」在「拆成哪些模块」这一小项里写明：多模块需求附用法草案（默认出、不先问；
   交审写全入口清单、典型用法与里程碑，并写出拆分核对的结论）。不新增第四个小项，`interface.json` 的 `reviewKinds` 不变；「Spec 交审」对属于草案的模块加一句「对外接口与用法草案一致吗，不一致在哪」；
   收尾文档建议写明 README 从草案展开。附模板 `templates/USAGE.md`。上游 agent-skills 不改。
10. 只改 spec-guard；发 0.87.0；不改 `interface.json`；仓库里不出现消费项目的名字、模块或编号。手册第 6 章那句话由 ecosystem-lead
    发版后去改，发版回告时说明。

## 命令

```text
python3 -B -m unittest plugins/spec-guard/hooks/test_usage_draft.py
python3 -B -m unittest plugins/spec-guard/hooks/test_module_insert.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## 项目结构

- 新增 `hooks/usage_draft.py`（解析与 `validate --project <dir>`，输出 JSON：`status` 为 `pass`／`fail`／`absent`，`failures`、`warnings`
  逐条带文件名）与 `hooks/test_usage_draft.py`；`verify-artifacts.sh` 调它，判据只在这一个文件里。
- `module-insert.py` 的预览报告调 `usage_draft.py` 取里程碑归属；读草案失败时提醒写「未读取到用法草案」，不让预览失败。
- 规则：`references/workflow-checkpoints.md`、`references/node-rules.md`；模板 `templates/USAGE.md`。
- 文档：`docs/concepts.md` 术语表（用法草案、里程碑）、`docs/commands.md`（verify-artifacts、add-module）、`docs/workflow.md`。

## 测试策略

- 先写测试并确认在 0.86.7 上失败，再实现。
- `test_usage_draft.py`：合格草案通过；假设 6 的每个失败项各一个反例，报告点名文件与具体项；提醒项不判失败；没有 `spec/usage/` 时
  `absent`；两份草案把同一模块各归一次判失败；逗号组跨里程碑判失败；表格写坏报失败而不是堆栈。
- `test-verify-artifacts.sh`：有合格草案时多一行通过；有坏草案时整体失败；没有草案时输出与 0.86.7 相同。
- `test_module_insert.py`：有草案且锚点在里程碑里时预览含提醒与里程碑名；没有草案时预览逐字不变；`--confirm` 不改草案。
- `test_workflow_checkpoints.py`（或现有规则回归）：能力图审阅有「用法草案」一项，Spec 交审有一致性一句。
- 变异（草稿副本）：去掉 Build order 顺序检查、去掉「最后里程碑覆盖全部用法」、去掉 add-module 提醒，三处都要让测试变红。

## 边界

- Always：先红后绿；能力图格式与解析器不动；没有草案的项目输出不变；草案只查结构不评内容。
- Ask first：把里程碑写进能力图（加列或加节）；让阶段提示读草案（属 milestone-stop）；`verify-artifacts` 判断入口与 Spec 内容是否一致；
  改 `interface.json`；给单模块需求也出草案。
- Never：改上游 agent-skills；add-module 自动改草案；在 Spec、代码、测试、提交信息或 PR 中写入消费项目的名称、模块或编号。

## 成功标准

- AC1：有合格草案的项目，`verify-artifacts` 多一行「用法草案」通过；没有 `spec/usage/` 的项目输出与 0.86.7 相同。
- AC2：假设 6 列出的每个失败项都被 `verify-artifacts` 报出（点名文件与具体项）并让整体失败；表格写坏不抛堆栈。
- AC3：里程碑里没有对应入口的模块只出提醒，不判失败。
- AC4：有草案时 `add-module` 预览写明草案文件、锚点所在里程碑并提醒归里程碑；没有草案时预览逐字不变；`--confirm` 不改草案。
- AC5：共享检查点规则与节点规则写明：多模块需求能力图审阅同一轮默认出用法草案（含拆分核对，写在「拆成哪些模块」小项里）；Spec 交审标出与草案是否一致；
  收尾 README 从草案展开；附 `templates/USAGE.md`。
- AC6：`capability_map.py`、`spec-digest.py`、`proposal_contract.py` 未改，既有回归全部通过；`interface.json` 未改。
- AC7：术语表、commands.md、workflow.md 写明用法草案与里程碑；版本 0.87.0。

## 文档建议

- 本模块自己的文档：术语表加「用法草案」「里程碑」；commands.md 的 verify-artifacts、add-module 段落；workflow.md 在能力图审阅一步
  加一句。README 只在命令与功能列表里提一句，不展开（完整说明等 milestone-stop 完成后一起写）。

## 待定问题

- 无。
