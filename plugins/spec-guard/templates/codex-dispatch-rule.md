<!-- spec-guard: build-task-dispatch -->
- 执行 `todo.md` 中非 Checkpoint 的 task 时，用 `spawn_agent` 把它交给**一个**子代理，子代理只做
  RED → GREEN → 全量回归 → 构建，不提交、不勾选；派活 prompt 写入该 task 原文、模块 spec 路径，并另起
  独占一行写档位标记，形如 `<!-- tier-guard: tier=L2 -->`（按 `tier-routing` 判断 L1/L2/L3；重试时加
  `failures=N`；todo 行已带标记则原样带上）。tier-guard 在 Codex 上（含交给 Codex worker 的派活）读不到
  标记，只作建议
- 子代理遇到停止条件（测试改不绿、spec 未覆盖的决策、高风险或不可逆操作）时原样交回，不自行越过；
  主代理验收 diff，只暂存该 task 动过的文件与勾选，提交、勾选，需要问人时由主代理问
