# Plan: docs-refresh

<!-- spec-guard: review approved -->

依据 [`spec/docs-refresh.md`](../../spec/docs-refresh.md)。本仓库评审节奏为分开审：Spec 已单独批准，本 Plan 单独交审。
分支 `claude/docs-refresh`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `899b715`（v0.63.1 发版证据合并）
开出。本模块一个 PR；只改文档，不改版本号、不发版、不写 CHANGELOG（先例 #316）。

所需工具：无 UI 改动，不需要浏览器或电脑操作；Task 3 需要联网读上游仓库（只读）。

已完成的前置：仓库的私密漏洞报告已于 2026-10-16 经用户同意用 `gh api` 开启，读回 `{"enabled":true}`。

## Overview

六处文档改动，每个任务改一组互不重叠的文件，各自提交：命令数、术语表、上游核对、审查报告、SECURITY.md、数据与隐私。
最后一次模块评审，推送与开 PR 由用户确认，合并由用户进行。

## Architecture Decisions

- **事实先核对再落笔。** 术语、隐私说明、收口状态都对着源码、git 历史或 PR 记录写，每条的依据记在 todo 对应任务里；
  查不到的写“未查到”，不推测。
- **中英 README 同步改。** 同一任务里两份一起改，结构保持一一对应。
- **历史内容不动。** 审查报告只在末尾追加，`spec/`、`tasks/`、`docs/releases/` 的历史内容不改。

## Task List

### Task 0：提交已批准的产物

能力图新行、已批准的 Spec、本 Plan 与 todo 一次提交。

- 验收：`verify-and-commit.sh` 快档通过并提交。

### Task 1：去掉命令总数（R1）

`README.md`、`README.en.md`、`docs/commands.md` 里“21 条命令／all 21 commands”改为不带数字的说法。核对 `docs/commands.md`
覆盖 `plugins/spec-guard/commands/` 的全部 24 条（每条有说明、命令对照表有对应行），缺的补上。

- 验收：三个文件里 `grep -nE '[0-9]+ ?(条|commands)'` 不再命中命令总数；24 条命令名在 `docs/commands.md` 里都能找到。

### Task 2：术语表补 7 个概念（R2）

`docs/concepts.md`「术语」表补：评审标记与批准指纹、评审节奏、挂起、插队与暂停、进度表与关键卡点、变更记录与回告、项目指向。
每条的说法对照对应命令文件或 `references/workflow-checkpoints.md`；顺带核对已有条目，与现行行为矛盾的才改。

- 验收：7 个概念都在术语表里；todo 里记下每条依据的文件。

### Task 3：重新核对上游（R3）

取上游 `addyosmani/agent-skills` 当前 HEAD（浅克隆到 scratchpad，只读），按 `docs/upstream-analysis.md` 现有核对项逐项比对，
每项写“未变／有变化但不影响／有变化且影响”。更新“末次核对”日期与上游 commit；“最低上游版本”若要改，同步改 README 中英里
引用它的地方。发现影响插件行为的变化时，只在文档里写明，并在交审时提出另开模块。

- 验收：末次核对与 commit 是本次的值；每个核对项都有结论；临时克隆已删除。

### Task 4：审查报告索引与收口状态（R4）

`docs/reports/README.md`「当前报告」补两份 2026-10-04 报告，按日期倒序。`2026-10-08-architecture-audit.md` 末尾追加「收口状态」，
20 条发现逐条写收口的版本或 PR，依据取自 CHANGELOG、git 历史与 PR 记录。

- 验收：目录下每份报告都在索引里；20 条都有状态或“未查到”。

### Task 5：SECURITY.md（R5）

新增仓库根目录 `SECURITY.md`：支持的版本、通过 GitHub 私密漏洞报告报告（不要公开提 issue）、范围、回应预期。README 中英
「开发、贡献与反馈」各加一行链接。

- 验收：文件存在，链接可达；不含个人邮箱。

### Task 6：数据与隐私一节（R6）

README 中英各新增「数据与隐私／Data and privacy」，回答读什么、写什么、何时联网、统计与上传。写之前逐条核对源码：钩子读写哪些
路径（`phase-guard.sh`、`session_context.py` 等）、哪些命令调用 `gh`／`glab` 或其他网络访问、`cost-report` 读哪些会话记录、
有无任何上报。依据记在 todo。

- 验收：四个问题都有答案，每条在 todo 里有源码位置；中英结构一致。

### Checkpoint 1（gate）：模块评审

列出实际改动的文件（取自版本库）、验证结果、未验证项与文档建议；拟回告为“无”（需求来自用户本人）。推送与开 PR 在此由
用户确认，合并由用户进行。

- 验收：`/bin/bash scripts/validate.sh` 全档通过；用户确认推送与开 PR。

## 影响面

只改 `README.md`、`README.en.md`、`SECURITY.md`（新）、`docs/commands.md`、`docs/concepts.md`、`docs/upstream-analysis.md`、
`docs/reports/README.md`、`docs/reports/2026-10-08-architecture-audit.md`，以及本模块的 Spec、Plan、todo 与能力图。
不改 `plugins/`，不进插件包。

## Risks and Mitigations

- **README 内嵌约定块被误改。** `check-readme-sync.py` 校验 README 里的约定块与模板一致；新节放在约定块之外，提交前跑校验。
- **隐私说明说多了或说少了。** 逐条对源码核对，拿不准的写保守说法并在交审时列为未验证项。
- **上游变化大到要改代码。** 本模块只记录，交审时提出另开模块，不扩大本模块范围。
- **收口状态找不到依据。** 写“未查到”，不补推测。

## Open Questions

- 无。
