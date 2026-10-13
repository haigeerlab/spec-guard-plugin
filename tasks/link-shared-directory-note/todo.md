# Todo: link-shared-directory-note

- [x] Task 1：`Linked project` 行、预览与 `show` 的说明（先红） — `test-phase-guard.sh` 把 `Linked project` 行的逐字期望改为带新句子的文字；`test_project_link.py` 新增 1 例（`set` 的预览与写入输出、有效时的 `show` 含这句话，没有指向或指向失效时不含）。两处先失败；`phase-guard.sh` 在该行末尾加一句，`project_link.py` 新增常量 `SHARED` 并在 `set` 与有效的 `show` 输出。单测 19 例、phase-guard 284 例全绿。
- [x] Task 2：命令文件、技能、排障文档、CHANGELOG 与版本号 — `commands/link-project.md` 加一段“指向按目录生效，不按会话”；`spec-guard-ops` 的 link-project 一节补同一要点；`docs/troubleshooting.md` 的 `Linked project` 一行补说明；CHANGELOG `[0.58.2] - 2026-10-13`；两份 `plugin.json` 改为 0.58.2，中英 README 的 `--ref` 改为 v0.58.2。
- [ ] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
