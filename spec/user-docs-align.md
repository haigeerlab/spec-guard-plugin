# Spec: user-docs-align

<!-- spec-guard: review approved de0584f0a664 -->

## 目标

2026-10-28 对使用者文档做了一次只读核对（对照 CHANGELOG 0.69.0～0.85.0 与源码），并让一个不知道背景的子代理以新手身份
从 README 读起。发现 13 处说法过时或与现行行为不符（A1～A13），8 处结构与写法问题（B1～B8）。本模块把这 21 处改掉，
让使用者读到的文档与 0.85.0 的实际行为一致、主线读得顺。

新手视角提出的新增内容（端到端上手例子、「你做什么／agent 做什么」对照表、功能选用指引、术语补全、Codex 话术清单）
不在本模块，之后另开模块。

登记：需求来自用户本人（2026-10-28，要求核对功能与文档是否对齐、以使用者身份读 README，选定先修 A 与 B），不需要回告。

## 边界

**总是做**

- 每处改动先对着源码或 CHANGELOG 核对现行行为，核对位置记进 todo，不凭记忆写。
- 中文 README 与英文 README 同步改，结构保持一致。
- 只改错的和放错位置的；没问题的段落不顺手改写。

**先问**

- 要删掉一整节（而不只是移动或压缩）时。
- 发现本清单以外、需要改插件行为才能对齐的不一致时：记下来交用户决定，不在本模块改代码。

**不做**

- 不改 `plugins/spec-guard/` 下的任何文件（命令、技能、模板、references、hook），不改版本号、不发版（先例：docs-refresh）。
- 不改 `docs/decisions/`、`docs/releases/`、`docs/reports/`、`docs/retirements/`、`docs/migrations/`、CHANGELOG 旧条目这类历史记录。
- 不改维护者文档（`design.md`、`maintainer-workflow.md`、`release-process.md`、`lenses.md`、`upstream-analysis.md`）。
- 不做 C 类新增内容（见目标）。

## 要你确认的假设

1. **只改插件包以外的文档，不发版。** 插件包内也有两处同类问题：`commands/config.md` 的「从本版起」与它 frontmatter 描述
   漏了自治档位。它们会随插件分发，改了就要发版，所以不在本模块，记进 todo 末尾的「留给下一个发版模块」。
   见未决问题 Q1。
2. **README 不展开自治档位。** autonomy-tier 模块当时定过「README 不加档位说明，用户从 config 说明里查」。所以 README 常用
   命令表里 config 一行改为不列全部键的说法（「产物语言、批准节奏等，全部键见命令参考」），只在 `docs/commands.md` 的
   config 表补上 `autonomyTier`。这样以后再加键也不会过时。
3. **「项目级审查后处理缺陷」一节压缩，不搬家。** 这一节（workflow.md 93～125 行）是 agent 规程，细则已在共享检查点规则里。
   改为几句给使用者的说明（审查会先限定范围、报告怎样算「审查完成」、它不等于缺陷已修复、发现的缺陷怎样入账）加链接；
   混在里面讲 `--replace` 的那段（99～102 行）移到「最终验收少一轮确认」附近讲约定块升级的地方，与其合并。
4. **链到仓库自用 `spec/` 的两处分开处理。** `/map --json` 的字段说明改为指向插件的 `interface.json`（`mapView`），不再链
   `spec/map-view.md`；Proposal 实例链接保留，因为它已写明是「本仓库的实例」，且是唯一的真实样例。
5. **版本历史残留只删「从哪一版起」的叙述，保留现象和处理。** 例如 README 安装表里 Codex 那一格的升级说明移到「更新」一节；
   troubleshooting 的 `/compact` 那一行去掉 0.57.1 的来历，只留「这是消息框命令，不是终端命令」。
6. **一个 PR**，按 Plan 分任务提交。

## 验收标准

**A 类：过时与不符**

- AC1：`docs/commands.md` 的 config 表有 `autonomyTier`（取值、默认 `strict`、一句作用、指向 config 命令说明）；README 中英
  config 一行改为不列全部键的说法（假设 2）。
- AC2：workflow.md 有一段讲 Plan 可选的 `## 预先声明`：写什么、批准 Plan 即授权所列公共改动、哪些不能预先声明；
  `docs/commands.md` 的 verify-artifacts 一节写明会校验这一节的格式。
