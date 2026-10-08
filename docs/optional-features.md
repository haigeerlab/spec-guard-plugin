# 可选能力

下面三项都**默认关闭**。不启用就不会运行，也不需要装它们的依赖。它们都不改变[使用流程](workflow.md)里的主流程。
原来的协作信箱已移到独立插件 agent-relay，见[会话协作](#会话协作已移到-agent-relay)。

| 能力 | 解决什么问题 | 适合谁 | 需要什么 |
|---|---|---|---|
| [本地事项账本](#本地事项账本) | 项目没有 GitHub/GitLab Issue 时，在本地记 bug、需求和讨论 | 私有仓库、离线项目、个人项目 | Node.js 18+；按插件自带 lockfile 装入 Epiq 运行时，连传递依赖共 270 个包 |
| [文档治理](#文档治理) | 说清楚哪些文档是项目的依据，以及每个模块对它们做了什么改动 | 文档本身也要交付、要评审的项目 | 无额外依赖 |
| [能力历史](#能力历史) | 核验旧版本归档下来的能力图和产物有没有被改动 | 从旧版 spec-guard 升级、留有归档的项目 | 无额外依赖 |

## 会话协作（已移到 agent-relay）

同一台 Mac 上 Claude Code 与 Codex 会话之间的协作信箱、统一会话路由与跨宿主会话委派，已拆成独立插件
**agent-relay**：只想让会话互相通信的项目不必再装 Spec Guard 的工作流。Spec Guard 只通过
`agent_relay_probe.py` 检测它是否可用，未安装时工作流照常运行。原先转交过去的过渡命令已于 0.54.0 移除，
请直接使用 agent-relay 的 `/agent-relay:collaboration`。安装与旧数据迁移见
[迁移说明](migrations/2026-10-07-collaboration-split.md)。

## 本地事项账本

**解决的问题：** 没有 GitHub/GitLab Issue 可用时，也能记录 bug、需求和讨论。同一个 Git 仓库的所有 worktree 共用一个账本。

**启用：** 一次性运行 `/spec-guard:local-ticket-ledger`，确认后才会安装。

**使用：**

- Claude Code：`/spec-guard:ticket`，或直接说「看看本地事项」「记一个 bug」；
- Codex：直接说 “show local tickets” 或 “record a bug”。

事项的短编号可以写进 agent-relay 的协作消息里。但另一个仓库里的 agent 看不到你的账本，发消息时要附上来源项目和问题摘要。

**不做什么：** 不持续同步远端 Issue。需要备份、恢复或逐项迁移时，使用独立的
[Local 事项归档与交接](../plugins/spec-guard/references/local-ticket-portability.md)流程；
远端写入须先预览并针对目标和内容单独授权。推送到 Git 远端也需要单独授权。

**详细说明：** [本地事项账本说明](../plugins/spec-guard/references/local-ticket-ledger-runtime.md)

## 文档治理

**解决的问题：** 需求文档、架构文档、使用手册很容易和实现脱节。文档治理不去猜文档有没有过期，而是要求你**明确声明**：

1. **基线**（`/spec-guard:documentation-baseline`）：在 `docs/DOCUMENTATION-BASELINE.md` 里列出哪些文档是项目的依据，
   以及每份文档的状态；
2. **影响**（`/spec-guard:documentation-impact`）：每个模块的 Spec 里写一张表，说明它对每份依据文档是遵循、补全、
   修改还是不涉及；
3. **核验**（`/spec-guard:documentation-verification`）：交付前只读检查这些声明是否都已收口。

没有 `docs/DOCUMENTATION-BASELINE.md` 的项目视为未启用，不会收到任何提醒。

**不做什么：** 不扫描代码，也不看 Git 历史推断文档状态；核验通过只说明声明已经收口，不代表文档内容正确。

**详细说明：** [基线](../plugins/spec-guard/references/documentation-baseline.md)、
[影响](../plugins/spec-guard/references/documentation-impact.md)、
[核验](../plugins/spec-guard/references/documentation-verification.md)

## 能力历史

**解决的问题：** 旧版 spec-guard 每批需求开一张新能力图，旧图归档在 `spec/history/`、`tasks/history/`，
由 `spec/CAPABILITY-HISTORY.json` 记录每个文件的 SHA-256。能力历史用来核验这些归档没有被改动。

**使用：** `/spec-guard:history-integrity`。

- 核验和审计只读；
- 发现记录有误时，可以在你确认后**追加**一条更正，原记录不改；
- 旧项目导入历史前，可以先只读预览。

现在每个项目只用一张能力图，不再产生新的归档。没有 `spec/CAPABILITY-HISTORY.json` 的项目用不到这项能力。
