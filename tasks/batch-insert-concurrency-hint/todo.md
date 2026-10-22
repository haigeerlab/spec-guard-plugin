# Todo: batch-insert-concurrency-hint

- [x] Task 0：提交 Plan 与 todo；收到开工通知后 `module-crew sync`，确认 Spec 带批准标记 — Plan 与 todo 提交于 2f23681e；按开工通知（C150）单独执行 `module-crew sync` 合入集成分支 cb1e55c（HEAD f6b15e73），Spec 带 `approved bf2c1f39e5db`、Plan 带 `approved`，均取自集成分支。validate、phase-guard（443 例）、verify-artifacts（74 例）全过。
- [x] Task 1：「并行评估」一节加批量插入时机（先红后绿，AC1～AC3） — `ConcurrencyAssessmentTests` 加 4 例（批量插入一小段、module-crew 一句、add-module 两处指引、停点规则不提开关与 module-crew），改前前两例与 Task 2 那例红，停点规则那例本来就绿（防回退）。「并行评估」一节时机改为三个、单个插入一句改为「插入单个模块不评估」，在「这些都只是建议」之前加「**批量插入之后。**」两段（Spec 假设 1～6）。只改了这一节与这个测试类。`test_workflow_checkpoints.py` 除 Task 2 那例外全过（测试与 Task 2 同一个文件，两者一起提交）；`check-no-parallel-surface.py` 通过。
- [x] Task 2：`add-module` 两处说明加指引（先红后绿，AC4） — `test_add_module_points_to_the_batch_assessment` 改前两个子例红；`commands/add-module.md`（写 `/spec-guard:config`）与 `SKILL.md` 的 add-module 一节（写 `spec-guard-ops` 的 config）在「对着旧预览确认」那段之后各加一句。`test_workflow_checkpoints.py` 80 例全过；`validate.sh --quick` 通过。
- [x] Checkpoint 1（report）：改坏验证与 off 不变（AC5、AC6） — 在 scratchpad 里 `mktemp -d` 建的两份整仓副本（`git archive HEAD`，d2325b65）上各改一处：① 删去「批量插入之后」里「只评估一次」那一句 → 只有 `test_section_covers_a_batch_insert` 红；② 往 `node-rules.md` 加一句 module-crew → 只有 `test_stop_rules_never_mention_the_switch` 红。（先用只含 `plugins/spec-guard` 的副本试过一次，因缺 `docs/`、`AGENTS.md` 另报 24 个与本模块无关的 ERROR，换整仓副本重做。）`git diff --stat crew/fix-batch`：只有 `add-module.md`、`test_workflow_checkpoints.py`、`workflow-checkpoints.md`、`SKILL.md`、本模块 todo 共 5 个文件，hook、约定块模板、`node-rules.md` 未改。副本留在本会话 scratchpad，不在仓库里。
- [ ] Task 3：合入集成分支（`module-crew sync`）并跑完整检查与越界检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **变更**：多模块并行开关 `moduleConcurrency` 为 `on` 时，为同一个需求一次插入 2 个及以上模块后，按「并行评估」规则评估一次并交用户选择
> （决定 D20）；本机装了 module-crew 时提示可用其协调会话并行开发，没装只给 Build order 建议。只评估一次；开关不是 `on` 时一切不变。

## 对使用者的影响

- 只影响打开了 `moduleConcurrency` 的项目：批量插入模块后多一段并行评估与选项；单个插入、开关关着的项目没有变化。
