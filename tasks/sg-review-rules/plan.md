# Plan: sg-review-rules

需求 `spec/sg-review-rules.md`、技术方案 `tasks/sg-review-rules/design.md`、回归 `tasks/sg-review-rules/regression.md`。每个任务先写红用例再实现；新用例放 `plugins/spec-guard/hooks/test_sg_review_rules.py`（Task 1 新建并登记进 `scripts/validate.sh`）；提交一律走 `scripts/verify-and-commit.sh`。

## 任务

- **Task 1：新流程重要需求只看风险路径**（`module_stage.py`）
  `important()` 的 `multi-module`、`cross-module` 只对老流程执行。
  验证：R11；`test_important_requirement.py` 全过。
- **Task 2：技术方案送审的三种高风险**（`module_stage.py`）
  `design_requirement()` 改为 `risk-path`、`irreversible`、`new-dependency`、`configured`，返回 `reasons`、`riskList`；删掉 `important → user`、`old-files`、`impact-unknown`；技术方案阶段的「没有风险清单」提示。
  验证：R6、R7。
- **Task 3：谁批技术方案与 /map 字段**（`module_stage.py`、`map_view.py`）
  `design_approver()` 只看档位；`designForcedBy` 新流程恒为 `null`；`DESIGN_APPROVAL_FIELDS` 加 `reason`、`reasons`、`riskList`；`DESIGN_ROUND_FIELDS` 加 `reportSha256`。
  验证：R8。
- **Task 4：技术方案的宿主子会话与没有审查者**（`module_stage.py`、`review_mark.py`）
  `DESIGN_ROUND` 接受 `report=none`（只限 `vendor=host|none`）；`--target design --state host-reviewed --blocking`、`no-reviewer`；档位检查改用 `effective_tier`。
  验证：R9、R10。
- **Task 5：需求文档的三种审查记录**（`module_stage.py`、`review_mark.py`）
  记录行解析、`requirement_review()`、`--state host-reviewed`、`no-reviewer --reason`、只记一轮（`requirement-review-recorded`）、原因校验（`requirement-review-reason`）、损坏行进 `flow_doc_problems`；`/map` 加 `requirementReview`。
  验证：R2（`/map` 部分）、R3。
- **Task 6：硬拦、确认停点提示与改动差异**（`module_stage.py`、`review_mark.py`）
  `requirement-unreviewed` 拒绝；`requirement_hint` 的「先审一轮」与差异（最多 60 行）；`requirement_review_diff()`；review-mark 确认预览打印全文差异。
  验证：R1、R2、R4、R5。
- **Task 7：规则文字**（`workflow-checkpoints.md`、`node-rules.md`、`doc-skeletons.md`、`commands/review-mark.md`、`skills/spec-guard-ops/`、`docs/workflow.md`、`docs/commands.md`）
  钉旧规则的断言改钉新规则，不删断言；加新断言。
  验证：R13。
- **Task 8：接口 1.27**（`interface.json`）
  新字段、取值、state、参数与拒绝码的说明；不改版本号与 CHANGELOG（发版等 hub）。
  验证：R12；`check-interface.py` 通过。

## 检查点

- **Checkpoint 1（report）**：Task 1～6 完成后跑完整档，并在临时副本上对关键判据各做一次变异（如空值清单少一项、只记一轮的检查去掉、硬拦不看 `required`、`report=none` 不限 vendor、`design_approver` 恢复重要需求交用户、差异不截断），确认对应用例变红后还原；结果记入 todo。
- **最终验收（gate）**：R1～R16 全部跑过并记证据；推送本分支、开 PR；合成一问「验收通过、合并吗？」，写明 PR 当前的 head 提交，并写明发版要等 hub 的 `flow_check` 改动合并。
