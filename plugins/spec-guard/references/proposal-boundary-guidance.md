# Proposal boundary guidance

`guide("module-deliver")`、`guide("module-advance")` 与 `guide("module-interrupt")`（半途的当前模块被显式插队打断时使用，见 /spec-guard:add-module --interrupt）返回同一组非阻断
Proposal 入口：`intake`、`review`、`promotion-proof`。其他工作事件返回
`not-applicable`，因此日常执行中不会出现候选池提醒。

这个结果只提示下一步，既不会读取也不会保存任何候选。它不会创建或修改 Issue、
讨论、PR、分支、任务、Proposal、能力图或 `.agent/state.json`，也不调用
`spec-github-bridge` 或 `/sync-map`。

- `intake`：用 `proposal-contract` 记录独立需求。未合并到远端默认分支的草稿不是共享
  Proposal，也不是待执行任务。
- `review`：依次运行 `proposal-publication`、`proposal-tracker-read` 和
  `proposal-review`。共享事实只来自固定的远端默认分支，以及 GitHub/GitLab 的只读
  Proposal Issue/讨论；本地、缓存或其他 worktree 不能替代。
- `promotion-proof`：在一次新的 `accepted` review 之后运行
  `proposal-promotion-proof`。`accepted` 与 `promoted-claim` 都不是自动授权，proof
  结果也不会回写 tracker。

`as_json(guidance)` 只提供状态、原始 boundary 和稳定 entry id，不包含需求、Proposal、
能力图、Issue/评论、URL、token、临时路径或异常详情。

调用方明确声明 mainline 时，同一边界额外提示 mainline-candidates、
mainline-review 和 promotion-preflight。声明只影响提示，不能取代后续
mainline policy、Git 拓扑与远端 snapshot 的实际核验。
