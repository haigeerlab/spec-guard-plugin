# Spec: module-cost-report

## Objective

`build-task-dispatch` 让 `/build` 把 task 交给子代理，目的只有一个：省钱（订阅账号省的是额度）。但「派了是否
更省」至今没人能回答：tier-guard 只在派活边界记录档位与请求的模型，主会话的花费没人统计，也没有「不派」的基线。
tier-guard 会话用 textkit 验收运行手工算过一次总账：父子同为 sonnet 时，派活比不派贵 2.1–3.0 倍。

本模块提供一个**只读的报告**：离线读取宿主自己的会话记录，按模块、按 task 汇总主代理与子代理的 token、
派活次数与返工信号，让用户在用一段时间后能回答两个问题：用了子代理是否更省；是否经常返工。

只有 spec-guard 知道一个模块有哪些 task、每个 task 何时完成，所以按模块算总账属于 spec-guard；tier-guard
继续只管「派活时选哪个模型」。两个插件互不读取对方的数据。

登记：2026-10-05 按用户决定经 `/spec-guard:add-module` 插入能力图，依赖 `local-convention`、`build-task-dispatch`。
数据来源一节的若干口径来自 tier-guard 会话实测踩过的坑（2026-10-05），与 tier-guard `hooks/tier_report.py` 的
`_usage_groups` 口径一致，以便联调时交叉核对。

## Assumptions

用户已于 2026-10-05 确认：

1. 入口是 Claude 的 `/spec-guard:cost-report <模块>`，Codex 由 `spec-guard-ops` skill 调用；只读，不写任何文件，
   不是 hook（仓库不变量：hook 不写文件）。
2. 用 git 历史里 `tasks/<模块>/todo.md` 各项被勾上的提交时间切出 task 时间窗；窗内本项目的会话记录归到该 task。
3. 每个 task 输出主代理、子代理各自的 token（按模型、按类别）、派活次数与返工信号。
4. 默认只输出 token；用户提供价格文件时折算为等价金额；插件不内置价格。
5. 只输出计数，不输出任何 prompt、代码或会话内容。
6. 可一次报告多个模块，并按「派过 / 没派过」分组汇总，用于对照。

## 数据来源（2026-10-05 在本机实测）

### Claude Code

- 主会话：`~/.claude/projects/<项目路径编码>/<sessionId>.jsonl`。路径编码：先取 realpath（macOS 上
  `/var/folders/…` 记作 `/private/var/folders/…`），再把 `/`、`.`、`_` 换成 `-`（本仓库为
  `-Users-vilin-Documents-haigeerlab-spec-guard-plugin`）；另以每条记录的 `cwd` 复核属于本项目。
  `--continue` 追加到同一主会话文件，`-p` 每次新建文件；同目录下可能有别的会话，一律按时间窗筛选。
- 子代理：`<sessionId>/subagents/agent-<agentId>.jsonl`，记录带 `isSidechain: true` 与 `agentId`；同名
  `.meta.json` 带 `agentType`、`model`、`toolUseId`（对应主会话里那次 Agent 调用的 `tool_use.id`）。
  主会话文件里不含子代理消息，**不能**靠主文件中的 `isSidechain` 找子代理。以 SendMessage 续派同一子代理时内容
  追加到同一文件，所以每个子代理文件**整份只计一次**。
- 有些子代理宿主不写 transcript（tier-guard 日志里约 85% 的结束事件属此类）：主会话有 Agent 调用、却找不到对应
  子代理文件时，计为「无记录的派活」，其用量未知，报告单列次数与覆盖率，不当作 0。
- 用量：`type: assistant` 记录的 `message.usage`，字段 `input_tokens`、`cache_creation_input_tokens`（其中
  `cache_creation.ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens` 分开）、`cache_read_input_tokens`、
  `output_tokens`；模型在 `message.model`。
- **必须去重**：同一条消息会按内容块各写一行，流式时还会重写，每行都带一份 usage（本会话 521 行带用量的记录只有
  226 个不同 `message.id`，最多重复 5 次；tier-guard 在 109 份 transcript 上实测，不去重时输入多算 1.97×）。规则：
  按（文件, `message.id`）分组，每组取 usage 总量最大的一行；没有 `message.id` 的行逐行计入。
