# Todo: compact-next-step

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [ ] Task 1：压缩后提醒补半句（先红） — 先改测试常量看到红，再改 `COMPACT_NOTE` 转绿；`docs/design.md` 同步。
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告
- [ ] Task 2：CHANGELOG 与版本号 — CHANGELOG `[0.64.2]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.64.2。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证 — 两边升级到 0.64.2，确认压缩后注入的新措辞与每轮注入不变；能做到时看一轮真实压缩；回告来源。
