# Todo: user-docs-fixes

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A；Q2 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：两处事实错误（AC1、AC2） — workflow.md 第 4 步改为验收获批后 agent 按阶段提示改 activeModule、接着写下一份 Spec（对照 getting-started 对照表「切换 activeModule」一行与 workflow-checkpoints 第 51 行「验收后接着写下一份 Spec」）；
  troubleshooting 例子换成 `module_stage.brief_line(<例子项目>, 'BUILDING', 'billing', 3, '00000000', True)` 的实际输出，放进 text 代码块，逐字一致。
- [x] Task 2：README 中英与账本说明（AC3、AC8） — 前置条件写明 `/spec`、`/plan`、`/build` 来自 agent-skills，两宿主安装命令与 Codex 用 `@skill` 调用，
  均取自 `gh api repos/addyosmani/agent-skills/readme`（默认分支 main，2026-10-28 读取：README 75-79、179-188 行）与 `docs/codex-setup.md` 25、35 行，页内标注读取日期并链到其 Quick Start；
  账本未启用时 ticket 的行为写在 optional-features 账本一节，取自 `commands/ticket.md` 第 10-14 行与 `skills/ticket/SKILL.md` 96-98、48 行（只读诊断、一条下一步、不写、保持待入账）；
  README 功能一览 ticket 一行补一句并链过去。
- [x] Task 3：`docs/workflow.md` 的批准与 gate（AC4、AC5） — 「批准要留下记录」加「什么算批准」：照 workflow-checkpoints「批准标记」13-15 行（明确批准才算，含糊的「继续」「看起来可以」不算，先问清楚；来源以协作插件为准）；
  「少停、该停的照停」加不可逆或高风险清单，照 node-rules「Plan 交审」停下清单原文（推送、发布、删除工作区外的文件、改全局配置、外发凭据、全局安装、下载脚本直接执行）。
- [x] Task 4：上手文档（AC6、AC7、AC9、AC10） — AC6 写在页首语言说明处：阶段名不翻译，因为 `/map --json` 顶层 `stage` 用同样的名字（对例子项目实跑 `map_view.py --json` 得 `NEEDS_SPEC`）；
  没用 config 说明里「结构关键字」那张清单（清单里没有阶段名），按实际读取方写。AC7：第 8 步后补图例链接（`commands.md#spec-guardmap`）、默认折叠与 `--all`、
  「判断不了」因为没有上游分支（`map_view.py` 114-117、580-581 行）。AC9：「先弄清」一节加 Codex 对应表，取自 agent-skills 的 `.claude/commands/{spec,plan,build}.md` 第 5 行与 `docs/codex-setup.md` 25、35 行。
  AC10：第 3 步后加 Spec 交审消息示意，按 node-rules「Spec 交审」小项与顺序，标明不是实跑输出。AC4 的链接：第 4 步链到 workflow「什么算批准」。链接检查 0 处问题。
- [x] Checkpoint 1（report）：整体检查（validate、两套回归、链接、插件包无改动） — `validate.sh` 通过；phase-guard 507 例、verify-artifacts 78 例通过；6 份改过的文档链接 0 处问题；插件包改动为空。
  Spec AC6 理由按核对结果修订（Spec 变更记录 2026-10-28），最终验收附差异。
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行 — 2026-10-28 呈现做了什么、AC1～AC11 逐条证据、文档与其他改动表、6 个提交、Spec AC6 修订差异；用户回复「user-docs-fixes 验收通过」，修订后的 Spec 一并批准并重新记批准标记。
