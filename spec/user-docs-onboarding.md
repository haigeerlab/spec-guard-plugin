# Spec: user-docs-onboarding

<!-- spec-guard: review approved 931f33bb4fd1 -->

## 目标

让第一次接触 spec-guard 的人只读文档就能决定要不要装、并自己走完第一个模块。2026-10-28 一个不知道背景的子代理以新手身份读
README 及其链接的文档，最大的三个缺口是：没有能力图样例（只能从故障排查的报错表倒推格式）、分不清「我做什么／agent 自动做什么」、
不知道各项可选能力什么时候该开。user-docs-align 已把现有文档对齐到 0.85.0；本模块补这些**新增内容**。

给谁用：已经在用或打算用 agent-skills、还没用过 spec-guard 的开发者，Claude Code 与 Codex 都要覆盖。

登记：需求来自用户本人（2026-10-28，确认需求总结「需求说完了」），不需要回告。

## 边界

**总是做**

- 例子里的阶段提示、`verify-artifacts` 与 `/map` 输出都在临时项目里实跑后原样贴入，不手写；实跑的命令记进 todo。
- 说法先对着源码或现有文档核对，核对位置记进 todo。
- README 中英同步改；新文档只写中文（与 `docs/` 现状一致）。

**先问**

- 要改 user-docs-align 刚改过的段落（而不只是加链接）时。
- 发现文档讲不通、需要改插件行为或提示文字才能讲清楚时：记下来交用户决定，不在本模块改。

**不做**

- 不改 `plugins/spec-guard/` 下的任何文件，不改版本号、不发版。
- 不录视频、不放截图；不为了例子好写去改提示文字。
- 不改写维护者文档，不改历史记录目录。
- 例子用虚构项目，不出现任何其他私有项目、模块或 issue 的名字。

## 要你确认的假设

1. **上手例子单独成页**（Q1 暂按 A）：新建 `docs/getting-started.md`，README「快速开始」末尾加一句指过去；README 本身不放长例子。
2. **例子项目是虚构的 3 模块小项目**，例如一个记事应用：`note-store`（存储）→ `note-api`（接口，依赖存储）→ `note-cli`（命令行，依赖接口）。
   只写到第一个模块的最终验收为止，后两个模块只出现在能力图里；够说明全流程，又不至于太长。
3. **例子用中文产物语言**（`artifactLanguage` 为 `zh-CN`），因为这一页是中文；页内提一句英文项目的提示是英文。
4. **对照表与选用指引放在上手文档里**，术语放进现有 `docs/concepts.md` 的术语表，Codex 话术放进 `docs/commands.md` 文末的命令对照（Q2 暂按 A）。
   每样东西只放一处，别处链过去。
5. **module-crew 只写分工、不写安装**（Q3 暂按 A）：它没有公开仓库，README 写「运行层（开会话、建 worktree、合并）由 module-crew 负责；
   spec-guard 不依赖它，没装时并行开关只打开规划层的规则」。
6. **一个模块、一个 PR**（Q5 暂按一个模块），按 Plan 分任务提交；分支 `claude/docs-onboarding`，从 #417 合并后的 `main` 开出（Q4 已按 A 执行）。

## 验收标准

- AC1：`docs/getting-started.md` 存在；README 中英「快速开始」末尾都有指向它的一句；README「架构与文档导航」的使用者一组列出它。
- AC2：上手文档给出例子项目完整的 `spec/CAPABILITY-MAP.md`（`## 目标`、模块表、Build order），并写明这份能力图在临时项目里
  `verify-artifacts` 结果为 0 失败。
- AC3：上手文档说明 agent-skills 的 `/spec` Phase 0 与 spec-guard 能力图的关系：上游给模板但不定文件名，spec-guard 固定路径为
  `spec/CAPABILITY-MAP.md`、要求恰好一张 `Module id`／`Responsibility`／`Depends on` 表和一行 Build order，模块 Spec 放 `spec/<id>.md`
  而不是项目根。每条对着 `docs/upstream-analysis.md` 与能力图解析器核对。
- AC4：上手文档给出第一个模块的最小 Spec（含 AC 编号）、带 `gate`／`report` 检查点的 `plan.md` 与 `todo.md`，并按步骤贴出每一步的
  阶段提示（至少 `MAP_ONLY`、`NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、最终验收前、`MODULE_DONE`），全部为实跑输出。
- AC5：上手文档有「你做什么／agent 自动做什么」对照表，至少覆盖：确认需求、批准能力图／Spec／Plan、写批准标记（review-mark）、
  勾 todo、切换 `activeModule`、变更记录、最终验收、推送与合并、回告、记账；每行写谁触发、你需不需要输入命令。
- AC6：上手文档有功能选用指引：Proposal、本地事项账本、多模块并行、文档治理、项目指向、挂起，每项写「该开」「别开」「怎么开」各一句；
  另有一段「只用 agent-skills、不装 spec-guard 时会碰到什么」，对着 `docs/concepts.md` 与 `docs/upstream-analysis.md` 的说法写，不夸大。
- AC7：`docs/concepts.md` 术语表补上：gate、report、检查点、激活信号、停点规则、预先声明、并行边界、自治档位、Build order 逗号组、
  零足迹模式、Epiq；每条一两句，写清是什么、在哪看到；已有条目不改，除非与现行行为矛盾。
- AC8：`docs/commands.md` 文末命令对照的 Codex 一列改为可以直接对 agent 说的一句话（例如「用 spec-guard-ops 查看阶段」），每句对着
  `spec-guard-ops` 等 skill 的实际小节名核对；原来「某 skill 的某一节」的写法不再出现。
- AC9：README 中英新增「功能一览」：按「约定与阶段／加需求／事项／文档治理与历史／报告／多模块并行」分组，每条命令一行一句话，
  链到命令参考；多模块并行一节按假设 5 写 module-crew 的分工。
- AC10：换一个不知道背景的子代理，只读 README 和它链接的文档重做新手测试：照上手文档写出的能力图在临时项目里 `verify-artifacts`
  0 失败；上次「最想要的三样东西」都能在文档里找到。结论原样记进 todo，新发现的问题列出，不在本模块里扩大范围处理。
- AC11：`/bin/bash scripts/validate.sh` 通过；改过的文档相对链接无断链；`git diff --stat origin/main -- plugins/spec-guard` 为空。

## 未决问题

- **Q1：上手例子放哪？** A（推荐）新建 `docs/getting-started.md`，README 指过去；B 直接写进 README，README 会长很多。
- **Q2：Codex 话术放哪？** A（推荐）改 `docs/commands.md` 命令对照的 Codex 一列；B 单独一页。
- **Q3：module-crew 怎么写？** A（推荐）只写分工、不写安装（它没有公开仓库）；B 你给出安装来源，再写一句怎么装。
- **Q5：要不要拆成两个模块？** A（推荐）一个模块，六项都在回答「新手怎么上手」；B 拆成「上手例子＋对照表」与「选用指引＋术语＋话术＋README 一览」两个模块，
  每次交审短一些，但要多走一轮 Spec、Plan、验收。

**已定（2026-10-28，用户）：Q1 A；Q2 A；Q3 A；Q5 A。**

（Q4 分支已按 A 执行：#417 合并后从 `main` 开出 `claude/docs-onboarding`。）

## 文档建议

本模块本身就是文档改动。项目没有文档基线。README 要改（AC1、AC9）。

## 变更记录
