# Todo: boundary-hint-unknown-size

- [x] Task 1：回归先行 — `test-phase-guard.sh`：`boundary()` 改为喂一份恰好 700k 的会话记录、断言带大小的那一行（9 个调用点不变）；不贴交接文本的检查循环去掉不带大小的那一行；原「DONE 读不到大小时保持现行 Module boundary 行」改为不出，并新增 Codex 与判断不了宿主两例；无人值守对照、Codex 模块完成行写法、判断不了宿主的写法、中文 DONE 各改为喂达到边界档的记录，断言带大小的行；新增中文 DONE 读不到不出一例。旧代码上只有「读不到就不出」的新用例变红（同段在第一处失败后停下），改喂记录的用例全绿，证明文字覆盖没丢。
- [x] Task 2：改分支 — `module_stage.py`：读不到大小（`None`）时 `boundary_note_line` 为空，删掉内联的中英两句不带大小的文字；phase-guard 413 例全绿。变异（恢复原分支）：Claude DONE 与 zh-CN DONE 两例变红。与模块 ③ 同样，Task 1、2 合成一个提交（新用例在旧代码上是红的，提交脚本检查整个工作区）。
- [x] Checkpoint 1（report）：phase-guard 全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [x] Task 3：CHANGELOG 与版本号 — CHANGELOG 新增 `[0.76.0] - 2026-10-19`；两份 `plugin.json` 改为 0.76.0，中英 README 的 `--ref` 改为 v0.76.0。
- [x] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-19 在对话里按 AC1–AC4 逐条给出证据（新增 4 例读不到不出、改喂记录的用例在旧代码上即绿、phase-guard 413 例、变异 2 例红、临时项目无记录实跑 DONE 无边界行）、与 Plan 的差异（无）、未验证项（真实宿主新会话第一轮待发版后各开一个核对）、实际改动的文件清单（取自版本库：10 个文件，新增 3、修改 7、删除 0，无超出 Plan 预计的文件）与文档建议（无）。用户批准：勾上 gate、推送、开 PR。

## 外部审查意见

<!-- spec-guard: external-review declined -->
