# Todo: compact-next-step

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：压缩后提醒补半句（先红） — 先把 `test-phase-guard.sh` 第 15 段的 `REMIND` 改为新措辞，回归报“带 SessionStart 参数时末尾有压缩后的核对提醒”失败（第 15 段红）；再改 `phase-guard.sh` 的 `COMPACT_NOTE`，转绿，339 例不变，“除末尾一句外逐字相同”一例保持通过。`docs/design.md` 转述补“核对后接着做建议的下一步，不就此结束这一轮”。三个文件各改 1 行。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档（含 ShellCheck）。
- [ ] Task 2：CHANGELOG 与版本号 — CHANGELOG `[0.64.2]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.64.2。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证 — 两边升级到 0.64.2，确认压缩后注入的新措辞与每轮注入不变；能做到时看一轮真实压缩；回告来源。
