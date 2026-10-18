# Todo: boundary-hint-unknown-size

- [x] Task 1：回归先行 — `test-phase-guard.sh`：`boundary()` 改为喂一份恰好 700k 的会话记录、断言带大小的那一行（9 个调用点不变）；不贴交接文本的检查循环去掉不带大小的那一行；原「DONE 读不到大小时保持现行 Module boundary 行」改为不出，并新增 Codex 与判断不了宿主两例；无人值守对照、Codex 模块完成行写法、判断不了宿主的写法、中文 DONE 各改为喂达到边界档的记录，断言带大小的行；新增中文 DONE 读不到不出一例。旧代码上只有「读不到就不出」的新用例变红（同段在第一处失败后停下），改喂记录的用例全绿，证明文字覆盖没丢。
- [x] Task 2：改分支 — `module_stage.py`：读不到大小（`None`）时 `boundary_note_line` 为空，删掉内联的中英两句不带大小的文字；phase-guard 413 例全绿。变异（恢复原分支）：Claude DONE 与 zh-CN DONE 两例变红。与模块 ③ 同样，Task 1、2 合成一个提交（新用例在旧代码上是红的，提交脚本检查整个工作区）。
- [x] Checkpoint 1（report）：phase-guard 全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [ ] Task 3：CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行

## 外部审查意见

<!-- spec-guard: external-review declined -->
