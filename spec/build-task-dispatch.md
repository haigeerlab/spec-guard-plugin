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

- 新增 `templates/claude-dispatch-rule.md` 与 `templates/codex-dispatch-rule.md`。两份第一行都是
  `<!-- spec-guard: build-task-dispatch -->`，其后是规则正文，正文为 2–4 个列表项，覆盖：
  - 何时派：`/build` 执行 `todo.md` 中非 Checkpoint 的 task；
  - 派给谁、做什么：一个 task 一个子代理，只做 RED → GREEN → 全量回归 → 构建，不提交、不勾选；
  - prompt 必含：task 原文、模块 spec 路径、独占一行的 tier-guard 标记（规则同 Assumption 5）；
  - 停止条件原样交回；验收 diff、只暂存该 task 的文件、提交、勾选、问人由主代理完成；
  - 上一个 task 提交、勾选完再派下一个；提交受阻时先解决提交或停下问人，不派下一个；
  - 三档的一句话定义（L1 机械、只读；L2 单模块内、验收明确的实现；L3 跨模块、有歧义、高风险或不可逆），
    有 `tier-routing` 时以它为准——没装 tier-guard 时没有这个 skill，标记取值仍要有统一依据。
- Codex 段把「Agent 工具」写成 `spawn_agent`，并加一句「tier-guard 在 Codex 上只作建议」。
- 现有 `claude-block-local.md`、`codex-block-local.md` 不改。
- 规则段不用 `*-block-*.md` 命名：`test_workflow_checkpoints.py` 要求每份完整约定块模板都带检查点规则，
  规则段只是追加在基础块之后的片段，基础块已带该规则，不该落入那条守卫的范围。

### C2 `setup-convention.sh`

- 新增互斥参数 `--dispatch`、`--no-dispatch`；同时给出时以退出码 2 拒绝，不改任何文件。
- 期望状态：显式参数优先；否则已有块中存在标记行即为开，其余为关。
- 写入内容 = 基础模板，开启时其后紧接规则段模板；仍由 `BEGIN`/`END` 包裹。新建块与 `--replace` 都按此组装。
- 已有块且未给 `--replace` 时行为不变（跳过并提示用 `--replace`），即使给了 `--dispatch` / `--no-dispatch`；提示里
  说明开关需配合 `--replace` 生效。
- 预览（`--dry-run`）在原有行之外多一行，写明规则段状态及来源：
  `build-task-dispatch rule: on (--dispatch)` / `on (kept from existing block)` / `off (--no-dispatch)` / `off`。
  状态行只在块会被写入（新建或 `--replace`）时出现；块被跳过时不打印，以免让人以为开关已生效。
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
plugins/spec-guard/templates/claude-dispatch-rule.md, codex-dispatch-rule.md  -> C1
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
  `/build auto`，达到其验收标准：
  1. 每个非 Checkpoint task 恰一次 Agent 派活；
  2. tier-guard 日志每次派活都有记录、`upstream_tier.status = accepted`，且请求的模型与标记档位对应
     （L1→haiku / L2→sonnet / L3→opus），`tier_conflict` 若出现须由 floor 解释（2026-10-05 修订，见下）；
  3. 实际执行的模型与档位对应；
  4. 每个 task 一次由主代理完成的提交，且上一个 task 提交后才派下一个，测试全过；
  5. 不装 tier-guard 时流程照常走完。
  该项由对方会话执行并回报，结果记入本 spec。

## 验收记录

### 第一轮（2026-10-05，`b200f39`）

tier-guard 会话以 `git archive b200f39 plugins/spec-guard` 只读导出插件，两个相同的 textkit 消费者项目以
`setup-convention.sh local --dispatch` 安装约定块；`claude -p --setting-sources project,local --model sonnet`，
A 加载 agent-skills 0.6.11 + 本分支 + tier-guard 0.2.4，B 不装 tier-guard；`/build auto` 后 `approve`。判据取自
transcript、tier-guard 日志、git 历史与测试结果，不采信主代理自述。以下为对方报告，本会话未亲自读取其日志。

1. 通过：A、B 各 2 次派活（Task 1、Task 2 各一次）。
2. 按原字面不通过：A 两条记录 `upstream_tier = {status: accepted, tier: L2}`、无 `tier_conflict`、`recommended = sonnet`，
   但 `tier_source = pin`——主代理同时遵守 tier-routing 显式传了 `model: sonnet`，按 pin > floor > tier 记为 pin。
   原标准没预见到这一点：guard 模式会拦首次未 pin 的派活，pin 几乎必然发生。用户 2026-10-05 决定按上面的
   修订标准判定，修订后通过。
