# Todo: user-docs-align

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：README 中英（AC1、AC9、AC13、AC16、AC19、AC20） — config 一行改为不列全部键；并行一节「从本版起」→「0.84.0 起」（核对 CHANGELOG 0.84.0 config-per-key）；
  对外接口不再只提 1.1；Codex 升级信任说明从安装表移到「更新」（0.61.0 压缩后、0.69.0 会话开始与清空，核对 `hooks/hooks.json` 两项 SessionStart）；
  隐私第一条拆成五条短句，并按 `hooks/session_context.py`（`last_state`、`unattended`）改正会话记录读取范围（Spec 变更记录 2026-10-28）。Codex 启用说法 README 已是标准写法，未改。
- [x] Task 2：`docs/commands.md`（AC1、AC2、AC4、AC5、AC10、AC17） — config 表加 `autonomyTier` 与一段说明（核对 `interface.json` 的 `autonomyTier`、CHANGELOG 0.85.0）；
  phase 一节写平时一行与何时完整（`module_stage.describe`／`brief_line`）、模块边界只在 MODULE_DONE／DONE 达到 70%、Claude 读数超过 200k 才按 1M 估算（`module_stage.thresholds` 与 919-924 行、CHANGELOG 0.84.1）；
  verify-artifacts 改为 11 项检查表（逐项对 `verify-artifacts.sh` 的 ok／warn／bad，退出码只看 ❌）；开头不再指向源码；`/map --json` 字段说明改指 `interface.json` 的 `mapView`。
- [x] Task 3：`docs/workflow.md`（AC2、AC3、AC4、AC11、AC12、AC14、AC15、AC16） — 「新项目」一节加四个小标题（检查点交审与批准、其他情况、账本、成本、项目级审查），
  步骤 1～4 连续；原第 84 行拆成「最终验收」「验收之后」「这些规则从哪来」三段，`--replace` 那段并进后者；新增「预先声明」一段（核对 workflow-checkpoints 77-81 行）；
  需求确认写进步骤 2、快速插入步骤 0 与 DONE 行（核对 workflow-checkpoints「需求确认」、CHANGELOG 0.82.0）；上下文提示改为一行注入与模块边界；
  「可以一次审完」两处加「你明确要求时」；补 AC 编号、中文检查点写法、验收表格与提交、复制块（CHANGELOG 0.74/0.81/0.80）；「项目级审查」压缩为三段并链到细则；Codex 说法两处统一为 spec-guard-ops。
  压缩时删去、细则里仍有的句子：Critical/Required/Optional 与优先级分开记、稳定发现编号与可恢复报告、审查冻结后「继续」的走向、`rootCauseReviewRequired` 人工核对、
  Proposal Issue 不能充当缺陷事项、旧远端 bridge 不恢复、关闭命令的 `verified` 不代替 CI 核对、后续批次改选目标不迁移（见 workflow-checkpoints 17-27 行与 hosted-ticket-workflow）。
- [x] Task 4：concepts、troubleshooting、convention-block（AC5、AC6、AC7、AC8、AC16、AC18、AC19） — concepts 设计原则 Proposal 一行如实写读取只读、晋级写能力图、收尾经授权改标签并关闭
  （核对 `module-insert.py --confirm`、proposal-closeout 命令）；troubleshooting 新增「只看到一行 spec-guard 提示」（文案取自 `module_stage.brief_line` 844 行）、
  `Project config: ignored` 一行（`module_stage.py` 413-414 行，中英两种写法）、hook 信任改为三项（`hooks/hooks.json`）、`/compact` 一行去掉 0.57.1 来历；
  convention-block 去掉同步脚本说明。Codex 说法 troubleshooting 开头已是「用 spec-guard-ops …」，未改。
- [ ] Checkpoint 1（report）：整体检查（validate、链接、AC22）
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行

## 留给下一个发版模块

- `plugins/spec-guard/commands/config.md`：`moduleConcurrency` 一行的「从本版起」改为具体版本（0.84.0）；frontmatter 描述补上自治档位。（Spec Q1 = A）
