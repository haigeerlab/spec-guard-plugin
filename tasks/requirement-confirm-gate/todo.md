# Todo: requirement-confirm-gate

- [x] Task 0：提交 Plan 与 todo（Plan 经 Codex 两轮仍有阻断，转用户批；2026-11-24 用户「Plan 和修订都批准」）
- [x] Task 1：新流程需求文档的批准路由与待确认提示，回归
- [x] Task 2：requirement_confirm、/map --json 字段、接口 1.19，回归
- [x] Task 3：verify-artifacts 对 Codex 批准的警告，回归
- [x] Task 4：共享检查点规则「需求确认」一节
- [x] Checkpoint 1（report）：完整检查、变异与实跑
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行

## 证据

- Checkpoint 1（2026-11-24，提交 b2a1022 上，macOS `/bin/bash`）：`validate.sh` 退出 0「校验通过 ✅」；`test-phase-guard.sh` 退出 0「phase-guard regression passed (541 cases)」；
  `test-verify-artifacts.sh` 退出 0「verify-artifacts regression passed (120 cases)」；`check-interface.py`「interface.json 与代码一致」（1.19）。
- 变异（各自还原）：Codex 批准对新流程也算（去掉 `codex_route` 的 requirement 分支、`requirement_wait` 不认 codex）→ 7 例失败（`RequirementConfirmHintTest` 的 Codex 两例与状态码、`RequirementConfirmFieldTest` 的四种状态与 review-mark 拒绝、map 的两例）；
  `revised` 当 `confirmed` → 3 例失败（`test_confirmed_and_revised`、`test_four_statuses`、`test_revised_with_a_baseline_is_not_batched`）。
- 本仓库新旧比对（旧代码取自 692d33b^）：`/map --json` 去掉 `requirementConfirm` 后逐字相同（194 个模块该字段全为 null）；阶段提示逐字相同；verify-artifacts 输出与退出码逐字相同；表格只有生成时间不同。
- 临时项目实跑（工作区代码，`takeover` spec=codex）：需求文档只有 Codex 批准时提示「只有 Codex 的批准，需求要用户在对话里确认」并给复述、拷问与 review-mark，verify-artifacts 警告不失败；
  review-mark 记 `codex-approved` 退出 2「codex-route-requirement」；用户批准并提交后 `requirementConfirm` 为 confirmed／user／提交时间／12 位指纹，`codexRoute.spec` 为 requirement，表格「需求 ✔」、待批准无，下一步转技术方案；
  确认后改文档变 revised，提示要用户重新确认。
- 偏离：Task 3 与 Task 4 合成一个提交 b2a1022（verify-and-commit 拒了 Task 3 那次——工作区有 Task 4 未暂存改动，我用 `| tail` 吞掉了失败码），内容已过全套检查，提交信息已改为写两个任务；Task 4 的断言在改规则之后才写。


2026-11-24 用户「验收通过」。

## 外部审查意见

<!-- spec-guard: external-review declined -->
- Plan 经 Codex 审两轮（轮次行见 plan.md），第 2 轮仍有阻断，转用户批（11-24「Plan 和修订都批准」）；最终验收未另做外部审查。
