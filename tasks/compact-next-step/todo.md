# Todo: compact-next-step

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：压缩后提醒补半句（先红） — 先把 `test-phase-guard.sh` 第 15 段的 `REMIND` 改为新措辞，回归报“带 SessionStart 参数时末尾有压缩后的核对提醒”失败（第 15 段红）；再改 `phase-guard.sh` 的 `COMPACT_NOTE`，转绿，339 例不变，“除末尾一句外逐字相同”一例保持通过。`docs/design.md` 转述补“核对后接着做建议的下一步，不就此结束这一轮”。三个文件各改 1 行。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档（含 ShellCheck）。
- [x] Task 2：CHANGELOG 与版本号 — CHANGELOG `[0.64.2] - 2026-10-17`（修复一条）；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.64.2。`validate.sh` 随提交通过。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-17 在对话正文列出实际改动的 12 个文件（新增 3、修改 9、删除 0，无超出 Plan 的文件）、新旧两句原文、验证（先红后绿、339 例不变、三次 `verify-and-commit.sh` 通过、ShellCheck 无告警）、未验证项（真实压缩后的行为待发版后；未做独立评审）、文档建议（只同步 `docs/design.md`）与拟回告（经「Codex LIVE-SAAS 前端基础架构监测」转 spec-guard-monitor，0.64.2 装上之后）；用户验收通过并确认推送与开 PR。
- [ ] 发版后的验证 — 两边升级到 0.64.2，确认压缩后注入的新措辞与每轮注入不变；能做到时看一轮真实压缩；回告来源。