- 按**每条消息自己的** `message.model` 计价，不按会话；会话中途可换模型。

### Codex

- 会话：`~/.codex/sessions/YYYY/MM/DD/rollout-*-<threadId>.jsonl`；`session_meta.payload.cwd` 判断是否属于本项目。
- 子代理：`session_meta.payload.session_id` 等于主线程 id、`id` 不同的 rollout；`source.subagent.thread_spawn`
  带 `parent_thread_id` 与 `agent_path`。`source.other == "guardian"` 是宿主的审批代理，单列，不算派活。
- 用量：`event_msg` 的 `token_count.info.total_token_usage`，为线程内**累计值**（`input_tokens`、
  `cached_input_tokens`、`cache_write_input_tokens`、`output_tokens`、`reasoning_output_tokens`）；不要把每条事件的
  累计值相加。某时间窗的用量是窗内最后一条与窗前最后一条累计值之差；整条子线程取其最后一条。模型在
  `turn_context.payload.model` 与 `effort`。
- `input_tokens` **已包含**缓存命中（实测 `total_tokens = input_tokens + output_tokens`）：非缓存输入 =
  `input_tokens − cached_input_tokens`。`reasoning_output_tokens` **已含在** `output_tokens` 内：2026-10-05 本机
  1417 份 rollout 的最后累计值全部满足 `total = input + output`，有推理的 1344 份全部满足 `reasoning ≤ output`。
  计价时推理不另加，只作参考列出。
- `codex exec --ephemeral` 不写 rollout，这类运行没有用量数据。
- 派活：主线程 `function_call` 中 `name == "spawn_agent"`，参数明文含 `task_name`、`model`、`reasoning_effort`；
  `message` 是加密的，不读。

## Contract

### C1 归属：模块 → task 时间窗

- task 列表取自 `tasks/<模块>/todo.md` 的勾选项（含 Checkpoint），顺序同文件。
- 每项的**完成时间**是首次把该行改为已勾选的提交的提交时间（`git log` 逐提交比对该文件）。task 的时间窗为
  （上一项完成时间，本项完成时间]；第一项的起点是首次出现该 todo.md 的提交时间。
- 尚未勾选的项归入「进行中」，窗口终点为报告运行时刻。
- 没有 git 历史、todo.md 未提交或无法确定窗口时，该模块报告为**无法归属**并说明原因，不报 0。
- 时间窗内本项目的所有会话都会计入，报告列出贡献会话的 id 与各自用量，并提示「并行会话也会被计入」。

### C2 统计口径（每个 task）

- **主代理**：主会话在窗口内的用量。Claude 按 `message.id` 去重后求和；Codex 取累计值之差。
- **子代理**：窗口内发起的每次派活（Claude：主会话 `Agent` 工具调用，经 `toolUseId` 关联子代理文件；Codex：
  `spawn_agent`，经 thread 关联子 rollout）的全部用量，计到发起它的 task；按模型分列。
- **类别**：Claude 为输入、缓存写（5m / 1h 分列）、缓存读、输出；Codex 为非缓存输入、缓存读、缓存写、输出（其中
  推理输出单列作参考，已含在输出内、不重复计价）。宿主未提供的类别标「未提供」，不推算。
- **覆盖率**：每个 task 报「有记录的派活 / 全部派活」；无记录的派活不计入平均值。
- **派活次数**、**重派**（同一 task 派活次数减一）、**收回**（主会话中 Agent 调用的错误结果以 tier-guard 收回原因
  开头，即包含「第二次失败后的收回」）、**子代理交回后主代理改动的文件数**（该 task 最后一次派活结束之后、窗口结束
  之前，主代理用 Edit / Write / MultiEdit 或 Codex `apply_patch` 改动的不同路径数，排除 `tasks/<模块>/todo.md`）。
- 「测试是否一次通过」本模块**不统计**：它需要解析工具输出语义，误判风险高；留给后续模块。

### C3 价格与等价金额

- `--prices <文件>`：JSON，形如
  `{"currency":"USD","per":"1M","models":{"claude-opus-5-5":{"input":5,"cache_write_5m":6.25,"cache_write_1h":10,"cache_read":0.5,"output":25}}}`。
  模型名按宿主记录的原样匹配。
