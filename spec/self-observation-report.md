# Spec: self-observation-report

## Objective

spec-guard 已过多轮审计，但问题至今都靠维护者手工审计发现。插件每次注入的阶段提示，宿主本来就记在会话记录里：
这是一份现成的、关于插件在真实使用中表现如何的观测数据，只是没人读。

本模块提供一个**维护者用的只读脚本**：离线读取本机 Claude Code transcript 与 Codex rollout 中 spec-guard 注入的
阶段提示，找出疑似问题，每条带稳定指纹与脱敏的位置。维护者挑出值得跟进的，由会话按指纹查本地事项账本、经预览确认后
记成事项，之后走现有的模块流程修复。脚本只负责「发现」；「改」永远经过人。

数据只来自维护者本人在自己各项目里的使用；脚本不随插件分发，不影响任何使用者。

登记：2026-10-09 按用户决定经 `/spec-guard:add-module` 插入能力图，依赖 `module-cost-report`（复用会话记录读取）、
`phase-and-verification`（阶段语义）。

## Assumptions

用户已于 2026-10-09 确认：

1. 只做维护者脚本（`scripts/`），不做插件命令，不进发布包，没有开关。
2. 不存任何状态；同一问题是否已处理，靠指纹去本地事项账本查。
3. 报告中的项目路径一律换成哈希；`--reveal` 时才在本机输出原始路径。
4. 只读：不写文件、不联网、不改 hook、不碰任何不变量。

## 数据来源（2026-10-09 在本机实测）

### Claude Code

- 主会话 `~/.claude/projects/<编码>/<sessionId>.jsonl`（只读顶层文件；`subagents/` 下的子代理文件不读，避免重复）。
- 注入记录：`type: attachment`，`attachment.type == "hook_additional_context"`，`attachment.content` 是字符串数组，
  每个 hook 一段。属于 spec-guard 的段以 `## spec-guard ` 或 `## agent-skills 链路状态` 开头（后者为 0.9 时代旧格式）。
- 实测：全部 transcript 中 spec-guard 注入 2946 段；阶段分布含 `BUILDING` 943、`DONE` 857、`LEGACY_TRACKER_RETIRED` 442、
  `MAP_INVALID` 114，另有 234 段为旧格式（如 `IDLE (已归档)`，阶段名不是单个词）。
- 项目：记录的 `cwd`，取 realpath。

### Codex

- `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`；`session_meta.payload.source.subagent` 存在的是子线程，不读。
- 注入记录：`type: response_item`、`payload.role == "developer"` 的消息，`payload.content[].text` 中以同样标题开头的段。
- 实测：近 30 天 1331 份 rollout，阶段分布 `BUILDING` 375、`DONE` 232、`IDLE` 82 等。
- 项目：`session_meta.payload.cwd`，取 realpath。

### 看不到的东西

- 两个宿主都**不记录 hook 进程失败**（全部 Claude transcript 中 hook 相关附件只有 `hook_additional_context` 与
  `hook_success` 两种；Codex 无对应记录）。hook 崩溃且无输出时，本脚本无从得知；报告固定在「无法观测」一节说明。
- 注入文本不含插件版本；只按时间报告首次与末次出现，不推断版本。

## Contract

### C1 注入事件

- 从两个宿主读出 spec-guard 注入事件：时间、宿主、项目、会话 id、行号、阶段、建议行。
- 阶段：匹配 `当前阶段: **<X>**`，`<X>` 取到 `**` 之前的全文（可含空格与括号）；无此行的段阶段记为 `?`。
- 建议行：以 `Suggested next step:` 或 `建议下一步:` 开头的第一行；没有则为空。
- `--since <N>d`（默认 `14d`）只取该时间之后的事件；时间戳小数位补齐到六位再解析（Python 3.9），无法解析的行计数后在报告中说明。
- `--claude-home`、`--codex-home` 注入目录（默认 `~/.claude`、`~/.codex`），测试用合成夹具。

### C2 信号

