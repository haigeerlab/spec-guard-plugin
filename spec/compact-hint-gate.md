# Spec: compact-hint-gate

<!-- spec-guard: review approved e160ff810c6b -->

## Objective

验收后接着写下一份 Spec 时，规则不再无条件提示 `/compact`。现在 `workflow-checkpoints.md`「验收后接着写下一份 Spec」与 `node-rules.md`
「最终验收」都要求验收消息里「提示可先 `/compact`」，这句提示不看上下文用了多少；而阶段提示的模块边界行只在上下文达到窗口 70% 时才出现。
真实使用中，上下文才 19% 时 agent 在验收后说「上下文已经很长，建议先 `/compact`」，然后结束本轮等用户，打断了本该接着写的下一份 Spec。
本模块删去那句无门槛的提示，压缩提醒只靠阶段提示的边界行，并写明验收后同一轮接着写、不结束本轮，没有读数时不说上下文很长。

给谁用：按阶段提示推进的 agent；验收后希望工作不被打断的用户。

登记：S99，由 ecosystem-lead 转来（bridge #21692，用户原话「转给 sg-coord」）。2026-11-20 用户在本会话选「乙：删掉那句」，确认需求「说完了」，
确认插入能力图「确认插入」。账本 WXMAMPH。

## Assumptions

1. **只改规则文字**：钩子的 70% 门槛（`module_stage.thresholds()`、`boundary_line()`）和边界行内容不变；这次不改任何 hook 代码。
2. **边界行出现时的做法不变**：上下文达到 70% 时，照旧一句话说明可以 `/compact`（带重点）或 `/clear`，命令放进不带 shell 语言标签的代码块，
   不贴交接文本、不建议开新会话。
3. **验收后接着写**：最终 gate 获批、下一个模块已在能力图里、用户没说停时，在同一轮接着写它的 Spec，不结束本轮；验收消息只预告这一步。
   阶段提示没给出上下文读数时，不说上下文已经很长或建议压缩。
4. **用户随时可以自己压缩**：`workflow-checkpoints.md` 连续构建一段末尾「用户在场时，边界提示照常由用户决定压缩还是清空」改为
   「用户随时可以自己发 `/compact` 或 `/clear`，agent 不为此停下」，免得被读成要停下来等。
5. **例外保留**：下一个模块还要新插入能力图时，照旧先给用户看能力图新行。
6. **版本**：0.90.1（只改规则文字与文档，阶段提示输出与接口都不变，补丁版本号）。

## Contract

### C1 规则

- `references/workflow-checkpoints.md`「阶段交接」里「验收后接着写下一份 Spec」一条：删去「并提示要先释放上下文的话先发 `/compact`」，
  加上假设 3 的「同一轮接着写、不结束本轮」与「没给读数时不说上下文很长」。
- `references/node-rules.md`「最终验收」最后一条：删去「并提示可先 `/compact`」，补「同一轮接着写，不结束本轮」。
- `references/workflow-checkpoints.md` 连续构建一段的最后一句按假设 4 改。
- 各节字节数在上限内。

### C2 文档与版本

- `docs/workflow.md`「验收之后接着做下一个模块」一段：删去「想先释放上下文，就先发 `/compact`」，改为说明压缩提示只在上下文达到窗口 70% 时
  由阶段提示给出，用户也可以随时自己发。
- 0.90.1：两份 `plugin.json`、README 中英 `--ref`、CHANGELOG `## [0.90.1]`。

## Acceptance criteria

- **AC1** `workflow-checkpoints.md`「阶段交接」：有「接着写」「已在能力图里」「新插入能力图」「不结束本轮」，以及没有读数不说上下文很长的那句；
  不再含 `/compact`。
- **AC2** `node-rules.md`「最终验收」：有「直接写它的 Spec」「不结束本轮」；不再含 `/compact`。
- **AC3** 连续构建一段：仍含 70%、`/compact`、一句话、不贴交接文本、不建议用户开新会话；不再含「由用户决定压缩还是清空」，含「agent 不为此停下」。
- **AC4** `test_workflow_checkpoints.py` 按 AC1–AC3 改断言（反向断言同样写），改规则前新断言失败、改后通过；`docs/workflow.md` 不再含
  「想先释放上下文，就先发 `/compact`」。
- **AC5** 版本 0.90.1（`check-manifests.py`、`check-readme-sync.py`）；`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿。

## Boundaries

- **会做**：C1、C2 及回归。
- **先问再做**：改钩子的 70% 门槛或边界行内容；改其他停点规则。
- **不做**：打 tag 与发 Release（合并后按发布流程做）。

## 并行边界

- 独占：`spec/compact-hint-gate.md`、`tasks/compact-hint-gate/`、`plugins/spec-guard/references/node-rules.md`
- 公共：无

## 文档建议

改 `docs/workflow.md` 与 CHANGELOG；README 只改 `--ref`（README 不讲验收后的交接细节）。项目没有文档基线。
