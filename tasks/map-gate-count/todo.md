# Todo: map-gate-count

- [x] Task 1：抽出共用判据（行为不变） — `module_stage.py` 加 `gate_checkpoint(line) -> (title, checked) | None`，用 `CHECKPOINT`（认 `[ ]` 与 `[x]／[X]`，替换只认未勾项的 `OPEN_CHECKPOINT`）与原有 `CHECKPOINT_TIER`；`next_gate` 与 `_open_gate` 改为调用它。现有回归期望值一个不改。变异：让它把 report 也算 gate，`test-phase-guard.sh` 第 13 段「已修订 + 只剩 report 检查点：照旧要求复审」变红，还原后通过。
- [x] Task 2：`gates` 的测试（先红） — `test_map_view.py` 新增 `GateCountTest` 5 例（gate＋未标级别＋report 勾一个 gate 为 {2,1}、全勾含大写 `[X]`、无检查点 {0,0} 与无 todo 为 null、无 git 历史照常有值、`nextGate` 同一判据；`Checkpointing` 不算检查点），`MODULE_KEYS` 加 `gates`。旧实现上 6 例红（4 例缺字段报错、2 例键集合），`nextGate` 一例本来就绿。因测试先红，与 Task 3 一并提交。
- [x] Task 3：实现与接口说明 — `map_view.py` 加 `_gates()`（用 `gate_checkpoint`，不新增文件读取与 git 调用），模块记录加 `gates`，`PROGRESS_FIELDS` 加 `gates`。66 例全绿，进度表用例一个不改。先只改代码常量时 `check-interface.py` 报「fields 缺 gates」；`interface.json` 升到 1.3、`progressFacts.fields` 加 `gates`（判据、null 的情形、最终验收已在 total 里勿重复计入基准）后通过。`test-checkers.sh` 加反例「缺 gates 说明 → 报错」，137 例全绿。变异：让已勾数不认大写 `X`，`test_all_checked_and_upper_case_x` 变红，还原后通过。
- [x] Checkpoint 1（report）：map 与接口回归全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [ ] Task 4：文档、实跑、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行
