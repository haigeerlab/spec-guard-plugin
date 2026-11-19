# Todo: pre-build-spec-batch

- [x] Task 0：提交 Plan 与 todo — 2026-11-20 用户批准 Spec（「批准」，能力图与 Spec 在批准后先行提交）与 Plan（「Plan 批准」）；能力图插入经用户「确认插入」。
- [x] Task 1：`spec_baseline` 与 `pre_build_batch`，单元测试 — `module_stage.spec_baseline()` 沿 Spec 最近 50 个提交从新到旧找指纹与批准标记一致的版本（原样字节解码，不经 `_git` 的 strip），返回 found／absent／unverified（不在 git 工作区或 git 出错为 unverified 带原因；还没有提交为 absent）；`pre_build_batch()` 只在 Spec 为 revised 且 NEEDS_PLAN 或 BUILDING＋Plan pending 时返回基线。新增 `test_spec_baseline.py` 6 例，实现前导入即失败，实现后通过；`validate.sh` 登记。
- [ ] Task 2：阶段提示接开工前攒批（中英两套、节点规则种类）
- [ ] Task 3：`review-mark` 的累计差异预览与拒绝文字
- [ ] Task 4：规则（workflow-checkpoints、node-rules）与规则回归
- [ ] Task 5：说明文字（review-mark 命令、ops 技能、workflow）
- [ ] Task 6：版本号 0.90.0 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查、变异验证与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：打 tag、发 Release 并立即通知 ecosystem-lead、刷新两个宿主、证据收尾 PR，回告 autopr-design
