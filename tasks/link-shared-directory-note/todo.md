# Todo: link-shared-directory-note

- [x] Task 1：`Linked project` 行、预览与 `show` 的说明（先红） — `test-phase-guard.sh` 把 `Linked project` 行的逐字期望改为带新句子的文字；`test_project_link.py` 新增 1 例（`set` 的预览与写入输出、有效时的 `show` 含这句话，没有指向或指向失效时不含）。两处先失败；`phase-guard.sh` 在该行末尾加一句，`project_link.py` 新增常量 `SHARED` 并在 `set` 与有效的 `show` 输出。单测 19 例、phase-guard 284 例全绿。
- [ ] Task 2：命令文件、技能、排障文档、CHANGELOG 与版本号
- [ ] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
