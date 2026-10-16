# Todo: phase-hint-gaps

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：D6 压缩后那一次不报大小（先红） — `test-phase-guard.sh` 新增第 16 段，6 例：UserPromptSubmit 900k 对照仍报大小；SessionStart 下 Claude BUILDING 900k、DONE 900k，以及 Codex DONE、BUILDING 250k，都不出上下文行与边界行，压缩后的核对提醒照旧。改实现前跑红（SessionStart BUILDING 900k 失败），`phase-guard.sh` 在 SessionStart 时把 `TOKENS` 置 0 后转绿；回归 308→314 例全绿，现有压缩相关用例未改。删掉置 0 那一行即为变异，对应用例变红（即改前的红）。
- [ ] Task 2：D5 没开工的当前模块也给边界行（先红）
- [ ] Task 3：D1 IDLE 与 MAP_ONLY 带配置行（先红）
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告
- [ ] Task 4：文档、能力图文字、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证：两边宿主各手动压缩一次；Claude Code 实测 `/reload-plugins`；回告观测会话
