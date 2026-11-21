# Plan: codex-final-acceptance

<!-- spec-guard: review approved -->

Spec：[spec/codex-final-acceptance.md](../../spec/codex-final-acceptance.md)（2026-11-22 批准；Q13 A；开工前按 autopr-design #21981 修订，随本 Plan 一起批）。

## 架构决定

- **校验在 `codex_review.py`**：`inspect_final(report, root, module)`（证据①：完成、有结论、无阻断、`scope.baseline.to` 等于 HEAD、Spec 在 `scope.files` 且 sha256 一致）；
  `inspect_check(root)`（证据②：按 `origin` 求 owner/repo、按 HEAD 拼本机证据路径，校验 schema、runner、non_author、head_sha、各 exit）。
- **记录在 git 目录**：`review_mark.py --target acceptance` 校验三样与越界（`module_scope.classify` 的 outside 为 0）、工作区干净后，写 `spec-guard/acceptance/<id>.json`
  到 `git rev-parse --git-path` 求出的位置；不改任何被跟踪文件。
- **读取**：`module_stage.acceptance_record(root, module)` 只在 `merge: auto` 的模块读；记录 sha 是 HEAD 或其祖先时，视最终 gate 已通过；`/map --json` 加 `acceptance`。
- **其余模块逐字不变**：所有新分支以 `merge == auto` 为前提，phase-guard 回归守住。

## 任务

- **Task 0**：提交本 Plan 与 todo（`--target both` 记下 Spec 修订与 Plan 的批准）。
- **Task 1**：`inspect_final`、`inspect_check` 与单测（AC1、AC2 的证据部分），先写测试确认失败。
- **Task 2**：`review-mark --target acceptance` 与 git 目录记录（AC2、AC3），`test_review_marker.py` 先写。
- **Task 3**：阶段提示与 `/map --json` 的 `acceptance`（AC4），`test-phase-guard.sh` 第 31 段（PARTS=31）、`test_map_view.py` 先写；接口同步与反例。
- **Task 4**：规则（「自治档位与底线」、「批准标记」或最终验收相关段）、说明（review-mark、SKILL、docs）。
- **Task 5**：0.91.0：两份 `plugin.json`、README 中英 `--ref` 与「自动接管」一段、CHANGELOG（S101 六个模块与 S102，接口 1.15）（AC5）。

## 会改哪些文件

- 新增：`tasks/codex-final-acceptance/{plan,todo}.md`。
- 修改：`hooks/codex_review.py`、`hooks/test_codex_review.py`、`hooks/review_mark.py`、`hooks/test_review_marker.py`、`hooks/module_stage.py`、`hooks/map_view.py`、
  `hooks/test_map_view.py`、`hooks/test-phase-guard.sh`、`interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`references/workflow-checkpoints.md`、
  `hooks/test_workflow_checkpoints.py`、`commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/workflow.md`、两份 `plugin.json`、`README.md`、
  `README.en.md`、`CHANGELOG.md`。新增依赖、锁文件：无。

## 风险

- **证据文件 autopilot 还没写**：autopr-design 说会在下一个改动里加上；在那之前只能用手写证据测，真实链路在 M3 停点验证。
- **最终 gate 不在验收时勾**：靠「记录 sha 是 HEAD 的祖先」判定已通过；记录只在本机这份克隆里，换一台机器看不到，需要合并后补勾（已写进 Spec）。
- **叠加分支**：基于 #465 的分支，前面合并后 rebase 再开 PR。

## 检查点

- Checkpoint 1（report）：完整检查与变异（证据② 不看 non_author、记录不看祖先关系）；临时项目实跑：手写证据与报告 → 记验收 → 阶段提示视最终 gate 已通过、`/map` 报 acceptance。
- Checkpoint 2（gate）：最终验收；通过后推送，前面合并后 rebase 开本模块 PR，合并由用户进行。合并后发 0.91.0 并到 M3 停点。

## 未决问题

- 无。
