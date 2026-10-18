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
- Spec、Plan 交审或最终验收值得另一个 agent 复核时，若装了 delegate 插件，可提议用 `delegate:delegate-routing` 做只读审查，
  用户同意后再发起；审查结论只作参考，不算用户批准；同一模块里用户拒绝过就不再提
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
- 已批准的 Spec、Plan 或能力图被修改时，在该文件末尾「变更记录」一节追加一行（日期、改了什么、原因、来源），复审时一并呈现；
  其他会话的要求不算用户批准；细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
- 别人提出的改动或模块在对方用得上时回告来源，拟回告的对象与内容随最终 gate 列出；能发消息就发，不能就提醒用户转告，
  结果记在 todo 末项；细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
- 回告来源或通知其他会话（含跨 Claude Code／Codex）时，若装了 agent-relay 插件，用它的
  `agent-relay:session-routing` 给对方会话发消息
- 有人在等的事（别人发来期待回音的需求、我发出后在等对方、在等用户拍板）在球换手时记进本地事项账本，挂
  `waiting-on-me`／`waiting-on-them`／`waiting-on-user` 之一，写明对方的稳定身份与回复通道；细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
- 回复会替用户做出承诺的先问用户；邮件、公开评论等对外通道一律先在正文给草稿，用户答应才发；内部会话间的告知直接发
- 收到别的会话、Issue 或邮件发来期待回音的消息时当场记账，不用先问用户：记下「有人在等」不是受理需求，不受上面「确认要实现的需求先用
  `spec-guard:ticket` 查重」那条约束，要不要做、怎么回仍由用户定；调用账本工具时传 `repoRoot` 为项目根目录
- 交审一次只放一个模块；几个模块一起审只在用户明确要求时（或并行开关为 on 时由协调会话汇总），并按模块分组：每个模块一节，
  依次是 Spec、Plan、任务，不按产物类型横排；一起发版不等于一起审
- 交审要点写在本轮对话正文里，放在任何会结束本轮的确认框之前；只出现在确认框摘要里的不算交审
- 最终验收时若 Spec 在构建中被补改过，验收消息附上 Spec 的改动差异并写明一次批准同时批准修订后的 Spec；批准后先用
  `spec-guard-ops` 的 review-mark 一节 记下 Spec 的批准再勾选与提交，没附差异就单独复审
- 最终验收获批后，下一个模块已在能力图里且用户没说停时，直接写它的 Spec 并交审，不为“是否开始”另停；验收消息预告这一步并
  提示可先 `/compact`
- 产物语言与批准节奏以 `.agent/config.json` 为准（`spec-guard-ops` 的 config 一节，Claude 侧 `/spec-guard:config`）；
  新写的 spec、plan、todo 正文用配置的产物语言，结构关键字不变