- **S1 重复未变**：同一项目内按时间排序，阶段与建议行（归一化后）都不变的连续注入，次数 ≥ `--min-repeat`（默认 20）
  且首末跨 ≥ 2 个自然日。含义：要么用户一直不照做（提示是噪声），要么照做不了（提示没用）。
- **S2 诊断态**：阶段为 `UNKNOWN`、`MAP_INVALID`、`?`，或文本含 `python3 无法运行`。每次出现都计入，不设阈值。
- 归一化：反引号内的内容替换为 `<id>`，数字替换为 `<n>`，用于建议行比较与指纹。

### C3 发现项与指纹

- 同一（信号, 阶段, 归一化建议行）跨项目合并为一个发现项，列出受影响项目、次数、会话数、首末时间，以及最多 3 个例子位置。
- 指纹：`F-` 加上（信号, 阶段, 归一化建议行）的 sha1 前 4 位；不含项目与时间，所以同一问题多次运行指纹不变。
- 按次数降序输出。

### C4 输出与隐私

- 默认人读文本；`--json` 输出同一份数据。
- 项目显示为 `project#<realpath 的 sha1 前 4 位>`；例子位置为「项目哈希、会话 id 前 6 位、行号」。
- `--reveal` 时额外输出哈希到原始路径的对照，只在本机终端使用。
- 输出不含 prompt、回复或注入正文以外的任何会话内容；注入正文只输出阶段与归一化后的建议行。
- 固定输出「无法观测」一节（hook 进程失败、插件版本）与本次无法解析的行数。
- 退出码：0 正常（含无发现、无会话数据）；2 参数错误。

### C5 维护者流程（文档）

`docs/maintainer-workflow.md` 增加一节：何时运行；如何挑选；用指纹在本地事项账本里查重；建事项前先预览并去掉
真实项目名；不想跟进的也可以记成事项再以「不修」关闭，下次报告即视为已处理（脚本本身不读账本）。

## Commands

```text
python3 -B scripts/test_self_report.py
python3 -B scripts/self_report.py --since 14d
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Project structure

```text
scripts/self_report.py         -> C1–C4（python3 标准库；复用 module_cost_report 的 JSONL 读取与时间解析）
scripts/test_self_report.py    -> 回归（合成的 transcript / rollout 夹具）
scripts/validate.sh            -> 登记新测试
docs/maintainer-workflow.md    -> C5
```

## Testing strategy

先写测试并确认在当前代码上失败，再实现。夹具全部合成，不读本机真实会话：

- 读取：Claude 附件中一段 spec-guard、一段其他 hook，只取前者；subagents 目录下的文件不读；Codex 子线程不读；
  旧格式 `IDLE (已归档)` 阶段完整取出；无阶段行记 `?`；`--since` 之外的事件不计。
- S1：21 次同阶段同建议跨 2 天 → 1 项；19 次 → 无；21 次但都在同一天 → 无；中途建议行变化 → 计数重置。
- S2：`MAP_INVALID` 1 次即报；python3 失败文本识别。
- 指纹：两个项目同一问题合并为一项、指纹相同；建议行中模块 id 不同但归一化后相同 → 同一指纹。
- 隐私：夹具中的项目路径、用户 prompt 字符串不出现在默认输出与 `--json`；`--reveal` 时路径出现。
- 默认 `python3` 与 `/usr/bin/python3` 3.9 下通过。

## Boundaries

- Always：只读；未知即未知（无法观测的写明，不报 0）；输出脱敏。
- Ask first：让 hook 自己写日志；在注入文本中加入版本号；把脚本做成插件命令或随包分发；脚本直接读写事项账本。
- Never：写文件、联网、自动修改插件代码或配置、把真实项目名写进仓库、提交或 PR。

## Success criteria

- 在本机真实数据上运行（`--since 3650d`），能报出 `LEGACY_TRACKER_RETIRED` 与 `MAP_INVALID` 两类发现项；S2 次数与
  验收当时用独立的一次性脚本手工统计的结果一致。
- 同一份数据运行两次，指纹完全相同。
- 默认输出中找不到任何真实项目路径。
