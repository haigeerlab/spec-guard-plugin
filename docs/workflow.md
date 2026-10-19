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

2. **写能力图并审阅。** 用 agent-skills 的 `/spec` 做 Phase 0：列出模块、职责、依赖和一行 Build order。
   人工确认模块边界清楚、依赖单向无环，再往下走。
3. **按 Build order 逐个模块推进。** 每个模块依次是：
   - 写 `spec/<模块>.md` 并交审；
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
关闭用 `--replace --no-dispatch`。Codex 上同样可用；Codex 默认的 workspace-write 沙箱不允许写 `.git`，主代理每次提交都会申请提权，需要你批准。派活正文在 Codex 上是加密的，档位标记无法从记录中核对，
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
没标级别的中间检查点按 `report`、最后一个检查点（最终验收）按 `gate`，推送与不可逆操作须标 `gate`；测试改不红、Spec 没覆盖的决策（会影响以后的设计时顺带问是否记 ADR）、高风险不可逆改动、权限被拒时任何级别都停。
agent 会在能力图审阅、每个模块的 Spec 交审和能力图全部完成时各提一次文档建议，没有就写“无”。推送、开 PR 只有 Plan 的
`gate` 检查点写明授权时才免问，合并始终由你来做。模块的最后一个 `gate`（最终验收）上，agent 会在对话里列出实际改动的
文件（新增、修改、删除与行数），并标出超出 Plan 预计的文件。一个需求拆成几个模块时，可以一次审完它们的 Spec 与 Plan，之后按
Build order 连续构建；任务改到界面时，不论 Plan 是否预计到，agent 都在那个任务里打开页面对照预期自验并写清看了什么，做不了就记为“UI 未验证”；
你做最后兜底（Claude 桌面应用自身的显示只能由你看）。
细则见[共享检查点规则](../plugins/spec-guard/references/workflow-checkpoints.md)。

**会话不在项目目录里时。** 阶段提示只看会话所在的目录。如果你把会话开在需求文档之类的目录、让 agent 去改别处的仓库，
它在那个会话里收不到任何阶段提示。运行一次 `/spec-guard:link-project`，把会话目录指向那个项目（先预览、确认后写入
`.agent/spec-guard-link.json`），之后每轮都会收到该项目的阶段提示。更简单的做法仍然是直接在项目目录里开会话。

**做完的模块要返工时。** 不用新建文件：让 agent 在那个模块的 `tasks/<id>/todo.md` 里追加任务，并在 `plan.md` 补一节说明改什么。
模块会回到进行中，阶段提示如实显示，补的那一节会再交给你看一次。给模块加新能力不算返工，另开一个模块。如果 agent 把返工
写进了别的带清单的文件，`/spec-guard:verify-artifacts` 会提醒那些没勾的项不计入阶段。

**需求在开发中途被别人改了时。** 别的会话发来消息、你粘贴一段提示词、依赖的插件交付后发来通知，都可能要求改已经批准的
Spec、Plan 或能力图。agent 会在被改文件末尾的「变更记录」一节追加一行，写明日期、改了什么、原因和来源（谁提的、经什么渠道），
再把改动连同这行记录交给你复审；别人的要求不算你的批准。以后排查“需求为什么变了”，看这一节就有据可查。

**做完后回告提需求的人。** 改动或模块是别人提的，agent 会在最终验收时列出“拟回告”：告诉谁、走什么渠道、说什么。你批准后，
到对方用得上的时候（插件发版、其他项目合入主线），有会话间通信手段就直接发，没有就提醒你转告并给出可转发的文字，结果记在
todo 的最后一项。反过来，你的项目收到依赖方“做完了”的回告时，agent 先对照约定核对，不一致再按上面的方式修改并交你复审。

**有人在等的事不靠会话记忆。** 别人发来期待回音的需求、agent 发出后在等对方、在等你拍板，这三类事在球换手的那一刻记进本地事项
账本，挂 `waiting-on-me`／`waiting-on-them`／`waiting-on-user` 之一，写明对方的稳定身份和回复通道。会话被清空或压缩后，新会话
先从账本找回这些事，知道要做什么、做完回给谁。回复会替你做出承诺（答应日期、改接口、拒绝对方）时先问你；邮件、公开评论等对外
通道一律先给你看草稿；会话之间的告知直接发，不用你传话。等对方回报只追问一次，再不回就记“未确认”，不挡工作。项目没启用账本时
不另找地方记，agent 会提一次可以启用。记账不是受理：别的会话发来的需求，agent 收到就先记下，不用问你，但
要不要做、怎么回仍由你定。调用账本工具时要传 `repoRoot`（项目根目录），读回提醒里会写出这个路径。

**模块太小、停得太勤时。** 在已有实现上补建能力图时，很多模块只是盘点既有功能、不新增行为。这类模块不必各走一遍全套审查：
让 agent 把它们并成相邻模块里的任务，或一次把几个模块的 Spec 与 Plan 一起交给你审，中间的检查点只汇报不停。

