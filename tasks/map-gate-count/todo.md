# Todo: map-gate-count

- [x] Task 1：抽出共用判据（行为不变） — `module_stage.py` 加 `gate_checkpoint(line) -> (title, checked) | None`，用 `CHECKPOINT`（认 `[ ]` 与 `[x]／[X]`，替换只认未勾项的 `OPEN_CHECKPOINT`）与原有 `CHECKPOINT_TIER`；`next_gate` 与 `_open_gate` 改为调用它。现有回归期望值一个不改。变异：让它把 report 也算 gate，`test-phase-guard.sh` 第 13 段「已修订 + 只剩 report 检查点：照旧要求复审」变红，还原后通过。
- [ ] Task 2：`gates` 的测试（先红）
- [ ] Task 3：实现与接口说明
- [ ] Checkpoint 1（report）：map 与接口回归全绿
- [ ] Task 4：文档、实跑、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行
