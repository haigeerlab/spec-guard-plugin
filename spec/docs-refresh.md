# Spec: docs-refresh

<!-- spec-guard: review approved 5857a6beb4d7 -->

## Objective

2026-10-16 对仓库文档做了一次整体盘点（只读）：`docs-reorganization`（2026-10-09）建立的文档体系大体完整，但有四处已与现状
不符，另缺两份公开仓库应有的说明。

不符的四处：

1. README（中英）与 `docs/commands.md` 写“21 条命令”，`plugins/spec-guard/commands/` 实有 24 条。
2. `docs/concepts.md` 的术语表停在 2026-10-07，之后加入的概念（评审标记与批准指纹、评审节奏、挂起、插队与暂停、进度表与
   关键卡点、变更记录与回告、项目指向）查不到定义。
3. `docs/upstream-analysis.md` 末次核对 2026-09-30，对的是上游 `addyosmani/agent-skills` 的 `2686b62`；上游 HEAD 已到
   `aeac41d4`。插件依赖上游的若干结构，上游变了而文档没核对，等于不知道插件是否还成立。
4. `docs/reports/README.md` 的“当前报告”漏了两份 2026-10-04 的报告；`2026-10-08-architecture-audit.md` 只有发现与修复顺序，
   没写各项已在哪个版本收口，读者会以为高危问题还开着。

缺的两份：

5. **安全策略**：仓库公开，钩子每轮自动运行，却没有私下报告漏洞的渠道，只能公开提 issue。
6. **数据与隐私说明**：插件读哪些本地数据、什么时候联网，现在散在 `docs/design.md` 等处，使用者和做安装审查的人找不到。

登记：2026-10-16 经 `/spec-guard:add-module` 插入能力图。需求来自用户本人（要求整体检查文档并按清单 1–6 全部处理），
不需要回告。

## Assumptions

用户已于 2026-10-16 确认：

1. **只改文档**：改动都在 `plugins/spec-guard/` 以外，不改插件行为、不改版本号、不发版（先例：#316）。合并后模块即完成。
2. **核对上游只记结论，不改代码**：重新核对发现插件依赖的上游结构变了时，在 `upstream-analysis.md` 里如实写明差异与影响，
   另开模块处理代码；本模块不改代码。
3. **命令数不再写死**：README 中英与 `docs/commands.md` 改为“全部命令”之类不带数字的说法，而不是把 21 改成 24。
   理由：数字每加一条命令就会过时，这次就是这么过时的；`docs/commands.md` 本身逐条列出，读者不需要总数。
4. **安全报告渠道用 GitHub 私密漏洞报告**：`SECURITY.md` 指向仓库 Security 页的 “Report a vulnerability”。该功能目前
   **未开启**（`gh api .../private-vulnerability-reporting` 返回 `enabled: false`）。用户同意由 agent 用 `gh api` 开启，
   开启后读回确认。不在文件里公开任何个人邮箱。
5. **隐私说明放 README 一节**（中英各一），不另建文件；细节链接到 `docs/design.md`。每条说法都对着源码核对，核对位置记在
   todo 里，不凭记忆写。
6. **审查报告补状态不改原文**：在 `2026-10-08-architecture-audit.md` 末尾追加一节「收口状态」，逐条写已在哪个版本或 PR
   收口；原有的发现与证据不改。
7. **一个 PR**，按 Plan 分任务提交。

## Requirements

### R1 命令数

- `README.md`、`README.en.md`、`docs/commands.md` 中“21 条命令／all 21 commands”改为不带数字的说法（按假设 3）。
- 改完后三处与 `plugins/spec-guard/commands/` 的实际命令一致：`docs/commands.md` 每条命令都有说明，命令对照表覆盖全部命令。

### R2 术语表

`docs/concepts.md` 的「术语」表补下列条目，每条一两句，写清是什么、在哪看到、对应哪条命令：

