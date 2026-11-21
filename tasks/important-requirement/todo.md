# Todo: important-requirement

- [x] Task 0：提交 Plan 与 todo — 2026-11-22 用户批准 Spec（「批准；Q7 A；Q8 A；Q9 A」）与 Plan（「Plan 批准」，同时批准开工前修订：清单位置改为 `.github/autopr/risk-paths.json`）。
- [x] Task 1：判据与通配 — `module_stage` 新增 `risk_hit`（`**` 跨目录、`*`／`?` 一层；独占路径是目录时，只有以字面段开头的模式才可能命中）、`_risk_patterns`（读 `.github/autopr/risk-paths.json`，schema `autopilot.risk-paths/v1`，T4＋T3）、`important()`（multi-module 用 `usage_draft.batches`；cross-module 看并行边界公共类别或与未完成模块独占重叠；risk-path 看独占路径与 Plan 预先声明的公共路径；cross-unknown、risk-unknown 只在 spec=codex 时出现）。新增 `test_important_requirement.py` 7 例（实现前导入失败），已在 `validate.sh` 登记。
- [x] Task 2：生效与阶段提示 — `codex_route(spec)` 在档位检查之后加 `important`；`codex_hint` 对重要需求（待批准或 Codex 已批）给出「重要需求（理由），不论档位都由用户批」的批准行与「先 interview-me 再交用户评审」的建议（中英）。`test-phase-guard.sh` 新增第 29 段 2 例（先写、改前失败），PARTS=29，531 例通过；第 28 段与 `test_review_marker.py` 里 codex-approval 的夹具补上并行边界与不命中的清单（按 Q7 A、Q8 A，没有它们现在会判为重要，属预期），新增 1 例（重要需求的 Spec 不算 Codex 批准、Plan 不受影响），46 例通过；`test_map_view.py` 的 `CodexReviewTest` 夹具同样补上边界与清单。提交前完整检查第一次没过：中文提示用了规则禁用的「评审」一词（`test_user_facing_text_uses_the_shared_terms`），改为「审」后通过。
- [x] Task 3：`/map` 的 important 与接口 — `map_view.py` 每个模块加 `important`（null 或 `{"reasons": [...]}`，按 `important()`）；`module_stage.IMPORTANT_REASONS`；`interface.json` 加 `mapView.values.importantReasons`、`reviewApprovedBy.null` 补一句；`check-interface.py` 核对理由取值；`test-checkers.sh` 加 1 个反例，177 例通过。`test_map_view.py` 新增 1 例、固定字段集合加 `important`（改前错误），全过。
- [ ] Task 4：规则与说明
- [ ] Checkpoint 1（report）：完整检查、变异验证与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
