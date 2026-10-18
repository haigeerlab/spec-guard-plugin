# AGENTS.md

本仓库的 agent 配置见 [CLAUDE.md](CLAUDE.md)。

作用域：配置在**本仓库**（spec-guard 插件源码）工作的 agent，
不是给使用者复制到自己项目里的。使用者需要的是
`plugins/spec-guard/templates/claude-block-*.md`，由 `/setup-convention` 写入。

<!-- BEGIN:spec-guard-codex-convention -->
## Spec Guard 项目约定

> 由 `setup-convention local --host=codex` 生成。

- 能力图：`spec/CAPABILITY-MAP.md`；模块 spec：`spec/<module-id>.md`
- 每个模块隔离使用 `tasks/<module-id>/plan.md` 和 `tasks/<module-id>/todo.md`
- 活跃模块在 `.agent/state.json` 的 `activeModule`；不要共用 `tasks/plan.md`
- 若项目已启用 Local 事项账本，确认要实现的需求或修复在动代码前先用 `spec-guard:ticket`
  查重并取得事项 ID；探索和无需追踪的小操作例外
- 项目级审查按 `spec-guard:spec-guard-ops` 的共享检查点规则限定批次、收束发现并交接缺陷；
  审查完成后的“继续”推进已预告的问题处理步骤，不重新泛扫
- 明确选用 GitHub/GitLab 普通 Issue 时，用 `spec-guard:hosted-ticket-workflow` 逐项查重、授权写入与交付对账；
  Local 事项仍走 `spec-guard:ticket`，不凭 Git remote 改目标
- 阶段交接或停止时，加载 `spec-guard:spec-guard-ops` 的共享检查点规则，预告已授权下一步。
- Plan 的检查点标 `gate`（停下等确认）或 `report`（记入 todo 后继续），未标注按 `gate`，范围内能自动判定的中间检查点可标 `report`；
  按需求批量前置审与 UI 自验按 `spec-guard:spec-guard-ops` 的共享检查点规则
- 交审 Spec 或 Plan 时在对话里呈现内容要点并写明这次批准授权什么，只给链接不算交审；细则见
  `spec-guard:spec-guard-ops` 的共享检查点规则
- 任务改到用户看得到的界面时，不论 Plan 是否预计到，都在这个任务里打开页面对照预期验证，写清看了哪个页面、对照了什么、
  看到了什么；做不了就记为“UI 未验证”并说明原因；细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
- 模块最终验收时在对话里列出实际改动的文件（新增、修改、删除与行数，取自版本库），任务做完的结果带文件数与提交号；
  细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
- 能力图审阅、每个模块的 Spec 交审、能力图全部完成时各提一次文档建议（README 默认在候选里），没有就写“无”；
  细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
- 同一模块、同一目标因外部原因（上游未修复、缺权限、要用户取舍）第二次过不去，或第二次为它报批时停下，把挂起（并
  先开可开工模块）、接受风险、换方案等选项与代价交用户决定，不按默认推荐继续重试；细则见 `spec-guard:spec-guard-ops`
  的共享检查点规则
- Spec 的验收标准按 AC1、AC2… 编号，最终验收按编号给证据；细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
- 写出 Spec 或 Plan 交审时在文件里标批准标记 `pending`；用户明确批准后才用 `spec-guard-ops` 的 review-mark 一节
  （Claude 侧 `/spec-guard:review-mark`）记为 `approved`，Spec 修订后须复审，细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
- 产物语言与批准节奏以 `.agent/config.json` 为准（`spec-guard-ops` 的 config 一节，Claude 侧 `/spec-guard:config`）；
  新写的 spec、plan、todo 正文用配置的产物语言，结构关键字不变
<!-- BEGIN:spec-guard-local -->
> `spec/CAPABILITY-MAP.md` 是整个插件唯一的能力图；新需求经 Proposal 按锚点插入模块，不另建图。
> `.agent/state.json` 只是本地 active-module 上下文，不是 Proposal 状态。
- Proposal 共享事实只来自远端默认分支；GitHub/GitLab 仅可作为只读 Proposal Issue 来源。
- Proposal 不调用旧 tracker bridge，不创建或修改 Issue、PR、分支、任务或 `.agent/state.json`。
- 退役 Spec 与 Plan 位于 `docs/retirements/`，不加入当前能力图。
<!-- END:spec-guard-local -->
<!-- END:spec-guard-codex-convention -->
