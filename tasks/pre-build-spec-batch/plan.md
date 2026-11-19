# Plan: pre-build-spec-batch

<!-- spec-guard: review approved -->

Spec：[spec/pre-build-spec-batch.md](../../spec/pre-build-spec-batch.md)（2026-11-20 批准）。

## 架构决定

- **基线只有一处判定**：`module_stage.spec_baseline(root, module)`，用现有 `_git` 读 `git log -n 50 --format=%H -- spec/<id>.md` 与
  `git show <sha>:spec/<id>.md`，对每个版本算 `review_digest` 与当前批准标记的指纹比较；不写文件。`review_mark.py` 与阶段提示都调它。
- **「开工前攒批」只有一处判定**：新函数 `pre_build_batch(root, module, stage, spec, plan)`，在 Spec 为 `revised` 且（NEEDS_PLAN，或 BUILDING
  且 Plan 为 `pending`）时返回 `spec_baseline` 的结果，否则返回 None。`review_hint`（中英两套）与 `stop_node` 都用它，保证批准行、建议下一步、
  节点规则种类三者一致。
- **节点规则**：有基线时 `stop_node` 给 `plan-review`（不是 `spec-review`），这样附上的是「Plan 交审」规则，含新加的累计差异一条。
- **状态码**：`stop_node` 的结果本来就在状态码的事实里；有无基线会改变节点种类与批准行，所以状态变了会重发完整内容，不另加事实。
- **review-mark**：`--target both --state approved` 时若 Spec 读作 `revised`，在现有预览之前打印累计差异（去掉标记行后的正文比较）；
  `--target plan` 的拒绝文字补一句 `--target both`。
- **BUILDING 且 Plan 待批准**：今天这种情形走的是构建中「范围内修正可以继续」的提示，实际上还没开工；本模块把它归入开工前攒批，是 Spec 假设 1
  明写的行为变化。

## 任务

- **Task 0**：提交本 Plan 与 todo（能力图与 Spec 已在批准后先行提交，作为本模块自己的基线）。验证：`validate.sh --quick`、verify-artifacts 0 失败。
- **Task 1**：`spec_baseline` 与 `pre_build_batch`。先在新测试文件 `hooks/test_spec_baseline.py` 写 AC1 的例子（临时 git 仓库）并确认失败。
  验证：单测绿，`validate.sh` 登记新测试。
- **Task 2**：阶段提示。`review_hint` 中英两套、`stop_node` 接 `pre_build_batch`；`test-phase-guard.sh` 新增第 26 段（AC2 五种情形，含「无基线时
  与改前逐字相同外加原因」）并确认改前失败。验证：phase-guard 全绿。
- **Task 3**：`review-mark` 的累计差异预览与拒绝文字（AC3）。`test_review_marker.py` 先写例子并确认失败。验证：单测绿。
- **Task 4**：规则。`workflow-checkpoints.md` 改那一句为攒批规则（含 E1–E4、先提交再改、取不到退回）；`node-rules.md`「Plan 交审」加一条；
  `test_workflow_checkpoints.py`、`test_stop_rules.py` 加断言（AC4）。验证：规则回归绿、字节上限内。
- **Task 5**：文档。`commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md` 的 review-mark 一节、`docs/workflow.md` 批准一段。验证：`validate.sh --quick`。
- **Task 6**：版本 0.90.0 与 CHANGELOG。验证：`check-manifests.py`、`check-readme-sync.py`（AC5）。

## 会改哪些文件

- 新增：`tasks/pre-build-spec-batch/{plan,todo}.md`、`plugins/spec-guard/hooks/test_spec_baseline.py`。
- 修改：`hooks/module_stage.py`、`hooks/review_mark.py`、`hooks/test_review_marker.py`、`hooks/test-phase-guard.sh`、`references/workflow-checkpoints.md`、
  `references/node-rules.md`、`hooks/test_workflow_checkpoints.py`、`hooks/test_stop_rules.py`、`commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`、
  `docs/workflow.md`、`scripts/validate.sh`、两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。
- 新增依赖、锁文件：无。

## 风险

- **阶段提示回归面大**：新分支只在 Spec 为 `revised` 且开工前时生效；其余输出用「没有修订的项目逐字不变」「Plan 已批准的 BUILDING 不变」守住。
- **每轮多几次 git 调用**：只在开工前且 Spec 已修订时才查，最多 50 个提交；平时不调用。
- **本仓库自身**：装上 0.90.0 后，本仓库开工前改 Spec 也按攒批走；Spec 已按新规则先提交，本模块自己的基线可取。

## 检查点

- Checkpoint 1（report）：发布前完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）；变异验证两处（基线不比指纹、
  `pre_build_batch` 不看 Plan 状态）各让回归变红；临时项目命令行实跑：批准 Spec 并提交 → 改 Spec → 阶段提示攒批 → 写 Plan → review-mark
  `--target both` 预览出累计差异 → 确认；另跑一遍批准后不提交就改，确认退回当场复审。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行。
- 发版（合并后按 Checkpoint 2 授权）：打 tag、发 Release 后立即通知 ecosystem-lead，刷新两个宿主，证据收尾 PR；回告 autopr-design 的全文交用户确认后发送。

## 未决问题

- 无。
