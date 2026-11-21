# Todo: codex-approval

- [x] Task 0：提交 Plan 与 todo — 2026-11-22 用户批准 Spec（「批准；Q6 A」）与 Plan（「Plan 批准」）。
- [x] Task 1：codex_review.py 报告校验与单测 — 按 delegate 接口 1.5（delegate-owner #21973；字段以 delegate 仓库 `spec/integration-interface.md` 与 `review_result.py` 核对：`scope.files` 为路径→sha256，`severity` 取 blocking／suggestion）新增 `hooks/codex_review.py` 的 `inspect()`：只读报告、限 4 MiB；`schema_version` 1、`execution_status=completed`、`review_outcome` 为 findings 或 no_findings_in_scope、`backend=codex`、被审文件在 `scope.files` 且 sha256 与工作区一致，才算 ok；返回阻断数（缺 severity 按阻断）与建议数。新增 `test_codex_review.py` 5 例（实现前导入即失败），已在 `validate.sh` 登记。
- [ ] Task 2：review-mark 的 codex-approved／codex-reviewed 与轮次
- [ ] Task 3：effective_review 与阶段提示
- [ ] Task 4：/map 的 reviewApprovedBy 与接口
- [ ] Task 5：规则与说明
- [ ] Checkpoint 1（report）：完整检查、变异验证与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
