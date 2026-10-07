# 使用流程

这一页讲三件事：新项目怎么从零开始、项目做到一半来了新需求怎么加进能力图、能力图有哪些规则。
名词解释见[设计理念与术语](concepts.md)。

## 新项目：从零到交付

新项目**不写 Proposal**。Proposal 需要引用远端 main 上已有的能力图，新项目还没有能力图，直接按下面的步骤走。

1. **安装约定。** Claude Code 里运行 `/spec-guard:setup-convention`；Codex 里说「用 spec-guard 在这个项目安装约定」，
   由 `spec-guard-ops` skill 执行。都会先预览，你确认后才写文件。写入的是：

   ```text
   CLAUDE.md 或 AGENTS.md 里的约定块   # 告诉 agent 多模块的目录规则
   spec/CAPABILITY-MAP.md               # 能力图模板
   .agent/state.json                    # 只记录当前模块：{"activeModule":""}
   ```

2. **写能力图并评审。** 用 agent-skills 的 `/spec` 做 Phase 0：列出模块、职责、依赖和一行 Build order。
   人工确认模块边界清楚、依赖单向无环，再往下走。
3. **按 Build order 逐个模块推进。** 每个模块依次是：
   - 写 `spec/<模块>.md` 并评审；
   - 用 `/plan` 生成 `tasks/<模块>/plan.md` 和 `todo.md`；
   - 用 `/build` 逐项实现，每完成一项勾掉一项。
4. **切到下一个模块。** 当前模块的 todo 全部勾完后，把 `.agent/state.json` 的 `activeModule` 改成下一个模块。

整个过程中不用自己记进度，每轮对话开头 hook 都会告诉 agent 现在到了哪一步。

