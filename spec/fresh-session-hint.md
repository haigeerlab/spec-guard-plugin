# Spec: fresh-session-hint

## Objective

费用的大头不在输出，而在每一轮把整个主会话上下文重读一遍。2026-10-05～06 本仓库的一次会话把十几个需求做在一起，
主会话上下文中位数 46.5 万 token、最高 95.8 万，按联调价格表折算约 $81.6，其中缓存读与缓存写占 87%；同期派活成本对照
（`evals/dispatch-cost/` 的 ledgerlite 种子项目）的短会话每轮约 7 万 token。spec-guard 已经把需求、计划与进度放在文件里、每轮注入阶段，开新会话不丢东西，但阶段提示
从不建议开新会话，会话长度也看不见。

本模块让阶段提示在两种时候多一行建议：模块刚完成时（模块边界）建议在新会话里开始下一个模块；主会话上下文已经很长时，
给出最近一轮的上下文大小，建议在下一个 task 边界记下决定、开新会话。此外每个阶段都注入一行当前分支与 worktree：
开新会话时要知道去哪个目录开，而本仓库这样挂着多个 worktree 的项目，用户经常不知道代码在哪。阶段提示只给模型看，
所以这一行同时要求 agent 在请求用户评审或确认时把位置说出来。

登记：2026-10-06 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-06 确认：

1. 两个触发条件各追加一行：模块完成（阶段为 `MODULE_DONE` 或 `DONE`），以及主会话上下文超过阈值。阶段取值、完成判据
   不变；除第 11 条的位置行外，其余输出逐字不变。
2. 上下文大小读宿主的会话记录：Claude 取主会话记录中最后一条带用量的 assistant 消息的
   `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`，跳过 `isSidechain` 为 true 的子代理记录；Codex 取 rollout 中最后一条 `token_count`
   事件的 `info.last_token_usage.input_tokens`（Codex 的 input 已包含缓存部分）。拿不到会话记录时只做"模块完成"一条，
   不猜。
3. 阈值固定为 200,000 token，不开放配置。
4. 遵守 hook 不变量：只读、不写文件（因此不记"已提醒过"，超过阈值就每轮提示），读取失败静默，只依赖 bash、git、python3；
   不复用 `module_cost_report.py` 的统计代码，只读最后一条用量。
5. 只在已启用约定的项目里出现，激活判据不变。
6. 不做：自动压缩、自动开会话、会话级费用报告。

本 Spec 依据实测补充的细节（2026-10-06）：

7. **hook 输入。** Claude Code 2.x 的 `UserPromptSubmit` 输入实测含 `transcript_path`（指向已存在的主会话 JSONL），另有
   `session_id`、`cwd`、`prompt` 等。Codex（`CodexCLI.app` 内置的 `user-prompt-submit.command.input` JSON Schema）声明
   `transcript_path` 为可空字符串；真实 Codex 会话中是否非空**未实测**（临时注册的 hook 未获信任，没有执行），放到
   Checkpoint 用安装版在真实 Codex 会话里核对。为空或缺失时按第 2 条只做"模块完成"一条。
8. **只读末尾。** 会话记录可达数十 MB；只从文件末尾向前读，最多读 4 MiB，找到第一条符合第 2 条的记录即停；读满仍没有
   就当作拿不到。读取中遇到无法解析的行跳过。
9. **输出。** 两行都写在阶段输出的末尾、`Suggested next step` 之前的事实列表里，英文，与现有行风格一致：
   - 模块完成：`- Module boundary: start the next piece of work in a new session; this stage summary carries over, the conversation does not need to.`
   - 上下文过长：`- Session context: about N k tokens in the last turn (over 200k); every turn re-reads it. At the next task boundary, record decisions in the spec and start a new session.`
     其中 N 为四舍五入到千的整数。
   两个条件同时满足时两行都出现，模块完成在前。
10. **`IDLE`、`MAP_ONLY`、`MAP_INVALID`、`UNKNOWN` 阶段不加第 9 条的两行**：这些阶段还没有可依赖的模块状态，开新会话后
    无从接上。（第 11 条的位置行仍然出现。）

用户已于 2026-10-06 确认（评审中追加）：

11. **位置行。** 所有阶段（含 `IDLE`、`MAP_ONLY`、`MAP_INVALID`、`UNKNOWN`）在标题 `## spec-guard local workflow` 与
    `当前阶段` 之间注入一行：
    `Location: branch `<分支>` · worktree `<工作树根目录>`. State this location to the user whenever you ask them to review or confirm.`
    分支取 `git rev-parse --abbrev-ref HEAD`，分离 HEAD 时写 `detached at <短 sha>`；工作树取 `git rev-parse --show-toplevel`。
    两个值都经 `module_stage.safe_fragment` 清洗；不是 git 仓库或 git 失败时不出这一行，其余输出照常。只用 git 读，不联网。
    转告用户是对 agent 的软约束，不做强制。

