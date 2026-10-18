# Todo: receipt-hint-on-message

- [x] Task 0：提交已批准的 Spec、Plan 与 todo — 用户按本模块的合并交审一次批准 Spec 与 Plan（2026-10-18），与能力图、todo 一次提交。
- [x] Task 1：回归先红 — `test-phase-guard.sh` 新增第 20 段 6 例（无账本、普通提示与正文中段提及、英文提醒位置与其余逐字不变、属性不合格与无属性、SessionStart、zh-CN）；当前代码上英文提醒那例先失败。
- [x] Task 2：实现 — `session_context.py` 新增 `--received`（只读包装开头与 from-name／from-session；会话须形如 `local_…`，名字经 `safe_fragment` 限 80 字）；`phase-guard.sh` 新增 `receipt_hint`，在阶段输出之前算好，由 `emit` 插到建议下一步之前，所有阶段都适用。构建中两处调整：①原写「第 5 行」，但第 5 行是宿主且 phase-guard 按最后一行认 Codex，改为单独的 `--received` 模式；②MAP_ONLY 等阶段由 phase-guard 直接输出，提醒改在 `emit` 里加。Spec 的 Contract 已同步修订，待最终验收时复审。phase-guard 回归 410 例全绿。
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警
- [ ] Task 3：CHANGELOG 与 0.72.0 版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
