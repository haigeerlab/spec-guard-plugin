# Todo: receipt-hint-on-message

- [x] Task 0：提交已批准的 Spec、Plan 与 todo — 用户按本模块的合并交审一次批准 Spec 与 Plan（2026-10-18），与能力图、todo 一次提交。
- [x] Task 1：回归先红 — `test-phase-guard.sh` 新增第 20 段 6 例（无账本、普通提示与正文中段提及、英文提醒位置与其余逐字不变、属性不合格与无属性、SessionStart、zh-CN）；当前代码上英文提醒那例先失败。
- [x] Task 2：实现 — `session_context.py` 新增 `--received`（只读包装开头与 from-name／from-session；会话须形如 `local_…`，名字经 `safe_fragment` 限 80 字）；`phase-guard.sh` 新增 `receipt_hint`，在阶段输出之前算好，由 `emit` 插到建议下一步之前，所有阶段都适用。构建中两处调整：①原写「第 5 行」，但第 5 行是宿主且 phase-guard 按最后一行认 Codex，改为单独的 `--received` 模式；②MAP_ONLY 等阶段由 phase-guard 直接输出，提醒改在 `emit` 里加。Spec 的 Contract 已同步修订，待最终验收时复审。phase-guard 回归 410 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警 — 随 fe20ba7 跑 `verify-and-commit.sh` 全档：phase-guard 410 例、verify-artifacts 68 例、repo-artifacts 5 通过 1 警告（Spec 批准后修订，待复审）、ShellCheck 无告警。
- [x] Task 3：CHANGELOG 与 0.72.0 版本号 — CHANGELOG `[0.72.0]`（1 个模块，新增）；两份 `plugin.json` 改为 0.72.0，中英 README 的 `--ref` 改为 v0.72.0。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-18 在对话里列出相对 207218d 的 12 个文件（均在 Plan 范围内）、实跑提醒行、Spec Contract 两处修订的原样差异（批准验收即批准修订后的 Spec）、验证结果与未验证项（真实会话复测与宿主安装副本放到发版后，未做独立代码评审），拟回告为无；用户验收通过并批准修订后的 Spec，已用 review-mark 重新记录 Spec 的批准；确认推送与开 PR。
- [ ] 发版后的验证

## 外部审查意见

<!-- spec-guard: external-review declined -->

用户在最终验收时直接验收通过、没有要求外部审查（2026-10-18）。
