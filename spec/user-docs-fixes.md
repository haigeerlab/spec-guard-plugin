# Spec: user-docs-fixes

<!-- spec-guard: review approved 5067155ab19f -->

## 目标

修掉 user-docs-onboarding 新手复测记下的问题和两处事实性错误，让第一次用的人在这几处不再卡住。共 10 项：两项事实错误（必改）、
七项新手卡点、一项可选的交审消息样例。

给谁用：第一次用 spec-guard 的开发者（Claude Code 与 Codex）。

登记：需求来自用户本人（2026-10-28，确认需求总结「需求说完了」），不需要回告。

## 边界

**总是做**

- 每项先对着源码、规则文件或官方源核对，核对位置记进 todo，不凭记忆写；安装命令、外部入口只按官方源写。
- 第 1、2 项改完后用插件函数实际生成一次，与文档逐字对照。
- README 中英同步改；每样内容只放一处，别处链过去。

**先问**

- 核对发现某一项按现行规则讲不通、需要改插件或规则才能写清楚时：记下来交用户决定，不在本模块改。
- 某项要改的地方超出下面 AC 列出的文件时。

**不做**

- 不改 `plugins/spec-guard/` 下的任何文件，不改版本号、不发版。
- 不演示 Plan 驳回、Spec 批准后修订的完整流程（链到 workflow.md 的变更记录说明）。
- 不改提交脚本分档（快档不跑 `test_hosted_ticket_entry.py`，属维护者工具，另行处理）。
- 不重写可选能力表里 Proposal、文档治理的「该开」。
- 不再派新手测试子代理。

## 要你确认的假设

1. **本模块会改 user-docs-align、user-docs-onboarding 刚写的段落**，这正是本模块的目的，所以那两个模块「改前一模块段落先问」的约束在这里不适用。
2. **规则里没有的东西文档不发明。** 「什么算批准」只照共享检查点规则「批准标记」一节写；「哪些检查点须标 gate」只用规则里现成的
   「不可逆或高风险」清单。
3. **Codex 对应先查再写**：查 agent-skills 在 Codex 里有没有同名入口；查不到就如实写「直接对 agent 说要写 Spec、写 Plan、开始实现」。
4. **分支** `claude/docs-fixes`，从 #418 合并后的 `main`（`462dbe05`）开出（原 Q3，已按 A 执行）；一个 PR，按 Plan 分任务提交。

## 验收标准

**事实错误**

- AC1：workflow.md「新项目」第 4 步写明 `activeModule` 由 agent 在验收获批后按阶段提示改，你不用动手；与上手文档「谁做什么」表一致。
- AC2：troubleshooting「只看到一行 spec-guard 提示」的例子与 `module_stage.brief_line` 实际生成的一行逐字一致（模块名带反引号、写「未勾选 N」）。

**新手卡点**

- AC3：README 中英「前置条件」写出 agent-skills 在 Claude Code 与 Codex 里的安装方法（按 agent-skills 官方 README 核对，链过去），并说明
  `/spec`、`/plan`、`/build` 来自 agent-skills。
- AC4：workflow.md「批准要留下记录」写清什么算批准：照共享检查点规则「批准标记」一节，明确的批准才算、「继续」不算、装了协作插件时以它为准；
  上手文档第 4 步链过去，不另写一份。
- AC5：workflow.md「少停、该停的照停」列出须标 `gate` 的「不可逆或高风险」操作清单（取自共享检查点规则或停点规则的原清单），让写 Plan 的人能对照判断。
- AC6：上手文档（或术语表的「阶段」一条）说明阶段名不随产物语言翻译，理由按实际读取方写（`/map --json` 的 `stage` 字段用同样的名字，其他插件按它读）；只写一处。
- AC7：上手文档第 8 步 `/map` 输出后说明图例（链到命令参考 map 一节已有的图例）与「N 个未就绪」默认折叠、`--all` 展开。
- AC8：写清没启用本地事项账本时 `ticket` 的实际行为（对着 `commands/ticket.md` 与 ticket skill 核对），写在 README 功能一览或可选能力一处，另一处链过去。
- AC9：上手文档写明 Codex 里与 `/spec`、`/plan`、`/build` 的对应（按假设 3）。

**可选**

- AC10（Q1 为 A 时）：上手文档第 3 步后放一段 Spec 交审消息样例：按停点规则「Spec 交审」的小项与顺序，用例子 note-store 的 Spec 写成，标明是示意、
  不是实跑输出。Q1 为 B 时改为只链到停点规则文件。

**整体**

- AC11：`/bin/bash scripts/validate.sh` 与 `test-phase-guard.sh`、`test-verify-artifacts.sh` 通过；改过的文档无断链；`git diff --stat origin/main -- plugins/spec-guard` 为空。

## 未决问题

- **Q1：要不要做第 10 项（交审消息样例）？** A（推荐）做，标明示意；B 不做，只链到停点规则。
- **Q2：README 里 agent-skills 写多少？** A（推荐）只写两个宿主的安装方法并链到 agent-skills README；B 再加几句它的用法介绍（与上游重复，易过时）。

**已定（2026-10-28，用户）：Q1 A；Q2 A。**

（原 Q3 分支已按 A 执行。）

## 文档建议

本模块本身就是文档改动。项目没有文档基线。README 要改（AC3，可能还有 AC8）。

## 变更记录

- 2026-10-28：AC6 的理由由「它们是结构关键字」改为「`/map --json` 的 `stage` 字段用同样的名字，其他插件按它读」。原因：config 说明里列出的结构关键字不含阶段名，实跑 `map_view.py --json` 确认顶层 `stage` 为阶段名；范围内修正，最终验收附差异。来源：构建中核对时发现（Task 4）。
