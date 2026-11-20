# Todo: compact-hint-gate

- [x] Task 0：提交 Plan 与 todo — 2026-11-20 用户批准 Spec（「批准」）与 Plan（「Plan 批准」）；能力图插入经用户「确认插入」。
- [x] Task 1：规则与规则回归 — `workflow-checkpoints.md`「验收后接着写下一份 Spec」删去 `/compact` 半句，改为同一轮接着写、不结束本轮，没给读数时不说上下文很长、不建议压缩；连续构建一段末句改为「用户随时可以自己发 `/compact` 或 `/clear`，agent 不为此停下」；`node-rules.md`「最终验收」最后一条同改。`test_workflow_checkpoints.py` 改断言（正反），改规则前 3 失败，改后 89 例通过。
- [x] Task 2：`docs/workflow.md`「验收之后接着做下一个模块」删去「想先释放上下文，就先发 `/compact`」，改为同一轮接着写、不为压缩停下，压缩提示只在上下文达到窗口 70% 时由阶段提示给出、用户也可随时自己发；断言加进 `test_workflow_checkpoints.py`（改前 1 失败，改后通过）。
- [ ] Task 3：版本号 0.90.1 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查与变异验证
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：打 tag、发 Release 并立即通知 ecosystem-lead、刷新两个宿主、证据收尾 PR
