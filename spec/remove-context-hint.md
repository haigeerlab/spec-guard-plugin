# Spec: remove-context-hint

<!-- spec-guard: review approved b2b3ef6d578b -->

## Objective

阶段提示在模块之间（MODULE_DONE、DONE、NEEDS_SPEC）上下文达到窗口 70% 时多出一行「模块边界: 本会话上下文约 N k token（…）；这是释放上下文的好时机」，让 agent 给用户一条 `/compact` 或 `/clear` 命令。
用户觉得这条提醒不准：还没到额度限制就弹出来，误导用户，体验不好，不如没有。决定把它去掉。

本模块删掉这条提示，以及只为它存在的上下文读数、窗口估算、无人值守判断、阈值、文字与测试。压缩后的阶段恢复（「上下文刚被压缩：…」）、位置行、收件记账提示、其他阶段提示一律不动。

给谁用：在 spec-guard 项目里干活的 agent 与用户；用户不再看到这条提醒。

登记：用户在 ecosystem-lead 处的原话（语音要点）「每次提醒的不准确，那还不如没有这个功能……可以规划一下，把这个功能去掉」，复述后回「对」（#23210）；在本会话回「说完了，并进 0.97.0」；Spec 与能力图新行 2026-11-26 用户回「批准；Q1 A；Q2 A」。不属于任何用法草案。账本 19AWVRM。

**数字从哪来（写 Spec 前核实，如实写下）**：
- 上下文大小：`hooks/session_context.py` 的 `_usage`（第 28～46 行）从会话记录尾部取主会话最后一轮的用量。Claude 是 `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`；Codex 是 `token_count` 记录里 `last_token_usage.input_tokens`。这是宿主自己写进会话记录的数，spec-guard 没有自己估。
- 窗口大小：Codex 记录里有 `model_context_window`，直接用；**Claude 的会话记录没有窗口大小**，`phase-guard.sh`（第 347～349 行）在读数超过 200k 时按 **1000k 估算**，否则不出这一行。
- 阈值：`module_stage.thresholds`（第 1287～1294 行）取窗口的 **70%**，这是 boundary-hint-70 定的建议线，不是宿主的限制。
- 所以「没到额度就弹」至少有两个原因是 spec-guard 自己的：70% 只是建议线，离宿主真正压缩还远；Claude 侧窗口是估出来的。上游给的用量数字本身是否不准，**没有核实到**：本机没有可比对的权威来源。不管原因在哪，用户的决定都是删。

**别的插件和文档有没有依赖**：查了 module-crew、decision-inbox、autopilot-hub、agent-relay、delegate-plugin、kb-plugin、tier-guard 的已跟踪文件，没有读这一行或它的文字的代码与说明。命中的「模块边界」是各自能力图里「模块边界确认」这个无关的说法；delegate 里有几份历史证据 JSON 原样录了当时的阶段提示，属于历史记录，不改。本仓库 `interface.json` 与 `/map --json` 都不含这条提示。

## Assumptions

1. **删掉什么**（Q1 A）：
   - 提示行本身：`module_stage.boundary_line`、`thresholds`、`_k`（只给它用的话）、各宿主的 `free-next` 文字与只为它存在的常量（`FREE_BOUNDARY` 等，写 Plan 时逐个核实还有没有别处用）；`_describe_body` 里三处追加这一行的地方；`describe` 在状态码没变时附带这一行的逻辑（`info["boundary"]`）。
   - 只为它存在的读数：`module_stage.py` 的 `--context-tokens`、`--context-window`、`--window-estimated`、`--unattended` 参数；`phase-guard.sh` 里 `TOKENS`、`WINDOW`、`OVER`、`WINDOW_ESTIMATED`、`UNATTENDED` 的解析与传参；`session_context.py` 里只为它算的上下文用量、窗口、over-200k、压缩后大小、无人值守判断，以及输出给 phase-guard 的对应行。
   - 对应的测试（`test-phase-guard.sh` 的边界行场景、`test_session_context.py` 里读数与无人值守的用例、`evals/hint-english-diff.sh` 里比对这一行的部分）。