- 有价格的类别折算为金额；缺价的模型或类别标「未定价」，总额注明「不含未定价部分」，不猜价格。
- 不提供价格文件时只输出 token。插件不附带任何价格数据。

### C4 输出

- 默认人读表格：模块 → task 行（主代理 / 子代理 token 合计与金额、派活、重派、收回、交回后改动），模块合计行，
  贡献会话清单，以及一节「无法统计的部分」（未提供的类别、无法归属的会话、Codex 子代理正文加密等）。
- `--json` 输出同一份数据的机器可读形式。
- 多个模块时追加对照节：按「有派活的 task / 没有派活的 task」分组，给出每 task 平均 token（与金额，如有价格）。
  同时注明：不同模块规模不同，对照只能看趋势，因果结论须来自受控实验。
- 退出码：0 正常；2 输入错误或模块无法归属；从不因「没有会话数据」而报错，而是如实报告为空并说明。

### C5 隐私与边界

- 只读宿主会话目录与本仓库 git；不写任何文件，不联网。
- 输出只含计数、模型名、会话与 agent 的 id、文件路径计数；不含 prompt、回复、工具参数或代码。
- 不读 tier-guard 的日志或配置。

### C6 文档

- `commands/cost-report.md`（Claude）、`skills/spec-guard-ops/SKILL.md` 增加 cost-report 路由（Codex）。
- `docs/workflow.md` 在可选（实验性）派活一段后加「怎么看省没省钱」。
- `CHANGELOG.md` 未发布节。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_module_cost_report.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
```

## Project structure

```text
plugins/spec-guard/hooks/module_cost_report.py       -> C1–C5 实现（只依赖 python3 标准库与 git）
plugins/spec-guard/hooks/test_module_cost_report.py  -> 回归（合成的 transcript / rollout / git 夹具）
plugins/spec-guard/commands/cost-report.md, skills/spec-guard-ops/SKILL.md,
docs/workflow.md, CHANGELOG.md                       -> C6
scripts/validate.sh                                  -> 登记新测试
```

## Testing strategy

先写测试并确认在当前代码上失败，再实现。夹具全部合成，不依赖本机真实会话：

- 归属：两个 task 的勾选提交切出两个窗口；窗口外的消息不计入；未提交的 todo → 无法归属、退出 2。
- Claude 去重：同一 `message.id` 出现三行（output 逐行增长）只计 usage 最大的一行；无 id 的行逐行计入；子代理经
  `toolUseId` 计到发起它的 task，续派追加的文件只计一次；缓存写 5m / 1h 分列；会话中途换模型时按消息各自计价；
  有 Agent 调用但无子代理文件 → 无记录的派活、覆盖率下降。
- 路径编码：含 `.`、`_` 的项目路径与 `/var` → `/private/var` 的 realpath 能找到正确的项目目录。
- Codex：累计值求差而非相加；非缓存输入 = input − cached；子 rollout 经 `session_id` 关联；guardian 单列不算派活；
  `spawn_agent` 计数。
- 返工信号：同一 task 两次派活 → 重派 1；收回原因 → 收回 1；交回后主代理改两个文件（含 todo.md）→ 计 1。
- 价格：有价折算；缺价标「未定价」且总额注明；无价格文件只出 token。
- 隐私：夹具里的 prompt 与代码字符串不出现在任何输出（人读与 `--json`）。
- 多模块对照：分组平均正确，并带「只能看趋势」的说明。
- 默认 `python3` 与 `/usr/bin/python3` 3.9 下通过。

## Boundaries

- Always：只读；未知即未知；去重后再求和；输出不含内容。
- Ask first：统计测试是否一次通过；读取 tier-guard 数据；内置任何价格；把报告接进 hook 或阶段注入。
- Never：写文件、联网、解密或读取 Codex 加密内容、把「没有数据」报成 0。

## Success criteria

- 在本仓库对 `build-task-dispatch` 运行，能给出各 task 的主代理与子代理 token，且与按 `message.id` 去重的手工核算一致。
- 在 tier-guard 会话的对照实验项目上运行，「派 / 不派」两组的总账与其 research 文档中的数字一致（联调验证）。
- Claude 与 Codex 两种会话记录都能统计；无法统计的部分在报告中明确列出。
