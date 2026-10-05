# Spec: build-task-dispatch

## Objective

agent-skills 的 `/build`（含 `/build auto`）按设计在主会话里直接实现每个 task，从不调用 Agent 工具。
2026-10-05 tier-guard 会话在隔离环境实测：agent-skills 0.6.11 + spec-guard 0.42.0 + tier-guard 0.2.4 跑完整
`/build auto`，两个 task 完成、8 个测试通过，主代理 Agent 工具调用 0 次，tier-guard 日志为空；对照组明确要求
派子代理时 tier-guard 正常路由。也就是说，在 spec → plan → build 主干上，子代理模型路由没有入口。

agent-skills 是第三方插件，不能改。本模块在 spec-guard 写入项目的约定块里提供一段**可选**规则，引导主代理把
每个 task 的实现交给子代理，并在派活 prompt 里带上 tier-guard 的档位标记。规则默认关闭；不开的项目约定块逐字不变。

这是 spec-guard 职责的一次扩张：此前约定块只规定取哪个任务、模块怎么隔离，不规定怎么执行。用户已于 2026-10-05
明确批准这次扩张，并要求以默认关闭的开关落地。

登记：2026-10-05 按用户决定经 `/spec-guard:add-module` 插入能力图，依赖 `local-convention`。

## Assumptions

用户已于 2026-10-05 确认：

1. **只引导，不强制。** 只加约定文字，不加检测「该派没派」的 hook；效果由真实宿主重跑衡量。
2. **运行时零耦合。** spec-guard 不检测、不要求 tier-guard；没装时档位标记只是一行 HTML 注释。tier-guard 也不读
   spec-guard 的任何文件。
3. **分工照搬 `/build`。** `/build` 每个 task 的循环是 RED → GREEN → 全量回归 → 构建 → 提交 → 勾选
   （agent-skills 0.6.11 `.claude/commands/build.md` 第 35 行）。子代理做前四步，不提交、不勾选；主代理验收
   diff 后只暂存该 task 动过的文件加勾选，提交，再勾选。`/build auto` 第 6 步要求停下问人的情况
   （测试改不绿、spec 未覆盖的决策、高风险或不可逆操作），子代理原样交回，由主代理问人。
4. **除 Checkpoint 外每个 task 都派。** `/plan` 的任务模板只有 `Estimated scope: Small | Medium | Large`，没有可执行的
   XS 门槛；规划指南本就要求拆到 S/M。固定开销先接受，日后按实测数据再加门槛。
5. **档位当场判断。** 主代理派活时按 `tier-routing` 判断 L1/L2/L3，在 prompt 中独占一行写
   `<!-- tier-guard: tier=Lx -->`，重试时加 `failures=N`（由派活方当场填写）；todo 行若已带标记，原样带进 prompt。
   spec-guard 不在 todo、state 或 tracker 里存储档位或失败次数。格式以 tier-guard `spec/tier-guard.md`
   「上游档位信号」为准（tier-guard 仓库 6dd3161）。
6. **开关是 `setup-convention --dispatch`，默认关闭。** 不带开关时写入的约定块与现在逐字相同。
7. **开关状态存在块里。** 规则段以独占一行的 `<!-- spec-guard: build-task-dispatch -->` 开头。`--replace`
   时若现有块里有这一行（去掉首尾空白后恰好相等），升级后保持开启；关闭必须显式 `--no-dispatch`。
8. **Claude 与 Codex 两份模板都加。** Codex 段注明：tier-guard 在 Codex 上（包括交给 Codex worker 的派活）
   读不到标记，只作建议。
9. **`verify-artifacts` 不加校验。** 档位标记格式的只读校验另立模块。
10. **两层验收。** 本仓库用回归锁住模板内容与开关行为；真实宿主 `/build auto` 由 tier-guard 会话按其验收标准跑。

## Contract

### C1 规则段模板

- 新增 `templates/claude-block-dispatch.md` 与 `templates/codex-block-dispatch.md`。两份第一行都是
  `<!-- spec-guard: build-task-dispatch -->`，其后是规则正文，正文为 2–4 个列表项，覆盖：
  - 何时派：`/build` 执行 `todo.md` 中非 Checkpoint 的 task；
  - 派给谁、做什么：一个 task 一个子代理，只做 RED → GREEN → 全量回归 → 构建，不提交、不勾选；
  - prompt 必含：task 原文、模块 spec 路径、独占一行的 tier-guard 标记（规则同 Assumption 5）；
  - 停止条件原样交回；验收 diff、只暂存该 task 的文件、提交、勾选、问人由主代理完成。
