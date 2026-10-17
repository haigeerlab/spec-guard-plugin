# Todo: module-concurrency-switch

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：配置键与读取函数（先红后绿） — `test_project_config.py` 新增 6 例并改 1 例（汇总项集合加入 `moduleConcurrency`，属 Spec 假设 4 的例外），先因 `module_concurrency` 不存在导入失败；`VALIDATORS`／`DEFAULTS` 加键、新增 `module_concurrency()` 后 27 例全绿，`test_python_compat` 通过。
- [x] Task 2：off 与 on 输出不变的回归（先写断言，预期直接绿） — phase-guard project-config 段加 2 例（只有 version／off／on 三种输出与无配置逐字节相同；on 加产物语言只多语言行），verify-artifacts 加 2 例（on 通过、`yes` 报 `moduleConcurrency-invalid`）。临时换回旧实现时 4 例全红，换回新实现后 phase-guard 367 例、verify-artifacts 63 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并做两次改坏验证 — `a8c7c30` 提交时 `verify-and-commit.sh` 全档通过（validate、phase-guard 367、verify-artifacts 63、repo-artifacts、ShellCheck 无告警）；首次提交被 validate 拦下一处 `$body` 后接全角括号，改为 `${body}`。改坏验证：`module_concurrency` 未设置也返回 True 时 `test_everything_else_is_false` 变红；`config_lines` 在 on 时多出一行时 phase-guard「moduleConcurrency 不应改变注入」变红；两处均已复原。
- [x] Task 3：命令说明、Codex 技能、设计文档与 CHANGELOG — `commands/config.md` description 加「多模块并行开关」、取值表加一行（含旧版本兼容提醒）、写明这个键不注入；`spec-guard-ops` 配置一节同步；`docs/design.md` 项目配置一段写明开关与唯一读取入口；`docs/commands.md` 取值表与命令总表同步；CHANGELOG 顶部新建「未发布」小节记一条「新增」。
- [x] Checkpoint 2（gate）：模块验收 — 2026-10-18 在对话正文列出：实际改动的 13 个文件（无超出预计）；`/spec-guard:config` 在未设置、设成 on、set 预览与无效值时的实跑原文；验证结果；两处小问题（汇总首列宽 16 使 `moduleConcurrency` 一行错位一格；无效值报错指向消费者项目里不存在的 `spec/project-config.md`，原有问题）；未验证项（已安装副本，待 0.68.0 发版）。用户验收通过，两处小问题决定不动。按批量发版约定不推送、不开 PR，直接进入 concurrency-assessment。
