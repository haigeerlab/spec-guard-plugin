<!-- spec-guard: build-task-dispatch -->
- 执行 `todo.md` 中非 Checkpoint 的 task 时，以下情况由主代理自己做、不派：任务块缺验收标准或验证步骤；
  属于停止条件（spec 未覆盖的决策、高风险或不可逆）；L3；为子代理选的模型不比你自己的模型便宜
- 其余用 `spawn_agent` 交给**一个**子代理，子代理只做 RED → GREEN → 全量回归 → 构建，不提交、不勾选；派活
  prompt 写入该 task 的完整任务块（描述、验收标准、验证、依赖、涉及文件；todo 只有一行时从 plan.md 取）、plan.md
  的 Architecture Decisions 与模块 spec 路径，并另起独占一行写档位标记，形如 `<!-- tier-guard: tier=L2 -->`
  （L1 机械、只读；L2 单模块内、验收明确的实现；L3 跨模块、有歧义、高风险或不可逆；有 `tier-routing` 时以它为准；
  重试时加 `failures=N`；todo 行已带标记则原样带上）。tier-guard 在 Codex 上（含交给 Codex worker 的派活）读不到
  标记，只作建议
- 子代理遇到停止条件（测试改不绿、spec 未覆盖的决策、高风险或不可逆操作）时原样交回，不自行越过；
  主代理验收 diff，只暂存该 task 动过的文件与勾选，提交、勾选，需要问人时由主代理问；
  上一个 task 提交、勾选完再派下一个，提交受阻时先解决提交或停下问人，不派下一个
