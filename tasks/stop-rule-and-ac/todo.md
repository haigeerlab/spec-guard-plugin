# Todo: stop-rule-and-ac

- [x] Task 1：规则文字的断言（先红） — `test_workflow_checkpoints.py` 加 `block_surfaces()`（两份模板、`docs/convention-block.md`、本仓库 `AGENTS.md`）；改写 `test_an_external_blocker_goes_back_to_the_user` 为新说法并断言旧说法「同一个 gate 因外部原因」在规则与各处约定块都不再出现；新增 `test_checks_a_script_can_judge_may_be_report`、`test_acceptance_criteria_are_numbered`。旧文字上 3 例失败。
- [x] Task 2：改规则文字与约定块 — `references/workflow-checkpoints.md`：异常停点与「交用户决定」一条改为同一模块、同一目标第二次外部失败或第二次报批，写明什么算同一目标、自己能修的不算、挂起并先开 `/spec-guard:map` 的 🟢 模块（没有就照实说）；「Plan 检查点分级」加 `report` 提示（默认仍是 `gate`）；Spec 交审要点改为「验收标准（按 AC1、AC2… 编号）」，新增「验收标准编号」一条。四处约定块同步：检查点一行补「可标 `report`」、外部阻塞一行改写、新增 AC 一行。53 例全绿；`validate.sh --quick` 通过；变异（Codex 模板退回旧文字）3 例变红。
- [x] Checkpoint 1（report）：规则文字断言全绿 — 随本次提交跑 `verify-and-commit.sh`。
- [x] Task 3：verify-artifacts 的 AC 编号提示 — `test-verify-artifacts.sh` 先加 7 例（未编号出提示且不失败、顶层以外的子项与后续小节不算、全部编号含 `**AC2**` 与 `1. AC3` 不出、`验收标准` 与 `Acceptance criteria` 标题识别、没有该节不出、围栏示例不算、已完成模块不追溯），旧代码上第一例即失败；`verify-artifacts.sh` 新增一段内嵌 python 检查（`parse_map` 取模块、`module_state` 跳过 DONE、按 `FENCES` 排除围栏、只数顶层列表项），只 `warn` 不 `bad`、不加 `ok` 行。75 例全绿；两处变异各有用例变红：不跳过已完成模块（「已完成模块不追溯」红）、不认 `**AC1**`（「全部编号时不提示」红）。本仓库实跑仍为 5 通过 · 0 警告 · 0 失败。
- [x] Task 4：CHANGELOG 与版本号 — CHANGELOG 新增 `[0.74.0] - 2026-10-19`；两份 `plugin.json` 改为 0.74.0，中英 README 的 `--ref` 改为 v0.74.0。
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行

## 外部审查意见

<!-- spec-guard: external-review declined -->
