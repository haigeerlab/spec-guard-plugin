# Todo: codex-approval

- [x] Task 0：提交 Plan 与 todo — 2026-11-22 用户批准 Spec（「批准；Q6 A」）与 Plan（「Plan 批准」）。
- [x] Task 1：codex_review.py 报告校验与单测 — 按 delegate 接口 1.5（delegate-owner #21973；字段以 delegate 仓库 `spec/integration-interface.md` 与 `review_result.py` 核对：`scope.files` 为路径→sha256，`severity` 取 blocking／suggestion）新增 `hooks/codex_review.py` 的 `inspect()`：只读报告、限 4 MiB；`schema_version` 1、`execution_status=completed`、`review_outcome` 为 findings 或 no_findings_in_scope、`backend=codex`、被审文件在 `scope.files` 且 sha256 与工作区一致，才算 ok；返回阻断数（缺 severity 按阻断）与建议数。新增 `test_codex_review.py` 5 例（实现前导入即失败），已在 `validate.sh` 登记。
- [x] Task 2：review-mark 的 codex-approved／codex-reviewed 与轮次 — `module_stage` 新增 `REVIEW_CODEX_DIGEST`、`review_codex_line`、`CODEX_ROUND`、`codex_rounds`，`review_state` 认 `codex-approved`（Spec、Plan 都带指纹，改了读作 revised），`REVIEW_STATES` 加 `codex-approved`；`review_mark.py` 加 `--state codex-approved|codex-reviewed` 与 `--review`：用 `codex_review.inspect` 校验报告，在「外部审查意见」一节追加轮次行（没有该节就新建），两轮阻断后两种 Codex 状态都拒绝、只能用户批，`codex-approved` 要求本轮无阻断，只能单个目标，写后回读。接口的 `mapView.values.review` 与 `reviewMark` 同步（原 Task 4 的这部分提前做，否则检查不过）。`test_review_marker.py` 新增 `CodexMarks` 5 例（改前 4 失败），状态集合测试同步，40 例通过。
- [x] Task 3：effective_review 与阶段提示 — `module_stage` 新增 `codex_route`（档位不是 codex → takeover；Plan 的「预先声明」有内容或写坏 → pre-declared，Q6）、`codex_rounds_exhausted`、`effective_review`（codex-approved 只在 route 为空时读作 approved，approvedBy=codex）、`cadence_combined`（Spec 与 Plan 批准人不同时 combined 不生效）、`codex_hint`（中英：交 Codex 审并写明 review-mark 用法、建议写理由、不可用就停；两轮阻断交用户；档位不允许时写明 Codex 批准不算）；`review_hint` 先换成生效状态再判断，`stop_node` 与两处 combined 判断改用 `cadence_combined`。`review_mark.py` 记 Plan 批准时认档位允许的 Codex 批准。`test-phase-guard.sh` 新增第 28 段 3 例（PARTS=28，用改前的 module_stage 跑该段失败，已核对），529 例通过；`test_review_marker.py` 新增 `Effective` 3 例与 1 例 Plan 批准，45 例通过。
- [ ] Task 4：/map 的 reviewApprovedBy 与接口
- [ ] Task 5：规则与说明
- [ ] Checkpoint 1（report）：完整检查、变异验证与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
