# Todo: sg-gate-flow

- [x] Task 1：预设 `autopilot` 与带 `preset` 的对象
- [ ] Task 2：提前授权
- [ ] Task 3：总体技术方案关卡
- [ ] Task 4：里程碑不阻塞
- [ ] Task 5：先说一句
- [ ] Checkpoint 1（report）：完整档与变异
- [ ] Task 6：规则文字
- [ ] Task 7：接口与版本
- [ ] 最终验收（gate）：推送、开 PR、验收并同时问合并

## 证据
- Task 1（2026-11-27）：`project_config.py` 加 `autopilot` 预设（reviewer／auto／auto-confirm，不是出厂默认）、对象可带 `preset` 键（`expand` 先取预设再覆盖，`legacy` 写了的照写、写了 design 时由它推 plan）、`PRESET_LADDER` 加一格、新函数 `module_preset`；拒绝旧值的提示补上新写法。`test_sg_gate_flow.py` 新建（`PresetConfig` 8 例、`NarrowAndGates` 4 例），实现前 6 处失败 7 处报错，实现后全过；`test_project_config`、`test_map_view`、`test_flow_v2`、`test_review_marker` 照旧全过。新测试登记进 `scripts/validate.sh`。