- Codex 段把「Agent 工具」写成 `spawn_agent`，并加一句「tier-guard 在 Codex 上只作建议」。
- 现有 `claude-block-local.md`、`codex-block-local.md` 不改。

### C2 `setup-convention.sh`

- 新增互斥参数 `--dispatch`、`--no-dispatch`；同时给出时以退出码 2 拒绝，不改任何文件。
- 期望状态：显式参数优先；否则已有块中存在标记行即为开，其余为关。
- 写入内容 = 基础模板，开启时其后紧接规则段模板；仍由 `BEGIN`/`END` 包裹。新建块与 `--replace` 都按此组装。
- 已有块且未给 `--replace` 时行为不变（跳过并提示用 `--replace`），即使给了 `--dispatch` / `--no-dispatch`；提示里
  说明开关需配合 `--replace` 生效。
- 预览（`--dry-run`）在原有行之外多一行，写明规则段状态及来源：
  `build-task-dispatch rule: on (--dispatch)` / `on (kept from existing block)` / `off (--no-dispatch)` / `off`。
- 其他行为（目录、state.json、能力图模板、标记校验、`.disabled` 拒绝）逐字不变。
- `teardown-convention` 不改：它删除整块，规则段随块一起移除。

### C3 文档

- `commands/setup-convention.md`：参数说明、默认关闭、开关存在块里、关闭需 `--no-dispatch`。
- Codex 侧 `skills/spec-guard-ops/SKILL.md` 的 setup 路由同步参数（`scripts/check-command-parity.py` 须通过）。
- `docs/workflow.md`：一段说明这条可选规则与 tier-guard 的关系，并写明它只是引导。
- `CHANGELOG.md` 未发布节。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
```

## Project structure

```text
plugins/spec-guard/templates/claude-block-dispatch.md, codex-block-dispatch.md  -> C1
plugins/spec-guard/hooks/setup-convention.sh                                     -> C2
plugins/spec-guard/hooks/test-setup-teardown.sh                                  -> C1/C2 回归
plugins/spec-guard/commands/setup-convention.md, skills/spec-guard-ops/SKILL.md,
docs/workflow.md, CHANGELOG.md                                                   -> C3
```

## Testing strategy

先写测试并确认在当前代码上失败，再实现。`test-setup-teardown.sh` 新增（Claude 与 Codex 各一遍）：

- 默认（无开关）新建：块内容与基础模板逐字相同，不含标记行——锁住「老项目零影响」；
- `--dispatch` 新建：块内含标记行与规则段，且规则段位于基础模板之后、`END` 之前；
- 开启的块 `--replace`（不带开关）：仍含标记行（状态保留）；
- 开启的块 `--replace --no-dispatch`：不再含标记行，块与基础模板逐字相同；
- 关闭的块 `--replace --dispatch`：开启；
- `--dispatch --no-dispatch` 同时给出：退出 2，文件不变；
- 已有块、无 `--replace`、给 `--dispatch`：跳过，文件不变；
- 预览四种状态行各出现一次，且 `--dry-run` 不改文件；
- 正文里提到标记文字但不独占一行时不算开启；
- 两份规则段模板首行是标记，且包含 `tier-guard: tier=`、`failures=N`、Checkpoint、不提交 等关键约定（内容断言）；
- 已有全部用例保留。

两种 Python（默认 `python3` 与 `/usr/bin/python3` 3.9）与系统 `/bin/bash` 3.2 下通过。

## Boundaries

- Always：默认关闭时输出逐字不变；先红后绿；脚本只依赖 `bash`、`git`、`python3`。
- Ask first：默认开启；把规则写进基础模板；加入检测「该派没派」的 hook；在 todo / state 中存储档位或失败次数。
- Never：检测或要求安装 tier-guard；读取 tier-guard 的文件或日志；修改 agent-skills；让子代理提交。

## Success criteria

- 不带开关的新项目与 `--replace` 升级，约定块与当前版本逐字相同。
- 开启的项目在升级后仍是开启，只有 `--no-dispatch` 能关。
- tier-guard 会话用 `--plugin-dir` 指向本模块分支、在开启规则的消费者项目里重跑 textkit 两个 task 的
  `/build auto`，达到其验收标准：每个非 Checkpoint task 恰一次 Agent 派活；tier-guard 日志每次派活都有记录、
  `upstream_tier.status = accepted`、`tier_source` 为 `upstream` 或 `floor`；模型与档位对应；每个 task 一次由主代理完成的
  提交且测试全过；不装 tier-guard 时流程照常走完。该项由对方会话执行并回报，结果记入本 spec。
