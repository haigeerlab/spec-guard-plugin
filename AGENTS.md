# AGENTS.md

本仓库的 agent 配置见 [CLAUDE.md](CLAUDE.md)。

作用域：配置在**本仓库**（spec-guard 插件源码）工作的 agent，
不是给使用者复制到自己项目里的。使用者需要的是
`plugins/spec-guard/templates/claude-block-*.md`，由 `/setup-convention` 写入。

<!-- BEGIN:spec-guard-codex-convention -->
## Spec Guard 项目约定

> `spec/CAPABILITY-MAP.md` 是整个插件唯一的能力图；新需求经 Proposal 按锚点插入模块，不另建图。
> `.agent/state.json` 只是本地 active-module 上下文，不是 Proposal 状态。

- 能力图：`spec/CAPABILITY-MAP.md`；模块 spec：`spec/<module-id>.md`
- Proposal 共享事实只来自远端默认分支；GitHub/GitLab 仅可作为只读 Proposal Issue 来源。
- Proposal 不调用旧 tracker bridge，不创建或修改 Issue、PR、分支、任务或 `.agent/state.json`。
- 退役 Spec 与 Plan 位于 `docs/retirements/`，不加入当前能力图。
- Plan 的检查点标 `gate`（停下等确认）或 `report`（记入 todo 后继续），未标注按 `gate`；按需求批量前置审与
  UI 自验按 `spec-guard:spec-guard-ops` 的共享检查点规则
- 产物语言与评审节奏以 `.agent/config.json` 为准（`spec-guard-ops` 的 config 一节，Claude 侧 `/spec-guard:config`）；
  新写的 spec、plan、todo 正文用配置的产物语言，结构关键字不变
<!-- END:spec-guard-codex-convention -->