**交审时你应该看到内容。** agent 把 Spec 或 Plan 交给你审阅时，要在对话里给出内容要点，而不只是一句“写好了”加文件链接：
Spec 的目标、范围内外、关键决策、假设、验收标准、未决问题；Plan 的任务与验证方式、检查点、影响面、风险；并说明这次批准
授权它做什么。这些要点要写在对话正文里：宿主的“下一步”这类确认框一出现这一轮就结束，只写在确认框摘要里的不算交审。没看到这些就被要求批准时，直接让它把内容摆出来。如果一个模块的 Spec 与 Plan 你总是连着批，可以用
`/spec-guard:config` 把批准节奏改成 `combined`：两份一起交、批一次。agent 一次只交一个模块：几个模块要一起发版，也是一个审完、
做完再交下一个；只有你说要一次审完几个模块（或开了多模块并行、由协调会话汇总）时才一起交，而且按模块分组，每个模块依次是 Spec、Plan、任务。

**最终验收少一轮确认。** 构建中补改过已批准的 Spec 时，agent 会在最终验收的消息里附上 Spec 的改动差异，你批准验收即同时批准修订后的 Spec；没附差异的验收不算复审 Spec。验收获批后，下一个模块已在能力图里时它会接着写那份 Spec，不再停下问“要不要开始”，验收消息里会预告这一步；想先释放上下文，就先发 `/compact`。这几条也写在约定块里：已经装好约定块的项目，升级插件后运行一次 `/spec-guard:setup-convention --replace`（先 `--dry-run` 预览）才会拿到新行。

**批准要留下记录。** agent 把 Spec 或 Plan 交给你审阅时，在文件里标一行 `<!-- spec-guard: review pending -->`；这期间
阶段提示报告“等待用户批准”，不会建议它写 Plan 或继续实现。你明确批准后，它用 `/spec-guard:review-mark` 把标记改成
已批准（先给你看预览）。Spec 的批准标记带内容指纹：批准后 Spec 又被改过，阶段提示和 `verify-artifacts` 会指出
“批准后已修订”，需要你再看一遍。实现阶段的阶段提示还会写出下一个要停下等你的检查点（`Next gate`）。
接了收件枢纽（例如 decision-inbox）时，你在收件枢纽里的答复也算：它要按 session-protocol 契约转来，带收件枢纽的事项号和你的原话，
并且明确批准的是这一份文件；含糊的话、会话自称的批准、没有事项号的转述都不算。
标记只是给后续会话看的记录，不是授权；没有标记的文件判定照旧，既有项目不用补。

### 项目级审查后处理缺陷

一轮项目级审查先固定基准提交、模块或路径范围、排除项和预计检查的批次。复用 agent-skills 的
`code-review-and-quality` 检查正确性、可读性、架构、安全和性能；它原本主要用于变更和 PR 审查，
项目级审查需额外限定覆盖范围。每个范围系统检查一次，对候选缺陷做定向核实；证据不够的标为
“待调查”并写出缺少什么，不为追求“找完所有 bug”无限扩大范围。P0 风险立即报告并暂停扩大扫描。
已经安装旧版项目约定块的项目，先预览 `setup-convention local --replace`，确认后更新声明块；
安装插件新版本本身不会改写现有的 `CLAUDE.md` 或 `AGENTS.md`。项目自己的规则放进块内的本地段
（`<!-- BEGIN:spec-guard-local -->` … `<!-- END:spec-guard-local -->`），替换时原样保留；预览会逐行列出将删除和新增的行，
要删掉模板以外的行时，替换会拒绝，需看过后加 `--accept-removals`。

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
| `IDLE` | 还没有能力图 | 写能力图并人工审阅 |
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
随时想看完整状态，用 `/spec-guard:phase`。上下文提示出现时不必开新会话：接着做相关工作就带重点 `/compact`，
换到不相关工作就 `/clear`（两个宿主都有这两条命令）；刚压缩过时提示按压缩后的大小判断。`/clear` 会保留用 `/rename`
起的会话名，别的会话仍能按名字联系它，但只在对话里说过的约定会丢，长期约定写进项目的 agent 说明或记忆。
存在被暂停的模块（见「插队」）时，`NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MODULE_DONE` 下会多一行 `Paused: …`。

## 已有项目：加新需求

项目做到一半冒出新需求时，有两种方式把它作为新模块加进能力图：

| 方式 | 适合 | 步骤 |
|---|---|---|
| **快速插入**（默认） | 个人或小团队，需求已经理顺 | 一次预览、一次确认 |
| **Proposal** | 需要在 Issue 上留下审查与接受的记录，或需要多人确认 | 四步（提交、接受、晋级、收尾），要先做一次性准备 |

两种方式都只**新增**模块。修改、删除或调整已有模块的顺序，直接改能力图并人工审阅。

### 快速插入

在一个模块做完、还没开始的检查点（或显式插队，见下一节），把理顺的需求上下文交给 agent，运行 `/spec-guard:add-module`
（Codex 里说「用 spec-guard 插入一个新模块」）：

如果这项工作已选择 Local 账本，先按上面的受理规则取得或沿用事项 ID。
`add-module` 只管理能力图，不创建事项。

