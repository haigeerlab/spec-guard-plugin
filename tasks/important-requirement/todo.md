# Todo: important-requirement

- [x] Task 0：提交 Plan 与 todo — 2026-11-22 用户批准 Spec（「批准；Q7 A；Q8 A；Q9 A」）与 Plan（「Plan 批准」，同时批准开工前修订：清单位置改为 `.github/autopr/risk-paths.json`）。
- [x] Task 1：判据与通配 — `module_stage` 新增 `risk_hit`（`**` 跨目录、`*`／`?` 一层；独占路径是目录时，只有以字面段开头的模式才可能命中）、`_risk_patterns`（读 `.github/autopr/risk-paths.json`，schema `autopilot.risk-paths/v1`，T4＋T3）、`important()`（multi-module 用 `usage_draft.batches`；cross-module 看并行边界公共类别或与未完成模块独占重叠；risk-path 看独占路径与 Plan 预先声明的公共路径；cross-unknown、risk-unknown 只在 spec=codex 时出现）。新增 `test_important_requirement.py` 7 例（实现前导入失败），已在 `validate.sh` 登记。
- [ ] Task 2：生效与阶段提示
- [ ] Task 3：/map 的 important 与接口
- [ ] Task 4：规则与说明
- [ ] Checkpoint 1（report）：完整检查、变异验证与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
