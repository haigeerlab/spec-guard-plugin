# Plan: sg-design-outline

需求 `spec/sg-design-outline.md`、技术方案 `tasks/sg-design-outline/design.md`、回归 `tasks/sg-design-outline/regression.md`。每个任务先写红用例再实现；新用例放 `plugins/spec-guard/hooks/test_sg_design_outline.py`（Task 1 新建并登记进 `scripts/validate.sh`）；提交一律走 `scripts/verify-and-commit.sh`。
发版方式：用户 2026-11-27「批准；单独发」——本模块 PR 里升 0.100.0。

## 任务

- **Task 1：三种情况的判定与批次缓存**（`module_stage.py`）
  `design_outline_case`；`batches()` 结果按（根目录、HEAD、能力图文件状态）缓存；`overall_design()` 把写坏的前缀行判 `invalid`。
  验证：R1、R7。
- **Task 2：全新四节判失败**（`module_stage.py`）
  `DOC_SECTIONS["design-new"]`、`["design-interfaces"]`；`flow_doc_problems` 的 `wanted`。
  验证：R2、R3。
- **Task 3：两条警告与阶段提示**（`module_stage.py`、`verify-artifacts.sh`）
  `design_outline_problems`、`design_outline_line`，接进 `_describe_body` 与状态码。
  验证：R4、R5、R6。
- **Task 4：骨架与规则文字**（`doc-skeletons.md`、`workflow-checkpoints.md`、`node-rules.md`、`docs/workflow.md`）
  验证：R8。
- **Task 5：版本与 CHANGELOG**（两份 `plugin.json`、两份 README、`CHANGELOG.md`）
  验证：R9。

## 检查点

- **Checkpoint 1（report）**：Task 1～3 完成后跑完整档，并在临时副本上对关键判据各做一次变异（如 `new` 不看路径、条数门槛改成 1、注释项算内容、提示不限阶段、缓存不看 HEAD），确认对应用例变红后还原；结果记入 todo。
- **最终验收（gate）**：R1～R11 全部跑过并记证据；推送本分支、开 PR；合成一问「验收通过、合并吗？」，写明 PR 当前的 head 提交。
