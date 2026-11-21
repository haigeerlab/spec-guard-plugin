# Plan: important-requirement

<!-- spec-guard: review approved -->

Spec：[spec/important-requirement.md](../../spec/important-requirement.md)（2026-11-22 批准；Q7 A、Q8 A、Q9 A）。

## 架构决定

- **判据只有一处**：`module_stage.important(root, module) -> list`，三条判据各一个小函数：多模块（`usage_draft.batches`，同批 2 个及以上）、
  跨模块（`module_scope.parse` 读 Spec 并行边界：公共类别非空，或与另一未完成模块的独占路径重叠；没有该节时 Q7 A 记 `cross-unknown`，
  只在档位勾了 spec=codex 时才算重要）、高风险路径（读 `.github/autopr/risk-paths.json`，`autopilot.risk-paths/v1`，T3＋T4 通配；读不到记 `risk-unknown`，同样只在
  spec=codex 时算）。只在需要时（Spec 交审节点、`/map`）调用，平时不读 git。
- **通配匹配**：新写一个小函数按 `**` 跨目录、`*` 一层把模式转成正则；独占路径是目录（以 `/` 结尾）时，模式命中该目录下任意路径即算命中。
- **生效**：`codex_route(spec)` 在 `takeover` 检查之后加 `important`；批准行与建议下一步（先 `interview-me`、写明理由）挂在 `codex_hint` 里，
  只在档位勾了 spec=codex 时出现，没勾的模块输出不变。
- **规则文字**：「需求确认」「能力图审阅」「Spec 交审」与「自治档位与底线」各改一处；不动阶段提示的其他节点。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`、verify-artifacts 0 失败。
- **Task 1**：判据与通配（AC1）。新测试文件 `hooks/test_important_requirement.py`（`validate.sh` 登记）：临时 git 仓库覆盖同批插入、公共类别、重叠、
  命中 T4／T3、清单缺失、无边界、全不命中；先确认失败再实现。
- **Task 2**：生效与阶段提示（AC2、AC3）：`codex_route` 加 `important`，`codex_hint` 加重要需求的批准行与「先 interview-me」的建议（中英）；
  `test-phase-guard.sh` 新增第 29 段（PARTS=29）；`test_review_marker.py` 补一例。
- **Task 3**：`/map --json` 的 `important`、`interface.json`、`check-interface.py` 与 `test-checkers.sh` 反例（AC4）。
- **Task 4**：规则与说明（AC5）：`workflow-checkpoints.md`「需求确认」「自治档位与底线」、`node-rules.md`「能力图审阅」「Spec 交审」，
  `test_workflow_checkpoints.py` 断言与字节上限；`commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`、`docs/commands.md`。

## 会改哪些文件

- 新增：`tasks/important-requirement/{plan,todo}.md`、`hooks/test_important_requirement.py`。
- 修改：`hooks/module_stage.py`、`hooks/map_view.py`、`hooks/test_map_view.py`、`hooks/test-phase-guard.sh`、`hooks/test_review_marker.py`、`interface.json`、
  `scripts/check-interface.py`、`scripts/test-checkers.sh`、`scripts/validate.sh`、`references/workflow-checkpoints.md`、`references/node-rules.md`、
  `hooks/test_workflow_checkpoints.py`、`commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`、`docs/commands.md`。
- 不改：版本号、CHANGELOG、README、autopilot 的任何东西。新增依赖、锁文件：无。

## 风险

- **清单文件还没有**：autopilot 写 `.github/autopr/risk-paths.json` 之前，勾了 spec=codex 的模块都会判为 `risk-unknown`，Spec 由用户批（从严）；已请 autopr-design 确认（#21975）。
  若对方要改文件名或格式，改动在 Spec 范围内就照改并在最终验收说明，超出就停下问用户。
- **阶段提示回归面**：新分支只在勾了 spec=codex 时出现，用「没勾 codex 时逐字不变」守住。
- **叠加分支**：基于 #463 的分支，前面合并后 rebase 到 main 再开 PR。
- **shell 改动**：提交前跑 ShellCheck。

## 检查点

- Checkpoint 1（report）：完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）；变异验证两处（多模块判据不看批次大小、
  通配 `*` 也跨目录）各让回归变红；临时项目实跑：档位 spec=codex，同批插两个模块 → Spec 交审节点要求先拷问、Codex 批准不算；单独插入且无公共、
  清单不命中 → Codex 批准算数；清单缺失 → risk-unknown。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送，前面合并后 rebase 开本模块 PR，合并由用户进行。本模块不发版。

## 未决问题

- 无。