3. 通过：标记 L2、请求 sonnet，`actual_execution = claude-sonnet-5-5`（2/2）。
4. 通过但有插曲：3 个提交（两个 task + checkpoint），子代理未执行任何 git 命令，8 个测试全过。主代理把「提交
   Task 1」与「派 Task 2」放在同一轮，提交被测试环境的权限白名单拦下，Task 2 的改动混入工作区后由主代理拆开。
5. 通过：B 无 tier-guard 日志，流程走完。另见：B 两次标 L1、A 标 L2——没装 tier-guard 就没有 tier-routing，
   档位无统一依据。

据此修订（用户 2026-10-05 确认）：规则段补「上一个 task 提交、勾选完再派下一个」与三档一句话定义；
标准第 2 条按上文修订；只复验第 4 条（顺带看 B 的档位是否按定义标注）。

### 第二轮：只复验第 4 条（2026-10-05，`10717c8`）

方法同第一轮，权限白名单未改（复合命令里的 `sed -i` 需审批、非交互下直接失败），以复现「提交受阻」。
以下为对方报告，按 transcript 工具调用先后判定。

- B（无 tier-guard）通过：Task 1 提交被拦后改用 Edit 勾选、提交，再派 Task 2；中途按 `/build` 停止条件就 spec
  未定义的 slugify 字符集停下问人。两个 task 均标 L2（第一轮为 L1），内联三档定义生效。
- A（有 tier-guard）不通过：09:52:32 提交 Task 1 被拦，09:52:35 即派出 Task 2，09:52:40 自行 TaskStop，
  随后勾选、提交 Task 1，09:52:57 重新派 Task 2。最终 3 个提交正确、8 个测试全过，被停的子代理没有留下改动；
  但 Task 2 有 2 次派活，第 1 条在这一轮也按字面不满足。档位 L2、`tier_source = pin`、实际 sonnet，与第一轮相同。

据此修订（用户 2026-10-05 确认）：规则段补「提交受阻时先解决提交或停下问人，不派下一个」，以同一白名单再复验
一次。若仍出现，作为已知限制记入本 spec 并接受，不加 hook 强制（Assumption 1）。

### 第三轮：再复验第 4 条（2026-10-05，`ac85154`）

方法与白名单同第二轮。以下为对方报告，按 transcript 工具调用先后判定。

- A 通过：10:05:00 提交被拦，下一次调用是 10:05:04 Edit 勾选 Task 1，随后 git add、git commit，10:05:14 才派
  Task 2；全程没有提交前派活，也没有 TaskStop。每个 task 各派 1 次。
- B 第一次运行**没测到**该场景：子代理跑测试时 Bash 被整体拒绝，子代理按停止条件交回，主代理停下问人——行为符合
  规则，但在提交之前就停了，不计为第 4 条通过。
- B 用全新项目重跑通过：10:07:41 提交被拦，10:07:44 Edit 勾选，提交后 10:07:56 才派 Task 2；每个 task 各派 1 次。
  其总结自述「Blockers: None」与 transcript 不符，判定只取 transcript。
- A：`upstream=accepted/L2`、`requested=sonnet`、`tier_source=pin`、无冲突、实际 `claude-sonnet-5-5`（2/2）。A 与 B 重跑
  均 3 个提交、8 个测试全过；两边都标 L2。第 3、5 条无变化。

结论：按修订后的五条标准，本轮全部满足。每个场景只有一个样本，不证明以后不会再犯；规则仍只是引导（Assumption 1），
「提交受阻时先派下一个」若再出现，按用户 2026-10-05 的决定作为已知限制接受，不加 hook。

### Codex 宿主（2026-10-05，已发布 v0.44.0）

本会话在本机 codex-cli 0.160.0（`features.multi_agent = true`，装有 agent-skills 0.6.12、spec-guard 0.44.0、
tier-guard 0.2.4）上实跑。消费者项目由**安装副本**的 `setup-convention.sh local --host=codex --dispatch` 写入
AGENTS.md；种子为 textkit 的两个 task 加 Checkpoint；提示只有「按 AGENTS.md 的约定实现 todo 中的全部任务，计划已获批准」。
`codex exec --json … </dev/null`；A 保持 tier-guard 启用，B 以 `-c 'plugins."tier-guard@tier-guard".enabled=false'`
仅对该次运行停用。判定取自主会话与子代理的 rollout、git 历史和重新运行的测试，不采信代理自述。

| # | A（tier-guard 启用） | B（停用） |
|---|---|---|
| 1 | 通过：`spawn_agent` slugify、word_count 各 1 次 | 通过：各 1 次 |
| 2 | 无法核验（见下） | 无法核验 |
| 4 | 通过：10:33:02 提交 Task 1，10:33:24 才派 Task 2 | 通过：10:38:54 提交 Task 1，10:39:11 才派 Task 2 |
| 5 | — | 通过：流程走完 |

