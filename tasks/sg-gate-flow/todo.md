# Todo: sg-gate-flow

- [x] Task 1：预设 `autopilot` 与带 `preset` 的对象
- [x] Task 2：提前授权
- [x] Task 3：总体技术方案关卡
- [ ] Task 4：里程碑不阻塞
- [ ] Task 5：先说一句
- [ ] Checkpoint 1（report）：完整档与变异
- [ ] Task 6：规则文字
- [ ] Task 7：接口与版本
- [ ] 最终验收（gate）：推送、开 PR、验收并同时问合并

## 证据
- Task 1（2026-11-27）：`project_config.py` 加 `autopilot` 预设（reviewer／auto／auto-confirm，不是出厂默认）、对象可带 `preset` 键（`expand` 先取预设再覆盖，`legacy` 写了的照写、写了 design 时由它推 plan）、`PRESET_LADDER` 加一格、新函数 `module_preset`；拒绝旧值的提示补上新写法。`test_sg_gate_flow.py` 新建（`PresetConfig` 8 例、`NarrowAndGates` 4 例），实现前 6 处失败 7 处报错，实现后全过；`test_project_config`、`test_map_view`、`test_flow_v2`、`test_review_marker` 照旧全过。新测试登记进 `scripts/validate.sh`。
- Task 2（2026-11-27）：`module_stage.py` 加 `RELEASE_PREAUTH`、`release_preauth_line`、`release_allowed`、`release_preauth`；`requirement_hint` 在档位把发版交给 autopilot 时多一句「做完自动发版吗？」（中英文），不交时逐字不变。`/map --json` 的 `takeover` 加 `releasePreauth`、`preset`，`interface.json` 写上两个字段的说明。`test_sg_gate_flow.py` 加 `ReleaseQuestion` 2 例、`ReleasePreauth` 4 例，实现前 2 处失败 4 处报错，实现后 18 例全过。`test_map_view.py` 三条钉死档位对象全部字段的用例（`test_without_config`、`test_module_entry_and_project_value`、`test_invalid_entries_fall_back`）补上两个新字段的预期值，原断言不删；124 例全过。
- Task 3（2026-11-27）：`module_stage.py` 加 `OVERALL_DESIGN`、`OVERALL_PATH`、`overall_design`（五种状态，Codex 或审查者标记算 pending）、`overall_wait`、`overall_hint`、`overall_problems`；`_review_hint` 在需求确认之后、模块技术方案之前拦，`stop_node` 记作 design-review，状态码加 `overall_wait`。`review_mark.py` 加 `--target overall`（只收 pending／approved，拒绝码 `overall-user-only`、`overall-none`、`overall-invalid`，检查放在 reviewer 状态的通用拒绝之前）。`/map --json` 每个模块加 `overallDesign`，`interface.json` 写字段、状态取值与 reviewMark 的 `overall`。`verify-artifacts.sh` 接上 `overall_problems`。
  用例：`OverallDesign` 6 例、`OverallReviewMark` 3 例、`OverallConsistency` 2 例。**这一项先写了实现后写用例，没有先看到红**；第一次跑有 2 处失败（reviewer 状态的拒绝码不对），改顺序后全过。用例能不能拦住回归，留到 Checkpoint 1 用变异补证。`test_map_view.py` 的 `MODULE_KEYS` 加 `overallDesign`，124 例全过。
