# Todo: cn-checkpoint-gates

- [x] Task 1：判据认中文写法（先红） — `test_map_view.py` 加 4 例（演练三种形状 1/1/2、中文未标规则、冒号前标级别的任务、nextGate 指向中文 gate），先红（4 failures）；`module_stage.py` 识别改为 `Checkpoint`／`检查点` 开头或冒号前有级别，73 例全绿，原有用例未改。
- [x] Task 2：phase-guard 正反回归 — 加 5 例（「检查点」开头、冒号前标级别、中文未标中间检查点、中文最终 gate、只写「最终验收」不算）；原第 1439 行「检查点 3（gate）不算检查点」是旧判据的期望，按 Spec 改为反例（只写「最终验收」、级别在冒号后的任务、非清单项都不算），原句改成正例；423 例全过。
- [x] Task 3：接口 1.6、规则文字与 CHANGELOG — `test_workflow_checkpoints.py` 加断言先红；规则第一句补中文写法与「不算检查点」；`interface.json` 1.6，只改 `gates` 与 `appearsWhen` 说明，检查器通过；CHANGELOG 新开「[未发布]」段，两份 `plugin.json` 未动。
- [x] Checkpoint 1（report）：变异核对与演练实测 — `git archive HEAD` 副本把识别改回只认 `Checkpoint` 开头，`GateCountTest` 4 例变红。用工作区 `map_view.py --json --all` 只读读 `crew-rehearsal`：新判据 gamma/summary/delta/epsilon/zeta 的 `gates.total` 为 1/1/1/1/2（与人工数一致），旧判据（变异副本）全为 0；演练仓库 `git status` 为空。
- [ ] Checkpoint 2（gate）：模块最终验收；推送与开 PR 在此由用户确认，合并由用户进行
