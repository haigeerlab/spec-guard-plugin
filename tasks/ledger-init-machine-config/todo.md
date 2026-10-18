# Todo: ledger-init-machine-config

- [x] Task 0：提交已批准的 Plan 与 todo — Plan 经用户批准（2026-10-18），与本 todo 一次提交。
- [x] Task 1：拒绝时报出清理过的 message（先红） — 新增 `EpiqRefusalMessageTests` 4 例，先 3 例失败；`clean_refusal_message` 换控制字符、合并空白、遮掉文本中任意 `scheme://userinfo@`、限 300 字；没有字符串 message 时仍是原文字。
- [x] Task 2：三项可选与警告编号（先红） — 改写 3 例、新增 1 例，先 4 例失败；`project_init_arguments` 只放给出的项，命令行去掉 `user-setup-required`；`warning_summary` 给出 `warningCount`、`warningCodes`，`warnings` 布尔保留，正文不出现；文本输出加警告行。验收测试的位置参数调用不受影响。
- [x] Task 3：status 的 machineSetup（先红） — 新增 `MachineSetupTests` 6 例，先失败；`machine_setup` 用 lstat + O_NOFOLLOW、限 64 KiB，只取三项。文本输出的几行只在项目未初始化时显示（已初始化时机器设置用不上，且已有单测要求那时的文本逐字不变），JSON 始终带 `machineSetup`——这一点比 Spec 的写法窄，最终验收时说明。单测 100 例全绿。
- [ ] Task 4：真实 Epiq 三种情形
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警
- [ ] Task 5：说明文档
- [ ] Task 6：CHANGELOG 与 0.71.0 版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证