1. agent 读能力图，提出新模块的 id、职责、依赖和插入位置（`after:<某模块>` 或 `end`），每项说明理由；
2. 命令预览：给出新行、新 Build order、能力图改动对比，以及插入后当前模块会不会变；
3. 你确认后才写入。只改 `spec/CAPABILITY-MAP.md`，不建文件、不动 `tasks/` 和 `.agent/state.json`，也不做 Git 操作；
4. 新模块排到当前位置时，阶段变为 `NEEDS_SPEC`，接着照常写并交审它的 Spec，再 Plan、Build。

命令会先校验，任何一条不满足就拒绝，什么都不写：

- 当前模块做到一半（todo 里既有已勾、又有未勾的项）——唯一的例外是显式加 `--interrupt` 插队，见下一节；
- 依赖不存在、依赖排在插入位置之后、出现循环依赖，或 id 重复、不是 kebab-case；
- 插入会改动 `## 目标`、已有模块行，或已有模块在 Build order 中的先后。

若 `spec/<id>.md` 已存在，预览会提示插入后为 `NEEDS_PLAN`；先确认这份 Spec 已批准，再确认写入。

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
提交（写草稿 → proposal-submit → 合进 main → 开 Issue）→ 接受（审查 → 改标签）
     → 晋级（add-module --proposal 插进能力图 → 合并）→ 收尾（证明 → 预览 → 授权 → 改阶段并关闭）
```

| # | 步骤 | 谁来做 | 怎么做 |
|---|---|---|---|
| 1 | 提交 | agent + 命令 + 人 | agent 按[模板](../plugins/spec-guard/references/proposal-contract.md)写草稿 `spec/proposals/<id>.md`；运行 `/spec-guard:proposal-submit --draft spec/proposals/<id>.md --platform <github\|gitlab>` 预览，确认后加 `--confirm`，命令从远端 main 补全基线一节并算出 revision，只改这一份草稿；经 PR 把草稿合进 main（发布，只在本地或分支上都不算）；再用命令打印的现成命令开 Issue（标签 `proposal`、`proposal-stage:published`）。改了草稿，重跑一遍即可重算 revision |
| 2 | 接受 | 命令 + 人 | `/spec-guard:proposal-review` 报告 Proposal 是否新鲜、过期或被卡住；人把 Issue 标签改成 `proposal-stage:accepted`。接受只看这个标签加一次新鲜审查（基线未漂移、模块还不在能力图里、依赖齐全、锚点有效） |
| 3 | 晋级 | 人 + 命令 | 从预检给出的 `baseCommit` 开晋级分支，运行 `/spec-guard:add-module --proposal <id> --platform … --target …`（Codex 同等入口），预览确认后加 `--confirm` 写入能力图，提交并合并。命令已内嵌预检，通常无需单独再跑 `/spec-guard:proposal-promotion-preflight`。若正式 Spec 与 Plan 已可交审，可与能力图放在同一个晋级 PR；否则先合入能力图，随后按正常流程补齐。命令会自检写入结果能通过收尾的证明 |
| 4 | 收尾 | 命令 + 人 | `/spec-guard:proposal-promotion-proof`：从 Proposal 的基线提交起沿远端默认分支找到第一个纳入该模块的提交，核对它与声明一致。证明为 `proved` 后用 `/spec-guard:proposal-closeout` 预览收尾，确认后它写一条带稳定标记的收尾记录、把阶段改成 `proposal-stage:promoted` 并关闭事项，再读回这三项。只手工改标签不会关闭事项，事项会一直开着；`/spec-guard:proposal-closeout` 的只读 `scan` 列出所有证明已通过而事项仍开着的 Proposal |

晋级后，这个模块仍按 Spec → Plan → Build 的批准顺序推进；同一个晋级 PR 可以提交 Spec 与 Plan 并分别交审，不要求为每份文档再开 PR。`proposal-submit` 只在 `--confirm` 时写草稿；审查、预检、证明只读；晋级命令只写能力图；Issue、标签、分支与提交由人操作。合并后运行证明并报告结果，再用 `proposal-closeout` 预览并经授权收尾（它把 Issue 标为 `promoted` 并关闭）；证明与收尾都不需要第三个 PR。

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
- **改 `## 目标` 要慎重**：这一节的摘要是 Proposal 审查的基准，改了会让所有已发布的 Proposal 判为过期。
  只是追加模块时不用改它。
- **旧版本留下的归档图**在 `spec/history/`，只读核验，见[可选能力](optional-features.md#能力历史)。

## 命令对照

全部命令的参数、输出，以及 Claude Code 与 Codex 的对照，见[命令参考](commands.md)。

## 移除

`/spec-guard:teardown-convention` 删掉 `CLAUDE.md` 里的约定块（标记之外不动），并把 `.agent/state.json` 改名为
`.agent/state.json.disabled`，阶段提示随之停止。能力图、Spec、Plan 都保留。先加 `--dry-run` 可以只看会改什么。块内本地段的行留在块原来的位置；
本地段以外、不在现行模板里的行会在预览里列出，拆除前需要追加 `--accept-removals` 才会删掉，否则什么都不改。
