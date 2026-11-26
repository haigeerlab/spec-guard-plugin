# Todo: rework-scope-baseline

- [x] Task 0：提交 Spec 批准、能力图新行、Plan 与 todo（2026-11-26 用户「批准；Q1 A」）
- [x] Task 1：`rework_base` 与 `scope_base`
- [x] Task 2：接到调用点与提示
- [x] Checkpoint 1（report）：本机完整检查、变异与老输出比对
- [x] Task 3：规则与文档
- [x] Checkpoint 2（gate）：推送、开 PR、最终验收并同时问合并（用户「验收通过并合并」）
- [x] Task 4：merge 过默认分支时的 `trimmed` 与 `scope_base`（返工，Spec 假设 8）
- [ ] Task 5：提示、规则与版本 0.97.0
- [ ] Checkpoint 3（report）：完整档、变异与老输出比对
- [ ] Checkpoint 4（gate）：推送、开 PR、最终验收并同时问合并

## 证据
- Task 0（2026-11-26）：能力图插入 rework-scope-baseline（用户「批准；Q1 A」）；Plan 经 Codex 两轮：第一轮 3 条阻断（返工勾完后丢基线、只剩正式延期不算完成、提示写错提交），改后第二轮全部解决、没有新阻断，记 codex-approved（第一次运行超时无结论，重跑）。
- Task 1（2026-11-26）：`module_scope.rework_info`（todo 历史从新到旧：最新的有未勾选项状态（工作区优先）→ 它之前最近的全部勾完提交 → 二者之间最旧的有未勾选项提交 R，返回 `{base: R^, start: R}`；只在工作区时 `{base: HEAD, start: None}`；正式延期算勾完；没有勾完过、读不到 git 时 None）与 `scope_base`（有返工用它，否则 `default_base`）。用例：`test_module_scope.py` `ReworkBase` 7 例，实现前 7 个出错。
- Task 2（2026-11-26）：改用 `scope_base` 的六处——老流程越界 `scope_overreach`、新流程越界 `_scope_part`（Spec 写的「scope_overreach」实际分两个函数）、`t4_hits`、`acceptance_step`、`review_mark._outside`、`module_scope.py check` 的默认基线；`_merge_at_base`、`module_baseline` 保持原基线。两处越界提示在返工时加「；返工：从提交 `<R 前 12 位>` 起算」，只在工作区时加「；返工：还没提交，与 HEAD 比较」（`_rework_note`）。用例：`test_flow_v2.py` `ReworkOverreachTest` 5 例（继承 `FlowOverreachTest` 一起跑），实现前核心 2 例失败；`_merge_at_base` 与 `module_baseline` 两例放在这个类里（Plan 写的是 `test_review_marker.py`，为共用夹具放这里）。
- Checkpoint 1（2026-11-26）：Task 1、2 的提交都走完整档且全绿。变异（临时副本）：用全部勾完的提交 D 代替 R^ → 5 例变红；不认正式延期 → 1 例；返工勾完后退回原基线 → 1 例；`_merge_at_base` 改用新基线 → 第一次没拦住（样本在返工开始后才放宽档位，两条基线上的配置一样），改成完工后、返工前放宽后拦住。已安装的 0.96.1 与本分支对本仓库的阶段提示、verify-artifacts 逐字相同。
  真实历史：regression-doc-check 的 `rework_info` 给出 base `17b97ad2`、start `fce30e2f`（#505），返工开始认对了；从原基线比到当前 HEAD 有 25 个越界文件，从返工基线比到当前 HEAD 还有 10 个——都是返工开始之后才合进来的 #506～#508 与本模块的改动。Spec 没写到的边界：返工期间别的模块再合进 main、返工分支 rebase 跟上时，这些后来的改动仍会算进来（#505 当时分支直接从 main 开出、中途无合并，不受影响）。验收时交用户。
- Task 3（2026-11-26）：共享检查点规则「返工与小模块」补一段；CHANGELOG「未发布 · 修复」一条；版本 0.96.1 → 0.96.2（两份 plugin.json、两份 README 的 `--ref`）。
- Checkpoint 2（2026-11-26）：基于 main `0a5cee38` 推送，开 PR #509 并绑定；最终验收与合并合成一问，用户「验收通过并合并」。已知边界（返工期间别的模块再合入、rebase 后仍会算进来）已在验收时交用户，没有要求这次修。拟回告：无。
- Task 4（2026-11-26）：`module_scope._trim`（默认分支取 `verification.default_branch`；当前分支是默认分支的本地分支 → None；`merge-base HEAD <默认分支>` 等于返工基线或不是它的后代 → None）、`rework_trim`，`scope_base` 返工时用 `_trim(...) or base`。没有按 Plan 给 `rework_info` 加 `trimmed` 键：老用例对整个字典做相等断言，改成独立函数不用动它们。用例：`test_module_scope.py` `ReworkMergeBase` 7 例（继承 `ReworkBase`，老的 7 例在 `main` 分支名下一起跑），实现前 7 例出错。提示（原属 Task 5）一并做了：`_rework_note` 在扣除时加「（已扣除默认分支上的提交）」；`test_flow_v2.py` 两例：merge 情形整句断言（实现前失败）、第一次开工 merge 过 main 的越界一行整行断言（实现前已通过，锁住 0.96.2 的写法）。

