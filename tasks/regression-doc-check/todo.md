# Todo: regression-doc-check

- [x] Task 0：提交 Spec 批准、Plan 与 todo（2026-11-25 用户「批准；Q1 A；Q2 A」「按处理办法改，批准」）
- [x] Task 1：解析与 sha256
- [x] Task 2：CLI 与 `--ref`
- [ ] Task 3：接进 `flow_doc_problems` 与 `section-empty`
- [ ] Task 4：阶段提示
- [ ] Task 5：联调回归
- [ ] Task 6：接口 1.23
- [ ] Checkpoint 1（report）：本机完整检查与变异
- [ ] Task 7：规则与文档
- [ ] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告

## 证据
- Task 1（2026-11-25）：新文件 `hooks/regression_view.py` 的解析部分：`parse_regression`（三种文档：模块回归、`spec/<id>.md` 的回归用例一节、联调回归）、`criteria_ids`、`case_sha256`（五个字段压空白后按固定键序算，标题与编号不算）。字段名中英文、冒号中英文都认，续行与代码块并入当前字段，围栏里的标题不算用例。
  用例：`test_flow_v2.py` `RegressionParseTest` 6 例（中英文各一份、围栏、成功标准编号、sha256 只改空白与标题不变而改内容变、九个问题代码各一份反例）；实现前运行 14 个错误（模块不存在）。
- Task 2（2026-11-25）：CLI `--json --project (--module|--usage) [--ref]` 与退出码；`--ref` 在临时目录里做共享对象的本地克隆、检出到那个提交，文档字节用 `git cat-file blob` 读原始 blob（R2-1、R2-2）。`module_stage.impact_has_old_files` 从 `design_requirement` 抽出，判定不变（`test_flow_v2.py` 全部通过）。
  用例：`RegressionViewCliTest` 7 例。实现写在这批用例之前，用例一次通过，没有经过先红；补做变异：`--ref` 改读工作区 → 3 例变红；改读克隆的检出文件而不是 blob → `test_ref_bytes_are_the_raw_blob` 变红（样本最初没有 `text eol=crlf`，检出与 blob 字节相同，这处变异没拦住，补上属性后拦住）。