**可选（实验性）：把 task 交给子代理执行。** agent-skills 的 `/build` 默认在主会话里直接实现每个 task。安装约定时加
`--dispatch`，约定块会多一段规则：非 Checkpoint 的 task 交给一个子代理做 RED → GREEN → 回归 → 构建，
派活 prompt 带一行 tier-guard 档位标记，验收 diff、提交、勾选和问人仍由主代理完成。装了
[tier-guard](https://github.com/haigeerlab/tier-guard) 时它据此为子代理选模型；没装时标记只是一行注释。
任务块不完整、属于停止条件、L3、或为子代理选的模型不比主会话便宜时，主代理自己做。这条规则只是引导，spec-guard
不检测是否照做。省钱效果尚未证明：对照实验里派活没有减少主会话轮次，比不派贵 15%–54%，因此规则默认由主代理自己做，
只派预计要改动 3 个以上文件、验收明确的 task。默认关闭；已开启的项目 `--replace` 升级时保持开启，
关闭用 `--replace --no-dispatch`。Codex 上同样可用；Codex 默认的 workspace-write 沙箱不允许写 `.git`，主代理每次提交都会申请提权，需要你审批。派活正文在 Codex 上是加密的，档位标记无法从记录中核对，
也没有程序读取，只作建议。

**怎么看省没省钱。** `/spec-guard:cost-report <模块>`（Codex 里让 `spec-guard-ops` 跑 cost report）离线读取本机的
Claude transcript 与 Codex rollout，按 task 列出主代理与子代理的 token、主会话轮次、派活次数与返工信号；加
`--prices <价格文件>` 折算成等价金额（订阅账号省的是额度，金额只是统一的尺子）。派活省不省钱主要看它让主会话少跑了
几轮，报告里的「主会话轮次」就是为此列出的。多个模块一起报告时附「有派活 / 没派活」的对照，只能看趋势。

若项目已明确采用可用的 Local 事项账本，并决定实施一个可追踪需求或修复，
先用 `ticket` 入口查重并取得事项 ID，再开始编码；Spec 和 Plan 可随后细化。
探索、讨论与无需追踪的小操作不强制建事项。Local 完成时把代码引用和验证结果
写回事项，经明确授权关闭后读回状态；本地不要求 PR/MR。
若实际通过 GitHub PR 交付，创建 PR 后将地址和本 PR 的覆盖范围记入已绑定的 Local 事项。
PR 合并后核对合并提交与验证结果并写回；只有事项全部范围已交付、验证通过且已有关闭授权
才关闭并读回。PR 未合并、只交付部分范围或仍待验收时保持开放；GitHub 合并事件不会自动
修改这台 Mac 上的 Local 账本，下一次可用的交付检查点须完成待办对账。

**少停、该停的照停。** Plan 里的检查点标 `gate`（停下等你确认）或 `report`（把验证结果记进 todo 后直接继续），
未标注的按 `gate`；测试改不红、Spec 没覆盖的决策、高风险不可逆改动、权限被拒时任何级别都停。推送、开 PR 只有 Plan 的
`gate` 检查点写明授权时才免问，合并始终由你来做。一个需求拆成几个模块时，可以一次审完它们的 Spec 与 Plan，之后按
Build order 连续构建；涉及 UI 的检查点由 agent 先用浏览器或电脑操作自验，你做最后兜底（Claude 桌面应用自身的显示只能由你看）。
细则见[共享检查点规则](../plugins/spec-guard/references/workflow-checkpoints.md)。

### 项目级审查后处理缺陷

一轮项目级审查先固定基准提交、模块或路径范围、排除项和预计检查的批次。复用 agent-skills 的
`code-review-and-quality` 检查正确性、可读性、架构、安全和性能；它原本主要用于变更和 PR 评审，
项目级审查需额外限定覆盖范围。每个范围系统检查一次，对候选缺陷做定向核实；证据不够的标为
“待调查”并写出缺少什么，不为追求“找完所有 bug”无限扩大范围。P0 风险立即报告并暂停扩大扫描。
已经安装旧版项目约定块的项目，先预览 `setup-convention local --replace`，确认后更新声明块；
安装插件新版本本身不会改写现有的 `CLAUDE.md` 或 `AGENTS.md`。

多轮审查保留带基准、覆盖进度、稳定发现编号、证据、状态、P0/P1/P2 优先级和下一停点的报告。
审查意见的 Critical/Required/Optional 与处理优先级分别记录，不能自动换算。范围覆盖且发现均已
分类时宣布**审查完成**；这不等于事项已入账、缺陷已修复或变更可合并。此后的“继续”按最近一次
预告进入查重、事项交接、规划或下一项修复，显示剩余数量；新证据或用户明确扩大范围才另开审查批次。

已选用且可用的 Local 账本走 `ticket` 查重和读回；GitHub 上托管代码不改变 Local 事项目标。
未启用 Local、账本归属未知或结果未知时，报告“待入账”而不重复创建。明确选用 GitHub/GitLab
普通 Issue 时，按 `hosted-ticket-workflow` 用完整分页和稳定标记查询；`absent` 的
`rootCauseReviewRequired` 仍须人工核对同根因异名事项。展示精确目标、可见性和脱敏内容，
取得该次授权后才创建，读回 ID/URL 才算入账；结果未知不自动重发。Proposal Issue
不能充当缺陷事项，旧远端 bridge 不恢复。
仅要求审查的用户收到报告，不自动建单或修改代码。

修复现有行为时，简单 bug 用 agent-skills 的 `debugging-and-error-recovery` 与 TDD 先复现再修复、验证和复审；
多步骤修复才在相关模块 plan 与 `todo.md` 中切片，不覆盖进行中的任务，也不为每个 bug 新建能力模块。
发现的是独立新能力时才按本页的快速插入或 Proposal 流程处理。通过 GitHub PR 交付 Local 事项时，
仍按上一节的 PR 创建、合并和关闭对账条件收尾。

托管日常事项在 Issue 中记录修复和验证；PR/MR 合并后按事项逐项读回合并提交、
CI／验收与剩余范围。只有全部交付并验证通过且获关闭授权才关闭并读回；平台
自动关闭、部分合并或待部署均不能当作已完成。关闭命令的 `verified` 只证明远端
Issue 已关闭并读回，不代替对 CI／验收证据的实际核对。后续批次改选目标不迁移已有事项。

### 阶段提示

| 阶段 | 意思 | 下一步 |
|---|---|---|
| `IDLE` | 还没有能力图 | 写能力图并人工评审 |
| `MAP_INVALID` | 能力图格式不对，比如 Build order 不是恰好一行 | 用 `/spec-guard:verify-artifacts` 查原因 |
| `MAP_ONLY` | 有能力图，还没有任何模块 Spec | 写第一个模块的 Spec |
| `NEEDS_SPEC` | 当前模块缺 Spec | 写 `spec/<模块>.md` |
| `NEEDS_PLAN` | 当前模块有 Spec、缺 Plan | 用 `/plan` 生成 plan 和 todo |
| `BUILDING` | todo 还有 N 项没勾 | 继续 `/build` |
| `MODULE_DONE` | `activeModule` 指向的模块已完成，但还有别的模块没做完 | 把 `activeModule` 改成提示里点名的下一个模块；有被暂停的模块时点名它 |
| `DONE` | 全部模块都已完成 | 新需求用 `/spec-guard:add-module` 插入；`activeModule` 还指着已完成模块时可以清掉 |
| `UNKNOWN` | 阶段算不出来 | 用 `/spec-guard:verify-artifacts` 查原因 |

有 Plan 但没有 `todo.md` 的模块按已完成计（历史上已交付的模块常是这种写法，所以判据不变）。DONE 汇总会显示这类模块的数量，可用 `/spec-guard:verify-artifacts` 查看具体模块。插队或新加的模块如果只有 Plan、没有 `todo.md`，会被读成已完成；把 `activeModule` 指向它时阶段提示会多一行提醒，补上 `tasks/<模块>/todo.md` 列出剩余任务即可。已交付、有意不建 todo 的模块，可在 `plan.md` 里加独占一行的 `<!-- spec-guard: no-todo -->` 声明，阶段提示与 `verify-artifacts` 就不再提它。

阶段**不是存起来的状态，而是每轮实时算出来的**：模块清单与顺序取自 `spec/CAPABILITY-MAP.md`，每个模块处在
哪一步只看 `spec/<模块>.md`、`tasks/<模块>/plan.md`、`tasks/<模块>/todo.md` 是否存在以及 todo 里还有几个
未勾选项。`.agent/state.json` 只存一样东西——`activeModule`，也就是当前焦点这个书签。所以它丢了也算得出阶段，
只是会退化为「按 Build order 取第一个没完成的模块」。

hook 是否出声由两个激活信号决定，有其一即可：`CLAUDE.md`／`AGENTS.md` 里独占一行的声明块，或含
`activeModule` 的 `.agent/state.json`。两者都没有时完全静默。

当前模块取 `.agent/state.json` 的 `activeModule`，没设置时按 Build order 取第一个没完成的模块。
它必须是 kebab-case 的 module id；写成别的会被报为无效并回退到 Build order（hook 仍然激活）。
注入文本里来自仓库的值都经过净化，详见[决策记录](decisions/2026-10-04-phase-context-sanitization.md)。
随时想看完整状态，用 `/spec-guard:phase`。开新会话前用 `/spec-guard:handoff`（Codex 里输入 `spec-guard handoff`）
拿一份可直接粘贴的交接文本；整条提示词恰好是这条命令时由 hook 本地作答，不调用模型。
存在被暂停的模块（见「插队」）时，`NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MODULE_DONE` 下会多一行 `Paused: …`。

## 已有项目：加新需求

项目做到一半冒出新需求时，有两种方式把它作为新模块加进能力图：

| 方式 | 适合 | 步骤 |
|---|---|---|
| **快速插入**（默认） | 个人或小团队，需求已经理顺 | 一次预览、一次确认 |
| **Proposal** | 需要在 Issue 上留下评审与接受的记录，或需要多人确认 | 四步（提交、接受、晋级、收尾），要先做一次性准备 |

两种方式都只**新增**模块。修改、删除或调整已有模块的顺序，直接改能力图并人工评审。

### 快速插入

在一个模块做完、还没开始的检查点（或显式插队，见下一节），把理顺的需求上下文交给 agent，运行 `/spec-guard:add-module`
（Codex 里说「用 spec-guard 插入一个新模块」）：

如果这项工作已选择 Local 账本，先按上面的受理规则取得或沿用事项 ID。
`add-module` 只管理能力图，不创建事项。

1. agent 读能力图，提出新模块的 id、职责、依赖和插入位置（`after:<某模块>` 或 `end`），每项说明理由；
2. 命令预览：给出新行、新 Build order、能力图改动对比，以及插入后当前模块会不会变；
3. 你确认后才写入。只改 `spec/CAPABILITY-MAP.md`，不建文件、不动 `tasks/` 和 `.agent/state.json`，也不做 Git 操作；
4. 新模块排到当前位置时，阶段变为 `NEEDS_SPEC`，接着照常写并评审它的 Spec，再 Plan、Build。

命令会先校验，任何一条不满足就拒绝，什么都不写：

- 当前模块做到一半（todo 里既有已勾、又有未勾的项）——唯一的例外是显式加 `--interrupt` 插队，见下一节；
- 依赖不存在、依赖排在插入位置之后、出现循环依赖，或 id 重复、不是 kebab-case；
- 插入会改动 `## 目标`、已有模块行，或已有模块在 Build order 中的先后。

若 `spec/<id>.md` 已存在，预览会提示插入后为 `NEEDS_PLAN`；先确认这份 Spec 已评审，再确认写入。

### 插队

当前模块做到一半、剩下的都要等外部条件（比如部署满七天后的复核），而新需求需要先做时，可以显式插队：

```text
/spec-guard:add-module … --interrupt
```

Codex 里用 `spec-guard-ops` 的 `add-module`，带同样的 `--interrupt` 参数。

- 预览会写明被暂停的模块及进度（`已勾 X/Y`），以及插入后的当前模块。新模块不会成为当前模块时
  （锚点在被暂停模块之后，或 `activeModule` 仍指向它），预览提示把 `.agent/state.json` 的 `activeModule` 改为新模块；
  命令本身仍只写 `spec/CAPABILITY-MAP.md`；
- 插入后，每轮阶段行都带 `Paused: …`，提醒被暂停的模块还没做完；
- 插队模块做完后，`MODULE_DONE` 会提示回到被暂停的模块，把 `activeModule` 改回它即可；
- 其他模块同时做到一半（并行推进）不影响插队；它们都会出现在 `Paused` 行里，插队模块做完后按 Build order 回到第一个被暂停的模块；
- 不带 `--interrupt` 时行为不变，当前模块做到一半仍然拒绝；当前模块没有做到一半时，`--interrupt` 不改变任何行为。

Proposal 路径同样适用。
晋级合并后，如果新模块没有成为当前模块，把 `activeModule` 改为它。

### Proposal（需要留痕时）

```text
提交（写草稿 → proposal-submit → 合进 main → 开 Issue）→ 接受（评审 → 改标签）
     → 晋级（add-module --proposal 插进能力图 → 合并）→ 收尾（证明 → 预览 → 授权 → 改阶段并关闭）
```

| # | 步骤 | 谁来做 | 怎么做 |
|---|---|---|---|
| 1 | 提交 | agent + 命令 + 人 | agent 按[模板](../plugins/spec-guard/references/proposal-contract.md)写草稿 `spec/proposals/<id>.md`；运行 `/spec-guard:proposal-submit --draft spec/proposals/<id>.md --platform <github\|gitlab>` 预览，确认后加 `--confirm`，命令从远端 main 补全基线一节并算出 revision，只改这一份草稿；经 PR 把草稿合进 main（发布，只在本地或分支上都不算）；再用命令打印的现成命令开 Issue（标签 `proposal`、`proposal-stage:published`）。改了草稿，重跑一遍即可重算 revision |
| 2 | 接受 | 命令 + 人 | `/spec-guard:proposal-review` 报告 Proposal 是否新鲜、过期或被卡住；人把 Issue 标签改成 `proposal-stage:accepted`。接受只看这个标签加一次新鲜评审（基线未漂移、模块还不在能力图里、依赖齐全、锚点有效） |
| 3 | 晋级 | 人 + 命令 | 从预检给出的 `baseCommit` 开晋级分支，运行 `/spec-guard:add-module --proposal <id> --platform … --target …`（Codex 同等入口），预览确认后加 `--confirm` 写入能力图，提交并合并。命令已内嵌预检，通常无需单独再跑 `/spec-guard:proposal-promotion-preflight`。若正式 Spec 与 Plan 已可评审，可与能力图放在同一个晋级 PR；否则先合入能力图，随后按正常流程补齐。命令会自检写入结果能通过收尾的证明 |
| 4 | 收尾 | 命令 + 人 | `/spec-guard:proposal-promotion-proof`：从 Proposal 的基线提交起沿远端默认分支找到第一个纳入该模块的提交，核对它与声明一致。证明为 `proved` 后用 `/spec-guard:proposal-closeout` 预览收尾，确认后它写一条带稳定标记的收尾记录、把阶段改成 `proposal-stage:promoted` 并关闭事项，再读回这三项。只手工改标签不会关闭事项，事项会一直开着；`/spec-guard:proposal-closeout` 的只读 `scan` 列出所有证明已通过而事项仍开着的 Proposal |

晋级后，这个模块仍按 Spec → Plan → Build 的评审顺序推进；同一个晋级 PR 可以提交 Spec 与 Plan 并分别评审，不要求为每份文档再开 PR。`proposal-submit` 只在 `--confirm` 时写草稿；评审、预检、证明只读；晋级命令只写能力图；Issue、标签、分支与提交由人操作。合并后运行证明并报告结果，再用 `proposal-closeout` 预览并经授权收尾（它把 Issue 标为 `promoted` 并关闭）；证明与收尾都不需要第三个 PR。

### Proposal 文档怎么写

由 agent 按[格式规范与草稿模板](../plugins/spec-guard/references/proposal-contract.md)写草稿。需要自己写的是：

- **Summary**：要解决什么问题，为什么它是一个独立模块；
- **Integration intent**：问题、范围内、范围外、安全边界、依赖假设、验收意图；
- **Change**：新模块的 id、职责、依赖，以及插入位置 `after:<某模块>` 或 `end`；
- **Tracker contract**：对应 Issue 的约定。

**Capability map baseline**（写作时远端 main 上能力图的版本和各模块的摘要）与首行标记里的 revision 由
`proposal-submit` 填写，不要手算；草稿里可以省略基线一节，revision 先写 64 个 `0`。

可以参考本仓库的实例 [`spec/proposals/local-ticket-ledger.md`](../spec/proposals/local-ticket-ledger.md)。

### 用 Proposal 之前的一次性准备

- 装好并登录 GitHub CLI（`gh`），GitLab 项目则是 `glab`。命令只读 Issue，不写。
- 远端默认分支上的能力图需要有 `## 目标` 一节。

## 能力图的规则

- **每个项目只有一张在用的能力图**，路径固定为 `spec/CAPABILITY-MAP.md`。阶段提示和产物校验都只认这一张。
- **新需求插进同一张图**：用快速插入或 Proposal，按锚点插到某个模块后面或追加到末尾，不再为新需求另开一张图。
- **和当前项目无关的独立产品**，另开一个项目，用它自己的能力图。
- **改 `## 目标` 要慎重**：这一节的摘要是 Proposal 评审的基准，改了会让所有已发布的 Proposal 判为过期。
  只是追加模块时不用改它。
- **旧版本留下的归档图**在 `spec/history/`，只读核验，见[可选能力](optional-features.md#能力历史)。

## 命令对照

Codex 不加载插件的斜杠命令，对应功能通过 skill 调用，用自然语言描述要做的事即可。

| 功能 | Claude Code | Codex |
|---|---|---|
| 安装或移除约定 | `/spec-guard:setup-convention`、`/spec-guard:teardown-convention` | `spec-guard-ops` skill 的 setup、teardown 一节 |
| 查看阶段、校验产物 | `/spec-guard:phase`、`/spec-guard:verify-artifacts` | `spec-guard-ops` skill |
| 查看或设置项目默认事项后端 | `/spec-guard:tracker-default` | `spec-guard-ops` skill 的 tracker default 一节 |
| 会话交接文本 | `/spec-guard:handoff` | 输入 `spec-guard handoff`，或 `spec-guard-ops` skill 的 handoff 一节 |
| 快速插入新模块 | `/spec-guard:add-module` | `spec-guard-ops` skill 的 add-module 一节 |
| Proposal 提交、评审、预检、证明、收尾（晋级用 `add-module --proposal`） | `/spec-guard:proposal-submit`、`proposal-review`、`proposal-promotion-preflight`、`proposal-promotion-proof`、`proposal-closeout` | `spec-guard-ops` skill 的 proposal 一节 |
| 文档治理 | `/spec-guard:documentation-*` 三条命令 | `spec-guard-ops` skill |
| 能力历史（含审计与 `correct` 补正） | `/spec-guard:history-integrity` | `spec-guard-ops` skill 的 history 一节 |
| 会话协作（已移到 agent-relay） | `/spec-guard:collaboration`（过渡期转交） | 安装 agent-relay 后用它的 skill |
| 本地事项 | `/spec-guard:local-ticket-ledger`、`/spec-guard:ticket` | `local-ticket-ledger-ops`、`ticket` skill |

## 移除

`/spec-guard:teardown-convention` 删掉 `CLAUDE.md` 里的约定块（标记之外不动），并把 `.agent/state.json` 改名为
`.agent/state.json.disabled`，阶段提示随之停止。能力图、Spec、Plan 都保留。先加 `--dry-run` 可以只看会改什么。
