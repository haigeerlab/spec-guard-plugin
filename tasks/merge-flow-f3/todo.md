# Todo: merge-flow-f3

- [x] Task 0：提交 Plan 与 todo（2026-11-24 用户「Plan 批准」）
- [x] Task 1：共享规则与回归
- [x] Task 2：本仓库文档
- [x] Task 3：版本与 CHANGELOG
- [x] Checkpoint 1（report）：本机完整检查与变异
- [x] Checkpoint 2（gate）：推送、开 PR、最终验收、按新规则合并、回复两个会话

## 证据
- Task 1（2026-11-24）：先改回归，4 项变红（规则仍是旧句）；改规则三行后只剩 `test_no_remote_write_is_authorized_by_default` 红——它禁用「自动合并」，与 Spec 原句冲突。
  用户原话「断言放过新句」：检查前从全文去掉 F3 那一句，其余部分照样禁用（超出 Plan 列的三处，验收时说明）。91 例全绿；在新句外追加「默认自动合并。」→ 该用例变红，已还原。
- Task 2（2026-11-24）：用户没回是否派给 Codex，按无肯定答复处理，在本会话改：release-process 第 4 条（长期授权原文保留，末句改为「照常按上面问用户」）、dev-flow-v2 第 58 行、README 第 223 行。
- Task 3（2026-11-24）：两份清单升 0.95.0；validate 要求两份 README 的安装命令 `--ref` 与清单一致，同步改为 v0.95.0（README.en.md 超出并行边界，验收时说明）。首次完整检查另有 `test_map_view.test_text_table_unchanged` 跨分钟边界的偶发失败（22:11 对 22:12）。
- Checkpoint 1（2026-11-24，提交 1be4855 上，macOS `/bin/bash`，`verify-and-commit` 完整档）：`validate.sh`「校验通过 ✅」；phase-guard「passed (541 cases)」；verify-artifacts「passed (120 cases)」。
  变异（各自还原，`git status` 干净）：第 137 行改回旧句 → `test_workflow_checkpoints` 3 失败 2 错误；删掉「任何 Plan 都不能代替用户这句话。」→ 2 失败 2 错误。
- Spec 修订（2026-11-24，规范 v1.5.1：必需检查已全部通过时 GitHub 拒绝 `--auto`）：用户原话「两项都批准」（F3 第 3 步改为先看 PR 状态；`README.en.md` 补进并行边界）。
  review-mark 重记 Spec 批准（`ab5b52151991`）。先改回归 → 2 失败 1 错误；改规则第 137 行、release-process 第 4 条、CHANGELOG 后 91 例全绿；
  删掉「必需检查已全部通过时直接合并（GitHub：`gh pr merge`），」→ 回归变红，已还原。
- Checkpoint 2（进行中）：PR #488。9050d67 上 CI：`plugin`、`python (3.9)`、`python (3.13)` 通过；`validate` 只失败于 `test_proposal_promotion_proof.OtherRowPromotionTests` 的 `copytree` 撞上
  `objects/maintenance.lock`（已知偶发，与本模块无关，另有会话提议），`CI required` 随之失败；已重跑失败任务。v1.6 第 0 步按用户「另开小模块」记账本 EVQX96F。
- Checkpoint 2（2026-11-24）：重跑后 9050d67 上五项全绿（CI required、validate、plugin、python 3.9／3.13），PR 状态 CLEAN。
  用户原话「验收通过，合并」（针对 AC1～AC6 证据、文件表与提交表、两处超出 Plan 的说明、Spec 的 v1.5.1 修订差异、给 ecosystem-lead 与 mc-coord 的拟回告）。
  v1.7 按用户「v1.7 放小模块」记账本 EVQX96F。合并按 F3：本提交推送后 CI 重跑，用 `gh pr merge --auto --squash`。