- 评审标记（待审核／已批准）与批准指纹（批准后被改报告“批准后已修订”）
- 评审节奏（`separate`／`combined`）
- 挂起（`module-suspend`，与“暂停”的区别）
- 插队与暂停（`add-module --interrupt`）
- 进度表与关键卡点（`map`）
- 变更记录与回告
- 项目指向（`link-project`）

已有条目不改，除非与现行行为矛盾（矛盾时改，并在 todo 里写明改了哪条、为什么）。

### R3 上游兼容性

- 按 `docs/upstream-analysis.md` 现有的核对项，逐项对上游当前 HEAD 重新核对，更新“末次核对”日期与上游 commit。
- 每项写结论：未变／有变化但不影响／有变化且影响（写明影响什么，按假设 2 另开模块）。
- “最低上游版本”一句若需要改，同步改 README 里引用它的地方。

### R4 审查报告

- `docs/reports/README.md` 的「当前报告」补上 `2026-10-04-a10-native-promotion-readiness.md` 与
  `2026-10-04-native-only-collaboration-closeout.md`，各一句说明，按日期倒序排列。
- `2026-10-08-architecture-audit.md` 末尾追加「收口状态」：20 条发现逐条写收口的版本或 PR；查不到证据的如实写“未查到”，
  不推测。

### R5 SECURITY.md

仓库根目录新增 `SECURITY.md`（中文，与其他文档一致），包含：

- 支持的版本：只修最新发布版。
- 怎么报告：GitHub 私密漏洞报告（按假设 4）；不要公开提 issue。
- 范围：本仓库的钩子、脚本、命令与技能；上游 agent-skills、agent-relay 等其他仓库的问题去对应仓库报。
- 回应预期：一句话说明，不承诺具体时限（单人维护）。

README 中英的「开发、贡献与反馈」一节各加一行链接到它。

### R6 数据与隐私

README 中英各新增一节「数据与隐私／Data and privacy」，回答四个问题：

1. 读什么：钩子读项目里的能力图、Spec、Plan、todo、`.agent/` 配置与 git 引用；读宿主给的会话记录只为取上下文大小。
2. 写什么：钩子不写文件；命令只在你确认后写，写在哪里。
3. 什么时候联网：哪些命令会访问 GitHub／GitLab（Proposal 与托管事项相关），用的是本机 `gh`／`glab` 的登录；其余不联网。
4. 统计与上传：`cost-report` 离线读本机的 Claude Code 与 Codex 会话记录统计用量，结果只打印、不上传；插件没有遥测。

每条说法写进 README 前先对着源码核对；与源码不符时以源码为准，必要时改写说法，不为了写得好看而夸大。

## Commands

```bash
/bin/bash scripts/validate.sh --quick
/bin/bash scripts/verify-and-commit.sh -- -m "<信息>"
git ls-remote https://github.com/addyosmani/agent-skills HEAD
```

## Boundaries

- Always：命令与参数以 `plugins/spec-guard/commands` 为准；隐私说明的每条说法对源码核对；提交走 `verify-and-commit.sh`。
- Ask first：推送、开 PR；删除任何文档；改 `plugins/` 下任何文件。
- Never：改插件行为或版本号；在任何文件里写个人邮箱；在文档、提交或 PR 里写其他私有项目的名称；改 `spec/`、`tasks/`、
  `docs/releases/` 里的历史内容。

## Success criteria

1. README 中英与 `docs/commands.md` 不再出现会过时的命令总数，且覆盖全部 24 条命令。
2. R2 列出的 7 个概念都能在 `docs/concepts.md` 的术语表里查到。
3. `upstream-analysis.md` 的末次核对日期与上游 commit 是本次核对的值，每个核对项都有结论。
4. `docs/reports/README.md` 列出目录下全部报告；架构审查报告每条发现都有收口状态。
5. `SECURITY.md` 存在，私密漏洞报告已开启并读回为 `enabled: true`。
6. README 中英都有数据与隐私一节，四个问题都有答案，每条有源码依据。
7. `validate.sh` 通过。

## Open questions

- 无。
