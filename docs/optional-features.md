# 可选能力

下面四项都**默认关闭**。不启用就不会运行，也不需要装它们的依赖。它们都不改变[使用流程](workflow.md)里的主流程。

| 能力 | 解决什么问题 | 适合谁 | 需要什么 |
|---|---|---|---|
| [协作信箱](#协作信箱) | 同一台 Mac 上的 Claude Code 和 Codex 会话之间传话，不用人工复制粘贴 | 同时开多个 agent 会话分工的人 | macOS、Node.js |
| [本地事项账本](#本地事项账本) | 项目没有 GitHub/GitLab Issue 时，在本地记 bug、需求和讨论 | 私有仓库、离线项目、个人项目 | Node.js 18+ |
| [文档治理](#文档治理) | 说清楚哪些文档是项目的依据，以及每个模块对它们做了什么改动 | 文档本身也要交付、要评审的项目 | 无额外依赖 |
| [能力历史](#能力历史) | 核验旧版本归档下来的能力图和产物有没有被改动 | 从旧版 spec-guard 升级、留有归档的项目 | 无额外依赖 |

## 协作信箱

**解决的问题：** 让一个 agent 把消息直接发给另一个会话，比如让 Codex 帮 Claude 审一段代码，结果自动回到信箱，
不用人在两个窗口之间来回复制。

**启用：** 在 Claude Code 里运行 `/spec-guard:collaboration` 查看状态。初始化、启动后台服务、接入 Claude 或 Codex，
每一步都要你明确同意才会执行，每一步也都有对应的移除命令。

**使用：** 用自然语言即可，比如「加入本机联调」「查看联调消息」「告诉 reviewer 这个 PR 可以看了」。

**两种传输方式：**

- **XATS**：默认方式，只在本机回环地址监听，令牌放在 `~/.spec-guard/collaboration/`。消息会保存在信箱里，
  但不会主动唤醒空闲的会话。
- **native**：实验性方式，要经过单独审批的切换才能启用。它可以唤醒空闲的 Claude Code 和 Codex Desktop 会话；
  唤醒失败时，消息仍留在信箱里等待读取。

**注意：** 加入协作默认不绑定唤醒（`wake: null`），只有你在对话里明确要求才会绑定；开着自动批准的会话永远不要绑定。被唤醒的会话会不经人工确认就执行消息里的请求。

**不做什么：** 不改 Git 和 Issue，不分派任务，不跨机器通信。

**详细说明：** [协作运行时说明](../plugins/spec-guard/references/collaboration-runtime.md)

## 本地事项账本

**解决的问题：** 没有 GitHub/GitLab Issue 可用时，也能记录 bug、需求和讨论。同一个 Git 仓库的所有 worktree 共用一个账本。

**启用：** 一次性运行 `/spec-guard:local-ticket-ledger`，确认后才会安装。

**使用：**

- Claude Code：`/spec-guard:ticket`，或直接说「看看本地事项」「记一个 bug」；
- Codex：直接说 “show local tickets” 或 “record a bug”。

事项的短编号可以写进协作消息里。但另一个仓库里的 agent 看不到你的账本，发消息时要附上来源项目和问题摘要。

**不做什么：** 不同步远端 Issue。推送到 Git 远端这类高风险操作需要单独授权。

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
