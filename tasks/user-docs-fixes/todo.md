# Todo: user-docs-fixes

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A；Q2 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：两处事实错误（AC1、AC2） — workflow.md 第 4 步改为验收获批后 agent 按阶段提示改 activeModule、接着写下一份 Spec（对照 getting-started 对照表「切换 activeModule」一行与 workflow-checkpoints 第 51 行「验收后接着写下一份 Spec」）；
  troubleshooting 例子换成 `module_stage.brief_line(<例子项目>, 'BUILDING', 'billing', 3, '00000000', True)` 的实际输出，放进 text 代码块，逐字一致。
- [x] Task 2：README 中英与账本说明（AC3、AC8） — 前置条件写明 `/spec`、`/plan`、`/build` 来自 agent-skills，两宿主安装命令与 Codex 用 `@skill` 调用，
  均取自 `gh api repos/addyosmani/agent-skills/readme`（默认分支 main，2026-10-28 读取：README 75-79、179-188 行）与 `docs/codex-setup.md` 25、35 行，页内标注读取日期并链到其 Quick Start；
  账本未启用时 ticket 的行为写在 optional-features 账本一节，取自 `commands/ticket.md` 第 10-14 行与 `skills/ticket/SKILL.md` 96-98、48 行（只读诊断、一条下一步、不写、保持待入账）；
  README 功能一览 ticket 一行补一句并链过去。
- [ ] Task 3：`docs/workflow.md` 的批准与 gate（AC4、AC5）
- [ ] Task 4：上手文档（AC6、AC7、AC9、AC10）
- [ ] Checkpoint 1（report）：整体检查（validate、两套回归、链接、插件包无改动）
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
