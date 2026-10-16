# Todo: rules-in-context

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：最终验收时的修订提示（先红） — `test-phase-guard.sh` 第 13 段在“BUILDING 时 Spec 批准后被改”之后加 5 个断言：只剩最终 gate（其后有“发版后的验证”）给新建议且 Review 行不变；还有未勾任务、其后还有别的 gate、只剩 report 检查点三种照旧要求复审。与 Plan 的出入：原计划的“todo 读不了”换成“只剩 report 检查点”——读不了的 todo 在阶段判定处就先报问题，到不了这条建议；`at_final_gate` 对读不了的文件返回否。改前新建议那例红；`module_stage.py` 加 `at_final_gate`（复用 `OPEN_CHECKPOINT`、`CHECKPOINT_TIER`）并在 `review_hint` 的已修订分支前判断，转绿，331→336 例，现有用例未改。变异：判断恒为否即回到改前的红。
- [ ] Task 2：约定块模板三行（先红）
- [ ] Checkpoint 1（report）：三套核心回归、规则测试与 setup-teardown 回归全绿，ShellCheck 无警告
- [ ] Task 3：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证：两边宿主各一轮真实会话观察最终验收；回告观测会话