两组：子代理没有执行任何 git 提交；3 个提交各只含该 task 的文件；8 个测试全过；todo 全部勾选。第三个子代理是
宿主配置的 guardian 审批代理（审批提交的提权），不是派活。

**已知限制（用户 2026-10-05 决定接受）**：Codex 把派活正文加密——主会话的 `spawn_agent.message` 与子代理收到的
`agent_message` 都只有 `encrypted_content`——所以从宿主记录无法核验标记是否写进 prompt；子代理记录中的 `tier=L`
全部来自它读到的 AGENTS.md 规则原文。Codex 上也没有消费者读这个标记（tier-guard 在 Codex 上只拿到不透明令牌，
规则段已写明只作建议）。因此第 2 条只对 Claude Code 判定；Codex 以第 1、4、5 条判定，本次通过。Codex 规则段里的
标记要求保留不改，两侧对称，日后 Codex 公开正文即可核验。`spawn_agent` 的明文参数里两组都显式传了
`model: gpt-6.1-sol`、`reasoning_effort: medium`，但那就是主代理的默认值，不作为按档位路由的证据。

另见：Codex 默认 workspace-write 沙箱不允许写 `.git`，主代理的 `git add` / `git commit` 都以 `require_escalated`
申请提权；本机由 guardian 自动审批，普通用户会看到审批提示，性质与 Claude Code 的权限提示相同。

## 修订：交接内容、不派条件与实验性（2026-10-05，用户决定）

对照 agent-skills 0.6.11 原文（`.claude/commands/build.md`、`skills/planning-and-task-breakdown/SKILL.md`、
`references/orchestration-patterns.md`；Codex 侧 0.6.12 这三份逐字相同）复核插口位置后：

- **插口位置不变**：`/build` 每个 task 循环的第 2–6 步（加载上下文 → RED → GREEN → 回归 → 构建）。拆任务与计划审批
  不接子代理（orchestration-patterns 的 Anti-pattern C）；第 6 步的停止条件与 Checkpoint 留在主代理。
- **交接内容**：原规则只交「task 原文」，而 spec-guard 约定下 todo 常只有一行，验收标准、验证、依赖、涉及文件在
  plan.md 的任务块里。改为交完整任务块、plan.md 的 Architecture Decisions 与模块 spec 路径。
- **不派条件**：任务块缺验收标准或验证步骤；属于停止条件（spec 未覆盖的决策、高风险或不可逆）；L3；为子代理选的
  模型不比主会话便宜。
- **实验性**：tier-guard 会话以 textkit 验收运行算总账（主会话加全部子代理，按 message.id 去重，父子都是 sonnet）：
  不派 $0.233，派 $0.50–0.70，贵 2.1–3.0 倍——父子同模型没有差价，主代理仍要读 diff、验收、提交，子代理另付一次
  上下文启动费。「子代理模型更便宜」只是省钱的必要条件，不是充分条件；可能省钱的主要场景是主会话上下文很大。
  在对照数据证明省钱之前，`--dispatch` 标为实验性；「上下文多大才派」的阈值由 tier-guard 的对照实验给出后再补。

### 再修订：默认不派（2026-10-05，用户决定）

tier-guard 会话的两份对照实验（tier-guard 提交 5282010）：

- `docs/research/2026-10-05-dispatch-cost-experiment.md`：opus 父代理、sonnet 子代理，textkit 两个 task，主会话上下文
  小（约 2.5 万 token）与大（约 12 万，追加系统提示模拟）各跑 2 次，8 次全部通过。不派 $0.321 / $1.076，派
  $0.523 / $1.284，分别贵 63% 与 19%。原因：派活没有减少主会话的轮次（两组都是 11–16 条消息），主代理仍要派活、
  读 diff、跑测试、提交、勾选；子代理每个约 $0.10 全是额外开销。推算一个 task 要让主会话少跑约 4–5 轮（12 万上下文）
  或约 2 轮（26 万上下文）才能回本——此项为推算，未实测。
- `docs/research/2026-10-05-codex-l2-luna-experiment.md`：Codex 10 个 L2 任务，luna/high 与 sol/medium 都是 10/10，
  luna 每任务成本约 1/14；tier-guard 将把 Codex L2 改为 luna/high（0.2.5）。

agent-skills 的 `/plan` 本就要求把 task 拆成规格明确的 S/M，这正是派出去最不划算的一类。据此规则改为：**默认由主代理
自己做**；只有预计需要大量探索或调试的 task（要先读懂大量现有代码、跨多个文件反复修改）才考虑派；原有不派条件保留，
并写明只是必要条件。`--dispatch` 继续标为实验性；回本条件由联调中的「大 task」模块实测（模块由 spec-guard 设计），
实测前不转正。

