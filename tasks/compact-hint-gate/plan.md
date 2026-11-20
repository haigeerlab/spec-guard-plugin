# Plan: compact-hint-gate

<!-- spec-guard: review approved -->

Spec：[spec/compact-hint-gate.md](../../spec/compact-hint-gate.md)（2026-11-20 批准）。

## 架构决定

- **只改规则文字与文档**：压缩提醒的门槛只在钩子一处（`module_stage.thresholds()`、`boundary_line()`，≥70%），规则文字不再另写一个无门槛的
  提示；hook 代码与阶段提示输出不动，所以 `test-phase-guard.sh` 不需要新断言，只作回归。
- **回归落在 `test_workflow_checkpoints.py`**：原有三处断言要求出现 `/compact`（「阶段交接」、`node-rules.md`「最终验收」、连续构建一段），
  按 AC1–AC3 改为正反断言；先改测试确认变红，再改规则。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`、verify-artifacts 0 失败。
- **Task 1**：规则与规则回归（AC1–AC4）。先改 `test_workflow_checkpoints.py` 的断言并确认失败；再改 `references/workflow-checkpoints.md`「阶段交接」
  那条与连续构建一段末句、`references/node-rules.md`「最终验收」最后一条。验证：规则回归绿、各节字节上限内（`validate.sh --quick`）。
- **Task 2**：`docs/workflow.md` 那一段（AC4 的文档部分），断言加进同一测试文件。验证：`validate.sh --quick`。
- **Task 3**：版本 0.90.1 与 CHANGELOG（AC5）。验证：`check-manifests.py`、`check-readme-sync.py`。

## 会改哪些文件

- 新增：`tasks/compact-hint-gate/{plan,todo}.md`。
- 修改：`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md`、
  `plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`docs/workflow.md`、两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。
- 新增依赖、锁文件：无。hook 代码：不改。

## 风险

- **措辞被读成另一种停法**：新句子要写清「同一轮接着写」，不出现「建议先压缩」这类可被读成停点的说法；用反向断言守住。
- **字节上限**：`node-rules.md` 各节有上限，删的比加的多，预计不超。

## 检查点

- Checkpoint 1（report）：发布前完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck 不涉及 `.sh` 则写明）；变异验证一处
  （把 `/compact` 那半句加回 `node-rules.md`「最终验收」→ 反向断言变红）。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行。
- 发版（合并后按 Checkpoint 2 授权）：打 tag、发 Release 后立即通知 ecosystem-lead（replyTo 21692），刷新两个宿主，证据收尾 PR。

## 未决问题

- 无。
