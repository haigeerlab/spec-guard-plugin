# Plan: ledger-local-only

<!-- spec-guard: review approved -->

依据 [`spec/ledger-local-only.md`](../../spec/ledger-local-only.md)。本仓库评审节奏为分开审：Spec 已单独批准，本 Plan 单独交审。
分支 `claude/ledger-local-only`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，叠在 `claude/v0.63.5-evidence`（证据 PR #331，
未合并）之上：main 上 `boundary-hint-70` 的“发版后的验证”要等 #331 合并才算勾上，否则 add-module 会拒绝。#331 合并后本分支的 PR
只含本模块的改动；开 PR 前先确认 #331 已合并，未合并就把 PR 的 base 说清楚。本模块一个 PR，含 0.64.0 版本号。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

`local_ledger_runtime.py` 三处行为（先红后绿，各一个 task），入口文档与 Spec 补句，CHANGELOG 与版本号。

## Architecture Decisions

- **推送屏蔽只走子进程环境。** 新增一个小函数生成 `local_only` 的环境（复制 `os.environ`，在已有 `GIT_CONFIG_COUNT` 之后追加
  `remote.origin.pushurl`），只在 `initialize_project` 传给 `mcp_tool_call`；不带 `local_only` 时仍传 `None`（与现在一致）。
  推送地址用一个不存在的本地路径（如 `/nonexistent/spec-guard-local-only`），git 在本机立即失败，不联网。
- **status 的两项都是附加字段。** `pendingEvents` 只在状态工作树 `owned` 时计算；`identityElsewhere` 只在 `uninitialized` 时计算。
  都用独立函数，读失败返回 `None`／不出字段，`state` 与返回码的判定不碰。
- **测试沿用现有夹具。** status 两项用 `StateWorktreeOwnerTests` 的真实临时仓库；preflight 用真实临时仓库加假 origin；initialize 打桩
  `mcp_tool_call` 看传入的环境。现有断言若比较整个 `project` 字典，因新增字段而需同步更新，在 todo 里如实记录。

## Task List

### Task 0：提交已批准的产物

能力图新行、已批准的 Spec、本 Plan 与 todo 一次提交。

- 验收：`verify-and-commit.sh` 快档通过并提交。

### Task 1：`--local-only` 预检与初始化（先红）

测试：preflight 四种组合（有 origin + local_only → ready / `disabled-local-only`；两者同给 → invalid；都不给 →
`push-confirmation-required` 且 `localOnly: available`；无 origin + local_only → 结果不变）；initialize 带 local_only 时传给
`mcp_tool_call` 的环境含三个变量、已有 `GIT_CONFIG_COUNT=1` 时追加为第 2 条（索引 1）、返回 `upstreamPush: disabled-local-only`；
不带时 `environment` 仍为 `None`；CLI `--local-only` 透传到 preflight 与 initialize，两者同给时 CLI 报 invalid。先红，再改实现转绿。

- 验收：新用例全绿，现有用例不改（除因新增字段需更新的整字典比较）；变异（不追加环境变量）变红。

### Task 2：status 报告未提交事件数（先红）

测试（`StateWorktreeOwnerTests` 夹具）：owned 工作树里两个 `~pending` 文件共 N 个非空行 → `pendingEvents == N`；只有已提交的事件文件
→ 0；`.epiq/events` 不存在 → 0；事件目录不可读 → `None` 且 `state` 不变；文本输出 `未提交到状态分支的事件：N 条`，N > 0 时多一行
离线归档提醒，N = 0 时没有。先红，再实现转绿。

- 验收：新用例全绿；变异（计数恒为 0）变红。

### Task 3：标识在别的分支上，与初始化后的提示（先红）

测试：仓库 A 的当前分支没有 `.epiq/project.json`、另一个本地分支有 → `identityElsewhere` 为该分支名，文本有说明行；只有
`__epiq_state__` 上有 → 无字段；哪里都没有 → 无字段；git 查询失败 → 无字段且 state 不变。initialize 成功的文本输出含“合进默认分支”
一行，`local_only` 时含“未推送”。先红，再实现转绿。

- 验收：新用例全绿；变异（去掉跨分支查询）变红。

### Checkpoint 1（report）：三套核心回归与账本测试全绿，ShellCheck 无警告（若改 `.sh`）

随 Task 3 的提交跑 `verify-and-commit.sh` 全档。

### Task 4：文档、Spec 补句、CHANGELOG 与版本号

`commands/local-ticket-ledger.md`、`skills/local-ticket-ledger-ops/SKILL.md`、`references/local-ticket-ledger-runtime.md` 开头写“本地使用
不需要任何推送”，推送确认处改为推荐 `--local-only`、说明 `--allow-epiq-push` 只在要推送时用；补 `autoSync` 关闭时事件不进 git、
status 的未提交事件数与离线归档、`.epiq/project.json` 要合进默认分支。`commands/ticket.md` 与 `skills/ticket/SKILL.md` 补 Claude 带
`repoRoot`、选非只读泳道。`spec/local-ticket-ledger.md` 推送确认那条补第三种选择并记变更来源。CHANGELOG `[0.64.0]`；两份
`plugin.json` 与 README 中英 `--ref` 改为 0.64.0。

- 验收：`validate.sh` 通过（含 README 同步与清单一致性）。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

在正文列出实际改动的文件（取自版本库）、各项行为前后对比、验证结果、未验证项、文档建议与拟回告（对象：会话
「ent-relay插件使用观测」`local_b1a6b3c6-e6c2-424b-9871-4cd370f89657`；渠道：宿主会话消息；时机：0.64.0 装上之后）。

- 验收：用户确认推送与开 PR。

### 发版后的验证

两边升级到 0.64.0。临时仓库配本机裸仓库作 `origin`，用安装好的运行时跑 `preflight --local-only` 与 `initialize --local-only`：
裸仓库 `git for-each-ref` 为空、当前分支没有上游。对本机一个已有账本跑 `status`，看未提交事件数。如实记录，回告来源会话。

## 影响面

`plugins/spec-guard/hooks/local_ledger_runtime.py`、`test_local_ledger_runtime.py`、`commands/local-ticket-ledger.md`、
`skills/local-ticket-ledger-ops/SKILL.md`、`references/local-ticket-ledger-runtime.md`、`commands/ticket.md`、`skills/ticket/SKILL.md`、
`spec/local-ticket-ledger.md`、CHANGELOG、两份 `plugin.json`、README 中英，以及本模块的 Spec、Plan、todo 与能力图。

## Risks and Mitigations

- **Epiq 用别的方式推送（不经 `origin` 这个远端名）。** 已读源码：初始化用 `git push -u origin HEAD` 与按远端名推状态分支；发版后
  用本机裸仓库实测兜底，有引用出现即判失败。
- **pending 计数读大文件慢。** 只数行数、按块读；账本事件文件目前百 KB 级。
- **跨分支查询在分支很多的仓库里慢。** 用一次 `for-each-ref` 列出后逐个 `cat-file -e`，找到第一个即停。

## Open Questions

- 无。
