# Plan: codex-approval

<!-- spec-guard: review approved -->

Spec：[spec/codex-approval.md](../../spec/codex-approval.md)（2026-11-22 批准，Q6 A：带非空「预先声明」的 Plan 不论档位都由用户批）。

## 架构决定

- **报告校验单独一个文件**：新增 `hooks/codex_review.py`，只做三件事：读报告 JSON、按 delegate 公布的 `blob-pairs-v1` 定义用 `git ls-tree`
  重算指纹、核对被批文件与工作区内容。`review_mark.py` 调它；阶段提示不调它（阶段提示只读文件里已写下的标记与轮次行，不读报告、不跑 git）。
- **生效判定只有一处**：`module_stage.effective_review(root, module, target)` 把标记（approved／codex-approved／pending／revised）、接管档位
  （`project_config.module_takeover`）、两轮上限、Q6（Plan 的「预先声明」是否有非「无」行，复用 `module_scope` 的解析）合起来，给出
  `state` 与 `approvedBy`；批准行、`stop_node`、评审节奏、`/map` 都用它。
- **轮次行的写法固定**：`<!-- spec-guard: codex-review round=<n> blocking=<k> fingerprint=<12 位> -->`，写在「外部审查意见」一节（没有就新建该节），
  只由 `review-mark` 写；阶段提示与 verify-artifacts 读它。
- **没勾 codex 的模块逐字不变**：所有新分支都以「档位里这一项是 codex 或文件里有 codex 标记」为前提；用 phase-guard 回归守住。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`、verify-artifacts 0 失败。
- **Task 1**：`codex_review.py` 与单测 `test_codex_review.py`（在 `validate.sh` 登记）：临时 git 仓库造提交与手写报告，覆盖 AC1 的七种情形；先写测试确认失败再实现。
  如果 delegate-owner 的答复与 Spec 假设 2、3 不一致（字段名、报告落盘方式），在这里停下把差异交用户（Spec 没覆盖的决定）。
- **Task 2**：`review_mark.py` 加 `--state codex-approved|codex-reviewed`、`--review`，轮次行、两轮上限（AC1、AC2）；`test_review_marker.py` 先写例子。
- **Task 3**：`module_stage.effective_review` 与阶段提示（AC3、AC4、AC5，含 Q6）：批准行文字、建议下一步（交 Codex 审／两轮后交用户／Codex 不可用就停）、
  `stop_node`、combined 按批准人拆开；`test-phase-guard.sh` 新增第 28 段（中英各一例、没勾 codex 时逐字不变）；`test_stop_rules.py` 补节点种类。
- **Task 4**：`/map --json` 的 `reviewApprovedBy`、`interface.json`（`reviewMark` 取值、`mapView`）、`check-interface.py` 与 `test-checkers.sh` 反例（AC6 接口部分）。
- **Task 5**：规则与说明（AC6）：`workflow-checkpoints.md`「自治档位与底线」按勾选项重写、「批准标记」加 Codex 批准一条；`node-rules.md`「Spec 交审」「Plan 交审」
  各加一条；`test_workflow_checkpoints.py`、字节上限；`commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/workflow.md`。

## 会改哪些文件

- 新增：`tasks/codex-approval/{plan,todo}.md`、`hooks/codex_review.py`、`hooks/test_codex_review.py`。
- 修改：`hooks/review_mark.py`、`hooks/test_review_marker.py`、`hooks/module_stage.py`、`hooks/test-phase-guard.sh`、`hooks/test_stop_rules.py`、
  `hooks/map_view.py`、`hooks/test_map_view.py`、`interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`scripts/validate.sh`（登记新测试）、
  `references/workflow-checkpoints.md`、`references/node-rules.md`、`hooks/test_workflow_checkpoints.py`、`commands/review-mark.md`、
  `skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/workflow.md`。
- 不改：版本号、CHANGELOG、README。新增依赖、锁文件：无。

## 风险

- **报告格式未确认**：依赖 delegate 的报告字段与落盘方式（已问 delegate-owner #21972）；不一致时 Task 1 停下交用户。
- **指纹算法有两份实现**：`blob-pairs-v1` 是 delegate 定义的；spec-guard 按它公布的定义另写一份只用于核对。用一份真实的 delegate 报告做夹具（能拿到时）证明两边算出同一个值；
  算不出就拒绝记录，不会误放行。
- **阶段提示回归面**：批准判定是阶段提示的核心；以「没勾 codex 的项目逐字不变」守住，phase-guard 全量回归。
- **叠加分支**：基于 #462 的分支；前面 PR 合并后 rebase 到 main 再开 PR。
- **shell 改动**：提交前跑 ShellCheck。

## 检查点

- Checkpoint 1（report）：完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）；变异验证三处（不核指纹、缺 severity 不当阻断、
  档位为 human 时也当已批准）各让回归变红；临时项目命令行实跑：档位 plan → 写 Plan 并提交 → 用手写（或真实 delegate）报告走一轮有阻断、一轮无阻断 →
  `codex-approved` → 阶段提示转到构建；另跑两轮阻断后交用户、带预先声明的 Plan 交用户。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送，前面 PR 合并后 rebase 到 main 开本模块 PR，合并由用户进行。本模块不发版。

## 未决问题

- 无（报告格式待 delegate-owner 确认，见风险第一条）。
