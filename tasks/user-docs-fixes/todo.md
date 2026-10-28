# Todo: user-docs-fixes

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A；Q2 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：两处事实错误（AC1、AC2） — workflow.md 第 4 步改为验收获批后 agent 按阶段提示改 activeModule、接着写下一份 Spec（对照 getting-started 对照表「切换 activeModule」一行与 workflow-checkpoints 第 51 行「验收后接着写下一份 Spec」）；
  troubleshooting 例子换成 `module_stage.brief_line(<例子项目>, 'BUILDING', 'billing', 3, '00000000', True)` 的实际输出，放进 text 代码块，逐字一致。
- [ ] Task 2：README 中英与账本说明（AC3、AC8）
- [ ] Task 3：`docs/workflow.md` 的批准与 gate（AC4、AC5）
- [ ] Task 4：上手文档（AC6、AC7、AC9、AC10）
- [ ] Checkpoint 1（report）：整体检查（validate、两套回归、链接、插件包无改动）
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
