# Todo: rework-in-place

- [x] Task 1：`verify-artifacts` 的旁路清单警告（先红） — `test-verify-artifacts.sh` 新增 8 例：有未勾选项时警告并含路径与项数、说明不计入阶段、全部勾选不输出、没有清单项不输出、`plan.md`／`todo.md` 自己的未勾选项不触发、子目录与非 md 文件不看、没有 `tasks/` 不输出、检查没跑成报未验证；先在第一例失败。`verify-artifacts.sh` 加一段只读检查，判据是 `module_stage.UNCHECKED`。60 例全绿；在本仓库实跑 5 通过 0 警告（两份既有旁路文件全是已勾选项）。
- [x] Task 2：规则「返工与小模块」，命令文件与技能（先红） — `test_workflow_checkpoints.py` 新增 1 例（新节的十个关键词；`add-module` 的命令文件与技能各含“返工”“不新增行为”），先失败。共享检查点规则新增一节「返工与小模块」；`commands/add-module.md` 与 `spec-guard-ops` 的 add-module 一节各补一段。改完后另一条既有断言变红：提到“共享检查点规则”的文件必须点名能找到它的技能，我在命令文件里新加的那句没点名；补上 `spec-guard-ops` 后 19 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 随 Task 2 的提交跑 `verify-and-commit.sh` 全档。未验证：安装副本上的实际输出（发版后看）。
- [x] Task 3：文档、CHANGELOG 与版本号 — `docs/workflow.md` 两段（返工、模块太小）；`docs/troubleshooting.md` 一行（新警告的含义与处理）；CHANGELOG `[0.59.0] - 2026-10-13`；两份 `plugin.json` 改为 0.59.0，中英 README 的 `--ref` 改为 v0.59.0。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-13 在对话里展示验证结果、未验证项与任务 2 里的一次偏差，用户确认推送与开 PR。验证链（`verify-and-commit.sh` 全档，macOS `/bin/bash`）：`validate.sh` 通过、phase-guard 284 例（未改）、verify-artifacts 60 例、`test_workflow_checkpoints.py` 19 例、ShellCheck 无告警；本仓库实跑 `verify-artifacts` 5 通过 0 警告。Spec 批准后未改动。未验证：安装副本上的实际输出（发版后看）；未做独立代码评审。同日收到一个实地用例（已完成模块里做“第二批”新增操作，agent 改写原文件并自建归档目录）：按本模块的规则属于新能力、应另开模块，未因此增加规则。
- [x] 发版后的验证（2026-10-13，v0.59.0） — 两份安装副本上跑改过的测试全绿；带旁路清单的临时项目上，两份副本的 `verify-artifacts` 都给出一条警告（文件与项数），汇总 3 通过 1 警告 0 失败，退出码 0；安装副本的检查点规则里有「返工与小模块」一节。固定文字与固定输出，未另做真实 agent 会话。记录见 `docs/releases/v0.59.0-*.json`。
