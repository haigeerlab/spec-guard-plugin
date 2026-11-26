# Todo: remove-context-hint

- [x] Task 0：提交 Spec 批准、能力图新行、Plan 与 todo（2026-11-26 用户「批准；Q1 A；Q2 A」）
- [x] Task 1：AC1 回归先红，再删提示、读数与无人值守判断
- [ ] Task 2：文档、英文提示比对脚本与 CHANGELOG
- [ ] Checkpoint 1（report）：完整档、变异与老输出比对
- [ ] Checkpoint 2（gate）：推送、开 PR、最终验收并同时问合并

## 证据
- Task 0（2026-11-26）：能力图插入 remove-context-hint；Spec 批准（「批准；Q1 A；Q2 A」）；Plan 经 Codex 两轮：第一轮 3 条阻断＋1 条建议全部采纳，第二轮余 1 条未证实、新 1 条，交用户「按改法改，批准」。
- Task 1（2026-11-26，executor 子代理实现，主会话核对）：先写回归，改前 `test-phase-guard.sh` 两段红（part_22 高读数一行模式多出第二行；新 part_32 MODULE_DONE 800k 带边界行），`test_session_context.py` 21 条失败（三行输出与 `_is_compaction` 尚不存在）。再删：`module_stage.py` 的 `thresholds`、`boundary_line`、`_k`、各宿主 `free-next` 与只为它存在的 8 个常量、`_describe_body` 三处追加与 `describe` 的附带逻辑、四个参数；`session_context.py` 的 `_count`、`_usage`、`_window`、`context_tokens`、`context_usage`、`STANDARD_WINDOW`、`over_standard_window`、`unattended`，`_compacted` 改为 `_is_compaction`，普通模式输出三行；`phase-guard.sh` 按三行解析，删读数、窗口与无人值守变量。旧用例：只测这条提示本身的删掉，无人值守、高读数场景改成「与低读数逐字相同」，位置行、压缩后提醒、收件记账、状态码的断言保留。结果：phase-guard 516 例、test_session_context 35 例、test_flow_v2 144 例、verify-artifacts 147 例、ShellCheck 全部通过。全仓 `git grep session_context.py`：普通模式只有 `phase-guard.sh:301` 一个读取方（R1-2）。
- Task 2 进行中（2026-11-26）：`evals/hint-english-diff.sh` 删 claude-850k、codex-230k 两个变体与夹具（比对照样通过）；`docs/commands.md`、`docs/workflow.md`（两处）、`docs/design.md`（两处）、`commands/phase.md`（三处）改为不再有上下文提醒；CHANGELOG「未发布 · 移除」一条。AC4 检索另发现 `references/workflow-checkpoints.md:555` 那段规则还在讲这条提示，该文件不在并行边界内，停下问用户。
