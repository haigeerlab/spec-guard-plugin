# Todo: sg-gate-flow

- [x] Task 1：预设 `autopilot` 与带 `preset` 的对象
- [x] Task 2：提前授权
- [x] Task 3：总体技术方案关卡
- [x] Task 4：里程碑不阻塞
- [x] Task 5：先说一句
- [x] Checkpoint 1（report）：完整档与变异
- [x] Task 6：规则文字
- [x] Task 7：接口与版本
- [x] 最终验收（gate）：推送、开 PR、验收并同时问合并

## 证据
- Task 1（2026-11-27）：`project_config.py` 加 `autopilot` 预设（reviewer／auto／auto-confirm，不是出厂默认）、对象可带 `preset` 键（`expand` 先取预设再覆盖，`legacy` 写了的照写、写了 design 时由它推 plan）、`PRESET_LADDER` 加一格、新函数 `module_preset`；拒绝旧值的提示补上新写法。`test_sg_gate_flow.py` 新建（`PresetConfig` 8 例、`NarrowAndGates` 4 例），实现前 6 处失败 7 处报错，实现后全过；`test_project_config`、`test_map_view`、`test_flow_v2`、`test_review_marker` 照旧全过。新测试登记进 `scripts/validate.sh`。
- Task 2（2026-11-27）：`module_stage.py` 加 `RELEASE_PREAUTH`、`release_preauth_line`、`release_allowed`、`release_preauth`；`requirement_hint` 在档位把发版交给 autopilot 时多一句「做完自动发版吗？」（中英文），不交时逐字不变。`/map --json` 的 `takeover` 加 `releasePreauth`、`preset`，`interface.json` 写上两个字段的说明。`test_sg_gate_flow.py` 加 `ReleaseQuestion` 2 例、`ReleasePreauth` 4 例，实现前 2 处失败 4 处报错，实现后 18 例全过。`test_map_view.py` 三条钉死档位对象全部字段的用例（`test_without_config`、`test_module_entry_and_project_value`、`test_invalid_entries_fall_back`）补上两个新字段的预期值，原断言不删；124 例全过。
- Task 3（2026-11-27）：`module_stage.py` 加 `OVERALL_DESIGN`、`OVERALL_PATH`、`overall_design`（五种状态，Codex 或审查者标记算 pending）、`overall_wait`、`overall_hint`、`overall_problems`；`_review_hint` 在需求确认之后、模块技术方案之前拦，`stop_node` 记作 design-review，状态码加 `overall_wait`。`review_mark.py` 加 `--target overall`（只收 pending／approved，拒绝码 `overall-user-only`、`overall-none`、`overall-invalid`，检查放在 reviewer 状态的通用拒绝之前）。`/map --json` 每个模块加 `overallDesign`，`interface.json` 写字段、状态取值与 reviewMark 的 `overall`。`verify-artifacts.sh` 接上 `overall_problems`。
  用例：`OverallDesign` 6 例、`OverallReviewMark` 3 例、`OverallConsistency` 2 例。**这一项先写了实现后写用例，没有先看到红**；第一次跑有 2 处失败（reviewer 状态的拒绝码不对），改顺序后全过。用例能不能拦住回归，留到 Checkpoint 1 用变异补证。`test_map_view.py` 的 `MODULE_KEYS` 加 `overallDesign`，124 例全过。
