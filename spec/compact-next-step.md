# Spec: compact-next-step

<!-- spec-guard: review approved ccdae812a792 -->

## Objective

上下文压缩后，phase-guard 的那次注入末尾有一句核对提醒（`phase-guard.sh` 的 `COMPACT_NOTE`）：摘要里较早的请求可能已做完，
重做前先核对 todo 与状态记录。它只说了「先核对」，没说「核对完做什么」。

真实使用中（Codex 桌面版，spec-guard 0.63.0）出现过：压缩后注入内容正确（当前模块 NEEDS_SPEC，建议下一步写并审 Spec），模型
照提醒去核对压缩摘要里一条 8 小时前的旧批准，发现早已执行，就把「已核实」当作本轮结果结束了这一轮，没有转去做建议的下一步。该会话
随后静止，等它交付的其他会话一起停住约 1 小时，靠用户手动拉回。0.64.1 仍是同一句。

本模块把这句补上半句：核对后若已做完，接着做注入里的建议下一步，不要就此结束这一轮。

登记：2026-10-17 经 `/spec-guard:add-module` 插入能力图。需求来自观测会话 spec-guard-monitor 的报告，经用户同意由会话「Codex LIVE-SAAS
前端基础架构监测」（`local_4f410de8-418e-440c-90d8-436a73edcc6b`）转来；用户 2026-10-17 先选只记录，随后决定做成 0.64.2 小模块。
发版后按「需求来源与回告」回告来源。

## Assumptions

1. **只改这一句英文文案**，不改它出现的时机（只在 `SessionStart` 事件，即压缩后那次注入）与位置（注入末尾）。
2. **措辞**：
   > Context was just compacted: earlier requests in the summary may already be done; check the todo and the state record
   > before redoing anything, and once checked, carry on with the suggested next step above, if there is one, instead of
   > ending the turn.

   「above」指同一段注入里的 `Suggested next step:` 行。各阶段（含 DONE、IDLE、能力图读不了）都带这一行；只有两种诊断输出没有：
   指向文件无效、阶段算不出。所以加「if there is one」，不另写条件分支。
3. **两边宿主同时生效**：Claude Code 与 Codex 用同一个 `phase-guard.sh`，不改约定块模板，已装项目升级插件即生效，不需要
   `--replace`。
4. 不改每轮（UserPromptSubmit）注入；那里没有这句提醒，行为逐字不变。
5. 版本 0.64.2，一个 PR。

## Contract

| 位置 | 改前 | 改后 |
|---|---|---|
| `plugins/spec-guard/hooks/phase-guard.sh` 的 `COMPACT_NOTE` | `… check the todo and the state record before redoing anything.` | `… check the todo and the state record before redoing anything, and once checked, carry on with the suggested next step above, if there is one, instead of ending the turn.` |
| `test-phase-guard.sh` 第 15 段的 `REMIND` | 同改前 | 同改后 |
| `docs/design.md` 对这句的中文转述 | 「重做前先核对 todo 与状态记录」 | 补「核对后接着做建议的下一步，不就此结束这一轮」 |

CHANGELOG 记一条「修复」。

## Commands

```bash
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先改测试常量 `REMIND` 为新措辞，跑 phase-guard 回归看到第 15 段「末尾有压缩后的核对提醒」一例变红；再改 `COMPACT_NOTE` 转绿。
  「带参数时除末尾一句外应与不带参数时逐字相同」一例保持通过，证明只动了末尾这一句。
- 不带参数（每轮注入）的现有用例全部不改、全绿。
- 发版后：Codex 与 Claude Code 各在临时项目里制造一次压缩后注入（或直接以 `SessionStart` 参数调用安装副本的钩子）确认文案；能做到时
  再看一轮真实压缩后 agent 是否接着做建议的下一步，做不到就如实记为未验证。

## Boundaries

- Always：钩子只读、只报告，输出仍是宿主接受的 JSON；除这一句外注入逐字不变。
- Ask first：改动提醒出现的时机，或在每轮注入里也加类似提醒；改约定块模板。
- Never：在仓库、提交或 PR 里写消费者项目的名称或路径。

## Success criteria

1. 压缩后那次注入末尾是新措辞；每轮注入与改前逐字相同。
2. diff 只涉及 `phase-guard.sh` 的一行、测试常量一行、`docs/design.md`、CHANGELOG、版本号，以及本模块的 Spec、Plan、todo 与能力图。
