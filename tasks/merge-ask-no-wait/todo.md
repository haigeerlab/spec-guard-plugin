# Todo: merge-ask-no-wait

- [x] Task 0：提交 Plan 与 todo（2026-11-25 用户「Plan 批准」）
- [x] Task 1：回归先红后绿，改共享规则、node-rules、release-process 与 CHANGELOG
- [x] Checkpoint 1（report）：本机完整检查与变异
- [x] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并（含本机三套与 CI required 结果）、按 F3 合并、补记 CI 结论

## 证据
- Task 1（2026-11-25）：先写两条回归跑红（`test_merge_timing_and_ci_waiting` 找不到新段而报错；`test_final_gate_asks_to_merge_with_the_acceptance` 断言失败），
  改共享规则（F3 那行之后另起一个物理行）、`node-rules.md`、`docs/release-process.md` 第 4 条与 CHANGELOG 后，`test_workflow_checkpoints` 92 例、`test_stop_rules` 22 例全绿；
  其中原有 `test_no_remote_write_is_authorized_by_default`（新段仍过禁用词检查）与 `ORIGINALS` 一组照常通过。
  注入：阶段提示到最终 gate 时由 `module_stage.py` 第 970 行取 `node_rules("final-gate")`；`module_stage.py . --node-rules final-gate` 输出第 14 行即新的一条。
- Checkpoint 1（2026-11-25，提交 4a128deb 上，macOS `/bin/bash`，完整档）：`validate.sh`「校验通过 ✅」（264s）；phase-guard「passed (541 cases)」；
  verify-artifacts「passed (120 cases)」；repo-artifacts 0 失败。同一提交的第一次完整档因机器负载 24～41 让 `test_map_view` 两例子进程超时（30 秒），
  单独重跑 113 例全绿，第二次完整档通过；这次改动没碰 `map_view`。
  变异（AC4，临时脚本逐个删掉锁住的短语、跑对应用例、还原）：共享规则新段 16 个短语、`node-rules.md` 4 个短语，20 个全部变红；还原后 `git status` 干净。
- Checkpoint 2（2026-11-25，PR #491）：推送 99601b38、开 PR；开 PR 后提议 Auto-fix，用户没开。最终验收按新规则与合并合成一问，用户原话「验收通过并合并」（AC6 第一步）。
  验收时 PR 上 `CI required` 还在跑，没有自己等；本提交推送后按 F3 开 `--auto --squash`，合并结果与 CI 结论在下次被叫醒时核实补记。

## 外部审查意见

- 第 1 轮（2026-11-25，Codex，Plan，5 条阻断，已记 codex-reviewed）：
  1. 规则点名了 Auto-fix，违反 Spec 假设 3 → 采纳：规则文字去掉「例如 Claude 桌面版的 Auto-fix」，例子只留在 Spec。
  2. 只取标题那一行、锁的短语不全、变异只有两项，验证不了 AC4 → 采纳：写明新段是一个物理行；补锁「验收通过并合并」「提议打开」「记下合并提交再告诉用户」等；
     变异改为对每个短语逐一删掉再还原。
  3. 和两条现有回归兼容的依据没写 → 采纳：Plan 写明禁用词检查删掉的范围和 `ORIGINALS` 比较的内容，Task 1 跑这两组确认。
  4. 检查点漏了 PR 上 `CI required` 的证据（AC5）→ 采纳：Checkpoint 2 的验收证据要包含它，没跑完就照实写。
  5. 回告和关闭账本超出 Spec「会做」、宿主监控没写批准步骤 → 采纳：回告改为按最终验收的拟回告规则、由用户批准验收时同意；关闭账本写明只是本机记账；
     Checkpoint 2 加上「宿主有 PR 监控时提议，用户批准才开」。
- 第 2 轮（2026-11-25，Codex，带上一轮报告复查，已记 codex-reviewed）：第 1 条已解决，第 2～5 条仍判未解决，没有新问题。两轮仍有阻断，按规则交用户。
  交用户前又补了三处：回归再锁「选后者之后照旧再问一次合并」；验收证据写明本机三套各自的结果，CI 没跑完时之后补记结论；
  回告和关闭账本移出检查点，验收时单独交用户。第 3 条（看不到测试代码，无法核实兼容）属审查范围所限：Plan 已写明两组现有回归在 Task 1 实跑确认。
