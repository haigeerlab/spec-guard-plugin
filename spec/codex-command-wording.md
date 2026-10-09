# Spec: codex-command-wording

## Objective

phase-guard 每轮注入的提示里写的是 Claude Code 的斜杠命令（`/spec-guard:*`、`/build`、`/plan`、`/compact`、`/clear`），
两个宿主看到的一样。Codex 里插件只提供技能、没有斜杠命令，`/build` 不存在，`/plan` 是 Codex 自己的 Plan 模式，意思不同；
本机一份真实 Codex 会话（2026-10-02）里注入的就是 "continue `/build` on …"。另外，提示只让 agent "说一句可以 /compact"，
用户还得自己拼命令。本模块让提示按宿主给写法，并让 agent 把用户要亲手输入的命令（`/compact`、`/clear`）写成可直接复制
的一整行。来源：用户 2026-10-09 报告并确认。

读者：在 Claude Code 或 Codex 里使用 spec-guard 的开发者。

## 实测与查证（2026-10-09）

- Codex 插件清单（`.codex-plugin/plugin.json`）只有 `skills` 与 `hooks`；agent-skills 在 Codex 里同样只有技能。
- 本机 Codex 0.160.1：基础指令写明技能用 `$SkillName` 或文字点名；斜杠命令里 `/compact`（压缩对话）、`/clear`（清屏并
  开始新对话）、`/plan`（进入 Plan 模式）都有。
- Codex 源码 `codex-rs/tui/src/slash_command.rs` 的 `supports_inline_args`：`/clear`、`/new`、`/plan` 可带参数，**`/compact`
  不行**（只能用配置项 `compact_prompt` 整体改摘要方式）。
- Claude Code 官方文档（code.claude.com/docs/en/commands）：`/compact [instructions]` 可带聚焦说明；`/clear [name]` 的参数
  只是给旧会话起名。
- spec-guard 的 Codex 技能 `spec-guard-ops` 已有 phase／verify、config、module-suspend、add-module 各节。
- 注入里带命令的位置：`module_stage.py` 的 `FREE_BOUNDARY`、`context_line`、配置无效行、MAP_INVALID 建议、挂起行、缺 todo
  汇总、DONE 三种建议、NEEDS_PLAN 与 BUILDING 建议；`phase-guard.sh` 阶段算不出时的兜底行。其中几处已带
  "(Codex: spec-guard-ops …)" 括注，两边都看得到。

## Assumptions

用户 2026-10-09 批准：

1. **判断宿主**（`phase-guard.sh` 判断后以 `--host codex|claude` 传给 `module_stage.py`，不传即"拿不准"）：
   - hook 输入里的会话记录首条是 Codex 的 `session_meta` → codex；是 Claude 的记录 → claude；
   - 没有可读的会话记录时看环境：实现时在两边真实宿主里各跑一次 hook、记下环境变量，选一个只有一边会设的变量
     （候选：Claude Code 的 `CLAUDE_PROJECT_DIR`／`CLAUDE_PLUGIN_ROOT`，Codex 的 `PLUGIN_ROOT`），实测结果写进 todo；
   - 两者都判断不了时，输出与现在逐字相同（包括现有的 "(Codex: …)" 括注）。
2. **Codex 下的写法**：
   - `/spec-guard:add-module`、`/spec-guard:verify-artifacts`、`/spec-guard:config`、`/spec-guard:module-suspend --resume <id>` →
     `` `$spec-guard-ops` `` 加同名动作（例如 "`$spec-guard-ops` add-module"），不再附 "(Codex: …)" 括注；
   - `/build` → `` `$incremental-implementation` ``；`/plan` → `` `$planning-and-task-breakdown` ``；
   - `/compact`、`/clear` 保留，但 `/compact` 不带参数（见假设 3）。
3. **可直接复制的命令**（只针对用户要亲手输入的 `/compact`、`/clear`；其余命令由 agent 自己执行，不要求）：
   - 模块完成行与上下文行改为让 agent 把命令单独放进一个代码块，整行可复制，不再只"说一句可以 /compact"；
   - Claude Code：`/compact` 后面带 agent 填好的聚焦说明（下一个模块或当前任务及其下一步，一句话），例如
     `/compact 聚焦于下一个模块 x：Spec 已批准，下一步写 Plan`；
   - Codex：只给 `/compact`（不能带参数），聚焦内容不再要求；
   - `/clear` 两边都只给命令本身，仍只在"接下来的工作与当前无关"时建议；
   - "不贴交接文本"（context-hint-no-paste）不变：给的是一行命令，不是交接内容；无人值守时照旧不出这两行。
4. **Claude Code 下其余输出逐字不变**：除模块完成行与上下文行这两种 `/compact` 行外，Claude 宿主的注入与现在逐字相同
   （"(Codex: …)" 括注也保留，避免这次改动牵动无关文字）。
5. **回归**：
   - 现有 phase-guard 用例除这两种 `/compact` 行的期望文本外一条不改；
   - 新增 Codex 用例：会话记录为 Codex、无 `CLAUDE_PROJECT_DIR` 两种判定方式下，各阶段建议与挂起、缺 todo、配置无效、
     MAP_INVALID 各行用 `$` 写法且不含 `/spec-guard:`、`/build`、`/plan`；`/compact` 行不带参数；
   - 拿不准宿主时与现在逐字相同；
   - 判据各改坏一次（例如把 codex 判成 claude、漏改一处 `/spec-guard:`），相应用例变红。
6. **真实宿主核验**：实现后在本机 Claude Code 与 Codex 各跑一次真实会话，看注入原文与 agent 的转述，结果写进 todo
   （按"AI 先自己核验 UI"的做法，用户只做最终确认）。
7. **范围与发版**：改 `module_stage.py`、`phase-guard.sh`、相应回归，以及文档里引用这些提示原文的地方；改的是插件发布包，
   随下次发版发出（与在等发版的三个模块一起）。

## Requirements

1. 按假设 1 判断宿主；按假设 2、3 生成 Codex 与 Claude 的写法；按假设 4 保持其余输出不变。
2. 按假设 5 补回归并做变异证明；按假设 6 做真实宿主核验。

## Commands

```bash
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Boundaries

- Always：拿不准宿主时输出与现在逐字相同；hook 仍只读、仍只依赖 bash、git、python3；输出仍是宿主接受的 JSON。
- Ask first：推送、PR；改动超出这两种 `/compact` 行的 Claude 侧文字；新增对其他宿主的支持。
- Never：让 hook 执行命令或替用户执行 `/compact`、`/clear`；在注入里贴交接文本。

## Success criteria

1. Codex 会话里的注入不再出现 `/spec-guard:`、`/build`、`/plan`，改为对应的 `$` 写法；`/compact` 不带参数。
2. Claude Code 会话里，agent 在模块边界给出一行带填好聚焦说明、可直接复制的 `/compact …`；其余注入逐字不变。
3. 真实宿主两边各核验一次；回归与 CI 绿。

## Open questions

无。
