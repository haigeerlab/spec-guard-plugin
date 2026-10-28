# Todo: user-docs-align

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：README 中英（AC1、AC9、AC13、AC16、AC19、AC20） — config 一行改为不列全部键；并行一节「从本版起」→「0.84.0 起」（核对 CHANGELOG 0.84.0 config-per-key）；
  对外接口不再只提 1.1；Codex 升级信任说明从安装表移到「更新」（0.61.0 压缩后、0.69.0 会话开始与清空，核对 `hooks/hooks.json` 两项 SessionStart）；
  隐私第一条拆成五条短句，并按 `hooks/session_context.py`（`last_state`、`unattended`）改正会话记录读取范围（Spec 变更记录 2026-10-28）。Codex 启用说法 README 已是标准写法，未改。
- [x] Task 2：`docs/commands.md`（AC1、AC2、AC4、AC5、AC10、AC17） — config 表加 `autonomyTier` 与一段说明（核对 `interface.json` 的 `autonomyTier`、CHANGELOG 0.85.0）；
  phase 一节写平时一行与何时完整（`module_stage.describe`／`brief_line`）、模块边界只在 MODULE_DONE／DONE 达到 70%、Claude 读数超过 200k 才按 1M 估算（`module_stage.thresholds` 与 919-924 行、CHANGELOG 0.84.1）；
  verify-artifacts 改为 11 项检查表（逐项对 `verify-artifacts.sh` 的 ok／warn／bad，退出码只看 ❌）；开头不再指向源码；`/map --json` 字段说明改指 `interface.json` 的 `mapView`。
- [ ] Task 3：`docs/workflow.md`（AC2、AC3、AC4、AC11、AC12、AC14、AC15、AC16）
- [ ] Task 4：concepts、troubleshooting、convention-block（AC5、AC6、AC7、AC8、AC16、AC18、AC19）
- [ ] Checkpoint 1（report）：整体检查（validate、链接、AC22）
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行

## 留给下一个发版模块

- `plugins/spec-guard/commands/config.md`：`moduleConcurrency` 一行的「从本版起」改为具体版本（0.84.0）；frontmatter 描述补上自治档位。（Spec Q1 = A）