- AC3：workflow.md 的快速插入步骤与阶段表 `DONE` 一行写明「先总结需求、问你说完没有，确认后才插入」。
- AC4：workflow.md 与 `docs/commands.md` 不再说「上下文接近上限时提醒」，改为只在模块边界提醒，并写明 Claude 读不出 1M 窗口时不提醒。
- AC5：`docs/commands.md` 的 phase 一节写明平时每轮只注入一行（`spec-guard: <阶段> · …`），什么时候给完整内容；
  troubleshooting 新增一条「只看到一行 spec-guard 提示」，说明这是正常的、怎么看完整内容。
- AC6：troubleshooting「其他提示」表有 `Project config: ignored`，写明只忽略那个键、其余照常。
- AC7：troubleshooting 的 hook 信任说明与 README 一致（`UserPromptSubmit` 加两项 `SessionStart`）。
- AC8：concepts.md 设计原则表不再说「Proposal 流程不创建或修改 Issue……和能力图」，改为如实描述：读取只读，晋级写能力图，
  收尾经授权才改标签并关闭 Issue。
- AC9：README 中英多模块并行一节不再出现「从本版起」这类相对版本说法，改成具体版本号。
- AC10：`docs/commands.md` 的 verify-artifacts 一节列出它实际检查的各项（能力图结构、Spec 与能力图对应、根目录 `SPEC*.md`、
  批准标记、并行边界与预先声明格式、挂起标记、任务目录里不计入阶段的清单项、有 Plan 没 todo 等），每项对着 `verify-artifacts.sh` 核对。
- AC11：workflow.md「一个需求拆成几个模块时，可以一次审完」加上前提「你明确要求时」，与同页的「一次只交一个模块」不再矛盾。
- AC12：workflow.md 补上四项用户看得到的行为：验收标准按 AC1、AC2… 编号；中文检查点写法（如「最终验收（gate）」）也能识别；
  最终验收用表格列改动文件，并列出本模块的提交；交审的推荐答复放在可复制代码块里。每项一两句，放进现有对应段落。
- AC13：README 中英「对外接口」一节不再只提 1.1，改为不列版本细节、指向 `interface.json` 与 design.md。

**B 类：结构与写法**

- AC14：workflow.md「项目级审查后处理缺陷」按假设 3 压缩，讲 `--replace` 的那段移出并合并。
- AC15：workflow.md「新项目：从零到交付」的编号步骤连续，账本与 PR 对账那段移到步骤之后、单独加小标题；第 84 行那段按主题拆开。
- AC16：Codex 的说法全文统一（README、workflow、troubleshooting 用同一句「用 spec-guard-ops 在这个项目里安装约定」这类写法）。
- AC17：`docs/commands.md` 开头不再让读者去读插件源码目录；`/map --json` 的字段说明按假设 4 改为指向 `interface.json`。
- AC18：convention-block.md 去掉写给维护者的同步检查脚本说明（改为一句「下面与插件模板一致」）。
- AC19：按假设 5 去掉 README 安装表里的升级说明（移到「更新」一节）和 troubleshooting 里 0.57.1 的来历。
- AC20：README 中英「数据与隐私」第一条拆成几条短句，每条一种情形，内容不增不减。

**整体**

- AC21：`/bin/bash scripts/validate.sh` 通过（含 README 中英同步、约定块同步、旧词回归）；文档内的相对链接都能指到存在的文件和锚点。
- AC22：`plugins/spec-guard/` 下无改动（`git diff --stat origin/main -- plugins/spec-guard` 为空）。

## 未决问题

- **Q1：插件包内的两处（`commands/config.md` 的「从本版起」与 frontmatter 描述）怎么办？**
  - A（推荐）：本模块不改，记进 todo，等下一个要发版的模块顺带改。代价：在那之前 agent 读到的 config 说明里仍有一句相对说法。
  - B：本模块一起改，发 0.85.1。代价：要走一遍完整发版流程（打 tag、Release、两个宿主的证据）。
  - **已定（2026-10-28，用户）：A。**

## 文档建议

本模块本身就是文档改动。项目没有文档基线。README 要改（AC1、AC9、AC13、AC19、AC20）。

## 变更记录
