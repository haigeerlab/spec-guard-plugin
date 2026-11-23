# Todo: review-rounds-in-map

- [x] Task 0：提交能力图新行、Spec、Plan 与 todo
- [x] Task 1：codex_round_records 与 /map --json 的 reviewRounds，先写回归
- [x] Task 2：接口 1.17、check-interface、docs/commands.md、0.93.0 版本号、CHANGELOG、README
- [ ] Checkpoint 1（report）：完整检查、变异与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行
- [ ] 合并后：核实合并、发 0.93.0、通知 ecosystem-lead、字段格式发 autopr-design 抄送 ecosystem-lead（记下 Release 地址、证据 PR、消息号）

## 证据

- Checkpoint 1：四条检查的退出码与末行、三次变异各自失败的断言、实跑结果记在这里。

## 外部审查意见

- Plan 经 Codex（/delegate:review）审两轮：第 1 轮 4 条阻断、第 2 轮 3 条阻断，均已改进 Plan（轮次行见 plan.md）；按两轮上限转用户，2026-11-23 用户「Plan 批准」。
