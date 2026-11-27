# Plan: sg-skill-map

需求 `spec/sg-skill-map.md`、技术方案 `tasks/sg-skill-map/design.md`、回归 `tasks/sg-skill-map/regression.md`。每个任务先写红用例再实现；新用例放 `plugins/spec-guard/hooks/test_sg_skill_map.py`（Task 1 新建并登记进 `scripts/validate.sh`）；提交一律走 `scripts/verify-and-commit.sh`。
用户 2026-11-27「批准；不改；单独发」：不改 `spec/map-view.md`；本模块 PR 里升 0.101.0。

## 任务

- **Task 1：回告 lead**（S7）
  经 agent-relay 发 `skillLog` 的位置、字段与 todo 写法到线程 `autopilot-m5-7`，消息编号记进 todo。
  验证：R9。
- **Task 2：位置判定与点名行**（`module_stage.py`）
  `skill_position`、`skill_line`，接进 `_describe_body` 与 `role_view()`，`skill_position` 进 `_role_facts()`。
  验证：R1、R2、R3。
- **Task 3：记录解析与 /map**（`module_stage.py`、`map_view.py`）
  `skill_log`；`map_view` 每个模块加 `skillLog`、文件头注明契约以 `interface.json` 为准。
  验证：R4、R5。
- **Task 4：最终验收提醒**（`module_stage.py`、`verify-artifacts.sh`）
  `skill_reminder_line`（进状态码，两种视角）、`skill_log_problems`。
  验证：R6。
- **Task 5：规则文字**（`workflow-checkpoints.md`、`node-rules.md`、`doc-skeletons.md`、`docs/workflow.md`）
  验证：R7。
- **Task 6：接口 1.28 与版本 0.101.0**（`interface.json`、三处版本断言、两份 `plugin.json`、两份 README、CHANGELOG）
  验证：R8。

## 检查点

- **Checkpoint 1（report）**：Task 2～4 完成后跑完整档，并在临时副本上对关键判据各做一次变异（如位置顺序颠倒、最终 gate 仍出构建行、第一个冒号改成最后一个、`none` 判断放在拆分之后、提醒不进状态码、完成态改成数勾选框、角色视角不接），确认对应用例变红后还原；结果记入 todo。
- **最终验收（gate）**：R1～R11 全部跑过并记证据（含 R10 下游复核）；先看阶段提示的越界行，再推送本分支、开 PR；合成一问「验收通过、合并吗？」，写明 PR 当前的 head 提交。
