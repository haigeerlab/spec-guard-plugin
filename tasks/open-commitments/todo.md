# Todo: open-commitments

- [x] Task 0：提交已批准的 Plan 与 todo — Plan 经用户批准（2026-10-18），与本 todo 一次提交。
- [x] Task 1：规则「未了的承诺」与模板行（先红） — `test_workflow_checkpoints.py` 新增 1 例（新一节的关键词；两份模板与 `docs/convention-block.md` 含新增两行），先失败；共享检查点规则在「需求来源与回告」后新增「未了的承诺」，三处约定块各新增两行，`git diff` 无删除行；43 例全绿，`verify-and-commit.sh` 全档通过（6092464）。
- [x] Task 2：钩子的读回提醒（先红） — `test-phase-guard.sh` 新增第 19 段 11 例（fresh：无账本静默、未激活目录静默、有账本只出英文/中文提醒、缺 python3 仍给英文、跟随指向按目标判断、指向失效静默；压缩后：无账本原句、有账本换成带账本的一句（中英）；UserPromptSubmit 有无账本逐字相同），并把第 15 段的 hooks.json 结构断言改为三项、新增「压缩那一项与 origin/main 逐字相同」；先在旧代码上确认第 15、19 段失败。`phase-guard.sh` 新增 `fresh_out`（只判断 `.epiq/project.json`，JSON 手写，不靠 python3）与带账本的压缩后核对句；`hooks.json` 新增 `startup|clear` 一项，命令与压缩那一项只差 `fresh` 参数。403 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 随 Task 2 的提交跑 `verify-and-commit.sh` 全档（暂存了 `.sh`，含 ShellCheck 4.1.0）。
- [ ] Task 3：宿主实测新一项钩子会触发
- [ ] Task 4：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
