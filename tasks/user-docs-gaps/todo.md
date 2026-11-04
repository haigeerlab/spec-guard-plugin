# Todo: user-docs-gaps

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-04 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」）。
- [x] Task 1：能力图审阅记录与 activeModule（模板注释、concepts、add-module、phase、SKILL、workflow、troubleshooting） — 模板「审阅记录」标题下加一行注释（首审自查清单、工具不读不校验、批准以对话答复为准），concepts 术语表加「能力图审阅记录」；add-module、SKILL 的「提醒用户把」与 phase 的「建议把」统一为 agent 直接改、用户也可自己改、没有专门命令，workflow 两处与 troubleshooting 同步。verify-artifacts 88 例、phase-guard 512 例通过；grep 不再有「提醒用户把」「建议把 `activeModule`」。
- [x] Task 2：命令参数补 --host 与包内 docs/ 引用改为仓库链接 — setup-convention 的 argument-hint 与 docs/commands.md 参数行补 `[--host=codex]`，teardown-convention 补 `[--host=claude|--host=codex]`（与两个脚本接受的参数一致），commands.md 各补一条什么时候用；add-module、phase、teardown-convention、verify-artifacts、spec-guard-ops 技能里 5 处插件仓库 `docs/` 引用改成 GitHub 链接。grep 包内 commands/skills/references：剩下的 `docs/` 都是使用者项目自己的文档基线路径，不是插件仓库文档，保留。
- [ ] Task 3：补说明（契约路径、单项目目录、关键卡点、idea-refine、Spec/Plan/todo 格式与标记）
- [ ] Task 4：版本号 0.86.4 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查与收尾 grep
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、回告 ecosystem-lead
