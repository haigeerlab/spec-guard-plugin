# Todo: ledger-init-machine-config

- [x] Task 0：提交已批准的 Plan 与 todo — Plan 经用户批准（2026-10-18），与本 todo 一次提交。
- [x] Task 1：拒绝时报出清理过的 message（先红） — 新增 `EpiqRefusalMessageTests` 4 例，先 3 例失败；`clean_refusal_message` 换控制字符、合并空白、遮掉文本中任意 `scheme://userinfo@`、限 300 字；没有字符串 message 时仍是原文字。
- [x] Task 2：三项可选与警告编号（先红） — 改写 3 例、新增 1 例，先 4 例失败；`project_init_arguments` 只放给出的项，命令行去掉 `user-setup-required`；`warning_summary` 给出 `warningCount`、`warningCodes`，`warnings` 布尔保留，正文不出现；文本输出加警告行。验收测试的位置参数调用不受影响。
- [x] Task 3：status 的 machineSetup（先红） — 新增 `MachineSetupTests` 6 例，先失败；`machine_setup` 用 lstat + O_NOFOLLOW、限 64 KiB，只取三项。文本输出的几行只在项目未初始化时显示（已初始化时机器设置用不上，且已有单测要求那时的文本逐字不变），JSON 始终带 `machineSetup`——这一点比 Spec 的写法窄，最终验收时说明。单测 100 例全绿。
- [x] Task 4：真实 Epiq 三种情形 — 2026-10-18，已装的 Epiq 1.11.0 运行时、临时 `EPIQ_GLOBAL_DIR` 与三个临时仓库（无 origin）跑工作区版本：① 机器 userName 为 A、传 `--user-name B`：退出码 1，诊断 `Epiq refused: This machine is already set up with userName "A"; epiq_project_init does not change it. Call again without userName, or let the user change it in the TUI with :config.`；② 同一机器不传三项：先 `status` 得 `machineSetup` 为 read 且三项取值正确，初始化退出码 0，`config.json` 三项不变；③ 空机器设置、三项都传：退出码 0，`config.json` 写入 C、`code --wait`、true。②③ 都报 `warningCount` 2、`warningCodes` [init:14, init:15]（无 origin 推送失败）。本机 `~/.epiq-global` 未变；临时目录已删。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警 — 随 e93d91a 跑 `verify-and-commit.sh` 全档：phase-guard 404 例、verify-artifacts 68 例、repo-artifacts 5 通过；本模块未改 `.sh`，ShellCheck 不适用。
- [x] Task 5：说明文档 — `commands/local-ticket-ledger.md`、`skills/local-ticket-ledger-ops/SKILL.md`、`references/local-ticket-ledger-runtime.md`：初始化前看 `machineSetup`，机器已有的告诉用户是整机设置、用 TUI 的 `:config` 改，不再传；只问缺的；`unknown` 时三项都问；`Epiq refused:` 诊断；警告报条数与编号。示例命令加一行省略参数的写法。
- [x] Task 6：CHANGELOG 与 0.71.0 版本号 — 顶部「未发布」并入 `[0.71.0] - 2026-10-18`（2 个模块，变更写本模块，维护者工具保留 stdin-timing-test 那条）；两份 `plugin.json` 改为 0.71.0，中英 README 的 `--ref` 改为 v0.71.0。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-18 在对话里列出相对 7444242 的 14 个文件（均在 Plan 范围内）、比 Spec 窄的一处（status 文本只在未初始化时列机器设置，JSON 始终带）、验证结果与未验证项（宿主安装副本放到发版后，未做独立代码评审），以及发给 session-protocol 契约负责人的回告草稿；用户验收通过，回告草稿一并批准，确认推送与开 PR。
- [ ] 发版后的验证

## 外部审查意见

<!-- spec-guard: external-review declined -->

用户在最终验收时直接验收通过、没有要求外部审查（2026-10-18）。
