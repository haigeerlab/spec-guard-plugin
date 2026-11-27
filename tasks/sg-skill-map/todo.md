# Todo: sg-skill-map

- [x] Task 1：回告 lead
- [x] Task 2：位置判定与点名行
- [x] Task 3：记录解析与 /map
- [ ] Task 4：最终验收提醒
- [ ] Checkpoint 1（report）：完整档与变异
- [ ] Task 5：规则文字
- [ ] Task 6：接口 1.28 与版本 0.101.0
- [ ] 最终验收（gate）：推送、开 PR、验收并同时问合并

## Skill 使用记录

- 需求确认：spec-driven-development
- 需求文档审查：delegate:review
- 技术方案：doubt-driven-development
- 写 Plan：planning-and-task-breakdown

- 实现：incremental-implementation、test-driven-development

## 证据
- 技术方案（2026-11-27）：Codex 两轮（第 1 轮 3 条阻断，第 2 轮剩 `spec/map-view.md` 一条交用户），用户「批准；不改；单独发」。
- Task 1（2026-11-27）：经 agent-relay 发给 ecosystem-lead（线程 `autopilot-m5-7`），消息 #23557，写了 `skillLog` 的位置、字段与 todo 写法；lead 会话未运行，消息已存入其收件箱，打开后读到。
- Task 2（2026-11-27）：`module_stage` 加 `SKILL_TABLE`、`skill_position`（按顺序判定：先审一轮、确认停点、总体技术方案、技术方案、构建、最终验收，任一时刻一个）、`skill_line`；`_describe_body` 接上一行，`role_view()` 给模块 checkout 同样一行，`skill_position` 进 `_role_facts()`。`test_sg_skill_map.py` 新建（`Position` 2 例、`SkillLine` 3 例、`RoleView` 1 例），对改动前实现全红（8 失败 9 报错），登记进 `scripts/validate.sh`；`test_flow_v2`、`test_stop_rules`、`test_sg_review_rules`、`test_sg_design_outline`、`test_sg_gate_flow`、`test_checkout_role` 照旧全过。
- Task 3（2026-11-27）：`module_stage.skill_log`（按第一个冒号切、先认两种「没有现成的 skill」、五种分隔符、去空与重复、跳过代码块与非 `- ` 行）；`map_view` 每个模块加 `skillLog`，文件头注明 1.15 起的字段以 `interface.json` 为准（用户「不改」`spec/map-view.md`）。用例 `SkillLog` 3 例（对改动前实现全红）、`TodoProgress` 1 例；`test_map_view.py` 的 `MODULE_KEYS` 加 `skillLog`。
