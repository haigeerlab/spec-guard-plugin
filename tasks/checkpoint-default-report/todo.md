# Todo: checkpoint-default-report

- [x] Task 1：新判据的测试（先红） — `test_map_view.py` 加 3 例（中间未标不算、只有一个未标与最后标 report、nextGate 跳过未标的中间检查点）；`test-phase-guard.sh` 加 2 类（Next gate 指向最后一个检查点、最终 gate 之后只有未标的中间检查点与 report 时仍附差异一并复审）；`test_workflow_checkpoints.py` 加 `test_checkpoint_default_is_report`（新关键句、七处产品文字不再出现旧说法）。旧判据上 map 3 例、规则 2 例红。因判据变化而改的原有期望：① `test_plan_checkpoints_are_gate_or_report` 的「未标注的检查点按 `gate`」换成新关键句；② `test_checks_a_script_can_judge_may_be_report`（stop-rule-and-ac 的 S3「默认值不改」）改为断言新判据并注明被决定 66 取代；③ 阶段提示用例标题「未标注级别按 gate」改为「未标级别的最后一个检查点按 gate」（期望不变，那份 todo 只有一个检查点）。
- [x] Task 2：判据函数与调用方 — `module_stage.py` 用 `gate_checkpoints(text) -> [(行号, 标题, 已勾)]` 取代 line 级 `gate_checkpoint`（显式 gate 算、显式 report 不算、未标的只有最后一个检查点算）；`next_gate` 取第一个未勾的，`at_final_gate` 按行号比对未勾的 gate，删掉 `_open_gate`；`map_view._gates()` 改用它。`git grep` 无旧函数引用。变异：未标的中间检查点也算 gate → map 3 例红，还原后通过。
- [x] Task 3：接口说明、规则、模板与文档 — `interface.json` 升到 1.4（`gates` 写新判据与「1.4 起未标的中间检查点不再计入、total 可能变小」，`appearsWhen` 注明）；共享检查点规则两条改写；两份模板、`docs/convention-block.md`、`AGENTS.md`、`docs/workflow.md`、`commands/map.md` 同步。`check-interface.py`、`check-readme-sync.py` 通过；`git grep` 产品文字里不再有「未标注／未标级别」的旧说法（历史证据 `docs/releases/` 除外）。
- [x] Checkpoint 1（report）：判据、接口与规则的回归全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [ ] Task 4：本仓库与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行
