# Todo: pre-build-spec-batch

- [x] Task 0：提交 Plan 与 todo — 2026-11-20 用户批准 Spec（「批准」，能力图与 Spec 在批准后先行提交）与 Plan（「Plan 批准」）；能力图插入经用户「确认插入」。
- [x] Task 1：`spec_baseline` 与 `pre_build_batch`，单元测试 — `module_stage.spec_baseline()` 沿 Spec 最近 50 个提交从新到旧找指纹与批准标记一致的版本（原样字节解码，不经 `_git` 的 strip），返回 found／absent／unverified（不在 git 工作区或 git 出错为 unverified 带原因；还没有提交为 absent）；`pre_build_batch()` 只在 Spec 为 revised 且 NEEDS_PLAN 或 BUILDING＋Plan pending 时返回基线。新增 `test_spec_baseline.py` 6 例，实现前导入即失败，实现后通过；`validate.sh` 登记。
- [x] Task 2：阶段提示接开工前攒批（中英两套、节点规则种类） — `review_hint` 中英两套接 `pre_build_batch`：有基线时批准行写基线短 sha，建议下一步换成「记变更记录、照常写 Plan、交审附累计差异、`--target both` 一起记」并列出 E1–E4 当场停；NEEDS_PLAN 无基线或未判定时保留原提示并加一句原因；BUILDING＋Plan 待批准且无基线时保持原来的构建中提示（Spec 假设 3「无基线时与现在逐字相同」）。`stop_node` 有基线时不再给 spec-review，NEEDS_PLAN 附 Plan 交审规则。`test-phase-guard.sh` 新增第 26 段 4 例（PARTS=26），524 例通过；临时 zh-CN 项目手看中文措辞正确。
- [x] Task 3：`review-mark` 的累计差异预览与拒绝文字 — 记 Spec 批准（`--target spec` 或 `both`）且 Spec 读作 revised 时，预览先打印相对基线的累计差异（去掉标记行后的正文比较，`fromfile` 带基线短 sha）；无基线或未判定时写一行原因并要求把改过的 Spec 全文给用户看；`--target plan` 照旧拒绝，revised 时多一句改用 `--target both` 并先给用户看累计差异。`test_review_marker.py` 新增 3 例，实现前 3 失败，实现后通过。
- [x] Task 4：规则（workflow-checkpoints、node-rules）与规则回归 — `workflow-checkpoints.md`「批准标记」删去「还没开工时 Spec 被改，照旧交用户复审」，新增一条「开工前的修订攒到 Plan 交审一次批」（累计差异、`--target both`、基线从 git 取、Spec 获批后先提交再改、取不到退回当场复审、E1–E4、第一次批准与最终验收照旧）；`node-rules.md`「Plan 交审」加累计差异一条。`test_workflow_checkpoints.py` 新增 1 例（89 例通过），`test_stop_rules.py` 新增 1 例（基线 found／absent／unverified 三种的节点种类，21 例通过）；`validate.sh --quick`（含各节字节上限）通过。
- [ ] Task 5：说明文字（review-mark 命令、ops 技能、workflow）
- [ ] Task 6：版本号 0.90.0 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查、变异验证与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：打 tag、发 Release 并立即通知 ecosystem-lead、刷新两个宿主、证据收尾 PR，回告 autopr-design
