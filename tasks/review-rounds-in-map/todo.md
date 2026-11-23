# Todo: review-rounds-in-map

- [x] Task 0：提交能力图新行、Spec、Plan 与 todo
- [x] Task 1：codex_round_records 与 /map --json 的 reviewRounds，先写回归
- [x] Task 2：接口 1.17、check-interface、docs/commands.md、0.93.0 版本号、CHANGELOG、README
- [x] Checkpoint 1（report）：完整检查、变异与实跑
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行
- [ ] 合并后：核实合并、发 0.93.0、通知 ecosystem-lead、字段格式发 autopr-design 抄送 ecosystem-lead（记下 Release 地址、证据 PR、消息号）

2026-11-24 用户「验收通过」（同时批准修订后的 Spec：sha256 改为被审文件指纹）。

## 证据

- Checkpoint 1（2026-11-23，提交 fb4858d 上的 verify-and-commit 全套）：`validate.sh` 退出 0「校验通过 ✅」；`test-phase-guard.sh` 退出 0「phase-guard regression passed (536 cases)」；
  `test-verify-artifacts.sh` 退出 0「verify-artifacts regression passed (105 cases)」；`check-interface.py` 退出 0「interface.json 与代码一致」，`interface.json` 为 1.17。
  另：`interface.json` 的单轮键改成 `digest` 时 `check-interface.py` 退出 1（已还原）。
- 变异（各自还原）：`reviewRounds` 写死为空 → ReviewRoundsTest 4 例失败（clean_round、reviewed_but_not_approved、revision_keeps、two_blocking）；丢掉 sha256 → 同 4 例失败；
  不跳过代码块 → `test_no_lines_missing_files_and_fenced_examples` 失败。
- 本仓库实跑 `/map --json`：本模块 `reviewRounds.plan` = round 1 blocking 4 `51d90b14d2df`、round 2 blocking 3 `73c0d0f0121f`，与 plan.md 的轮次行一致；`reviewRounds.spec` = `[]`。
- 实跑中发现：轮次行的 sha256 是被审 Plan 内容的 sha256（两份报告 `scope.files` 里 plan.md 的值正是 `51d90b14d2df`、`73c0d0f0121f`），不是报告文件的哈希
  （两份报告文件的 sha256 前缀为 `b73f70ab3f21`、`6de4cabd9b02`）。已把 Spec 假设 2、能力图职责、Plan、接口说明、CHANGELOG、docs/commands.md、代码注释里的「报告 sha256」改为「被审文件 sha256」；Spec 与 Plan 因此变为修订，最终验收时请用户一起批。

## 外部审查意见

- Plan 经 Codex（/delegate:review）审两轮：第 1 轮 4 条阻断、第 2 轮 3 条阻断，均已改进 Plan（轮次行见 plan.md）；按两轮上限转用户，2026-11-23 用户「Plan 批准」。