- Task 4（2026-11-27）：`module_stage.milestone_blocking`（里程碑里每个模块的 `module_preset` 都是 `autopilot` 才为 False）；`milestone_stop` 不阻塞时事实行写「autopilot 档，不阻塞，写进汇报」、下一步为空（不替换成「先不开下一个模块」），状态码事实记 `report`。`/map --json` 的 `milestoneStop` 加 `blocking`，表格文字在不阻塞时加一句；`interface.json` 写上。用例 `MilestoneBlocking` 2 例先红（3 处失败 1 处报错）后绿；其余档位与改动前逐字相同由同一用例比对。`test_map_view.py` 的 `test_stop` 补 `blocking: True` 的预期。
- Task 5（2026-11-27）：新流程模块在 `NEEDS_REGRESSION`、`NEEDS_PLAN`、`BUILDING`，没有停点（`stop_node` 为 None）、没有待批文档、不是模块或协调角色时，下一步末尾加「先用一句话告诉用户接下来做什么」。用例 `SayFirst` 2 例先红（3 个阶段都没有）后绿；写用例时 BUILDING 夹具的技术方案影响面没写路径，越界检查正确地停在中途 gate，夹具补上路径。phase-guard 516 例、`test_flow_v2`、`test_stop_rules`、`test_review_marker`、`test_map_view` 全过。
- Checkpoint 1（2026-11-27）：Task 1～5 的提交都走完整档且全绿（phase-guard 516 例、verify-artifacts 147 例）。变异在临时副本里做（`mktemp -d` 固定前缀，跑完按前缀删除），9 个：release_preauth 不看确认、milestone_blocking 恒 False、overall 把 revised 当 approved、Codex 批过又改过的标记算批准、review-mark overall 收 Codex 状态、去掉同一草案一致性检查、先说一句不看停点、module_preset 不看模块条目、发版一问不看档位。第一次跑 8 个变红、1 个（Codex 批过又改过）没红——用例没覆盖这一分支；`OverallDesign` 补 `codex-edited` 一例后单独复跑这个变异变红。还原后 `test_sg_gate_flow.py` 33 例全过。Task 3 先写实现后写用例缺的「先红」由这几个变异补证。
- Task 6（2026-11-27）：`workflow-checkpoints.md` 六处按附录 A 逐字替换（第 162～163 行与第 331 行的发版一句按 O1 A 收窄，原文取自总账 `cae816e`，用脚本提取、替换前断言原段只出现一次）；新增「总体技术方案」「出事处理」两节（后者为用户批过的附录 B 原文）；第 154 行补指向；「需求确认」加发版一问与总体技术方案两条；「里程碑停点」加 autopilot 不阻塞。`doc-skeletons.md` 加两行标记与总体技术方案章节表；`node-rules.md` 最终验收与里程碑各补一句（最终验收一节超 3200 字节上限后压短）；`commands/config.md`、`commands/review-mark.md`、Codex 侧 `spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/workflow.md` 同步。
  `test_workflow_checkpoints.py`：钉旧原文的 9 处改为钉新原文（预估 8 处，多出 `**不授权**合并` 一个短语），断言不删；`test_no_remote_write_is_authorized_by_default` 的「自动合并」不出现改为「出现的行必须写明 autopilot」，并排除「出事处理」一节（那里只是参考时长）。新增 `IncidentSection` 4 例、`GateFlowRules` 5 例（对旧规则文件必然红：两节和新句子都不存在）。106 例全过，快档通过。
- Task 7（2026-11-27）：`interface.json` 升 1.26（各新字段在前面各 Task 里已写说明），版本 0.97.1 → 0.98.0（两份 plugin.json、两份 README 的 `--ref`），CHANGELOG 直接写 `## [0.98.0] - 2026-11-27`（不留 `[未发布]`）。`InterfaceFields` 3 例先红（版本仍是 1.25）后绿。
- 最终验收（2026-11-27）：R1～R14 全部通过，最后一次完整档全绿（validate、phase-guard 516 例、verify-artifacts 147 例）。推送分支 `claude/sg-gate-flow`，开 PR #522 并绑定，验收时 head 为 `f350f1a8`。合并前验证没有结论（没有非作者执行），在验收消息里写明。用户回「验收通过并合并」。
- 合并与发版（2026-11-26）：PR #522 squash 合并，合并提交 `b96de49f`；用户「授权发布 0.98.0」，tag `v0.98.0`，包 sha256 `f493f32c…28c8c2`，本机两边安装并逐文件比对，Codex smoke 通过（用户重新批准 hook、重开 ChatGPT 后），四份证据在 `docs/releases/v0.98.0-*.json`。
