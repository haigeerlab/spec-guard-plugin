# Todo: quiet-injection

- [x] Task 0：同步批准标记 — 按开工通知 C150 单独 `module-crew sync` 到集成分支 cb1e55c（HEAD 520fc41e）；Spec、Plan 取集成分支带批准标记的版本。validate、phase-guard（443 例）、verify-artifacts（74 例）全过。按用户批准 C145 的原话改 Spec 的 AC9 并在变更记录记一行（Spec 指纹随之变为修订，最终验收附这段差异）。
- [x] Task 1：删 80% 行、修 Claude 窗口（改动 2） — 回归先改：part_9 的 80% 用例改为反向断言（BUILDING 800k、Codex BUILDING 窗口 80%、NEEDS_SPEC 两模块夹具里的 BUILDING 850k、中文 BUILDING 850k 都不出上下文行），无人值守的几条改用 DONE 的边界行，SessionStart 对照改用 DONE；新增 Claude 估算 4 例（140k 按 200k 出行、差一个 token 不出、恰好 200k 仍按 200k、早先有读数超过 200k 后按 1M 估算 150k 不出）；边界行的阈值说明改为「at or over 70% of an estimated 1000 k window」／「达到或超过按 1000 k 窗口估算的 70%」。改前 9 段红。实现：`module_stage.py` 删 `MID_SHARE`、`DEFAULT_WINDOW`、`context_line`、各宿主的 `free-current`，`thresholds()` 只算边界档、没有窗口时不出行，新增 `--window-estimated`；`session_context.py` 抽出 `tail_lines()`（尾部只读一遍）与 `over_standard_window()`，第六行输出 `over-200k`；`phase-guard.sh` 改为逐行解析事实（原来按「末行是 codex」判宿主，多一行后会失效），Claude 有读数时传估算窗口。`test_workflow_checkpoints.py` 的短语 `80%` 改为 `70%` 并断言不含 `80%`（先红），检查点规则那一句改为只讲边界提示。phase-guard 440 例、`test_workflow_checkpoints.py`、`test_stop_rules.py`、`test_module_stage_sanitization.py`、`test_python_compat.py` 全过；三个删掉的名字 grep 为空。**越界一处**：`hooks/test_session_context.py` 不在 Spec 独占清单里，它断言会话事实恰好 5 行，加第六行必须改它（只改这一条用例的行数与新行断言），最终验收的越界检查里写明。
- [ ] Task 2：状态码（改动 1 前半）
- [ ] Task 3：一行形式与选择（改动 1 后半）
- [ ] Task 4：英文标签与评测脚本（改动 3、改动 5 的 evals）
- [ ] Task 5：说明文字（改动 4）
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 6：真实宿主核对（AC9）
- [ ] Task 7：合入集成分支并跑完整检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做