## Contract

- 新增 `hooks/session_context.py`（只依赖标准库）：
  - `context_tokens(transcript_path) -> int | None`：按第 2、8 条读取；路径为空、不存在、读失败或没有找到记录时返回
    `None`；不输出任何会话内容。
  - `transcript_path_from_hook_input(text) -> str | None`：从 hook 输入 JSON 取 `transcript_path`；不是 JSON、字段缺失、
    为空或不是字符串时返回 `None`。
  - `location_line(root) -> str | None`：按第 11 条生成位置行；失败返回 `None`。
  - 命令行入口 `python3 session_context.py <root>`：从标准输入读 hook 输入（最多等 1 秒、最多读 1 MiB），输出两行：第一行
    为上下文 token 数或空，第二行为位置行或空。任何异常都输出两行空行、退出 0。
- `module_stage.describe(root, context_tokens=None)`：新增可选参数；按第 1、9、10 条追加行。`context_tokens is None` 时
  只可能出现"模块完成"一行。命令行入口新增可选参数 `--context-tokens N`。`verify-artifacts`、`module-insert` 调用不变。
- `phase-guard.sh`：激活后调用一次 `session_context.py`（标准输入是终端时不转交标准输入），得到上下文大小与位置行；
  上下文大小传给 `module_stage.py --context-tokens`，位置行插在所有阶段输出（含 `IDLE`、`MAP_ONLY`、`UNKNOWN`）的标题与
  `当前阶段` 之间。任何一步失败都按"拿不到"处理，阶段输出照常注入。手工运行或调用方没有关闭标准输入时，hook 不能挂住。
- 输出仍是宿主接受的 JSON；不使用 `cmd | grep -q`。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_session_context.py
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先写测试并确认它在当前代码上失败，再改实现。
- `test_session_context.py`（构造的会话记录，不读本机真实记录）：
  - Claude 记录：取最后一条带用量的 assistant 消息，三项相加；最后几行是 user 或无用量的行时向前找；
    末尾是 `isSidechain: true` 的 assistant 消息时跳过它、取更早的主会话消息；
  - Codex 记录：取最后一条 `token_count` 的 `last_token_usage.input_tokens`；`info` 为 null 的事件跳过；
  - 末尾 4 MiB 内没有用量记录、坏行、空文件、文件不存在、路径为空 → `None`；
  - hook 输入：正常、非 JSON、缺字段、`null`、非字符串 → 对应结果；
  - 位置行：普通分支、分离 HEAD、linked worktree（报告该 worktree 自己的根目录）、非 git 目录 → `None`、含控制字符的
    分支名被清洗。
- `test-phase-guard.sh`：通过标准输入喂 hook 输入：
  - `MODULE_DONE` / `DONE` → 有"模块完成"一行；`BUILDING` 且上下文 25 万 → 只有上下文一行；`DONE` 且 25 万 → 两行，
    顺序固定；`BUILDING` 且 15 万 → 输出与现在逐字相同；
  - 没有标准输入（终端）、输入不是 JSON、记录不存在 → 只按阶段决定是否出现"模块完成"一行，其余逐字不变；
  - 标准输入是一直不关闭的管道 → 约 1 秒内照常输出，不挂住；
  - `IDLE`、`MAP_ONLY` → 不加第 9 条的两行，但有位置行；
  - 位置行出现在标题与 `当前阶段` 之间；git 仓库里的各阶段都有，非 git 目录（夹具不 `git init`）没有，其余逐字不变；
  - 只读：运行前后项目文件与会话记录文件的修改时间不变。
- 已有的 phase-guard、verify-artifacts、module-insert 测试全部通过；两种 Python 下最小验证通过。
- Checkpoint：用安装版在真实 Claude Code 与真实 Codex 会话各跑一次，记录实际注入的行；Codex 若 `transcript_path` 为空，
  如实记为"Codex 只有模块完成一条"。

## Boundaries

- Always：先红后绿；hook 只读；读不到就不提示；只读用量数字，不把会话内容带进输出。
- Ask first：开放阈值配置；记录"已提醒过"等任何写文件的状态；改变阶段判定。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号；在输出中带出会话原文。

## Success criteria

- 模块完成时，阶段提示建议在新会话里开始下一个模块。
- 主会话上下文超过 20 万 token 时，阶段提示给出大小并建议在 task 边界开新会话；Claude Code 上实测生效，Codex 上的实际
  情况有记录。
- 每个阶段都给出当前分支与 worktree，并要求 agent 在请求评审或确认时转告用户。
- 其余输出逐字不变；阶段判定、`verify-artifacts` 与 `module-insert` 不受影响。

## Open questions

- 无（第 7–10 条为依据实测的补充，随本 Spec 评审）。
