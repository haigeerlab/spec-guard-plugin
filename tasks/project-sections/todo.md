# Todo: project-sections

- [x] Task 0：提交 Plan 与 todo
- [x] Task 1：projectSections 配置键、校验与 set，回归
- [ ] Task 2：追加章节的检查与提示，回归
- [ ] Task 3：骨架与配置说明、0.94.0、CHANGELOG、README
- [ ] Checkpoint 1（report）：完整检查、变异与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行
- [ ] 延期：合并后发 0.94.0 并通知 ecosystem-lead 与 S110 各方；恢复条件：本模块的 PR 合并进 main

## 外部审查意见

- Plan 经 Codex（/delegate:review，对照 project_config.py、module_stage.py）审两轮：第 1 轮 5 条阻断，改进后第 2 轮 0 条阻断，按 takeover=plan 记 codex-approved（轮次行见 plan.md）。第 1 轮引出 Spec AC4 修订，用户 11-24「批准 AC4 修订」。
  第 2 轮建议：测试说明「前两类之外」易误读——实现时写成「bug、small 均忽略 design、regression 的追加章节」。

## 证据

- Checkpoint 1 的检查结果、变异与实跑记在这里。
