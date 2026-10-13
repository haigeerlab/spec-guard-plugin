# Todo: rework-in-place

- [x] Task 1：`verify-artifacts` 的旁路清单警告（先红） — `test-verify-artifacts.sh` 新增 8 例：有未勾选项时警告并含路径与项数、说明不计入阶段、全部勾选不输出、没有清单项不输出、`plan.md`／`todo.md` 自己的未勾选项不触发、子目录与非 md 文件不看、没有 `tasks/` 不输出、检查没跑成报未验证；先在第一例失败。`verify-artifacts.sh` 加一段只读检查，判据是 `module_stage.UNCHECKED`。60 例全绿；在本仓库实跑 5 通过 0 警告（两份既有旁路文件全是已勾选项）。
- [x] Task 2：规则「返工与小模块」，命令文件与技能（先红） — `test_workflow_checkpoints.py` 新增 1 例（新节的十个关键词；`add-module` 的命令文件与技能各含“返工”“不新增行为”），先失败。共享检查点规则新增一节「返工与小模块」；`commands/add-module.md` 与 `spec-guard-ops` 的 add-module 一节各补一段。改完后另一条既有断言变红：提到“共享检查点规则”的文件必须点名能找到它的技能，我在命令文件里新加的那句没点名；补上 `spec-guard-ops` 后 19 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 随 Task 2 的提交跑 `verify-and-commit.sh` 全档。未验证：安装副本上的实际输出（发版后看）。
- [ ] Task 3：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