2. **不动什么**：SessionStart（compact）后的阶段恢复与「上下文刚被压缩」那句；位置行；宿主判断；`last_state`（quiet-injection 的状态码比对）；收件记账提示（`--received`）；项目根目录解析（`--resolve-root`）；其他所有阶段提示与停点规则。阶段判定、状态码不变。
3. **会话事实的输出格式**：`session_context.py` 现在按行输出七项给 `phase-guard.sh`。删掉的几项不留空行占位，两边一起改成只剩用到的几项（两个文件都是本插件自己的，没有外部读取方）。
4. **文档**：`docs/commands.md`、`docs/workflow.md`、`docs/design.md`、`commands/phase.md` 里讲这条提醒的句子删掉或改写；`docs/troubleshooting.md` 里 `/compact` 代码块那条与这一行无关，留着；历史目录（`docs/retirements/`、`docs/reports/`、`docs/releases/`）不改。CHANGELOG「未发布」加一条「移除」。
5. **能力图**（Q2 A）：context-hint-thresholds、boundary-hint-70、boundary-hint-unknown-size、unattended-run-hint、unattended-long-first-record 等老模块的行留在能力图里不动（它们是已完成的历史，其中几个还有别的部分仍在用），本模块那一行写明删掉了它们的提示。
6. **版本**：并进 0.97.0（同批已有 #512、#513）；版本号已是 0.97.0，本模块不改。不改接口（`interface.json` 不含这条提示）。

## Acceptance criteria

- **AC1** 任何阶段、任何上下文大小（含 Claude 读数超过 200k、Codex 带窗口）都不再出现「模块边界: 本会话上下文约」或 "Module boundary: this session's context"；用例覆盖原来会出这一行的 MODULE_DONE、DONE、NEEDS_SPEC 与 quiet-injection 的一行模式。
- **AC2** 不出这一行之外，阶段提示逐字不变：已安装的 0.96.2 与本分支对本仓库、对几种老流程夹具（低于 70% 时）跑出的阶段提示与状态码逐字相同。
- **AC3** 压缩后（SessionStart compact）那次注入照旧给完整内容和「上下文刚被压缩」那句；位置行、收件记账提示照旧。
- **AC4** 仓库里（不含历史目录与 CHANGELOG 旧条目）不再有代码读上下文用量、窗口或无人值守来决定提示；`git grep` 核对。
- **AC5** 本机 `validate.sh`、phase-guard、verify-artifacts 全绿；合并前头提交的 `CI required` 通过。

## Boundaries

- **会做**：假设 1～6 及回归。
- **先问再做**：动到假设 2 列的任何一项；改阶段判定或状态码；改其他插件。
- **不做**：另做一个更准的提醒；改宿主自己的压缩行为；改历史目录。

## 并行边界

- 独占：`spec/remove-context-hint.md`、`tasks/remove-context-hint/`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/phase-guard.sh`、`plugins/spec-guard/hooks/session_context.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test_session_context.py`、`plugins/spec-guard/hooks/test_flow_v2.py`、`evals/hint-english-diff.sh`、`plugins/spec-guard/commands/phase.md`、`docs/commands.md`、`docs/workflow.md`、`docs/design.md`、`CHANGELOG.md`、`spec/CAPABILITY-MAP.md`
- 公共：无

## Open questions

- **Q1 删到哪一层？**（2026-11-26 用户选 A）
  - A（推荐）：提示行连同只为它存在的读数、窗口估算、无人值守判断一起删（假设 1）。用户的话是「把这个功能去掉」，留着读数没人用，以后还要维护。
  - B：只删提示行和阈值，读数与无人值守判断留着不用。改动小一些，但留下死代码。
- **Q2 老模块在能力图上的行怎么办？**（2026-11-26 用户选 A）
  - A（推荐）：留着不动，本模块的行写明删了它们的提示（假设 5）。几个老模块还有别的部分在用，挪走反而不准。
  - B：照 collaboration-map-retirement 的做法，把只为这条提示存在的模块挪到 `docs/retirements/`。代价：要逐个拆分哪些部分还在用，工作量翻倍。

## 文档建议

见假设 4。项目没有文档基线。
