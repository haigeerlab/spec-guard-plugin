# Plan: sg-gate-flow

需求 `spec/sg-gate-flow.md`、技术方案 `tasks/sg-gate-flow/design.md`、回归 `tasks/sg-gate-flow/regression.md`。每个任务先写红用例再实现；提交一律走 `scripts/verify-and-commit.sh`。

## 任务

- **Task 1：预设 `autopilot` 与带 `preset` 的对象**（`project_config.py`）
  `PRESETS`、`valid_takeover`、`expand`、`legacy`、`PRESET_LADDER`、`narrow_step`、`module_preset`；config 写入。
  验证：R9、R10（收窄部分）、R14；`test_project_config.py` 全过。
- **Task 2：提前授权**（`module_stage.py`、`map_view.py`）
  `release-preauth` 解析、`release_preauth()`、需求确认提示的发版一问、`takeover.releasePreauth`、`takeover.preset`。
  验证：R1、R2。
- **Task 3：总体技术方案关卡**（`module_stage.py`、`map_view.py`、`review_mark.py`、`verify-artifacts.sh`）
  `overall-design` 解析与路径校验、`overall_wait()`、阶段提示、`flow.overallDesign`、`review-mark --target overall`、verify-artifacts 三项检查。
  验证：R3、R4、R5、R10（关卡部分）。
- **Task 4：里程碑不阻塞**（`module_stage.py`、`map_view.py`）
  `milestone_blocking()`、阶段提示、`milestoneStop.blocking`。
  验证：R6。
- **Task 5：先说一句**（`module_stage.py`）
  验证：R11。
- **Task 6：规则文字**（`workflow-checkpoints.md`、`doc-skeletons.md`、`node-rules.md`、config 与 review-mark 说明、`docs/`）
  六处替换（O1 那一句用用户批过的收窄措辞）、「出事处理」「总体技术方案」两节、第 154 行指向、需求确认与里程碑两处补充；八处断言改钉新原文并加新断言。
  验证：R7、R8。
- **Task 7：接口与版本**
  `interface.json` 1.26、CHANGELOG、两份 plugin.json 与两份 README 的 `--ref` 升到 0.98.0。
  验证：R12；`check-interface.py` 通过。

## 检查点

- **Checkpoint 1（report）**：Task 1～5 完成后跑完整档，并在临时副本上对关键判据各做一次变异（如 `release_preauth` 不看批准、`milestone_blocking` 恒为 False、`overall_wait` 不看指纹），确认对应用例变红后还原；结果记入 todo。
- **最终验收（gate）**：R1～R14 全部跑过并记证据；推送本分支、开 PR；按「合并的时机与 CI」合成一问「验收通过、合并吗？」，写明 PR 当前的 head 提交。
