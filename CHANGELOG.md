# Changelog

## [0.51.3] - 2026-10-07

### 修复

- **Proposal 评审与晋级预检写明要加入的模块。** 两者输出只有 `proposalId`，而 Proposal 的 id 不一定是它要加入的模块 id
  （`collaboration-split` 加入的是 `collaboration-interface`），读结果的会话曾把前者当成模块名。现在凡是读到了 Proposal
  的结果都带 `moduleId`，与晋级证明的字段同名；没读到 Proposal 时不带，不猜。状态与判定不变。

## [0.51.2] - 2026-10-07

### 修复

- **已晋级的 Proposal 不再被报成「过期」。** 远端能力图里已经有该 Proposal 的模块时，`/spec-guard:proposal-review` 与晋级
  预检报的是 `stale`（JSON 里甚至只有笼统的 `proposal-stale`），而命令说明把 `stale` 解释为「按新基线重新发布」——
  对已晋级的 Proposal 正好说反。现在这种情况报 `in-map`（`proposal-module-already-present`），说明写明两种去向：本
  Proposal 已晋级就跑晋级证明再收尾，与已有模块重名就换 id 重新发布。基线、依赖、锚点漂移仍报 `stale`，基线漂移
  优先；预检照样不放行，晋级证明与收尾判据不变。

## [0.51.1] - 2026-10-07

### 修复

- **上下文提醒不再让 agent 贴出交接文本。** 模块边界（窗口 50%）与模块进行中（80%）注入的 `Module boundary`、
  `Session context` 两行，原来写着「运行 `/spec-guard:handoff` 得到可直接粘贴的交接文本」，共享检查点规则也要求连续
  构建到 80% 时「给出 `/spec-guard:handoff` 的交接文本」，于是 agent 在上下文接近满时会把整段交接文本贴进回复。
  2026-10-06 的「只说一句」只记在了作者本机的 agent 记忆里，从未进入任何发布版本。现在两行与检查点规则都只让 agent
  用一句话提示可以 `/compact` 或换会话，并明写不贴交接文本；交接文本由你需要时自己运行 `/spec-guard:handoff`
  （Codex：`spec-guard handoff`）。阈值、出现在哪些阶段与交接命令本身不变。

## [0.51.0] - 2026-10-07

### 新增

- **提醒还没收尾的 Proposal。** Proposal 事项只有第四步 `/spec-guard:proposal-closeout` 会关闭，此前没有任何东西提醒
  去跑它；文档还写着「证明通过后由人工把标签改为 promoted」，而只改标签不会关闭事项——本仓库的 #221 就在晋级
  合并一天后仍开着。现在：`proposal_closeout.py scan`（命令里的「扫描」一节）只读地对远端默认分支上每一份
  Proposal 走与预览同一套判据，列出证明已通过而事项仍开着的 `pending`，读不到的报 `unknown`、不算待收尾，不写任何
  东西；`proposal-promotion-proof --prove` 在 `proved` 时带 `closeoutPending`；共享检查点规则新增「Proposal 晋级 PR
  合并后」一条，发布流程的发布后核对加跑一次扫描。`add-module`、`spec-guard-ops` 与 `docs/workflow.md` 里让人手工改
  标签的说法改为走收尾命令。关闭仍须逐条预览并取得授权，扫描结果不构成授权。

## [0.50.1] - 2026-10-07

### 修复

- **Claude Code 上的命令找不到插件根目录。** 17 条命令（`phase`、`verify-artifacts`、`add-module`、`handoff`、
  `cost-report`、文档与历史、Proposal 各命令、`tracker-default`、`collaboration`、`local-ticket-ledger`）的第一行写的是
  `${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}`。Claude Code 不把 `CLAUDE_PLUGIN_ROOT` 导出给 Bash 工具，只在命令 Markdown
  里把精确的 `${CLAUDE_PLUGIN_ROOT}` 换成路径（2026-10-07 在 2.1.291 上实测，headless 与交互式一致；官方插件参考
  同样写明），所以这些命令在 Claude 上一律退出 2 并报「插件未安装或未启用」；机器上装了 `codex` 时则改跑 Codex 那份
  安装，版本可能不同。现在第一行改为会被代入的 `ROOT="${CLAUDE_PLUGIN_ROOT}"`，再依次回退到 `PLUGIN_ROOT` 与
  `codex plugin list`；全部失败时说明是哪一步没定位到（没有代入或环境变量、没有 `codex`、`codex` 的退出码或输出无法
  解析、列表里没有已启用的 spec-guard、目录不存在），并明确这是定位失败、不代表插件未安装。`ticket` 与
  `hosted-ticket-workflow` skill 改为让 Claude 使用会被代入的写法；Codex 的 `spec-guard-ops` 不再把查询失败说成未安装。
  `evals/test-codex-command-roots.sh` 按宿主真实的代入方式回归每条路径，并禁止不会被代入的写法回来。

## [0.50.0] - 2026-10-07

### 移除

- **会话协作拆为独立插件 agent-relay。** 本机协作信箱、统一会话路由与跨宿主会话委派（`collab`、`collaboration-ops`、
  `session-routing`、`session-delegation` skill 及其运行时、宿主适配器与测试）移到 agent-relay，代码连同逐文件历史迁入
  新仓库。只想让会话互相通信的项目不必再装 Spec Guard 的工作流；只用工作流的人也不再背 macOS／Node.js 依赖。
  Spec Guard 只通过 `agent_relay_probe.py` 检测 agent-relay（读宿主的插件记录，含 git worktree 记在主仓库的本地启用，与它的 `interface.json`，失败报 `unknown`，
  从不写文件），未安装时工作流照常运行。`/spec-guard:collaboration` 保留一到两个版本作为转交入口：agent-relay 可用时
  转交给它，否则提示安装与迁移。旧的信箱与委派数据不会被删除，迁移步骤见
  [`docs/migrations/2026-10-07-collaboration-split.md`](docs/migrations/2026-10-07-collaboration-split.md)。
  `scripts/check-collaboration-boundary.py` 防止协作实现或其内部名字重新进入 Spec Guard。

## [0.49.0] - 2026-10-06

### 新增

- **检查点分级、按需求批量前置审与 UI 自验（共享检查点规则与约定块）。** Plan 的检查点标 `gate`（停下等确认）或
  `report`（把验证结果记入 todo 后直接继续，不停也不倒计时），未标注按 `gate`；异常停点在任何级别都停。推送、开 PR
  只有 Plan 的 `gate` 检查点写明授权时才免问，合并始终由用户进行，插件不把任何远端写入设为默认授权。一个需求拆成多个
  模块时可一次审完全部 Spec 与 Plan，plan.md 写明“随同一需求批量批准”的模块会在前一个完成后接着构建；连续构建时遇到
  模块边界提示不停，到窗口 80% 时停下并给出 `/spec-guard:handoff` 交接文本。涉及 UI 时 agent 先用浏览器或电脑操作自验，
  缺工具时提前提醒，人做最后兜底；Claude 桌面应用自身的显示只能由人看。这些是写给 agent 的规则，没有改 hook 判定；
  已有项目需重新运行 `setup-convention --replace` 才会在约定块里看到新的一行。

## [0.48.0] - 2026-10-06

### 变更

- **上下文提醒以模块为单位、分两档。** 原来最近一轮主会话上下文超过 200k 后每一轮都提示开新会话，不管模块做没做完；
  模块中途换会话要重读正在改的代码、写交接，代价最高。现在模块完成（`MODULE_DONE` / `DONE`）时，上下文达到窗口 50%
  才在 `Module boundary` 一行给出大小并建议开新会话，低于就不提示；模块进行中只在达到窗口 80% 时作为安全阀提示。
  Codex 按会话记录里的窗口大小算；Claude 的会话记录没有窗口大小，按 1M 窗口折算为 500k / 800k，所以 200k 窗口的
  Claude 模型基本不会看到这两条提示。读不到会话记录时，模块完成仍保留原来不带大小的 `Module boundary` 一行。

## [0.47.0] - 2026-10-06

### 新增

- **会话交接命令 `/spec-guard:handoff`（Codex：`spec-guard handoff`）。** 开新会话时要自己写交接：仓库在哪、哪个分支或
  worktree、HEAD、阶段到哪、哪些发布证据还没核对、有没有没合并的提交。现在这条只读命令从仓库文件与 git 拼出可直接粘贴的
  交接文本，末尾留一行“下一步：____”由你填写；不写文件、不读会话记录内容。`Module boundary` 一行改为指向它。
- **交接命令在本地作答，不调用模型。** 已启用约定的项目里，整条提示词恰好是上面两个触发词之一时，UserPromptSubmit hook
  直接拦下并把交接文本显示给你（Claude Code 会带宿主固定的 “UserPromptSubmit operation blocked by hook:” 前缀），这一轮不花
  模型费用；`claude -p` 实测费用为 0。带参数或其他文字一律放行，不识别自然语言的状态问句。拼装失败时照常注入阶段。
  Codex 的拦截输出只有 `decision` 与 `reason`：多一个未知字段会让 Codex 判 hook 失败、提示词照常送给模型。

### 修复

- **worktree 会话的阶段提示读到主检出目录。** 桌面版 worktree 会话里，宿主给 hook 的项目目录可能是主检出目录，阶段与位置
  因此报告主仓的分支与模块状态。现在 hook 先读输入里的 `cwd`，以它所在的 git 仓库为项目根；读不到时行为不变。
  代价是每轮多一次约几十毫秒的 python 启动（含未启用约定的项目，它们仍然静默）。

## [0.46.0] - 2026-10-06

### 新增

- **阶段提示建议开新会话。** 费用的大头是每轮重读整个主会话上下文；spec-guard 把需求、计划与进度放在文件里，开新会话
  不丢东西，但提示从不这样建议。现在 `MODULE_DONE` / `DONE` 多一行 `Module boundary`，建议在新会话里开始下一项工作；
  宿主 hook 输入带 `transcript_path` 且最近一轮主会话上下文超过 200k token 时，再多一行 `Session context` 给出大小，
  建议在下一个 task 边界记下决定、开新会话。只读会话记录末尾 4 MiB 里的最后一条用量（跳过子代理与用量为 0 的记录），读不到就不提示；
  标准输入最多等 1 秒。Claude Code 已确认提供 `transcript_path`；Codex 真实会话里是否有值待安装版核对。
- **每个阶段提示都给出当前分支与 worktree。** 标题下多一行 `Location: branch … · worktree …`，并要求 agent 在请用户
  评审或确认时说明位置，挂着多个 worktree 时不用再问代码在哪。不在 git 仓库里时没有这一行。
- **派活成本对照脚手架存档到 `evals/dispatch-cost/`。** 与 tier-guard 联调用的 ledgerlite 种子项目、参考实现、隐藏测试、
  价格表与 18 次运行的成本数据原来只在临时目录里。现在 `run.sh <claude|codex> <组> <编号>` 按组从本仓库导出当时的
  spec-guard 版本（联调中途的两版临时规则存在 `variants/`），`grade.sh` 判分并计价，`verify-seed.sh` 证明种子有效；
  运行目录必须在仓库之外。要调用真实宿主、花真钱，不进 `validate.sh`。

## [0.45.0] - 2026-10-06

### 新增

- **成本报告列出模块完成后的收尾用量。** 最后一次勾选之后主代理写收尾总结的那一轮不属于任何 task，模块合计因此比整次
  运行少 2–8%。现在模块全部勾选后多一行「模块完成后的收尾」（到该会话下一次用户发言为止，只计参与过模块的会话）与
  「合计（含收尾）」；ledgerlite 联调中它与 tier-guard 的整次运行金额逐次一致。
- **`/spec-guard:cost-report`：只读的模块成本与返工报告。** 离线读取本机 Claude Code transcript 与 Codex rollout，
  按 `tasks/<模块>/todo.md` 的勾选提交切出 task 时间窗，统计每个 task 的主代理与子代理 token（按模型、按类别）、
  主会话轮次与缓存读、派活次数与覆盖率、重派、收回、交回后主代理改动的文件数；`--prices` 折算等价金额，缺价标
  「未定价」；多个模块附「有派活 / 没派活」对照。口径与 tier-guard 一致：Claude 按（文件, message.id）取用量最大的一行，
  子代理文件整份只计一次；Codex 取累计值之差、非缓存输入 = input − cached、推理含在输出内。宿主没留下记录的派活、
  被 hook 拦下的调用、通过 shell 的改动都单列说明，不报为 0。Codex 侧由 `spec-guard-ops` 的 cost report 一节调用。

### 变更

- **`--dispatch` 规则的派活门槛写具体，Codex 段要求一次长等待。** ledgerlite 联调（Claude 8 次、Codex 6 次，成本由
  module-cost-report 与 tier-guard 独立核对一致）：只有「改多个文件、验收明确」的 Task 4 派出去省钱（主会话 8/4→2/3 轮，
  改按 L2 派给 sonnet 后比不派便宜 23%）；探索量小的 task 派了主会话轮次不降。原规则「只有预计需要大量探索或调试的 task
  才考虑派」在 4 次运行里一次都没派。现改为「只派预计要改动 3 个以上文件、验收明确的 task」。Codex 主代理派出后每
  10–40 秒用 `wait_agent` 轮询一次（每次运行 25–31 次），每次都是一轮主会话，Luna 子代理 $0.07 的成本被主代理翻倍的
  花费吃掉、整组贵 138%；Codex 段现要求派出后一次等到完成、不要短间隔轮询。
- **`--dispatch` 规则：交出完整任务块，并写明哪些 task 不派；标为实验性。** spec-guard 约定下 todo 常只有一行，
  验收标准、验证、依赖与涉及文件在 plan.md 的任务块里，原规则只交「task 原文」会让子代理缺上下文。现在交完整任务块、
  plan.md 的 Architecture Decisions 与模块 spec 路径。任务块缺验收标准或验证步骤、属于 `/build` 的停止条件、L3、
  或为子代理选的模型不比主会话便宜时，由主代理自己做。tier-guard 实测同模型对照里派活比不派贵 2.0–2.8 倍，
  因此在对照数据证明省钱之前，这个开关标为实验性。随后的对照实验（opus 父代理、sonnet 子代理）显示派活没有
  减少主会话轮次，仍贵 15%–54%，规则因此改为**默认由主代理自己做**，只有预计需要大量探索或调试的 task 才考虑派。已开启的项目需 `setup-convention --replace` 取得新规则。

### 修复

- **`--dispatch` 规则段的档位定义补上「取舍」。** 原文「L3 跨模块、有歧义、高风险或不可逆」漏了 tier-guard 定义里的
  「取舍」，主代理把「改多个文件、验收明确」的 task 读成跨模块、判为 L3 并派给与主会话同价的模型，派活因此没有差价。
  现为「L1 机械、只读；L2 验收明确的实现，可以改多个文件；L3 需要跨模块取舍、有歧义、高风险或不可逆」，两个宿主同步。

## [0.44.0] - 2026-10-05

### 新增

- **可选规则：`/build` 把 task 交给子代理执行（`setup-convention --dispatch`）。** agent-skills 的 `/build`
  在主会话里直接实现每个 task，从不派子代理，所以子代理模型路由（如 tier-guard）在 spec → plan → build
  主干上没有入口。开启后约定块多一段规则：非 Checkpoint 的 task 交给一个子代理做 RED → GREEN → 回归 → 构建，
  不提交、不勾选，上一个 task 提交、勾选完再派下一个；派活 prompt 带独占一行的 tier-guard 档位标记
  （规则段内联三档定义，装了 tier-guard 时以 `tier-routing` 为准）；遇到 `/build` 的停止条件原样交回，由主代理
  验收、提交、勾选和问人。**默认关闭**，不带开关时约定块逐字不变；开关状态存在块里，`--replace` 保留已开启
  的状态，关闭须 `--no-dispatch`。Claude 与 Codex 两份规则段，Codex 段写明 tier-guard 在 Codex 上只作建议。
  spec-guard 不检测、不要求安装 tier-guard。

## [0.43.0] - 2026-10-05

### 新增

- **有意不建 todo 的模块可以声明，提醒只列真正缺 todo 的模块。** 已交付的模块常常只有 Plan，此前
  `verify-artifacts` 的汇总和阶段注入的 `Plan without todo: N` 每次都把它们全部列出，真正漏建 todo
  的模块被淹没在里面。现在 `tasks/<id>/plan.md` 中独占一行的 `<!-- spec-guard: no-todo -->` 声明它是
  有意的：汇总、计数行和 `activeModule` 提醒都跳过它。**完成判据不变**，带不带声明都按已完成计。
  判据由 `module_stage.plan_without_todo` 唯一实现，两边共用；本仓库 13 个登记模块已加上声明。

### 修复

- **两份被取代的决策不再读作生效中。** `docs/decisions/2026-09-28-xats-sunset.md` 的状态行此前
  写着「尚未触发，XATS 仍是默认传输」，`2026-10-04-a10-single-mac-promotion-gate.md` 写着
  「其余条款继续有效」，而取代它们的
  `2026-10-04-native-only-collaboration-sunset.md` 早在 v0.40.0 就把旧传输的产品面删掉了。
  两份旧文件也都不指回取代者，所以搜 XATS 的人第一眼读到的是一个不成立的现在时事实。现在两份的
  状态行都声明已被取代并链接到取代者；**正文一字未改**——那份取代决策明确要求旧门槛不能被改写成
  当时已经满足。
- **新增 `scripts/check-decision-supersession.py`。** 本仓库原本已有一对做对了的先例
  （`single-capability-map` ↔ `initiative-rollover`），但那只是写在文档里的习惯，没有任何东西
  执行它——于是下一对就漂了。判据只要求两件可机械判定的事：被取代者的状态行自称已被取代、
  并与取代者互相链接；它不读正文、不判断取代的是全部还是部分条款。七个回归用例里最关键的是
  「指回去了但状态行仍读作生效中」——那是本次真实缺陷的另一半，只查链接的版本会把它判过。

## [0.42.0] - 2026-10-05

### 变更

- **这些路径里潜藏的代码缺陷，现在会以 traceback 暴露，不再是一句柔和的「读不到」。**
  托管事项、Proposal 收尾、Local 事项交接发布与 native-wake 续轮一共 23 个处理器此前捕获裸
  `Exception`，于是适配器里一个拼写错误产生的 `AttributeError` 被报成 `unknown` +
  `provider-unavailable`、`partial` + `close-result-uncertain`、`publication-uncertain`
  或 `host-result-unknown`。这些状态的含义都是「结果存疑，重试或去查远端」，而**重试修不了拼写错误**，
  读者会去检查一个根本没问题的远端。
  这是 v0.41.0 拆开的那一类的第三种形态：那一版分开了「探测读不到」与「读到了但不成立」，
  却把「我们的代码坏了」留在第一个桶里。
  **升级后看到 traceback，说明撞上的是一个此前被静默吞掉的缺陷，请按栈报告，不要当成环境问题重试。**
  已降级的行为一字未改：探测失败、响应丢失、确定性 4xx 仍然各走各的路（见下）。

### 修复

- **诊断：四条链路把自身缺陷与探测失败共用一个结果。** 按每个模块能支持的方式分别收窄，
  没有把一种形状硬套到所有地方：
  - 托管事项家族（`hosted_ticket_actions|write|read.py`，9 处）收窄到 `HostedTicketError`。
    这不是新策略——`publish_preview` 的外层与两个 CLI 顶层本来就在用它；传输层
    （`run_json` / `run_write_json` / `pages` / `_target`）已把 OSError、超时、非零退出与坏 JSON
    全部转成它，确定性拒绝转成子类 `ProviderRejected`，所以没有合法异常会漏出去。
  - `local_ticket_publish.py`（2 处）收窄到 `InventoryError`，该模块在每处的上一行就已捕获
    `ProviderRejected`。
  - `proposal_closeout.py`（11 处）**不能**具名传输异常：`_rejection` 的契约写明它按 `status_code`
    鸭子类型判断，「so any adapter can report one without this module importing a transport」。
    改为在降级前重抛确定属于编程错误的那些。
  - `session_delegation_claude.py`（1 处）包的是注入式 `native_wake`，类型不可知；而且该处理器
    还做状态推进，`begin_follow_up` 已经跑过。改为**先 `advance` 到 `unknown`，再重抛**，
    否则委派会停在 follow-up 中途无法恢复。异常类型也无法写进诊断：`DelegationStore.advance`
    把 evidence 串硬校验成枚举，不匹配即 `untrusted-state-evidence`。
  判据集中在新增的 `plugins/spec-guard/hooks/defect_guard.py`，两个无法具名传输异常的模块共用一份；
  它刻意**不含 `ValueError`**：`HostedTicketError`、`InventoryError`、`ClaudeAdapterError` 都是它的子类，
  journal 也用它表示 JSON 读不出来，收进来就会误伤本该降级的失败。
  全仓库吞掉型宽捕获由 24 处降到 1 处；剩下的 `spec-digest.py:72` 不是缺陷，它把 error 原文打印出来。
  19 处 `except BaseException` 后接清理再 `raise` 是正确惯用法，未改动。

- **放行 `KeyError` / `TypeError` 前先钉死了输入来源。** 托管事项的 preview 由 `make_*_preview`
  在进程内生成，只有 digest 经 CLI 往返；Proposal 收尾的 preview 虽然来自文件，但 `close_preview`
  在任何下游动作之前就以 `_valid_preview` 拒绝不合格输入，且写入路径下标用到的每个键都在它的必查
  集合内（用 AST 机械核对，不靠通读）。手改坏的 preview 仍然是干净的 `preview-invalid`，不是 traceback。

- **`session-routing` 与 `collab` 不再争同一个意图。** 两个 skill 的 description 都宣称「按名称告诉
  另一个 Agent 一件事」，而选错是**静默的**：正文会被复制进协作信箱，不走同宿主原生通道。
  现在「告诉某个会话一件事」只由 `session-routing` 宣称，`collab` 只宣称加入、收件箱与会话清单，
  并指明另两个 skill。`collab` 的发送能力一个都没删，只是明确标为「`session-routing` 不可用或只能经
  bridge 时」才直接使用。

### 测试

- 新增 24 个缺陷传播用例（每个收窄点一个，外加 native-wake 的状态推进不变量），并配对了
  「探测失败仍降级」「响应丢失仍 `partial`」「确定性 4xx 仍 `rejected`」三类对照用例：
  缺了它们，「让一切都抛出」的改法会与正确修复长得一样。
- **两个测试夹具此前钉死了传输层不可能产生的形状。** `test_local_ticket_publish.py` 的 `FakeProvider`
  与 `test_local_ticket_providers.py` 的 `ApiFixture` 都顶替 `run_json`——而 `run_json` 的全部职责就是
  把 OSError 与 `subprocess.TimeoutExpired` 转成 `InventoryError`——却都抛裸 `TimeoutError` 来模拟
  响应丢失。收窄产品代码把这件事暴露出来；现在它们抛真实传输真正会抛的异常，而**那些用例的断言一条
  没改也全部仍绿**：夹具不忠实，期望本身是对的。与 v0.41.0 的 `gh --json state` 大小写事故同类——
  一个从未与真实形状核对过的夹具。
- **新增 `scripts/check-acceptance-wired.py`。** `hooks/test*acceptance*` 需要固定外部运行时，
  刻意不进 `validate.sh` 与 CI；但此前没有任何运行器或维护者文档提到它们，
  `test_proposal_closeout_local_acceptance.py` 处于全仓库零引用状态——而它是唯一能证明 Local 适配器
  发出的参数名被真实 `epiq@1.11.0` 接受的测试。判据只问「有没有东西告诉下一个维护者跑它」，
  不问「它是否在 CI 里跑」；`docs/reports/` 这类历史运行记录不算运行指引。
- 两个 skill 入口契约测试随意图归属一并搬移：`test_collab_entry` 去掉该词汇并新增反向断言
  （`collab` 的 description 不得再宣称它），`test_session_routing_entry` 断言它必须带。
  少了这一对，两个 skill 会漂回互相竞争，或这个意图从两边同时消失——第一版正是删掉而不是搬移，
  被前者当场抓住。

### 文档

- `docs/maintainer-workflow.md` 新增「可选验收测试」一节：三个验收测试的运行方式、所需的
  `SPEC_GUARD_EPIQ_RUNTIME`，以及它们未设该变量时**退出 2**（实测）而非 0 ——
  接进任何运行器都要按 `2` 判「没跑起来」。
- `CONTRIBUTING.md` 不再声称 CI 定义了 Ubuntu + macOS 两个 job。`ci.yml` 自 `150169e` 起只跑
  `ubuntu-latest`，其 `/bin/bash` 是 5.x；bash 3.2 在 CI 里只由静态判据 `check-bash32.py` 覆盖，
  真正在 3.2 上跑过的只有贡献者本机那一次。
- README 的功能一览补上「会话路由」与「跨宿主会话委派」：两者都是双宿主可自然语言触发的 skill，
  此前只作为 `docs/optional-features.md` 里协作信箱的子节出现，而那份文档开头写「下面四项」，
  数能力的读者看不到它们。
- `docs/optional-features.md`：兼容传输的退役不再写成「等待下一版本发布」（v0.40.0 已发）；
  本地事项账本的「需要什么」注明它按插件自带 lockfile 装入 Epiq 运行时，连传递依赖共 270 个包。
- `references/proposal-closeout.md` 补上阶段迁移「先加后删」真的留下两个阶段标签时的处理办法：
  `closeout` 返回 `state: invalid` + `tracker-contract-invalid`，人工删掉旧标签后重新 preview，
  不要改 Proposal 文档。诊断码是实跑该情形核对的，不是推的。
- 13 个有 Plan 而没有 `todo.md` 的模块中，此前只有 6 个在 Plan 里写了登记说明；其余 7 个补齐，
  分两组各写其真实来源（转单图时原样恢复的 initiative 计划 / 既有能力的一次性人工登记）。
  完成判据未变，`verify-artifacts` 仍报同样的 13 个模块。
- `hosted_ticket_action.py`（CLI）与 `hosted_ticket_actions.py`（库）在各自 docstring 里互相点明分工。
  没有重命名：`docs/reports/` 的历史审计按行号引用后者，改名会让那些记录指向不存在的文件。
- 新增 `docs/releases/v0.41.0-write-paths.json`：v0.41.0 的三条写入能力（Proposal 收尾、Proposal 的
  Local 后端、项目级默认事项后端）当时没有留下任何证据记录，现补记为三条 `not-verified` 并写明原因。
  按 `docs/releases/README.md` 的约定这是**新增**一份未验证记录，不反向改写已发布的四份。

## [0.41.0] - 2026-10-05

### 修复

- **可靠性：一次偶发的只读探测失败，要靠重跑写命令才能绕过。** `proposal_publication.fixed_snapshot()`
  用两次 git 网络往返把远端默认分支 tip 钉住（`ls-remote` 观察 + 临时 bare 仓库 `fetch` 核对），任一次
  抖动就整体失败，而且全链路没有任何地方重试。一次 `proposal_closeout close` 要跑三段互不相干的快照、
  共 6 次网络往返；2026-10-04 对真实远端实测：机器空闲时单段成功率 9/10，三段串起来约 0.73；本机有并发
  git 活动时更差 —— 关掉一条真实事项用了 8 次 `close --confirm`，另两条分别 3 次和 2 次。每次失败都是安全
  的（什么都没写），但读不到却要人重跑**写**命令，而且每次重跑把 6 次往返全部重做。现在探测失败在
  `fixed_snapshot` 内部有界重试（3 次，退避 0.2s 递增）：`_head` 读不到、`fetch` 失败、`rev-parse
  FETCH_HEAD` 失败。**tip 真的动了永不重试** —— 两次都成功的读取一旦不一致（重新观察到不同的 head，
  或 `FETCH_HEAD` 不是观察时的 tip），立刻失败，绝不把更新的 tip 当成新快照；把这一条弄反会把安全属性
  变成竞态，所以它在代码里写明并有正反回归钉住。

- **诊断：探测失败与 tip 真的移动共用同一句话。** 上面那两件事原先都报
  `remote default branch moved or fetch failed`，调用方分不出「重试即可」和「真的有人在推」。现在
  `remote default branch is unavailable`（`_head` 读不到）、`remote default branch fetch failed`
  （fetch / rev-parse 读不到，可重试）、`remote default branch moved between observation and fetch`
  （真的移动，不可重试）各自独立，`read_published` 与 `read_published_pool` 原样透传，
  `proposal_submit` 直接报给用户。

- **诊断：晋级证明把快照探测失败和 tip 真的移动都报成 `promotion-unknown`。** `proposal_promotion_proof`
  的 `as_json` / `preflight_as_json` 只透传 kebab 码形态的诊断，散文原因会被归一化掉，而 `prove` 自己那段
  快照的 `failure` 连传都没传。于是 `--prove` 和 preflight 对「重跑即可」和「有人在推」给的是同一个码。
  现在 `proposal_publication.PROBE_CODES` / `probe_code()` 把四种快照失败映射成稳定码 ——
  `snapshot-head-unavailable`、`snapshot-fetch-failed`、`snapshot-tip-moved`、
  `snapshot-temp-repo-failed` —— 三个入口（`prove` 自己的快照、`prove_from_remote` 与 `_preflight`
  读 pool 的那段）都带上。认不出的诊断仍返回 `None`，保留调用方原来的 `proposal-pool-<state>` /
  `promotion-<state>` 折叠，绝不把别的错误装成快照判决。远端不可达现在报 `snapshot-head-unavailable`
  而不是折叠后的 `proposal-pool-unknown`。

- **诊断：把「探测读不到」说成了「这条 Proposal 不能关闭」。** `closeout_decision` 把 proof 的
  `unknown`（探测读不到）与 `not-promoted` / `stale` / `invalid` / `not-accepted`（读到了，不成立）
  一起映射到 `not-eligible`。`not-eligible` 读起来是对 Proposal 的判决，于是读者去查一份从没动过的
  文档，而真正该做的是重试。诊断本该区分两者，但 `prove()` 的四条 `unknown` 路径（快照取不到、
  `rev-list` 空、读不到第一父提交、publication 非 published）**根本不带诊断**，closeout 于是补成
  `promotion-not-proved`——state 和 diagnostic 两格都在指责 Proposal，探测失败完全不出现在输出里。
  2026-10-04 收尾真实事项时踩到：八次 `close --confirm` 里三次报 `not-eligible`，实际原因是偶发的
  `remote default branch moved or fetch failed`。现在 proof 的 `unknown` 映射到 state `unknown`
  并透传 proof 自己的诊断（没有时用 `promotion-unknown`），`not-eligible` 只留给读到了而不成立的那几种
  与 `stage-not-closeable`。这与同一次发布里 `build_preview` / `_close_locked` 对 publication 探测
  失败的处理同形，也是本仓库「探测失败必须降级」的不变量。
  **这是契约变更，不只是修 bug**：`unknown` 与 `not-eligible` 都写在
  `references/proposal-closeout.md` 与命令文档的结果表里，两处都已更新；`closeout_decision` 的签名
  不变（仍不含 project/root/provider）。写入行为一字未改——两种 state 都什么都不写。
  正反两向都有测试锁死：探测失败不得报 `not-eligible`，真正不成立的 proof 仍须报。六个变异全红，
  含「每个非 proved 都变成 unknown」这一过度修正。
- **诊断：把探测失败说成了「Proposal 的 revision 变了」。** `proposal_closeout` 的 `_close_locked`
  把三件事塌缩成同一个 `preview-stale` + `proposal-revision-changed`：快照探测读不到、Proposal 不在或
  不合法、revision 真的变了。只有最后一种跟 revision 有关。一次偶发的 `git fetch` 失败因此会让人
  去 diff 一份从没变过的 Proposal 文档（2026-10-04 实际踩到）。这违反本仓库「探测失败必须降级，
  不能把环境故障说成链路断裂」的不变量。现在三者各有诊断：探测失败是 `unknown` 并带上探测自己的
  原因，`absent` / `invalid` 各有其码，`proposal-revision-changed` 只在 revision 真的变了时出现。
  `build_preview` 原先只回 `{"state": "unknown"}`、把原因整个丢掉，现在同样带上。

- **回归：GitHub Proposal tracker 只读整条链路失效。** `proposal_tracker_read` 的 `CLOSED_STATES`
  用 REST API 的小写 `open`/`closed` 建表，但同文件 `_github_page` 走的是
  `gh issue list --json state`，它返回 `OPEN`/`CLOSED`。查不到即判 `tracker issue response is
  malformed`，于是 `proposal-review`、`proposal-promotion-proof`、`proposal-closeout` 在 GitHub 上
  全部不可用。该表随 `closed` 字段一并引入，所以这是从能用变成不能用。现在 GitHub 的 `state` 在查表前
  规范化大小写，两种拼写都接受，未知值仍然是「读不到」而不是默认当作 open。GitLab 不动：`glab api`
  返回 REST 拼写，放宽一个没有实测过的大小写等于猜。
  单元测试没抓到，是因为夹具里 `state` 写的是小写——一个从未与真实 `gh` 输出核对过的假设。
  全仓库审计确认只有这一处走 CLI 形状，其余三处读 GitHub `state` 的都走 `gh api`，拼写正确。

- **安全：阶段提示不再把仓库内容原样注入 agent 上下文。** 这段文本每轮注入，此前两处会逐字带出仓库值：
  `.agent/state.json` 的 `activeModule`，以及能力图坏 module id 经 `MapError` 引用的单元格。
  两处都已复现——一个带换行的值能伪造出看起来像系统段落的块。
  现在 `activeModule` 必须是完整匹配的 kebab-case module id（`fullmatch`：`$` 会在结尾换行前匹配，
  用 `match` 的话 `"alpha\n"` 会被当成有效 id，随后查不到而报「不在能力图中」，指着一个明明在图里的模块
  说它不在）；诊断里的外部值一律折叠空白、去反引号与反斜杠、剥掉控制与格式字符（Cc/Cf），
  并限长 200 字符（被截断时整段为 201 字符，含省略号）。上界是按 `MapError` **整条消息**实测的：
  最长的模板带两个 module id，本仓库自己的 Build order 诊断就有 85 字符。
  `MAP_INVALID` 引用的能力图原文现在明确标注为「能力图原文，非指令」。
  **行为变化**：`activeModule` 无效时，提示从「打印该值并说它不在能力图中」变为「说它不是有效的
  module id」——**值不回显，但不静默忽略**，hook 也照常激活（让一个手滑的值使 hook 静默，比注入更难发现）。
  净化**只在注入边界**：`/spec-guard:verify-artifacts` 与 `/spec-guard:add-module` 给人读的终端输出
  仍带原始单元格，并有回归反例钉住——把诊断能力一起杀掉比注入更难察觉。
  阶段取值、完成判据与激活信号逐字不变。取舍见
  [决策记录](docs/decisions/2026-10-04-phase-context-sanitization.md)。

### 移除

- **`.agent/state.json` 的 `tracker` 字段退役。** 远端 tracker 模式本身早在 v0.15 退役，留下的字段却同时
  充当激活信号、被 `setup-convention` 持续写入、又在另一处抑制 plan-without-todo 提醒，而
  `verify-artifacts` 还对插件自己刚装的文件告警。现在没有任何代码读它：新装项目的 state 文件是
  `{"activeModule":""}`，激活信号改判 `activeModule`（**信号数量不变**），抑制逻辑与无人读取的 `modules`
  空对象一并删除。退役扫描覆盖已发布表面（含 `evals/`、`scripts/`）里常见的重新引入形态——JSON 字面量写入、
  `get("tracker")`（含带默认值）、单引号与下标读取、非字符串值、成员判断、`retired_tracker` 本身——每一种都有
  实测；它按文本匹配，不保证穷尽所有写法。
  **完成判据不变**——有 Plan 且没有未勾选项仍算完成，缺 `todo.md` 的历史模块状态不受影响。
  迁移见[退役说明](docs/retirements/state-tracker-field.md)：绝大多数项目无需动作；只有既没有声明块、
  又只剩 `{"tracker":"none"}` 的项目需要补 `activeModule` 或重装声明块。
- `verify-artifacts` 不再对 `.agent/state.json` 的存在告警，只在确实残留 `tracker` 字段时提示删除。

### 新增

- **Proposal 收尾现在能关闭事项，而不只是改标签。** 四步流程的第四步此前只走了一半：证明能说明晋级
  已进入远端默认分支，但之后没有任何东西收尾，事项长期保持 open，只能靠事后审查发现。
  `/spec-guard:proposal-closeout`（Codex：`spec-guard-ops` 的 proposal 一节）在**同一次运行内**重新取得
  `proved` 之后给出预览，经针对该 Proposal 的明确授权，写一条带稳定标记的收尾记录、把阶段改成
  `proposal-stage:promoted`、关闭事项并读回这三项。
  关闭只说明**设计决定已落地**，不代表模块已交付——收尾记录本身写明了这一点，判据也绝不读模块 stage
  或 todo（有 Plan 无 `todo.md` 的模块按已完成计，刚晋级的模块因此一定「看起来完成了」）。
  只读的 `proposal-promotion-proof` 没有获得任何写入开关，相对发布基线零字节改动。
- **Proposal 的讨论与阶段可以落在本地事项账本。** `local` 与 `github`、`gitlab` 共用同一个纯状态机、
  同一套 `proposal-stage:*` 取值和同一个身份判定，只有适配器不同；`proposal-submit` 与
  `add-module --proposal` 同步支持 `--platform local`，且完成后的草稿与托管路径**逐字相同**。
  因此一个有 Git 远端、但没有可用托管 Issues 的项目也能走完 Proposal。
  **共享事实的来源没有放宽**：baseline 仍然只来自远端默认分支，没有 Git 远端的项目不支持 Proposal。
- **Proposal 事项读取新增开闭状态与三个诊断短码。** 此前 `gh issue list` 只取 number/body/labels，
  连「已关闭」都表达不出来；缺这个字段现在是 `unknown`，**不默认当作 open**。`invalid` 拆出
  `tracker-marker-ambiguous`、`tracker-marker-foreign-container`、`tracker-legacy-marker`，
  调用方得以分别处置而不必去匹配散文诊断。
- **项目级默认事项后端。** `/spec-guard:tracker-default`（Codex：`spec-guard-ops` 的 tracker default 一节）
  查看或按明确确认设置 `.agent/tracker.json` 的 `defaultBackend`（`local`／`github`／`gitlab`）与精确目标，
  省去为一个几个月不变的选择逐次手打参数。它**只预填预览**：预览仍完整显示后端、精确目标与来源，每次外部
  写入仍逐次授权；它不改变已有事项的绑定（只影响此后新建的事项），不是激活信号，也不决定能力图、Proposal
  基线或 Spec/Plan/todo 等共享事实。文档不可用时报 `invalid` 并带稳定诊断码，**绝不降级为「没配过」**。
  设计与取舍见[决策记录](docs/decisions/2026-10-04-tracker-backend-default.md)，它修订了
  `spec/hosted-ticket-workflow.md`「不新增项目级 Tracker 配置」一条。

## [0.40.0] - 2026-10-04

### 变更

- **同机协作只保留 native bridge。** 会话委派、日常邮箱和跨宿主路由不再选择或回退到旧传输；native
  不可用时明确停止。已删除旧守护进程、HTTP／令牌适配器、选择器以及切换和回退工具，保留历史报告与用户
  私有数据库，不自动修改全局 Claude 或 Codex 配置。升级边界见
  [兼容协作传输退役说明](docs/retirements/xats-collaboration-transport.md)。
- **A10 退役门槛按单机单用户现实收口。** 一台 Mac 的双向收发、重复空闲唤醒、native-only 回归和无阻断
  P1/P2 成为当前发布前证据；旧的双版本等待、revision 升级前置和回退演练不再阻止旧传输退役。

### 修复

- **受控会话在宿主边界状态下安全收口。** Claude background 恢复会在最终判断前等待可观察状态稳定，避免把
  短暂缺席误判成最终结果；Codex app-server 明确拒绝请求时返回可诊断的 held 状态，不再落成 unknown 或崩溃。
  这些修复已随 v0.40.0 发布，原发布标签不因本条发布后补记而改写。

## [0.39.0] - 2026-10-04

### 变更

- **A10 native 转正改为单 Mac、多版本实机门槛。** 连续两个发布版本均只需在一台本机 Mac 完成收发、空闲唤醒与回退，不再要求第二台 Mac；上游 revision 升级复验、无开放 native P1/P2、Proposal 人工接受及 XATS 默认状态均不变。GitHub-hosted macOS CI 可补充源码兼容性，但不能替代带真实登录态和目标会话的宿主验收。

### 新增

- **同机 Claude Code／Codex 会话使用统一的双向路由。** 用户按宿主、会话名称和项目描述即可发现并联系目标；Claude 同宿主复用 `ListAgents`／`SendMessage` 和 reply address，Codex 同宿主复用 App task/thread、turn 与 wait/read，跨宿主继续走当前唯一选择的持久 bridge。目录标明 `[Claude Code]`／`[Codex]` 与 `native-visible`／`bridge-joined`；同宿主原生能力不可用时，只有授权有效、bridge ready 且两端唯一加入才显式 fallback，不双写正文。
- **会话通信授权可在流畅度和范围之间明确选择。** 联系既有会话复用当前 task 授权；新建会话默认一次 task，也可由用户选择固定数量 batch 或当前 session。扩项目、扩权、超额、过期和有后果的外部操作仍停止；消息和回复不授予开发权限。

### 修复

- **Claude background 委派能收到首轮 prompt，并可继续真实的 `blocked/idle` 会话。** 创建命令在可变长 `--tools` 后加入参数终止符，避免 prompt 被解析成工具名；第二轮把 Claude Code 2.1.288 的 `blocked/idle` 作为可精确 stop 后恢复的空闲状态，停止后的 `done/null/null` 条目可读回为 `done`。真实 Codex→Claude 双轮、safe-review 写入拒绝与精确停止已通过。
- **授权会话委派把目标结果精确回传给发起会话。** 控制器只接受当前 origin session 唯一绑定的 mailbox 身份，为每轮生成独立 route，并只核对发件人、收件人和 thread/subject 元数据；同步最终回复经路径和内部 ID 脱敏后显示。Claude Code 与 Codex 两个方向的最小真实回传均已通过。
- **同名委派会话可按公开短编号精确操作。** `continue`、`status`、`cancel` 接受列表返回的 6 位 `--disambiguator`；省略短编号时仍拒绝猜测。两个真实同名 Codex 会话已分别按短编号停止。

### 已知限制

- **授权会话委派的候选验收不等于 A10 native 转正。** 2026-10-04 的本机验收已覆盖双向创建、自注册、两轮继续、结果回传、同名消歧和取消，但没有覆盖 XATS 或跨机器；v0.39.0 发布后仍须在安装版上完成单 Mac 的收发、空闲唤醒和回退，才能记作 A10 的 R1，且不据此删除 XATS。
- **统一会话路由只声明已证明的同机语义。** Claude Code 2.1.288 的原生 peer 双向两轮和 Codex App 0.160.0 的同一 task 两轮 wait/read 已通过；Codex 目标 task 主动跨 task 发送仍需该发送 task 的直接人类授权。受控 bridge fallback 的前台双向两轮已通过，但一次 Claude `--background` 临时 MCP 探针因工具未挂载记为环境不可用；XATS 未重复实机验收。

## [0.38.3] - 2026-10-03

### 修复

- **本地事项回复指引禁止回显完整内部 ID。** Claude 的 ticket 命令与共用 skill 明确要求面向用户显示已读取的标题和短编号；完整内部 ID 仅用于写工具参数。契约测试覆盖两处指引，候选源码已通过隔离合成 Claude Code MCP 回复验证；真实账本的已安装宿主回复仍待验收。

## [0.38.2] - 2026-10-03

### 修复

- **拆除项目约定先展示预览。** Claude 的 `/spec-guard:teardown-convention` 先运行 `--dry-run` 并显示将删除的内容；预览失败时停止，实际拆除须在用户看到预览后明确确认。显式传入 `--dry-run` 时只预览。
- **产物校验不再把汇总脚本失败显示成零警告。** 有 Plan 却没有 `todo.md` 的二次汇总运行失败时，`verify-artifacts` 明确提示该项未验证；回归测试确认目标汇总路径执行过且失败会被报告。

## [0.38.1] - 2026-10-03

### 修复

- **托管日常事项评论在 Issue 范围变化后停止使用旧预览。** 预览绑定 Issue 的标题与正文；发布前若内容改变，要求重新核对并预览。已经发布的评论仍可按稳定标记找回，避免不确定响应后重复发送。
- **关闭结果只表述已读回的远端状态。** `verifiedFact` 明确为 `remote-issue-closed`；CI 与验收是否通过仍须在关闭前按真实证据核对，不能由关闭命令的 `verified` 推断。

## [0.38.0] - 2026-10-02

### 新增

- **GitHub/GitLab 普通 Issue 成为显式、按需的日常事项路径。** `hosted-ticket-workflow` 先完整分页查重并复核同根因候选，再以精确目标、可见性、脱敏内容和 digest 取得逐次授权；创建、评论和关闭都保存意图并读回稳定标记，结果未知时不盲目重发。PR/MR 合并后逐项核对覆盖范围、合并提交与真实 CI／验收证据，再记录结论和关闭；Local 事项继续走本地账本，Proposal 生命周期保持只读。
- **项目级审查在有限批次后明确交接缺陷。** 两端项目约定和共享检查点要求报告审查范围、进度、发现项证据与下一停点；审查完成后的“继续”进入查重、事项入账或已预告的修复步骤，不重新泛扫，也不把发现问题冒充为已经解决。

### 变更

- **Local 事项与 GitHub PR 的交付收尾连成一条链。** 已完成工作默认提交可评审 PR；合并后读回 PR、验证证据和 Local 事项，再记录交付结论并按授权关闭，避免代码已进入 GitHub 而本地事项长期悬空。
- **已退役的 Proposal 模块移出当前能力图。** 历史 Spec 与 Plan 保留在 `docs/retirements/`，当前能力图只描述仍受支持的能力。

### 修复

- **审查评估与 Codex smoke 不再接受错误归因。** namespace 评估要求对照基线，宿主 smoke 绑定匹配的会话记录并拒绝模型回显；仓库校验忽略嵌套 Git checkout，避免把外部工作区内容算作当前插件结果。
- **Local 状态与用户回复更完整。** 禁用状态会保留到显式恢复，缺少 `todo.md` 的计数和建议与实际阶段一致，事项回复包含标题，归档检查明确只覆盖本机存储。

## [0.37.0] - 2026-10-01

### 新增

- **移动项目后可显式重绑定 Local 交接日志。** `journal-bind-preview` 只读核对旧分区、Local 历史和旧路径或归档证据；人工确认后 `journal-bind` 原子安装私有指针，发布与归档继续使用原始映射及锁。再次移动沿同一绑定链，循环、断链或额外候选会停止。绑定归档增加可核验的 v2 来源记录，旧 v1 仍可验证与恢复；真实用户日志尚未执行重绑定。
- **本地事项账本增加只读的 `storage-check`。** 检查 Epiq 用户级数据根目录的类型、所有者与 POSIX 权限，报告宽权限、不可用或不确定状态；不读取事项内容，不修改目录、宿主配置或原有 `status` 判据。另有只读 `storage-protect` 预览；获明确授权并加 `--confirm-protect` 后只把符合安全条件的根目录收紧至 0700，不递归改动账本。新生成的宿主 MCP 命令与插件初始化子进程使用 umask 077，首次创建目录默认私有；现有宿主条目不自动迁移。

### 变更

- **Local 事项可离线归档、隔离证明和显式恢复，并可逐项预览 GitHub/GitLab 交接。** 固定 Epiq 1.11.0 的原始事件、待提交文件与媒体按字节校验；真实恢复只进入空 Git 仓库和独立 Epiq 目录。托管交接先生成私有预览，再凭精确目标授权发布，写前记意图、写后按稳定标记读回；响应丢失或人工改动时停止盲目重试。合成事项已在 GitHub 与 GitLab 读回验证；真实账本未迁移，附件尚无法证明目标原字节与权限时保持 `partial`。
- **本地事项账本 `status --format text` 在 `conflict` 时写出占用者。** 除状态行外再打印状态 worktree 路径、占用仓库路径，以及处理办法所在的参考文档；此前这些只出现在 `--format json` 里。
- **Local 事项在开发前受理，并保留变更与关闭证据。** 日常入口先检查状态 worktree，再查重和绑定事项 ID；实质变更先留决定评论，验证通过并获关闭授权后读回状态。受管路径缺失而状态分支在别处检出或不存在时报告 `unknown`，不把它当作空账本；不安全的项目 ID 和受管路径符号链接也被拒绝或标为未知。完整归档与显式迁移仍按独立 Proposal 推进。

## [0.36.0] - 2026-09-30

### 新增

- **阶段提示在 `DONE`／`MODULE_DONE` 时指出未合并的分支提交。** 当前分支有提交不在本地已知的远端默认分支（`refs/remotes/origin/HEAD`，缺省时依次回退 `origin/main`、`origin/master`）里时，追加一行 `This branch has N commit(s) not yet in \`origin/main\` (as last fetched).`，并把建议改为先推送、合并这些提交，再按原建议插入新模块（`MODULE_DONE` 时在原建议前加同一句）。只读且不联网：不执行 `git fetch`，比较的是本地跟踪引用，可能过时；没有远端、没有默认分支引用、分离 HEAD 或 `git` 调用失败时不提示。其余阶段与没有未合并提交时的输出逐字不变，`module_state`／`project_stage` 与 `verify-artifacts` 的判据不变。
- **本地事项账本 `status` 报告状态 worktree 被另一个仓库占用。** Epiq 把状态 worktree 固定在 `<EPIQ_GLOBAL_DIR 或 ~/.epiq-global>/worktrees/<projectId>`，两个仓库共用 `projectId`（如仓库副本）时，后到的仓库每次调用都以 `already exists` 失败。项目已初始化时，`status` 现在带 `project.stateWorktree`（`absent`／`owned`／`foreign`／`unknown`）；`foreign` 时顶层 `state` 为 `conflict`、`diagnostic` 为 `ledger-state-worktree-foreign`、退出码 1，并给出占用仓库路径。其余情况的顶层状态与退出码不变；只读，不移动或删除任何 worktree。处理办法见运行时参考文档与仓库副本迁移记录。

## [0.35.0] - 2026-09-30

### 变更

- **晋级证明被拒时给出具体原因。** `/spec-guard:proposal-promotion-proof` 在晋级提交里的行与 Proposal 声明不符时返回 `promotion-row-mismatch`，并带 `promotionCommit` 与 `mismatchedFields`（`responsibility`、`dependsOn`、`position` 的子集，按此顺序）；行相符但晋级提交还改动了其他模块行或顺序时返回 `promotion-other-rows-changed` 与 `promotionCommit`。`state` 仍为 `invalid`，其余 `invalid` 分支与成功路径的输出不变；`_matches` 改为基于同一个不符字段函数，判断不会分叉。
- **`add-module` 允许在 `spec/<id>.md` 已存在时插入能力图。** 先写 Spec 再插入不再被“已存在，拒绝覆盖”卡住（命令本来就从不写 Spec 文件）。预览与 `--confirm` 的输出会追加一行提示：该模块插入后阶段为 `NEEDS_PLAN`（视为已评审），Spec 尚未评审时应先评审再确认；`--proposal` 路径同样适用。其余校验与写入范围（只写 `spec/CAPABILITY-MAP.md`）不变，Spec 不存在时输出逐字不变。

## [0.34.0] - 2026-09-30

### 新增

- **`/spec-guard:proposal-submit --draft spec/proposals/<id>.md --platform <github|gitlab>`：补全并校验 Proposal 草稿。** agent 按模板写好草稿（基线一节可省略、revision 可为 64 个 `0`），命令从远端默认分支的固定快照生成基线一节并重算 revision，用 `parse_proposal` 与 `validate_proposal` 校验；草稿修改后重跑即重算 revision。草稿路径必须是 `spec/proposals/<id>.md`；远端另一个文件声明同一 id 时拒绝，同一路径已发布则视为修订并提示。先预览，加 `--confirm` 才写回，且只写这一份草稿。最后打印开 Issue 的现成命令（标签 `proposal`、`proposal-stage:published`），命令本身不执行任何远端操作。Codex 的 `spec-guard-ops` 同步提供该入口。

### 修复

- **读取远端 Proposal 快照不再偶发“Directory not empty”。** 快照用的临时裸仓库在 `git fetch` 时关闭自动维护：此前 fetch 返回后会在后台拉起 `git maintenance run --auto --detach`，它可能在临时目录被删除时仍往里写文件，导致 Proposal 评审、预检、晋级与证明偶发 `写入失败: [Errno 39]`。

### 变更

- **Proposal 文档改写为四步（提交、接受、晋级、收尾）。** `docs/workflow.md`、README 与概念文档同步；删除手工计算 revision 的片段，`references/proposal-contract.md` 增加可复制的草稿模板；发版流程不再快进 `integration/mainline`。
- **上游兼容基线更新至 agent-skills 0.6.11（`2686b62`）。** 按 [上游分析](docs/upstream-analysis.md) 的核对清单逐条复核：spec 查找路径、Task List Target、tracker 激活条件均未变，五个缺口仍成立；上游新增的 `/constraints` 与 `constraint-driven-development`、「不覆盖未完成 plan」止损、外部 spec 约定条款均与 spec-guard 不冲突。上游 0.6.10 起不再注册 SessionStart hook，spec-guard 不依赖它。最低上游版本仍为 `5a5ea45`，无需迁移。

## [0.33.0] - 2026-09-30

### 新增

- **`add-module --proposal <id> --platform <github|gitlab> --target <target>`：从已接受的 Proposal 晋级。** id、职责、依赖与锚点全部取自远端已发布的 Proposal，与 `--id`／`--responsibility`／`--depends-on`／`--anchor` 同用即报错；命令内嵌晋级预检（非 `ready` 时原样报告 state 与 diagnostic 并停下），要求本地 `spec/CAPABILITY-MAP.md` 与 `baseCommit` 上的能力图逐字相同（否则提示 `git switch -c <晋级分支> <baseCommit>`），并用证明所用的匹配器自检写入结果，例如锚点位于 Build order 并行段中、写入后无法被证明时直接拒绝。先预览，再加 `--confirm` 写入，只改 `spec/CAPABILITY-MAP.md`，不建分支、不提交、不改标签。不带 `--proposal` 时行为与输出不变；`/spec-guard:proposal-promotion-preflight` 保留为只读预览，Codex 的 `spec-guard-ops` 同步提供该入口。

## [0.32.0] - 2026-09-30

### 移除

- **Proposal 主链裁决层整体删除。** 命令 `/spec-guard:proposal-mainline-candidates`、`/spec-guard:proposal-mainline-review`，hook `proposal_mainline_review.py`、`proposal_boundary_guidance.py` 及其参考文档，以及主链策略文件、验收记录（attestation）、`--authority-id` / `--boundary` / `--current-module-id`、受保护的 `integration/mainline` 分支这些要求都不再存在，也不设过渡版本。说明与迁移见[退役说明](docs/retirements/proposal-mainline-review.md)：已在 accepted 阶段的 Proposal 确认 Issue 标签为 `proposal-stage:accepted` 后直接跑预检；已有的策略文件与验收记录可保留或自行删除，插件不再读取（`scripts/check-acceptance-immutable.py` 仍保护已有验收记录）；原先在模块边界用 mainline-candidates 看候选的，改用 `/spec-guard:proposal-review` 逐个查看。

### 变更

- **接受只看 Issue 标签与评审新鲜度。** 已发布的 v2 Proposal 加上 Issue 标签 `proposal-stage:accepted`，且评审新鲜（基线未漂移、模块还不在能力图中、依赖齐全、锚点有效）即为接受；v1 仍返回 `legacy-revision-required`。预检不再读取主链策略与验收记录，基线漂移时返回 `stale` 与评审的诊断（如 `proposal-baseline-drifted`），通过时 `ready` 并给出 `baseCommit`。`skippedProposals` 保持不变。
- **晋级证明从基线起算，收尾可重复执行。** 证明接受 Issue 阶段 `accepted` 或 `promoted`，从 Proposal 的基线提交起沿远端默认分支的 first-parent 找到第一个纳入该模块的提交，核对该行与声明一致且没有其他模块行被改动，并在其父提交的能力图上判断新鲜度。不再要求该提交同时带 Spec 与 Plan（PR 合并提交可带其他文件）。`reviewCommit` 现在是晋级提交的父提交；新增状态 `stale`（诊断缺省为 `promotion-stale`）。
- **Proposal 池不再读取主链策略与验收记录。** 每个 publication 的 `review_commit` 一律是观察到的远端默认分支提交。

## [0.31.0] - 2026-09-29

### 修复

- **已晋级 Proposal 的基线失效，不再让整个 Proposal 池失效。** 读取 Proposal 池时，若某个 Proposal 能解析、其 `Module id` 已在远端默认分支的能力图里（已晋级），且基线检查（远端与默认分支不符、基线提交不在默认分支上或其基线能力图缺失）或校验失败，就只把它排除，而不是让整个池 `invalid`；典型成因是仓库迁移后，早已晋级的历史 Proposal 的基线提交不复存在。解析失败、尚未晋级的 Proposal 出错、重复 id、能力图缺失或无效、池超出大小上限仍使整个池失效；健康的已晋级 Proposal 留在池中，验收记录与策略摘要不受影响。被排除的 Proposal 按“不在池中”处理：预检 `absent` / `publication-absent`、证明 `absent`、主链决策 `invalid` / `proposal-not-published`。单个评审（`/spec-guard:proposal-review`）仍如实报告其为 `invalid`，可据此查看完整原因。

### 变更

- **晋级预检／证明与主链候选／决策的 JSON 在有 Proposal 被排除时新增 `skippedProposals`。** 形如 `[{"proposalId": ..., "diagnostic": ...}]`，仅在非空时出现，否则输出与此前逐字节一致。`diagnostic` 只有短码 `proposal-baseline-remote-mismatch`、`proposal-baseline-unavailable`、`proposal-invalid`，不输出原始错误；在主链评审里与既有的 `skipped`（候选跳过原因）是两个独立的键。

## [0.30.0] - 2026-09-29

### 新增

- **有 Plan 却没有 `todo.md` 的模块，在会误导的地方给出提醒。** `activeModule` 指向这样的模块时，阶段行（`MODULE_DONE` / `DONE`）多一行提示它因缺 `todo.md` 而按已完成计，仍有活要做就补 `todo.md`；`verify-artifacts` 多一条汇总警告，列出所有这类模块（最多 10 个），不算失败、退出码不变。完成判据本身不变：有 Plan 且没有未勾选项仍算完成。`.agent/state.json` 里 `tracker` 仍是 `github` 或 `gitlab` 的项目（已退役的远端 tracker 模式，任务当时在远端 Issue 里）两处都不提醒。

## [0.29.0] - 2026-09-29

### 新增

- **显式插队：`/spec-guard:add-module --interrupt`。** 当前模块做到一半又在等外部条件时，可以把新模块插到它前面；预览写明被暂停的模块及进度，并在新模块不会成为当前模块时提示改 `activeModule`。其他模块在并行推进（同样做到一半）时也能插队。
- **阶段行新增 `Paused` 行与回到被暂停模块的提示。** 存在被暂停的模块时，`NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MODULE_DONE` 都会列出它；插队模块完成后 `MODULE_DONE` 指回它。
- **Proposal 主链评审接受 `--boundary module-interrupt`。** 与 `module-advance` 同样检查，boundary 不进入验收记录；已有验收记录不受影响。不带 `--interrupt` 时行为与此前完全相同。

## [0.28.0] - 2026-09-29

### 变更

- **阶段行新增 `MODULE_DONE`，`DONE` 现在只表示「全部模块已完成」。** 此前当前模块做完而后面还有未完成模块时也会报 `DONE`，与「全部完成」无法区分；现在前者报 `MODULE_DONE`，并指出 Build order 中第一个未完成的模块及其阶段。全部完成但 activeModule 仍指向已完成模块时报 `DONE`，并提示该 activeModule 可清除。把 `DONE` 当作「全部完成」的用法不受影响。

## [0.27.0] - 2026-09-29

### 变更

- **本地事项账本运行时改用 `npm ci` 按插件自带的 lockfile 安装。** 会逐个校验每个依赖的完整性哈希；安装宁可失败，也不会拉取不同的代码。
- **本地事项账本状态新增 `lock` 字段，标明运行时是否按 lockfile 安装。** 旧方式安装的未锁定运行时仍可照常使用；确认后可用 `install --confirm-install --replace-unlocked` 替换（先在临时目录安装并校验，失败则旧运行时不变），替换后请重启会话。

## [0.26.0] - 2026-09-29

### 变更

- **加入协作默认不再绑定唤醒。** 会话以 `wake: null` 登记；只有你在对话里明确要求被唤醒，且会话没有开着自动批准时才绑定唤醒。
- **协作 Claude 启动器不再把 bearer token 放进 Claude 会话的环境变量。** 启动器改为和 `install-claude` 一样经 stdio 代理连接，token 只由代理从 `0600` 文件读取，并仅出现在 `mcp-remote` 子进程环境里。

### 已知限制

- 唤醒默认值由 `collab` skill 的指令约束，并用措辞回归锁定；上游 bridge 服务端自己的 MCP 说明仍描述
  `wake: "auto"`。以前已经绑定唤醒的身份保持不变，可按运行时说明中的退役命令移除。

## [0.25.0] - 2026-09-29

### 新增

- **主链裁决直接给出可复制的验收记录。** 结果为 `accepted-candidate` 时，`/spec-guard:proposal-mainline-review`
  的输出附带 `attestation`（七个字段，`policyDigest` 已算好）和 `attestationPath`（应写入的路径）。命令仍不写任何
  文件；字段、摘要算法和"合入默认分支后不得修改"的规则见 `references/proposal-mainline-review.md`。
- **晋级证明新增 `not-promoted` 状态。** 晋级分支还没合并时，`--prove` 返回 `not-promoted`（诊断
  `promotion-not-found`），不再和"晋级内容违反声明"一样报 `invalid`。晋级提交现在也可以额外带
  `tasks/<id>/todo.md`（不强制）。
- **Codex 补上 teardown 与历史补正入口。** `spec-guard-ops` 新增 teardown 一节（先 `--dry-run` 预览，确认后才执行），
  history 一节补上 `correct --confirm`；`local-ticket-ledger-ops` 补上账本适配器的 `install-codex` /
  `install-claude` 安装命令。此前 `docs/workflow.md` 声称 Codex 能移除约定，但 skill 里没有这一节。

### 变更

- **晋级预检与证明的 `diagnostic` 改为透传具体原因。** 以前一律是 `promotion-preflight-<state>` /
  `promotion-<state>`，缺 Issue 和缺 Proposal 看起来一样；现在是下层给出的诊断，例如 `tracker-absent`、
  `publication-absent`、`proposal-stale`、`acceptance-attestation-invalid`、`proposal-pool-<state>`。`state` 取值
  不变；只有没有具体原因时才退回旧字符串。**按旧诊断字符串匹配的脚本需要更新。**

### 修复

- **macOS 自带的 Python 3.9 下阶段提示不再是 `UNKNOWN`。** 15 个 hook 模块在类型注解里用了 3.10 才支持的
  `X | None`，在 `/usr/bin/python3`（3.9）下有 18 个模块一导入就失败：阶段提示每轮都是 `UNKNOWN`，
  `/spec-guard:add-module`、协作信箱与本地事项账本的脚本也无法运行。README 现在写明需要 Python 3.9 及以上。
- **快速插入不再假成功。** 能力图在真实模块表之前有代码围栏里的示例表时，`/spec-guard:add-module` 会改写示例、
  报告"已写入"，新模块却没进能力图。现在定位时跳过围栏，并断言新模块确实出现在解析结果里；写入后能力图也保留
  原有权限（以前会从 0644 变成 0600）。
- **历史孤立目录检查覆盖三棵树。** `/spec-guard:history-integrity` 的核验以前只在 `spec/history` 下发现未登记目录，
  `tasks/history`、`.agent/history` 下的未登记证据会被判为通过。
- **原生协作切换的归档不再残留 SQLite 临时文件。** 较新的 SQLite（例如 3.43.2）下，归档目录会留下
  `.messages-*.sqlite-shm`；现在连接显式关闭并清理暂存文件的附属文件，日志模式没切到 DELETE 时拒绝归档。只影响
  实验性的原生切换路径。
- **文档与代码对齐。** `commands/phase.md` 的 `DONE` 含义改为与实现一致（报告的是当前模块，新需求默认用
  `/spec-guard:add-module`）；`spec/documentation-verification.md` 不再声称 `/verify-artifacts` 会显示文档核验结果；
  维护者文档不再引用已删除的变异测试脚本，也不再断言 CI 的运行情况。

### 测试

- 新增 `test_python_compat.py`：静态检查注解写法，并在本机有 3.10 以下的系统 Python 时实际导入每个模块。
- 新增 `scripts/check-command-parity.py`：每个命令引用的 `hooks/` 脚本都必须在某个 skill 里有路由。
- 退役扫描覆盖 `plugins/spec-guard/` 下所有非测试文件；两处"不调用旧 bridge"的否定说明按"路径 + 行文字"放行。
- 晋级证明补上依赖不符、`end` 锚点错位、Spec 头部错误三条判据的反例。
- 本地在 Python 3.10.7 与系统 Python 3.9.6 下都跑通 `validate.sh`、phase-guard 与 verify-artifacts 回归。

## [0.24.0] - 2026-09-28

### 新增

- **快速插入新模块：`/spec-guard:add-module`。** 项目做到一半冒出新需求时，在模块检查点把需求上下文交给 agent，
  它提出新模块的 id、职责、依赖和插入位置并说明理由；命令复用现有能力图解析器校验（依赖存在且排在前面、无环、
  id 合法且不重复），并用 `spec-digest.py` 确认 `## 目标`、已有模块行和已有模块在 Build order 中的先后都没被改动；
  预览改动对比，经你确认后只写能力图。当前模块做到一半、或 `spec/<id>.md` 已存在时拒绝，失败时什么都不写。
  写入后新模块若成为当前模块，阶段为 `NEEDS_SPEC`，照常先写并评审 Spec。Codex 经 `spec-guard-ops` 的 add-module
  一节使用。这是新增模块的默认方式；Proposal 九步保留，需要留痕时选用。
- **全部完成时的阶段提示指向快速插入。** 并注明需要留下经过评审的决定记录时用 Proposal。

### 变更

- **Proposal 在使用者项目里是可选的。** 全部模块完成时，阶段提示此前写「Add new work to the map through a
  Proposal」，读起来像必须走 Proposal。现在改为：新增模块时加进能力图并评审；需要留下经过评审的决定记录时，再用
  Proposal。`docs/workflow.md` 写明两种做法各适合什么场景，README 功能表把 Proposal 标为可选。阶段回归新增一例，
  断言新措辞。

## [0.23.3] - 2026-09-28

### 文档

- **自动批准模式下不要绑定唤醒。** 2026-09-28 受控试验：开着自动批准、以 `wake: "auto"` 登记的空闲 Claude Code
  会话，被另一个本机 agent 的消息唤醒后，未经人工确认就执行了消息要求的命令。`collab` skill 与运行时参考新增指引：
  这类会话改用 `wake: null`，被唤醒后只处理只读请求，试验后退役测试身份。

## [0.23.2] - 2026-09-28

### 修复

- **GitLab 上能找到 Proposal Issue 了。** 读取器此前用 marker 调 `search=`，而 GitLab 的搜索匹配不到 HTML 注释里的
  文字，marker 恰好是一行 HTML 注释。2026-09-28 在一台 GitLab 15.3.2 上只读实测：注释内文字 0/6 命中、正文可见文字
  5/6 命中，所以无论 Proposal Issue 是否存在都会报 `absent`。现在 GitLab 与 GitHub 一样分页列出全部 Issue（最多
  1000 个），在本地匹配 marker；读满上限仍未结束报 `unknown`。对同一实例只读复验：分 2 页完整读完 144 个 Issue。

## [0.23.1] - 2026-09-28

### 修复

- **Codex 从仓库子目录启动时，阶段注入不再消失。** Codex 不提供 `CLAUDE_PROJECT_DIR`，并在会话目录里运行 hook；
  `phase-guard.sh` 此前直接用当前目录判断激活，在子目录里找不到根目录的声明块，于是静默。2026-09-28 在真实 Codex
  上复现：根目录注入 `IDLE`，子目录回复 `HOOK_NOT_RUN`。现在没有 `CLAUDE_PROJECT_DIR` 时先用 git 仓库根目录，
  不在仓库里才用当前目录。回归新增三例：子目录注入、无激活信号的仓库子目录静默、非 git 目录退回当前目录。

### 新增

- **已有验收记录不可改写。** 新增 `scripts/check-acceptance-immutable.py`，经 `validate.sh` 与预推送 hook 运行：
  `origin/main` 上已有的 `spec/proposal-acceptances/*.json` 必须逐字节不变，只允许新增。它防意外改写，不证明作者。

### 文档

- **记录 Codex 不加载插件 `commands/`。** 已核实 codex-cli 0.154.0 的插件组件里没有命令；Codex 用户经 `spec-guard-ops`
  等 skill 使用。写入 `docs/maintainer-workflow.md` 的 Codex 一节。
- **主链评审分支的同步方式。** 两个主链命令说明遇到 `mainline-review-commit-not-ancestor` 时先把主链分支快进到远端默认
  分支；发布流程加入“发布后快进 `integration/mainline`”。本仓库的 `integration/mainline` 已从落后 `main` 107 个提交快进
  到一致，并加了分支保护（禁止 force push 与删除）。
- **定下 XATS 协作传输的日落条件。** native 须先经 Proposal 转为默认；提出该 Proposal 的门槛是连续两个发布版本在
  至少两台主机上实机验收通过、升级一次固定上游 revision 后唤醒仍有效、没有未关闭的 native P1/P2。转正后 XATS 留
  一个 minor 过渡期再删除，保留归档读取与卸载命令。见 `docs/decisions/2026-09-28-xats-sunset.md`。本次不改变任何行为。

## [0.23.0] - 2026-09-28

### 破坏性变更

- **裁剪能力历史里只服务于 initiative 轮换的部分。** 整个插件改用一张能力图后，账本只保存已归档的旧 initiative，
  不再追加生命周期事件。删除 `capability-history.py` 的 `ensure`、`append`、`checkpoint`、`active`、
  `verify-checkpoint`，以及自 `55278e9` 起就没有调用方的 `artifact_history.py`。保留 `validate`、`status`、
  `verify`、`audit`、`correct --confirm`，以及迁移导入要用的 `create`。已有账本的格式不变，核验与审计结果不受影响。

## [0.22.0] - 2026-09-28

### 破坏性变更

- **移除 XATS channel 唤醒实验开关。** 删除 `collaboration_claude.py --enable-channel-wake` 与
  `collaboration_adapters.py claude --include-channel`。它们只在打印的片段和启动器临时配置里生成
  `spec-guard-collaboration-channel` 条目，从未写入持久配置，所以无需清理。Anthropic 的开发通道确认页警告不要用它
  加载下载的 Channel，文档也一直不建议使用，真实 CLI 上从未观察到唤醒。包装器仍拒绝
  `--dangerously-load-development-channels`；Claude CLI 的 tmux 提醒不受影响。

### 修复

- **Codex smoke 认可全角冒号。** 模型复述注入内容时可能写成 `当前阶段：IDLE`，判定此前只匹配半角 `当前阶段:`，会把已执行的
  hook 误判为“无法证明是否执行”。现在两种都算，自检新增全角用例。

### 测试

- **主链验收的 attestation 每个字段都有反例。** 此前只有 `revision` 一个反例，删掉 `reviewCommit` 比对时测试仍全绿。现在
  7 个字段各改错一次，外加多一个字段，都必须判为 `blocked` / `acceptance-attestation-invalid`；逐项删掉 8 处比对，
  测试都会失败。

## [0.21.1] - 2026-09-28

### 修复

- **Codex smoke 不再在用户配置里留下临时目录的信任记录。** `codex exec` 会把运行目录记为受信任项目（实测加 `-c`
  覆盖也照样写入），`evals/codex-plugin-smoke.sh` 删掉临时目录后，`~/.codex/config.toml` 里就多出一条指向不存在目录的
  `[projects."…/tmp.xxxx"]`。现在 smoke 退出时只删除本次新增、且内容只有 `trust_level = "trusted"` 的那张表，原子写回并
  保留文件权限；自检覆盖保留他人条目、带其他键的表不删与权限保持。
- **能力图模板不再引用旧 tracker。** `## 目标` 的注释改为说明它是 Proposal 评审的目标指纹、改写会让已发布的
  Proposal 过期；module id 的定稿说明不再提 `feat/<id>` 分支和 issue 标题。退役扫描新增对模板的检查。

## [0.21.0] - 2026-09-28

### 破坏性变更

- **删除旧 tracker 迁移提示。** `tracker` 为 `github`、`gitlab` 的 `.agent/state.json` 不再触发
  `LEGACY_TRACKER_RETIRED` 提示，改为与其他已启用项目一样报告本地阶段（通常是 `IDLE` 或按模块的阶段）；其中的
  映射仍不被读取。这条提示在 v0.15 退役旧 tracker 时加入，迁移指南原定在下一个 minor 版本删除。

- **退役 Claude Desktop MCPB。** 删除 `manifest.json`、`mcp/claude_desktop_server.mjs` 及其测试、清单检查与文档。它从未
  进入发布流程，本机安装副本停留在 0.7.51。已安装扩展的用户请在 Claude Desktop 的 Settings → Extensions 中卸载；
  阶段与产物检查请改用 Claude Code 的斜杠命令或 Codex 的 `spec-guard-ops`。见
  `docs/retirements/claude-desktop-mcpb.md`。

### 修复

- **XATS 信箱数据库只对本人可读写。** XATS 按调用者的 umask 创建 `messages.sqlite` 及其 `-wal`、`-shm`，
  实测为 0644（所在目录为 0700，因此此前其他用户仍无法进入）。现在 `start` 与 LaunchAgent 使用的 `serve`
  都以 umask 077 启动 XATS，并在启动前把已有的三个文件收紧到 0600；它们若是符号链接则拒绝启动，不跟随链接改权限。
  native 后端的 `bridge.sqlite` 此前已强制 0600，不受影响。

- **hook 入口不再执行项目仓库里的脚本。** `hooks.json` 此前在找不到插件根目录时回退到
  `${CLAUDE_PROJECT_DIR}/.claude/hooks/phase-guard.sh`：任何被打开的仓库只要放一个同名文件，就能让它在每轮提示时
  执行。插件从不向项目写这个文件，Claude Code 提供 `CLAUDE_PLUGIN_ROOT`，Codex CLI 0.154.0 提供 `PLUGIN_ROOT`
  与 `CLAUDE_PLUGIN_ROOT`（2026-09-27 真实 Codex smoke 在不含该文件的临时项目中通过），回退从未被正常路径用到。
  现在只用宿主提供的插件根目录；缺失时注入一条“插件安装或宿主问题”的诊断，而不是静默或改跑项目脚本。
  新增 `test-hook-entry.sh` 直接运行注册的入口命令。

- **检查器覆盖真实调用面。** `check-gh-json-fields.py` 此前只认 `gh <sub> view --json` 命令行写法，而插件里唯一的
  `--json` 调用是 `proposal_tracker_read.py` 中 `gh issue list` 的 Python 参数列表，从未被检查；现在同时检查
  `view`／`list` 与跨行的参数列表写法，并扫描 `plugins/**/*.py`。`check-no-parallel-surface.py` 可传入夹具根目录，
  补了一正两反用例。
- **退役扫描不再假通过。** `test-retire-legacy-tracker-bridge.sh` 改用 `grep` 并区分“无命中”与“扫描出错”：此前缺少
  `rg` 或路径不存在（例如已删除的 `mcp/`）都会被当成无命中。扫描范围加入 `skills/`。
- **`spec-digest.py compute` 出错时退出 1。** 此前读不到或解析不了能力图时仍输出空摘要并返回 0。
- **脚本执行位由校验强制。** 补上 7 个脚本缺失的执行位；`validate.sh` 缺执行位时由警告改为失败。
- **文档与现状对齐。** `CLAUDE.md` 的插件目的改为当前的四项能力；严格串行迁移指南不再引用不存在的
  `/spec-guard:roadmap`、`next`、`deliver`；teardown 的说明不再称 `state.json` 保存 issue 编号映射；
  `history-migration.py` 说明 `import` 会写入；README、`CLAUDE.md` 与维护者流程的验证清单统一为预推送 hook 的三条。

- **setup 与 teardown 不再留下半完成状态。** `setup-convention.sh` 在任何写入之前校验已有声明块，标记重复、缺失或
  顺序错误时拒绝且不建目录、不改文件（此前 `--replace` 只替换第一块，缺 END 时在建好目录后才抛出 traceback）；
  `--replace` 改用受管的 `managed-block.py replace`。setup 与 teardown 都按独占一行识别标记，正文里提到标记不再
  被当作声明块。setup→teardown 往返后指令文件逐字节还原（此前末尾多出一个换行）。`/spec-guard:setup-convention`
  先预览，用户确认后才写入。
- **移除失效的 Claude 协作条目不再超时。** `uninstall-claude` 不再先调用 `claude mcp get`：它会对条目做连接健康
  检查，失效端点实测需 17 秒，超过 10 秒超时后被误报为“无法检查配置”，而这正是最需要移除的情形。现在直接
  运行 `claude mcp remove --scope user`，按其结果区分已移除与本就不存在。
- **Claude 接入遇到同名失效条目时不再超时或误报。** 协作（XATS、native）与本地事项账本的 `install-claude`
  同样不再先调用 `claude mcp get`，直接运行 `claude mcp add`／`add-json`，由 CLI 自己拒绝同名条目并报告
  “already exists”。native 此前在 10 秒超时后误报“无法检查配置”。拒绝规则与 ask 规则仍先于注册写入，
  名称被占用时保留，它们只作用于本服务的工具。
- **协作切换后不再遗留另一套后端。** 新增 XATS 与 native 的 `uninstall-claude`／`uninstall-codex`
  （需 `--confirm-uninstall`）：Claude 经 `claude mcp remove` 移除，Codex 表只有与安装时逐字一致才删除，
  被改过的表拒绝并给出行号。参考文档新增切换与回退检查清单，包括停用 XATS LaunchAgent 与移除旧条目。
- **回退前置条件可以达成。** 新增操作员命令 `native_collaboration_retire.py --name <精确名称> --confirm-retire`，
  经固定版 CLI 以 `--keep-backlog` 退役单个 native 身份；仍有未确认投递时拒绝，不会把未读消息标成已处理。
- **XATS Codex 接入不再崩溃。** `~/.codex/` 已存在而 `config.toml` 不存在时，`install-codex` 不再抛出
  `FileExistsError`。
- **共享检查点规则可达。** `spec-guard-ops` 重新链接 `references/workflow-checkpoints.md`；
  本地约定模板、`/phase` 与 `/verify-artifacts` 让 agent 加载的检查点规则不再指向空内容。
- **Desktop 文档对齐实现。** `docs/claude-desktop.md` 移除已退役的同步预览说明，补充
  `audit_history`，并写明 Desktop 不提供 Proposal、协作与本地事项入口。
- **Desktop 扩展描述。** `manifest.json` 的描述改为只列出实际提供的只读阶段、产物与
  capability history 检查，不再宣称 Proposal 评审与协作能力；Desktop 回归测试守住这一点。
- **账本安装失败不再卡死。** 运行时先装进临时目录、校验通过后才改名到位；npm 失败或包不符时受管目录保持
  `absent`，可直接重试，诊断带 npm 错误输出的最后一行。旧版本失败留下的空目录可被安装接管。
- **Codex 账本配置不再崩溃。** `~/.codex/` 已存在而 `config.toml` 不存在时，`install-codex` 不再抛出
  `FileExistsError`；文件系统错误统一报告为可读诊断。

### 新增

- **Proposal 评审与晋级证明入口。** 新增 `/spec-guard:proposal-review`（任何分支只读查看单个 Proposal 的
  新鲜度与 Issue 阶段）和 `/spec-guard:proposal-promotion-proof`（晋级合并后，从新鲜远端事实重新确认接受，
  再证明 module 按声明纳入能力图）。此前这两步只有库函数，README 承诺的合并后证明没有任何入口。
  Codex 的 `spec-guard-ops` 新增 proposal 一节，覆盖评审、主链候选与裁决、预检和证明；共享检查点规则补充
  模块交付或推进时可用的 Proposal 命令。

### 变更

- **远端默认分支快照只有一份实现。** `read_published`、`read_published_pool` 与 `prove` 此前各自复制了
  “取远端 → `ls-remote` → 临时 bare 仓库 → fetch → 核对 tip”的流程，现在共用 `proposal_publication.fixed_snapshot()`；
  诊断文字与状态不变。`publication` 读取远端 HEAD 时也像 `prove` 一样校验 commit 格式，格式异常报
  “remote default branch is unavailable”。

- **阶段注入按模块判断。** phase-guard 不再在有 Spec 后永远报 `SPECED` 并建议“创建 plan”：它取 `activeModule` 或
  Build order 中第一个未完成的模块，按 Spec、`tasks/<id>/plan.md` 与 `tasks/<id>/todo.md` 的未勾选项报告
  `NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING` 或 `DONE`，并附全局计数；全部完成时建议经 Proposal 追加新模块。能力图无效时
  报告 `MAP_INVALID`，无法计算时报告 `UNKNOWN` 而不是静默。`SPECED` 阶段取消。
- **verify-artifacts 使用唯一的严格能力图解析器。** 不再用自带正则扫描所有表格行：围栏示例或其他表格首列
  中的 id 不再被当作模块；缺少 Build order、依赖未知或成环的能力图现在报 ❌ 并给出解析原因（此前通过）。
  python3 不可用或解析器异常时报「未验证」，不再把合法 spec 全部判成违规。命令说明删去已不存在的 plan、
  issue 与远端检查，并更正退出码 2 的含义。
- **phase-guard 激活信号收窄，缺 python3 不再静默。** 声明块标记必须独占一行（与 `managed-block.py`
  一致），`.agent/state.json` 必须带 `tracker` 为 `none`／`github`／`gitlab`；正文里提到标记、或其他工具的
  state 文件不再让无关项目每轮收到注入。已启用的项目缺 python3 时注入可诊断的 JSON，而不是静默成“未启用”。
- **native 工具面不能静默扩大。** `probe` 要求固定版的工具目录与“邮箱工具＋拒绝工具”完全一致；上游新增
  任何未审查的工具都会让探测失败并报出名称。`collab` 在选择 native 但工具不可用时只报告并转交运维，
  不改用残留的 XATS 工具。
- **本地事项账本高风险工具门控。** `epiq_sync`（推送事项到 Git 远端）、`epiq_project_init`、
  `epiq_skill_install`、项目级删除／移除与贡献者邮箱工具共 10 个，在 `ticket` skill 与命令中改为逐次
  确认；`install-claude` 同时写入用户级 `permissions.ask`，`install-codex` 以 `enabled_tools` 白名单只暴露
  其余 29 个日常工具。已接入的 Claude 可用新增的 `install-claude-guard --confirm-install` 单独补上确认规则；
  Codex 需按参考文档手动加入 `enabled_tools`。Claude 的 `bypassPermissions` 模式会跳过确认。
- **主链评审报告真实原因。** 远端快照读不到时 `proposal-mainline-*` 返回 `unknown` /
  `proposal-pool-unknown`，不再与分支不符一起显示为 `blocked` / `mainline-blocked`；策略缺失、授权 id 不符、
  无上游、本地主链未包含远端提交与 Proposal 不存在各有稳定诊断码。候选列表新增 `skipped`，列出未成为候选的
  Proposal 及原因，空列表不再无法区分“没有 Proposal”与“Proposal 没有 Issue”。
- **Proposal 评审区分缺失的层。** 远端没有该 Proposal 时诊断为 `publication-absent`；Proposal 已发布但
  Issue 缺失或不可读时为 `tracker-absent`／`tracker-invalid`／`tracker-unknown`，并附 proposal id 与
  review commit。

### 测试

- **阶段回归扩到 21 例。** 覆盖 `NEEDS_PLAN`、`BUILDING` 与剩余项数、模块推进、`activeModule` 优先与回退、`DONE` 计数、
  `NEEDS_SPEC`、`MAP_INVALID` 与 `UNKNOWN`。
- **setup 与 teardown 回归。** 新增 `test-setup-teardown.sh`（14 例）并接入 `validate.sh`：覆盖预览、首次安装、
  重复安装、`--replace`、无效标记、正文提及标记、往返逐字节还原、`--keep-state`、未启用项目与 Codex 主机。
- **协作运维回归。** 覆盖 Codex 表的逐字删除与拒绝（改动、追加键、重复、带引号子表、符号链接）、XATS 与
  native 的安装→卸载往返、退役命令的未读拦截与结果核验；拒绝清单与邮箱工具清单改为逐字写死，不再用被测
  常量验证自己。
- **检查点规则可发现性回归。** 任何提到共享检查点规则的命令、skill 或模板都必须能到达它。
- **Claude Desktop MCP 回归恢复。** `test-claude-desktop-mcp.sh` 按当前 5 个工具重建并进入
  `validate.sh`：核对每个工具分派到对应 hook、hook 失败以 `isError` 返回、已移除的
  `sync_map_preview` 被拒绝。`check-manifests.py` 同时核对 Desktop `manifest.json` 的名称与版本。
- **history 回归不再假绿。** `test-history-verification.sh` 与 `test-history-migration.sh`
  改为任一断言失败即退出并报告行号；此前只有最后一条命令决定结果。
- **Proposal 入口回归。** 晋级证明 CLI 以本地 bare 远端跑通“发布 → attestation → 晋级提交 → `proved`”，
  并覆盖未接受、仅有 accepted 标签而 attestation 不匹配、Proposal 缺失、远端不可达，以及不带 `--prove` 时只做
  预检；评审 CLI 覆盖组合、未发布时不读
  tracker 与 GitLab 数字项目 id。
- **verify-artifacts 回归从 1 正 1 反扩到 8 例。** 覆盖围栏与第二张表、无效能力图、缺 python3 和解析器异常。
- **命令名检查器的反向用例改用夹具。** “上游删除 `/plan`”一例此前依赖仓库文案恰好提到 `/plan`，文案一改就
  失去检测能力；现在在临时夹具中引用 `/plan`。
- **phase-guard 回归从 3 个场景扩到 9 例。** 每条输出都按 JSON 解析并核对事件名；覆盖无关 state、正文提及
  标记、CRLF、IDLE 与缺 python3。
- **主链评审 CLI 端到端回归。** 首次覆盖 `main()` 的两种模式，以及各层失败的诊断码与 Git 拓扑判定。
- **账本运行时回归进入 `validate.sh`。** 以会真实写入 `--prefix` 的假 npm 覆盖成功、失败后重试、包不符、
  接管空目录与拒绝非空无效目录；可选验收测试缺少运行时时以退出码 2 表示“未运行”，不再与通过混淆。
- **账本适配器回归进入 `validate.sh`。** 覆盖 Codex 白名单、Claude ask 规则合并与畸形配置拒绝；`ticket`
  契约测试要求日常入口点名全部门控工具。

### 说明

- **全插件一张能力图。** `spec/CAPABILITY-MAP.md` 改为整个插件唯一的能力图：保留原有 7 个 Proposal 模块与
  `collaboration-messaging`，目标改写为产品级，并在末尾登记 `local-ticket-ledger`（既有能力的一次性人工登记，
  未经 Proposal 流程）。新需求经 Proposal 按锚点插入模块，不再为每个需求另建一张图。同日较早的“按 initiative
  分图”方案（归档为 `proposal-lifecycle`、另建 `local-collaboration`）已撤回，历史账本恢复原状。README 与设计文档
  写明可选的协作邮箱与本地事项账本，二者都不替代、不同步 GitHub/GitLab Issue。随后补登 6 个更早交付的模块：
  本地约定、阶段注入与产物校验、能力历史、文档基线／影响／核验，各有当前模块 Spec 与登记型 Plan。决策见
  `docs/decisions/2026-09-28-single-capability-map.md`。

## [0.20.1] - 2026-09-27

### 修复

- **本地阶段提示。** 首个模块 Spec 尚未建立时，提示中的 `spec/` 保持为字面文本，
  不再被 shell 当作命令执行。

### 变更

- **公开安装来源。** Marketplace 与插件元数据改指向
  `haigeerlab/spec-guard-plugin`；已有安装需要重新添加该来源以接收后续更新。
  历史 `v0.20.0` tag 保持不变。

## [0.20.0] - 2026-09-27

### 新增

- **实验性原生跨会话唤醒。** Claude Code 与原生 Codex Desktop 在同一台 Mac 上可经显式安装、
  受控切换后使用同一个持久邮箱，按名称收发消息，并在宿主支持时唤醒空闲会话；同项目与跨项目
  往返均已完成实机验收。普通安装和日常 `collab` 不会自行安装运行时或切换邮箱，未选择 native
  的用户继续使用 XATS。

### 说明

- 原生唤醒依赖宿主私有接口，仍属实验功能；唤醒失败不代表消息丢失，收件人实际读取并确认后
  才能称为已处理。切换与回退必须单独确认旧会话和未读消息，保留原邮箱归档。ChatGPT in Chrome
  与 Claude Code in Chrome 的原有配置不因协作功能而改变。

## [0.19.1] - 2026-09-25

### 修复

- **本地事项短编号写入指引。** `ticket` skill 与 Claude Code 的 `/spec-guard:ticket` 命令入口
  明确要求在评论、关闭等写入前解析完整事项 ID，避免将短编号直接传给 Epiq 写工具；命令入口
  同时要求仅在写工具确认成功后报告完成。

## [0.19.0] - 2026-09-24

### 新增

- **本地事项日常入口。** 在已启用本地账本的项目中，可用 Claude Code 的
  `/spec-guard:ticket` 或 Codex 的 `ticket` skill 以自然语言查询、创建、讨论和关闭事项；
  Claude Code 与 Codex 共用当前仓库的账本，同机 linked worktree 也可读取同一事项。
- **事项与联调消息衔接。** 用户指定收件人时，Agent 可先记录事项，再通过协作邮箱按名称通知对方，
  分别报告事项写入与消息投递结果；跨仓库消息会附来源项目和摘要，不假定对方能直接读取本仓库账本。

### 说明

- 日常入口不会隐式安装、初始化或修改宿主配置；本地账本尚未启用时仅做只读诊断。

## [0.18.0] - 2026-09-24

### 新增

- **一步加入本机联调。** Claude Code 与 Codex 会话现在可通过 `collab [可选别名]` 或“加入本机联调”
  完成当前会话注册、读取收件箱并发现联系人；用户不再需要填写 team、PID、agent type、项目路径或 MCP
  工具名。
- **按人类名称安全通信。** Agent 可根据别名、项目简称、宿主和自由工作描述理解“告诉可乐……”等请求，
  只在唯一匹配时发送；无匹配会提示对方先加入，多匹配只请求一次最小澄清，不引入项目分组或固定路由框架。

### 变更

- **日常使用与运维操作分离。** `collab` 只处理加入、收件和发信；初始化、启动、配置与精确清理仍由
  `collaboration-ops` 显式执行。原生 Codex Desktop 继续使用持久邮箱模式，保留 ChatGPT in Chrome，
  且不会把“消息入箱”夸大为实时唤醒或已读。

## [0.17.0] - 2026-09-18

### 新增

- **本机 Agent 协作邮箱。** Claude Code 与原生 Codex Desktop 可在同一台 Mac 上通过私有、
  loopback-only 的持久邮箱交换自由文本技术消息。会话只提供显示用自我介绍，不建立项目组、
  自动路由或任务所有权；Git、Issue 与 Ticket 仍不受此能力写入。
- **显式且无密钥的宿主接入。** 可选 LaunchAgent 维持固定版 XATS 运行时；Claude 的用户级
  stdio bridge 与 Codex 的动态请求头 helper 都不把 bearer token 写入项目或宿主配置。原生
  Codex Desktop 保持邮箱模式，因此 ChatGPT in Chrome 可继续使用。

## [0.16.6] - 2026-09-17

### 修复

- **Promotion 后证明。** post-merge proof 改用 acceptance attestation 绑定的历史
  review snapshot 验证首次能力图插入；preflight 仍要求 promotion 前的当前能力图与
  该 snapshot 完全相同。此前 promotion 本身会被错误当作 acceptance stale。

## [0.16.5] - 2026-09-17

### 修复

- **Proposal 接受证明可落地。** acceptance attestation 现在绑定其写入前的已评审
  远端快照，而 promotion base 仍取最新远端 main；仅当 Proposal、能力图和主链策略
  自该快照起完全未漂移时才认定该证明有效。此前 attestation 必须引用包含自身的 Git
  提交，形成不可满足的自指哈希约束。

## [0.16.4] - 2026-09-17

### 修复

- **私有 GitHub Proposal Issue 发现。** 主链评审改用仓库范围的只读 Issue 列举，
  不再依赖在已认证私有仓库中可能返回空结果的 Search API。若列举恰达 1000 条读取上限，
  则保守返回 `unknown`，不遗漏候选也不自动接受。

## [0.16.3] - 2026-09-16

### 修复

- **Codex 迁移命令根目录。** 所有会被 Codex 自动迁移的只读命令现在优先使用
  Claude/Codex 提供的插件根目录；若两者均不可用，则只读解析已启用的 Codex 插件清单。
  `phase` 与 `verify-artifacts` 不再链接到迁移目录中不存在的相对 checkpoint 文件。

## [0.16.2] - 2026-09-16

### 迁移

- **公开来源恢复。** 公开 marketplace、插件作者与主页迁回
  `yizhongkaimail-collab/spec-guard-plugin`。这是在原公开来源不可访问后的连续性恢复，
  不重写既有 Git 历史、Issue 或发布证据；已缓存的旧安装可继续运行，但后续更新需手动重加
  marketplace 来源。

## [0.16.1] - 2026-09-16

### 修复

- **主链本地观察边界。** mainline review 现在只接受固定观察 kind，且 module id
  必须关联当前模块或 Proposal 声明的模块、依赖、锚点；自由文本或无关 id 会保守
  返回 `invalid`，不能进入可审计 reason code。

## [0.16.0] - 2026-09-16

### 新增

- **主链 Proposal 评审。** Proposal v2 将文档内容绑定 revision，并由远端
  policy、当前 worktree Git 拓扑、受限本地观察和显式人工裁决共同限制
  accepted-candidate。普通提出支路只能发布和读取，不能自行接受。
- **晋级前后证明。** revision-bound attestation 与 accepted Issue 阶段共同
  作为 fresh preflight 前提；promotion proof 额外验证首次能力图插入、模块
  Spec、Plan 与严格文件 allowlist。
- **显式只读命令。** 新增 mainline candidates、mainline review 与 promotion
  preflight 入口；它们不创建或修改 tracker、分支、能力图或任务。

### 迁移

- 已发布 v1 Proposal 保留可读，但不能接受或晋级；仍相关的需求须由人工发布为
  v2 revision，并走主链评审流程。

## [0.15.1] - 2026-09-16

### 修复

- **GitHub Proposal Issue 读取。** 兼容 GitHub Search API 的
  `repository_url` 响应形状；此前真实 Proposal Issue 会被保守降级为
  `unknown`，从而阻断 review 与 promotion proof。

## [0.15.0] - 2026-09-15

### 破坏性变更

- **Legacy GitHub/GitLab tracker bridge。** 移除远端任务投影、选择、worktree
  binding、交付与 Desktop 同步预览，以及对应命令、skills、hooks、模板和测试。
  现有 state、远端对象与归档保持不变；升级前请按迁移指南完成、放弃或保留在途工作。

### 变更

- **本地约定与 Proposal 边界收紧。** setup 仅支持本地多模块目录约定；phase/verify
  只做本地结构检查，并对遗留 tracker state 给出无副作用的迁移提示。Proposal 继续只读。

## [0.14.0] - 2026-09-15

### 新增

- **只读 Proposal 生命周期。** 新增版本化 `new-module` Proposal 契约、远端默认分支发布快照、GitHub/GitLab Proposal Issue 只读核验、基线新鲜度评审、first-parent 晋级证明，以及仅在模块交付/推进边界给出的非阻断入口提示。
- **共享事实与写入边界收紧。** Proposal 只接受远端默认分支的能力图事实；不使用其他 worktree 或未提交文件，不依赖 `spec-github-bridge` 或 `/sync-map`，也不自动创建或修改 Issue、PR、分支、任务或 `.agent/state.json`。

### 变更

- **归档记录的仓库身份绑定到 Epic 编号。** 归档快照新增 `initiative.repositoryIssue`，记录写入 `repository` 那一刻的 Epic 编号；若 `resume` 后 Epic 编号变了（例如在另一个仓库重建），下一次归档会发现两者对不上，重新从 origin 解析仓库身份。没有这个字段的旧快照（v0.13.0 写出）仍保留原 `repository`，并在下一次归档时补上当前 Epic 编号。已知限制：这类旧快照如果被 `resume` 后在另一个仓库重建 Epic，补记的是新 Epic 编号，因此会一直被记到旧仓库，不会自动纠正。phase-guard 把「存在但对不上」的 `repositoryIssue` 视同缺少仓库身份，不再核验。

### 修复

- **归档记录仓库身份认得更多 GitHub origin 写法。** origin-URL 解析提取为可导入的 `github_remote.py`，新增识别尾随斜杠（`.../Owner/Repo/`）、大小写不敏感的 `.git` 后缀（`Owner/Repo.GIT`）与不带用户名的 scp 别名（`alias:owner/repo`）；此前只有带用户名的 `user@alias:owner/repo` 能解析。
- **清理失败回滚不再泄漏归档改写。** `tracker=github` 归档会把 `initiative.repository` 写回快照；若随后清理当前产物失败，回滚现在恢复改写前保存的原始字节，而不是那份已被写回仓库身份的快照，不再把归档的副作用带回当前 `.agent/state.json`。
- **归档快照字段含控制字符时整条判不可读。** `archived_completed_trackers` 用 `\x1f` 分隔单行记录；若 tracker/issue/repository 或 initiative id 混入 `\n`、`\r` 或 `\x1f`，会撕裂那一行、被拆成错位记录进而拼出看不出归属的空 tracker 条目。现在整条记录直接标记为 `__snapshot_unreadable__`，不再产出畸形条目。

## [0.13.0] - 2026-09-14

### 变更

- **归档记录 GitHub 仓库身份。** 归档快照写入 `initiative.repository`（`owner/repo`），远端核验只查询该仓库，仓库迁移或 origin 变更后仍核验原 Epic。
- **旧归档不再按当前 origin 核验。** 缺少仓库身份的历史快照报告“无法核验（缺少仓库身份）”，不调用 `gh`；历史快照不改写。
- **永久无法核验的归档不再卡住阶段。** 归档时未记录仓库身份、或没有 Issue 编号的条目单独报告为“无法核验”；当归档中只剩这类条目时，阶段为 `IDLE (已归档，部分无法核验)`，不再建议开启远端核验（#20）。
- **归档快照不可读时指向历史审计。** 归档状态快照缺失或损坏时，下一步改为先用 `/spec-guard:history-integrity` 做只读审计，不再建议开启远端核验。

## [0.12.0] - 2026-09-13

### 破坏性变更

- **移除并行工作流。** 不再提供 `parallel-*` 命令、worker/worktree/lease 运行时或并行边界分析；模块只能按 Build order 串行推进。

### 变更

- **保留上游能力图格式兼容。** `Build order` 的逗号分组仍可解析，但会依书写顺序展开为单模块串行步骤，不构成并行授权。

### 修复

- **生命周期清理失败不再伪造成功。** 清理当前产物失败时恢复已删除内容，并且不写入生命周期事件、账本或 checkpoint。
- **GitHub 子任务查询有时限。** UserPromptSubmit hook 最多等待两秒；超时保守降级，不阻塞会话。
- **历史补正进入审计结论。** 追加式 `history-correction` 现在会标记对应 finding 为 `corrected`；原始证据仍保留，摘要单列未解决项。

## [0.11.3] - 2026-09-13

### 修复

- **归档 GitHub 核验兼容 SSH host 别名。** 远端核验现在从 `origin` 明确传递
  `owner/repo` 给 `gh`，不再依赖别名 host 推断认证上下文；已合并的 Pull Request
  也会正确视为终态，不再误报为“待核验”。

### 变更

- **维护者入口收敛。** 源码仓库的 agent 指引拆分为维护工作流和发布流程文档，移除已弃用的
  Superpowers 设计/计划资料。

## [0.11.2] - 2026-09-13

### 修复

- **路线图远端证据诊断。** `/spec-guard:roadmap` 区分 GitHub CLI 认证/凭据不可用与 GitHub API 网络不可用；两种情况均保留本地路线图，并把远端事实保守标为未知。
- **Codex 路线图命令前置检查。** GitHub tracker 模式先检查 `gh` 登录状态；共享检查点规则改由插件根目录的绝对路径读取，避免迁移后的相对路径失效。

## [0.11.1] - 2026-09-12

### 修复

- **迁移后的安装来源。** Claude Marketplace、Claude/Codex 插件清单与 README 现在都指向 `haigeer-labs/spec-guard-plugin`，避免新安装继续读取旧账号的仓库。

## [0.11.0] - 2026-09-10

### 修复

- **能力图表格边界。** 指纹和产物核验只读取唯一的模块表，不再把检查点等辅助 Markdown 表误判为未投影模块。

## [0.11.0-rc.1] - 2026-09-10

### 新增

- **声明式文档治理。** 可显式建立项目级文档基线，并在模块 Spec、Plan 与交付前分别记录文档影响、计划交付物和声明结果；不以代码、Git diff 或时间戳反推文档真相。
- **保守交付提醒。** `documentation-baseline`、`documentation-impact` 与 `documentation-verification` 提供预览优先的只读查询；`verify-artifacts` 汇总未决或延后项，但不把它们伪装为内容验证或已发布证明。

### 已知限制

- 文档交付状态是模块的显式声明；它不替代文档内容审阅、代码验证或已发布证明。

## [0.10.0] - 2026-09-09

### 新增

- **按需工作流路线图。** `/spec-guard:roadmap`（以及 Codex 的同名只读操作）先展示
  agent-skills 的正常生命周期，再展示唯一活跃 Initiative 的当前模块、显式依赖/后继、下一行动、
  检查点、完成边界和 Git/worktree 上下文；`--all` 只展开活跃能力图。
- **路线图不制造伪进度。** 任务数不是总工作量；不计算百分比或 ETA，不把分支、worktree、端口或
  计划文字当作执行授权、模块绑定或完成证据。缺失或不可读取的事实保留为未知。
- **紧凑阶段摘要补充执行位置。** `/phase` 现在区分 primary checkout 与 linked worktree，并显示
  attached branch 或 detached HEAD；完整路线只在用户按需调用时生成。

### 已知限制

- 0.10.0 的安装与真实宿主验收尚未完成；源码/包校验不能替代新会话加载、hook trust 与实际命令调用。

## [0.9.0]

### 本地工作流与产物一致性

- 正确识别尚未激活 tracker 的本地验证阶段；setup-convention 提供显式上下文预览/写入，GitLab 直接同步入口同样拒绝本地阶段。
- 图外 spec 按历史内容已验证、历史归属可证但内容未验证、真正无归属分别报告；本地 pause/resume 保存图中已有 spec/plan。
- 阶段交接、失败、授权和取消使用共享检查点预告规则，已有授权不重复询问。
- 本地 setup 从子目录调用时正确解析项目根目录；显式 CLAUDE_PROJECT_DIR 仍优先。

### Tracker、历史与安全边界

- **GitLab tracker 恢复、worktree binding 与 `/next` 选择收紧。** 能力图投影仅从完整 marker
  恢复；每个 worktree 显式保存本地 tracker/module/task context，复制或失配即停止。GitLab
  `/next` 只按计划 IID、完整 marker、远端 opened 状态、assignee 与本地 closing commit 选择；
  binding 不是 lease，且不启用自动并行或真实实例写入 E2E 声明。
- **统一严格能力图与边界诊断。** 并列 Build order 现由共享解析器验证，GitLab 同步、Desktop
  预览及 GitHub/Codex 新建入口共享其顺序和失败语义；旧摘要的表格行序兼容语义不变。
  并行候选仍只代表 Depends on 依赖层，未核验任务状态或运行资源，不能立即领取或执行。
- **收紧人工并行边界检查。** 路径按组件比较并保留原始/规范值；非法路径、空声明、链接、
  权限、大小写/Unicode 别名和无项目上下文都保守降级。文本与 JSON 均保留冲突和不确定原因，
  非 eligible 组不生成 worker 建议，不解除 `PARALLEL_WRITES_DISABLED`。
- 暂停实验性并行写入口：run/lease、worktree、CLI Agent 启动、Desktop 登记、汇合与回收均返回
  `PARALLEL_WRITES_DISABLED`，保留已有资源；普通串行与只读候选分析继续可用。
- 旧 run/worker/process 读取校验文件名、身份关联和路径；查询失败返回非零。旧 completed 显示
  unverified 并保留 recordedState，宿主管理不等同于可回收。
- 升级不停止旧进程、不接管已加载旧版本的会话。先保存成果、核对任务并由用户决定停止或重启，
  确认新版本加载；不自动清理旧 ledger 或 worktree。不构成四端原生 E2E 验收。
- **历史与发布证据完整性。** 历史语义审计、证据补正与发布验收记录分层验证，包清单校验不替代安装或宿主实测。

### 开发验证

- **隔离 pre-push 的 Git 仓库环境。** 检查运行前清除仓库级环境变量，避免临时仓库测试修改真实仓库的 bare、身份或 remote 配置；任一检查失败仍阻止推送。
- 已完成源码五项规定回归、候选包内容核对与本地夹具验证。pre-push 新增普通 checkout、linked worktree 和检查失败阻断的真实本地 Git push 回归。
- 已安装的旧 pre-push 需要显式重新运行 `scripts/install-git-hooks.sh` 才能更新；拉取源码不会自动替换已安装 hook。

### 已知限制

- 安装、真实宿主交互与真实项目尚未完成 0.9.0 验收；静态规则引用测试与 smoke 自检不是宿主行为证明。
- 无内容快照的旧 spec 仅能证明历史归属，不能证明内容未改变。
- 自动并行执行器继续暂停，不因版本升级恢复；保留旧资源，不自动停止进程或清理 worktree。

## [0.8.0] - 2026-09-04

### 新增

- **并行开发就绪度与只读子代理预检。** 能力图可识别无依赖候选、边界冲突与
  build order 歧义；在用户确认后，可由 Codex 原生子代理并行进行只读预检。
  它不会自动创建 worktree、分支或并行写入，结论由父任务汇总后再由用户决定实施方式。

### 修复

- **GitLab `sync-map` 的状态写回稳定化。** Initiative 标题与 Issue IID 立即写回
  state，模块映射不再覆盖 `activeModule`，完成后始终按能力图 Build order 选取首个模块。
- **GitLab 15.3 合并短暂 422 的安全重试。** 首次失败后仅在 MR 仍开启、
  `can_be_merged` 且无冲突时重试一次；其他失败保持中止，不绕过保护。

### 验证

- 在真实 GitLab 15.3 项目完成 Issue/MR、`relates_to` 降级关联、状态同步、
  合并重试与清理的端到端验证；完整本地校验通过。

## [0.7.51] - 2026-09-04

- **修复已归档项目的 phase 误报。** 当合法 capability history 证明所有 Initiative
  都已终态结束时，遗留 module spec 现显示为 `IDLE (已归档)`；没有有效终态账本的
  缺失 state 仍会报断链。

## [0.7.50] - 2026-09-04

- **新增 Claude Desktop MCPB 入口。** 以官方 MCP Bundle 分发只读 `phase`、验证、history
  检查与 GitHub/GitLab/local `sync-map` 预览；桌面端不会执行任何本地或远端写入。
- **四端权限模型已明确。** Claude Code CLI、Codex CLI 与 Codex 桌面端保留显式确认写入；
  Claude Desktop 必须切换至其中之一执行写操作。

## [0.7.49] - 2026-09-04

- **Codex GitLab `sync-map` 与 Claude 统一。** `spec-guard-ops` 直接调用确定性预览/
  确认脚本，不再依赖模型转述 bridge。

## [0.7.48] - 2026-09-04

- **GitLab `sync-map` 现为确定性安全入口。** 默认预览 Initiative 与模块 Issue；仅显式
  `--confirm` 才创建远端 Issue 并写回 state。标准能力图的目标段与模块表已在真实 GitLab
  仓库完成零写入预览验证。

## [0.7.46] - 2026-09-04

- **修复 Claude tracker 命令缺少执行权限。** `sync-map`、`next` 与 `deliver` 显式声明
  `Bash`、`Read`、`Write`，使 bridge 规则可实际读取产物、调用 tracker CLI 和写回 state。

## [0.7.45] - 2026-09-04

- **修复 Claude tracker 命令可能静默结束。** `/spec-guard:sync-map`、`next` 与
  `deliver` 现在明确要求加载对应 GitHub/GitLab bridge、执行指定操作，并在远端写入前
  列出影响和请求确认，不能只复述路由规则。

## [0.7.44] - 2026-09-04

- **修复 Claude Code 的插件命令入口。** Claude 当前版本会将插件命令注册为
  `/spec-guard:<command>`；README、注入的 `CLAUDE.md` 模板和 hook 的下一步建议已统一使用
  命名空间形式，避免显示“Unknown command”。

## [0.7.43] - 2026-09-04

### 修复

- **`/verify-artifacts` 现只读核对 GitLab state 映射。** 已认证时逐条确认 initiative 与模块 Issue 可读取，并警告活跃模块已关闭的状态；认证、项目读取或 API 查询失败明确标为未验证，不误报为缺失。

## [0.7.42] - 2026-09-04

### 修复

- **`/verify-artifacts` 现检查 GitLab 的本地映射一致性。** 能力图指纹、模块 Issue 映射和 `plan.md` 的远端 Issue 索引不再仅限 GitHub；不支持远端映射的 tracker 仍明确跳过。

## [0.7.41] - 2026-09-04

### 修复

- **GitLab 初始化现在先验证 `glab`。** 未安装、未认证或无法读取当前 GitLab 仓库时不再写入 `tracker=gitlab`，避免留下后续必然失败的半初始化状态。
- **GitLab bridge 补齐完整工作流协议。** 明确 `sync-map`、任务落库、`next`、模块级 MR 交付、状态增量写回和 capability history 的安全顺序；`relates_to` 始终只作降级关联。
- **文档、模板与插件简介三方一致。** README 提供 GitLab 手动模板、前置条件及 Codex 参数；同步检查现在覆盖 GitHub、GitLab 和本地模板。

## [0.7.40] - 2026-09-04

### 修复

- **GitLab 支持矩阵与已知限制已同步实现。** README 现在明确 GitLab 的 Issue / Merge Request 任务流，以及 GitLab 15.3 下平面 Issue 与 `relates_to` 的边界。

## [0.7.39] - 2026-09-04

### 修复

- **`/next` 命令说明与实际路由一致。** 用户可见描述不再错误地限定 GitHub，明确从当前 tracker（GitHub、GitLab 或本地）取任务。

## [0.7.38] - 2026-09-04

### 修复

- **GitLab 的下一步不再被误导为不受支持。** `PLANNED (gitlab)` 现在会路由到
  `spec-gitlab-bridge`，并以 state 中的模块 Issue 与 GitLab `opened` 状态作为进入
  `/build` 的判据。

## [0.7.37] - 2026-09-03

### 新增

- **GitLab 初始化覆盖 Claude Code 与 Codex。** `setup-convention gitlab` 现在会为两种宿主写入 GitLab Issues 事实源与 `spec-gitlab-bridge`，不再只支持 Codex。
- **tracker 路由一致化。** Codex 运维 skill、命令提示和禁用 state 恢复提示现在统一覆盖 GitHub、GitLab 与本地模式。

### 修复

- **已有历史台账的新 initiative 可正常归档。** lifecycle 会先将缺失的 initiative 原子登记到已有 ledger，再追加终态 checkpoint；不会再留下未登记的归档目录。

### 验证

- 在自建 GitLab 15.3 项目实测 Issues、Merge Requests、SSH Git 操作和 `relates_to` 关联；平台缺少原生父子/阻塞语义时明确降级，不伪造依赖关系。
- 完整校验通过；Claude Code 与 Codex 的 GitLab 初始化回归均通过。

## [0.7.36] - 2026-09-03

- 修复 GitLab 初始化后的下一步提示，改为 GitLab Issues 与 GitLab bridge 流程。

## [0.7.35] - 2026-09-03

- 新增 `setup-convention gitlab --host=codex`，可在 GitLab 项目初始化 Codex 约定。

## [0.7.34] - 2026-09-03

- 新增 GitLab tracker 自动探测、GitLab bridge 与非交互安全保护。
- GitLab 15.3 使用平面 Issue、`relates_to` 与 Merge Request；明确降级缺失的层级和阻塞语义。

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.7.33] - 2026-09-03

### 修复

- **pause 后可以真实恢复完整工作区。** lifecycle 在 checkpoint 成功写入后，会一并移除 state 所列模块的当前 spec 与 plan；此前它们残留在工作区，导致 `resume` 为避免覆盖而拒绝恢复。

## [0.7.32] - 2026-09-03

### 修复

- **新 initiative 的首次归档可自举历史账本。** 当 `pause`、`complete`、`abandon` 或 `supersede` 发现账本尚未建立时，lifecycle 会从当前完整产物先原子创建 `created` checkpoint，再追加目标事件；`resume` 仍拒绝无历史账本的工作区，避免凭空恢复。

## [0.7.31] - 2026-09-03

### 修复

- **最后模块交付后 initiative 不再悬空。** `/next` 的最终收口规则现在要求显式关闭 GitHub Epic，再写 completed 历史 checkpoint、归档产物并清空活跃模块；lifecycle hook 保持离线且不直接写 GitHub。

## [0.7.30] - 2026-09-03

### 修复

- **模块内 task 依赖不再被模块级 PR 卡死。** `/next` 现在将当前模块分支中已通过 closing keyword 完成的 task 同时视为“不可重复领取”和“已满足的前置依赖”。因此前置 issue 尚未随模块 PR 合入而关闭时，后续 task 仍可继续执行。

## [0.7.29] - 2026-09-03

**能力图历史从一次性快照成为可验证、可迁移的生命周期。**

### 新增

- **能力图历史账本与校验。** 为 initiative 保存不可变 checkpoint，并校验历史能力图、模块 spec 与计划文件的 SHA-256 证据；非法事件序列或被篡改的历史证据会被拒绝。
- **生命周期操作。** 支持安全地暂停、恢复与完成 initiative：先原子写入 checkpoint，成功后才清理当前产物；恢复只从最后一个暂停 checkpoint 还原。
- **历史迁移与工作流集成。** 可预览并确认导入既有能力图证据，历史操作进入共享工作流；迁移会保留或补回 canonical `spec/CAPABILITY-MAP.md`，使后续生命周期操作始终有规范来源。

### 修复

- **暂停归档不再遗漏模块产物。** lifecycle 现在会归档全部已记录模块的 spec 与计划，而不是仅处理活跃模块。
- **私有 GitHub 仓库的任务依赖不会被误判为无阻塞。** `/next` 在依赖汇总字段不足以证明无阻塞时，逐项查询开放阻塞者；已关闭阻塞者不影响可选性。

### 验证

- 新增并运行历史账本、生命周期、验证与迁移回归，涵盖原子性、损坏 checkpoint、完整模块归档、canonical map 迁移与私有仓库依赖查询路径。

### 已知限制

- 真实宿主验证仍依赖已登录的 Claude Code / Codex 与本机 hook 信任状态；该环境未就绪时 smoke 检查会明确返回“未就绪”，不把环境错误判为产品失败。

## [0.7.28] - 2026-08-30

**插件在最需要它的那一刻是哑的。**

「没有约定标记就静默退出」（三条不可违反的性质第 1 条）从 v0.1.0 起没动过，
它挡住的是「装了插件污染无关仓库」。这一版补的是它的**代价面**：一个从没跑过
`/setup-convention` 的新项目，恰恰是最需要本插件的那种项目 —— 而插件在它上面
一声不吭。

实测出处：`delegate-plugin`（一个用本工具链从零做出来的项目）。无 `CLAUDE.md`、
无 `.agent/`，`/spec` 把 `capability-map.md` 和三个 `SPEC-<模块>.md` 落在项目根、
`tasks/` 下建出 `todo.md`。**README 问题①的形状被完整复现，全程零提示**，
直到人肉翻目录才发现，此时已是三个模块九个文件。

### 新增

- **休眠项目的迁移提示（`phase-guard.sh`）。** 未激活时不再无条件 `exit 0`：
  若项目里已经有**多模块** spec 产物却没落约定，注入一条建议跑
  `/setup-convention --migrate` 的提示。

  判据只认多模块证据：根上的 `SPEC-<模块>.md`、根上的能力图（大小写都认）、
  `tasks/` 下 ≥2 个模块的 `plan.md`。**根上孤零零一个 `SPEC.md` 不报** ——
  那是 agent-skills 完全合法的单模块形态，本插件对它没有价值，报它就是
  性质 2 说的假警报。只读、只建议、`touch .spec-guard-ignore` 可永久静音。

- **`/setup-convention --migrate`。** 把根上的 `SPEC-<模块>.md` 迁成
  `spec/<模块>.md`、根上的能力图迁成 `spec/CAPABILITY-MAP.md`。

  **不加它时只列清单、一个文件都不动** —— 移动用户的文件比往 `CLAUDE.md`
  追加危险得多，此前脚本唯一的破坏性操作是 teardown。目标已存在一律不覆盖
  并以非零退出；优先 `git mv` 保住重命名记录。**不改任何正文里的相对链接**
  （越权，且改错很难发现），改为把仍在引用旧路径的文件列出来交给人。

- **Codex 支持模式。** 新增 Codex 清单、共享 `UserPromptSubmit` hook、
  `spec-guard-ops` 操作 skill 与独立 `AGENTS.md` 约定块；状态机、迁移、digest 和
  校验仍和 Claude Code 共用一份实现。
- **Codex smoke 判决器。** `evals/codex-plugin-smoke.sh --selftest` 已接入
  `validate.sh`，免费验证 `0=通过 / 1=行为失败 / 2=环境未就绪` 三态不会混淆。

### 兼容性与限制

- 既有 Claude Code 项目无需迁移；其 `CLAUDE.md` 标记与 slash 命令不变。Codex 用
  `spec-guard-ops` 的 `setup` 以 `--host=codex` 写入 `AGENTS.md`，不提供 Claude slash 命令。
- 真实 Codex smoke 不进 `validate.sh`。运行前须安装并启用插件、登录 Codex，并在新会话
  的 `/hooks` 审核和信任 hook；任一条件缺失均返回 2，不算产品失败。

### 修复

- **SSH host 别名被判成「远端不是 GitHub」。** 判据写的是
  `*github.com*|*github.*`，而 `git@github-collab:o/r.git` 里 `github` 后面
  跟的是 `-` 不是 `.` —— 用 host 别名的仓库一律落进 `other` 分支，在
  `state.json` 还没建出来时会吃一条**假断链**（性质 2 要防的正是这个）。
  实测出处：本插件作者自己的每一个仓库都用 `github-collab:` 别名，包括
  本仓库 —— 这条从 v0.1.0 一直躺到现在。

  改法：抽出 `is_github_remote()`，**先剥到 host 段再判**。不能简单松成
  `*github*`：`gitlab.com/me/github-tools.git` 的**路径**里含 github，
  那是仓库名不是宿主。`phase-guard.sh` 和 `verify-artifacts.sh` 两边同改，
  两边各加一正一反。

### 测试

- `test-phase-guard.sh` 89 → 110 条，`test-verify-artifacts.sh` 63 → 65 条。新增 15 条休眠提示与远端判定（7 正 8 反）
  + 6 条 `--migrate`（3 正 3 反）。
- 反向那半边是重点：单模块 `SPEC.md` 不报、单个 `plan.md` 不报、空项目不报、
  静音文件生效、两种激活方式下都不出这条提示。最后一条另配了一个**非空断言**
  （激活后仍注入「当前阶段」）—— 0.7.20 出过三条空断言，反向断言全绿而
  什么都没验。
- 迁移那组有一条专门冲着顺序去的：迁过来的能力图必须是**原内容**。迁移和
  「复制能力图模板」写的是同一个路径，顺序反了就把用户写好的能力图冲掉，
  而「文件存在」那条断言照样绿。

### 已知限制

- 提示每轮都会出，直到你落约定或建静音文件。`phase-guard` 是只读探测器
  （禁止写操作），没有地方记「已经提示过了」—— 所以做不到只提示一次。
  代价是 8 行注入，且只有真踩进这个形状的项目付。
- `--migrate` 只认 `SPEC-<模块>.md` 和能力图两种形状。`docs/SPEC-*.md`、
  `tasks/*/todo.md`（github 模式禁止的那个）都不迁，也不报。
- 迁移后的相对链接要手工改。列表给了，但没有验证「改完了没有」的判据。

## [0.7.27] - 2026-08-29

两条都是同一个形状：**0.7.26 的表格里声明了判据，代码只兑现了一半。**
上一版的主题是「判据看的对象和真正生效的对象不是同一个」；这一版是它的近亲 ——
**声明的对象和实现的对象不是同一个。**

两条都是拿第三方读同一段代码读出来的（Codex 只读审查）。行号都对，
但它给的严重度两条都高估了 —— 找得准和判得准是两回事，裁决仍然得自己做。

### 修复

- **「超出前 200 条落进 skip」只兑现了一半，另一半在打绿灯。**

  0.7.26 的已知限制白纸黑字写着「只看 open 的前 200 条。超出的落进 skip
  （并声明『不代表通过』），不猜。」但 `verify-artifacts.sh` 里那个 skip
  **只发生在「`state.json` 记的 Epic 自己不在列表里」这一支**。

  记的 Epic 在窗口内、而**重复的那个落在窗口外**时，代码走的是另一支：
  窗口内没找到同名 → 直接打印 `OK|没有与 Epic #N 同名的其他 open issue`。
  **「没看见」被当成了「没有」** —— 这条检测存在的理由（没被记下来的那个
  Epic 谁都看不见）在判据自己身上原样重演了一次。

  改法：`--limit` 200 → **201**，多要一条**纯粹用来探测截断**。
  返回 ≥201 条且窗口内没找到同名 → `skip`（声明不代表通过）；
  **找到了仍然 `BAD`** —— 找到就是找到，截断不影响已经看见的东西。

- **表格写「标题逐字相同」，代码比的是压缩空白之后的标题。**

  0.7.26 那张闸门表第二行是「与记录在案的那个 Epic **标题逐字相同**」，
  整条检测的安全性论证就建立在这个「逐字」上。而实现里
  `norm()` 把所有空白压成单个空格再比 —— **声明的比实现的紧，实现的比声明的松**。

  改成原始 `title` 逐字比较（保留 `None` 兜底）。
  `initiative:` 前缀那条 WARN 扫描**保留 `norm()`** —— 它是模糊前缀匹配，
  用途不同，收紧它反而会漏掉「重跑会再建一套」的前夜。

  `norm()` 是 0.7.26 同一个提交引进来的，不是历史包袱，没有需要保留的理由。

### 测试

  `test-verify-artifacts.sh` 59 → **63**，两正两反：

  | | 用例 | 期望 |
  |---|---|---|
  | 正 | 返回 201 条、Epic 在其中、窗口内无同名 | `skip`，不是 `OK` |
  | 反 | 200 条以内、无同名 | 仍然 `OK`（新逻辑不许制造假 skip） |
  | 正 | 另一个 issue 标题与 Epic 只差空白数量 | **不**报重复 |
  | 反 | 另一个 issue 标题与 Epic 逐字相同 | 仍然报重复 |

  写完当场注入两个回归复跑（A2c：全绿不是断言存在的证据）：
  撤掉截断检测 → `❌ 201 条截断列表里没找到同名项却报了 ✅`；
  精确比较改回 `norm()` → `❌ 标题只差空白数量仍被报成重复`。
  各 62 通过 / 1 失败，都如期被抓。两条已固化进
  `mutation-check.py`（22 → **24** 个变异体）。

  已有 4 组重复-Epic 用例的标题本来就是逐字节相同的，
  所以改成精确比较**没有碰红任何一条已有断言**（77 插入 / 0 删除）。

  **顺带修好两个被自己弄失效的锚点。** 改 `dups=` 那一行的写法，直接让 0.7.26
  的两个变异体（「放宽成 `Initiative:` 开头就算」/「不排除记录在案的那个号」）
  找不到锚点 —— 变异体**静默不跑**，等于两道防线悄悄下岗，而套件仍然全绿。
  是 `mutation-check.py` 把「锚点失效」和「没抓到」分开报才看见的。
  改完 5 个重复-Epic 变异体：**符合预期 5 / 不符 0 / 锚点失效 0**。

  > 教训：**动了被变异体锚定的那一行，就要复跑 `--only` 那一组。**
  > 锚点失效不会让任何测试变红。

### 已知限制

- **只看 open 的前 201 条**，第 201 条纯粹用来探测截断。
  返回满 201 条时一律 skip —— 包含「恰好 201 条、窗口其实是完整的」这个边界，
  宁可多 skip 一次也不发假绿灯（A1）。**202 条以上仍然无法判定。**
- 0.7.26 那两条仍然开着：**只查 Epic 这一层的重跑残留**（`--parent` 没跑成的
  孤儿模块 issue 两条判据都看不见）；**弃用仍然没有落点**（位置想好了是
  `state.json` 的 `modules.<id>.retired`，本轮仍未做）。

## [0.7.26] - 2026-08-29

前半轮三件事同一个形状：**判据看的对象，和真正生效的对象，不是同一个。**
后半轮补上一条从 0.7.18 起就挂在已知限制里的检测。

### 新增

- **`verify-artifacts` 查得出重复的 Epic 了。**（0.7.18 已知限制的最后一条）

  操作一在外部系统上做不可逆写入，中途会失败（限流 / `--type` 被拒 / 用户按停）。
  0.7.13 之后 `state.json` 是增量写回的，重跑本该可续 —— 但那条只是 skill 里的
  一句话，0.7.13 之前建起来的项目、以及模型没照做的那次，仍然会落到
  「GitHub 上已经有一个 Epic / `state.json` 里没有它」，重跑就再建一套。

  而**已有的每一项检查问的都是 `state.json` 记着的那一个**：sub-issue 数、
  正文体量、三处指纹，全都从 `initiative.issue` 出发。
  **没被记下来的那个 Epic，没有任何东西看得见** —— 它不在任何一条判据的视野里。

  判据刻意收得很紧（A1：假断链比不报断链危害大得多）：

  | 闸门 | 挡掉的假失败 |
  |---|---|
  | 只看 open | 上一个 initiative 做完关掉的 Epic 不该算进来 |
  | 与记录在案的那个 Epic **标题逐字相同** | 重跑用的是同一份能力图，标题必然相同；而两个**不同名**的 initiative 同时开着是正常的 |
  | 记的 Epic 不在 open 列表里（已关闭 / 超出 200 条）→ skip | 不猜 |
  | 读不到列表 → skip 并声明「不代表通过」 | 同段其余每一处探测失败都是这么做的 |

  另一条支线：`state.json` 没有 `initiative.issue`、而 GitHub 上已经有
  `Initiative:` 开头的 open issue → **只 warn**。那是「重跑会再建一套」的前夜，
  但那个 issue 也可能是人手建的、跟本插件无关。

  `test-verify-artifacts.sh` 52 → **59**，**七条里五条是反向的**。
  写完当场把判据改坏三次复跑（放宽成「`Initiative:` 开头就算」/ 不排除自己 /
  读不到列表时发绿灯），三次都如期变红 —— 「全绿」不是断言存在的证据（A2c）。
  三条同时进了 `mutation-check.py`（19 → 22 个变异体）。

### 修复

- **`scripts/mutation-check.py` 会污染工作区，而且没人拦。**

  它**在工作区就地改文件**。实测踩到两次后果：
  ① 它在后台跑的时候另一边跑测试，读到的是被注入变异的 `phase-guard.sh`，
  得到一条假失败，差点被当成真 bug 去查；
  ② `git diff` 里躺着 `rows.append((mid, mid))` —— 那是「模块行只 hash id」
  那个变异体，**要是直接 commit 就发出去一个坏掉的指纹算法**。

  加两道闸 + 一层兜底：
  - **锁文件**，两个实例不能同时跑
  - **目标文件必须相对 HEAD 干净**，否则拒跑（只列真脏的那个，不是把三个全列出来）
  - `SIGINT/SIGTERM/SIGHUP` + `atexit` 还原 —— 原来只有 `try/finally`，挡不住被 kill

  `scripts/test-checkers.sh` 22 → 26 条，四条全是这两道闸的正反用例。
  已在 `validate.sh` 里，免费。

- **`test-checkers.sh` 里那条正向用例，在正常工作流下必红。**

  「mutation-check: 干净且无锁 → 放行」这条只检查了 `spec-digest.py` 干不干净，
  而 mutation-check 的目标有**三个**。改完 `verify-artifacts.sh` 跑
  `scripts/validate.sh`（本仓写在工作流里的第一条命令）就会看到它红 ——
  而它红的理由是「你正在改东西」，不是「有什么坏了」。
  **假失败会让人学会忽略整套校验**（A1）。

  改成三个目标全干净才跑，否则跳过并**点名是哪个文件脏着**、
  声明「跳过不代表通过」。

- **`evals/_preflight.sh` 只比提交，不看工作区。**

  它比的是 installed sha 与 HEAD 两个**提交**。插件文件在工作区改了没提交的话，
  两边照样判「一致」—— 而 `claude -p` 加载的是**装着的那份**。
  评测于是安静地测了上一版，结论却会被读成当前版的。

  这次就撞上了：0.7.25 的 SKILL 还没提交，评测跑的是 0.7.24。
  现在工作区不干净就直接拒跑。

### 新增

- **`evals/sync-map.sh` 加「刷新」那一组。**

  刷新分支是 0.7.23 加的，**至今零验证** —— 那个 eval 只有一个 prompt
  「把它落成 GitHub Issue 结构」，只测新建。而刷新是操作一里唯一会
  **修改已存在 issue** 的动作，也是唯一**会丢用户数据**的动作。

  **必须做成差分，不能只判「没去覆盖」** —— 那样一个什么都不做的模型也满分。
  两个 issue 一组对照：

  | issue | 正文 | 期望 |
  |---|---|---|
  | `#101` Epic | **有**标记块 | 目标段改了 → **必须**刷（否则刷新形同虚设） |
  | `#102` identity | **没有**标记块，且含能力图里没有的实测数据 | **绝不能**动它 |

  `#102` 的正文是照着真实项目造的（`sentinel-video-scaffold` 的模块 issue 里
  有「孤儿 ffmpeg 已实测发生过，最老 18 小时 42 分」这种东西）。

  判据全在 `gh` 桩的调用记录上：按目标 issue 分开数「带正文的 edit」。
  `--selftest` 14 → 19 条，五条覆盖判决器自己的每条出口
  （含「一个 gh 都没调 → 没跑起来，不是结论」）。

  **首跑（对照组，跑的是 0.7.24 的旧措辞）三条全过**：
  `#101` 刷了 1 次、`#102` 动了 0 次、没新建 issue。
  这是刷新分支**自 0.7.23 加进来以来第一次被执行** —— 它真的能跑，
  而且不会覆盖无标记的 issue。

  > **这条 eval 分不出 0.7.24 和 0.7.25。** 旧措辞的安全来自「先问、
  > 得到确认后再重写」，而 headless `-p` 里没有人可问，所以两版都不会覆盖。
  > 别把它读成「0.7.25 的措辞改进被行为验证过了」—— 没有。
  > 要分辨得判模型**说了什么**（提议加标记 vs 提议整体重写），
  > 那是 transcript 判据，比 `gh` 调用记录弱，暂不做。

### 已知限制

- **只查 Epic 这一层的重跑残留。** 模块层的同一个形状（重跑建出第二个模块
  issue）由已有的「Epic sub-issue 数 ≠ 能力图模块数」间接兜住 —— 但**只有在
  那个重复的 issue 真的被挂上 Epic 时才成立**。`--parent` 那一步没跑成的孤儿
  不算 sub-issue，两条判据都看不见它。
- **只看 open 的前 200 条。** 超出的落进 skip（并声明「不代表通过」），不猜。
- **弃用仍然没有落点**（0.7.23 那条还开着）：能力图删了一行、issue 还在，
  这里只能 warn，人确认「确实是弃用」之后没有任何地方记得住，下次体检照样再 warn。
  位置已经想好，是 `state.json` 的 `modules.<id>.retired`，本轮没做。

## [0.7.25] - 2026-08-29

两件事：把一直没写下来的命名约定写下来；以及**看了真实项目之后，把旧 issue
的迁移方向整个掉了个头**。

### 新增

- **`SKILL.md` 补上「module id：一个名字，五处用」。**

  格式是 kebab-case（`^[a-z0-9]+(-[a-z0-9]+)*$`），但**只有 `/verify-artifacts`
  会校验**，`phase-guard` 不查 —— 定稿那一刻就得对。之前这条只以「评审 checkbox」
  的形式存在，格式本身一个字没写。

  同一个 id 同时是五样东西的名字：能力图第一列 / `spec/<id>.md` /
  `tasks/<id>/` / `state.json` 的 `modules["<id>"]` / `feat/<id>` 分支。
  原来表里写的是「改名 = 三处失联」，**数少了两处**，其中「已建好的 issue
  标题」和「已推上去的分支」是**改不动**的。

  同时澄清：`modules.<id>` 是**路径记法不是字面 key** —— kebab id 在 jq/JS 里
  写不了点号，要 `modules["lab-page-skeleton"]`。

- **`SKILL.md` 补上「state.json 的字段」**，列出当前全部字段并写明
  **不要往里加插件不读的字段**。

  已经发生过一次：某个真实项目的 `modules.<id>` 里长出了 `dependsOn` ——
  插件全部历史里零引用，谁也不读，而它是能力图 `Depends on` 那一列的复制品。
  没有消费者所以暂不处理（删它要写用户的项目，而 hook 只读），
  但触发条件记在这里：**哪天有东西开始读它，它就得像 ②③ 一样上指纹，或者删掉。**

### 改动

- **旧 issue 的迁移从「确认后整体重写」改成「人手加标记」。**

  0.7.23 写的是：正文里没有标记块 → 停下来问用户，确认后整体重写。
  **看过真实项目之后发现这个方向是错的。**

  > **说准一点**：旧措辞是「**得到确认后**再整体重写」，不是「直接重写」。
  > 后来的对照实测（`evals/sync-map.sh` 的 refresh 组跑 0.7.24）显示，
  > 模型在旧措辞下**自己就提出了标记边界方案**：「只换第 3 行、补上标记，
  > 人写的两段原样保留 —— 但这是我推断的边界，需要你点头」，
  > 并且没写指纹（「正文没真改之前写指纹等于谎报已同步」）。
  > 所以这条改的是**潜在**风险，是把一次观察到的好行为固化成规则、降低方差，
  > **不是修一个已经在发生的缺陷**。别把它记成后者。

  `sentinel-video-scaffold` 的模块 issue 正文里，除了照着能力图写的摘要，
  还有能力图里没有的东西：补充说明、实测数据
  （「孤儿 ffmpeg 已实测发生过，最老 18 小时 42 分」）、
  `Initiative spec: … § 4` 这类指针。**整体重写会把它们全删掉** ——
  而它们恰恰是最贵的那部分：能力图能重新生成，实测数据不能。

  现在的做法是让**用户手动加一对标记**，把「照着能力图写的那一段」框起来，
  其余留在标记外；加完之后刷新就能工作，且永远只动框里的。
  一次性、可控、零丢失，机器不猜边界。只有用户明确说「整个重写吧」才整体重写。

  > 这条是「先看目标再动手」赚回来的。批量刷新那 12 个 issue 的方案在动手前
  > 被真实正文推翻了 —— 如果先跑再看，损失不可逆。

### 顺带记下（不改代码）

- `sentinel-video-scaffold` 的 **Epic #470 正文是能力图全文**（5715 vs 7706 字节），
  0.7.19 那条违规活在真实项目里，`verify-artifacts` 现在报得出来。
- 两个真实项目（`sentinel-livelab` Epic #4 / 5 模块、`sentinel-video-scaffold`
  Epic #470 / 7 模块）都是 0.7.23 之前同步的，**一条指纹都没有**：
  ① 集合比对有效，②③ 不生效。走的正是设计好的「指纹缺失 → 不报」降级路径，
  实跑确认零误报。

## [0.7.24] - 2026-08-29

一个字段命名的修复。看着琐碎，但它是 0.7.23 那套设计**自己踩的那个坑**。

### 修复

- **同一个值有两个名字，翻译只存在于散文里。**

  0.7.23 的 `spec-digest.py compute` 输出 `goalDigest` 和 `rows[].digest`，
  却要求存成 `initiative.mapDigest` 和 `modules.<id>.rowDigest`：

      compute 吐的      →   要存成的
      goalDigest        →   mapDigest      ← 名字不一样
      rows[].digest     →   rowDigest      ← 名字不一样

  这个翻译**只写在 `SKILL.md` 的散文里**，靠模型每次执行 `/sync-map` 时读对。
  翻错一次 → 指纹永远对不上 → **一条关不掉的假警报**。而 0.7.23 引入
  `spec-digest.py` 的全部理由，就是「算法只有一份，免得两边算出对不上的 hash」——
  我在算法上守住了，却在**字段名**上原样又造了一遍同一个洞。

  `mapDigest` 这个名字本身也是错的：它只 hash `## 目标` 那一节，不是整份能力图。
  看到这个名字的人会合理地以为模块表也被它覆盖了 —— 没有（那是 `rowDigest`
  加 key 集合的事）。

  现在的规则：**`compute` 输出的 key 名就是 `state.json` 里的 key 名，照抄，
  不做任何翻译。**

      compute → {"goalDigest": "...", "rows": [{"id": "...", "rowDigest": "..."}]}
      state   →  initiative.goalDigest      modules.<id>.rowDigest

### 兼容性

**直接改名，不留别名。** 改之前核过：本机四个真实项目（含 `sentinel-livelab`
Epic #4 / 5 模块、`sentinel-video-scaffold` Epic #470 / 7 模块）**没有一条
写了 `mapDigest`** —— 它们都是 0.7.23 之前的形态，一条指纹都没有。
0.7.23 发出去到现在没有任何项目在它下面跑过 `/sync-map`。

留别名等于把要修的错固化。老项目走的是已经测过的那条降级路径：
**指纹字段缺失 → 不报**。它们现在能拿到 ① 的集合比对（不需要指纹），
②③ 要等下次 `/sync-map` 才生效。

### 顺带

- 这次改名漏了 `evals/sync-map.sh` 里一处形式不同的引用
  （`mod["rowDigest"] = cur["rows"][0]["digest"]`），crash 固件因此抛异常、
  state 写不出来，把三个「应该通过」的用例一起拖红了。
  **是 `--selftest` 抓到的** —— 那一层就是为这种事存在的。

## [0.7.23] - 2026-08-29

上一版只做了三处复制里的一处，而且做的方式是**数个数**。这一版把三处一起
收进同一套指纹，并且给出了一条能真正修好它的路径。

**先纠正 0.7.22 写下的一个结论。** 那一版的「已知限制」说 Epic 正文摘要
过期「机械检测不了，要语义比对」——**这是错的**，错在把比较对象设成了
「拿 Epic 正文去比能力图」。正确的比较对象是「拿现在的能力图去比**上次同步时的
能力图**」，那是一个 hash 比对，纯本地。同一个错误让第三处复制整整两版没被提起。

### 一致性模型

    spec/CAPABILITY-MAP.md   唯一事实源
    GitHub issue             它的投影
    .agent/state.json        「上次投影时，能力图长什么样」

三处复制，现在三处都有指纹：

| # | 复制点 | 指纹 | 0.7.22 |
|---|---|---|---|
| ① | 模块集合 → 模块 issue | `modules` 的 key（本来就有） | 只比**数量** |
| ② | Epic 正文的目标摘要 | `initiative.mapDigest` | 完全不查 |
| ③ | 模块 issue 正文的职责描述 | `modules.<id>.rowDigest` | 完全不查，**连提都没提** |

### 新增

- **`hooks/spec-digest.py`** —— 指纹算法，`compute` / `check` / `--selftest`。

  **它必须只有一份。** 写指纹的是 `/sync-map`（模型执行），读的是两个 hook；
  各写各的实现，只要空白归一或反引号剥离有一处不同，digest 就永远对不上，
  表现是**一条关不掉的假警报**。而关不掉的警报比不报还糟。

  `--selftest` 14 条，已接进 `validate.sh`（免费）。含两条容易翻车的：
  行尾空格 + CRLF **不该**让指纹变，目标段改一个字**必须**让它变。

- **`## 目标` 段进了能力图模板。** `SKILL.md` 从 0.7.19 起就让模型去摘
  「能力图目标段落」，而模板里**根本没有这一节** —— 判据引用了产物里不存在的
  结构。现在它既是 Epic 摘要的唯一来源，也是 ②的指纹底本。

- **issue 正文加 `<!-- BEGIN/END:spec-guard-sync -->` 标记块**，
  以及 `/sync-map` 的**刷新**分支。

  这是本轮真正的缺口所在：0.7.22 报出分歧之后**没有任何命令能修**——
  操作一整节只有 `gh issue create`，**一行 `gh issue edit --body` 都没有**，
  重跑只补缺的 issue，从不更新已存在的正文。检测得出、修不了 = 又一条
  关不掉的警报。

  刷新只重写标记之间，标记外人手写的内容一字不动（和 `setup-convention --replace`
  同一套做法）。正文里没有标记的旧 issue **停下来问**，不猜边界、不往末尾追加。
  顺序也钉死了：**先 `gh issue edit` 成功，之后才写新指纹** —— 反了就是把分歧
  抹掉，正文永远是旧的而检测再也不报。

- **hook 每轮注入 `spec-digest: <绝对路径>`。** 模型的 Bash 里没有
  `CLAUDE_PLUGIN_ROOT`，不注入的话 `/sync-map` 只能去 `find`，找错版本就算出
  对不上的 hash。纯参数展开，不 fork。

### 改动

- ① 从**数量比对**改成**集合比对**，并报出是哪几个。数量比对有个盲区：
  改名、或「删一个 + 加一个」，`N` 不变 = 查不出来。评审项写着「module id
  之后绝不改名」，但那是一句约定，没有任何东西强制。
- `verify-artifacts` 加 A2 段（纯本地，不打 `gh`），和 `phase-guard` 共用
  同一个脚本、同一份判据。**两个 hook 共用的判据要在两边都加用例** ——
  0.7.0 犯过一次，漏了三个版本。
  一处刻意的不对称：反方向（能力图删了行、issue 还在）在 `verify-artifacts`
  里 `warn`，在 `phase-guard` 里**整个不报** —— 手动跑时人在旁边，能自己判断
  是弃用还是手滑；每轮自动跑时问不了人。

### 测试

120 → 141 条断言（`test-phase-guard.sh` 80 → 89，`test-verify-artifacts.sh`
40 → 52），外加 `spec-digest.py --selftest` 14 条。
**两边加起来 21 条里 14 条是反向的** —— 这组检测的全部风险在假断链，不在漏报。

变异体 15 → 19（旧的两条随重写作废）。六条全部被抓到，含
「把『判不了』当成『过期了』」和「模块行只 hash id 不 hash 整行」。

### 已知限制

- **反方向不报**：能力图删了一行、issue 还在。没有「弃用」这个状态，
  「刻意不做了」和「手滑删了一行」在文件上长得一模一样。
  评估过给能力图加 `Status` 列，**否决了**：能力图是 Phase 0 的评审产物、
  近乎不可变，而状态是高频变动的东西；往前者塞后者等于造出第四处复制，
  而且是最容易过期的那一处。真要做，位置是 `state.json` 的
  `modules.<id>.retired`（会变的东西住在会变的文件里），不是能力图。
- **指纹只在 `tracker=github` 下工作。** 它由 `/sync-map` 写，而那是 GitHub
  专属命令。本地模式和 gitlab/jira 项目一律不报（报了也是执行不了的建议）。
- **正文摘要写得对不对，指纹管不了。** 它只保证「摘要是照着当时那份能力图写的」，
  不保证「摘要写得准」。后者要语义判断，仍然只能靠人。

## [0.7.22] - 2026-08-28

「能力图是本地文件，Epic 和模块 issue 是它在 GitHub 上的投影」——
**投影不会跟着文件自己变**。本轮补上其中一处分叉的检测，另一处写进已知限制。

### 新增

- **`phase-guard.sh` 现在会发现「能力图加了模块但没重跑 `/sync-map`」。**

  能力图里加一行新模块，这一刻起：能力图有 N 个模块、Epic 底下还是 N−1 个
  sub-issue、`state.json` 的 `modules` 也还是 N−1 条。要重跑 `/sync-map`
  选「补充」才会补上——**在你想起来之前，它一直不同步**。

  `verify-artifacts` 其实早就查得到这个（`SUBN != MAPN`），但它要打 `gh`、
  只在手动跑时动；而每轮自动跑的 `phase-guard` 对能力图**只做 `[ -f ]`，
  从不解析表格**（0.7.21 及以前的 `phase-guard.sh:135`）。
  **能查的不自动跑，自动跑的查不了**，于是这个分叉可以静默存在很久。

  现在 `phase-guard` 做纯本地比对（能力图解析出的 module id 数 vs
  `state.json` 里带 `issue` 的条目数），不打 `gh`，一次 python3，进得去
  1s 预算。判据刻意收得很紧，只报**一个方向**，三道闸各挡一种假断链：

  | 闸门 | 挡掉的假断链 |
  |---|---|
  | 仅 `tracker=github` | `modules.<id>.issue` 只有 `/sync-map` 写，而它是 GitHub 专属；给 gitlab/jira 项目报出去等于给一条执行不了的建议 |
  | 已落 ≥ 1 个 | 能力图刚写完还没同步是 Phase 0 的正常中间态（模板占位符 `example-*` 也落在这里），不是断链 |
  | 只报「能力图多出来」 | 反方向（能力图删了行、issue 还在）可能是刻意的 |

  六条断言，**五条是反向的**——这条检测的全部风险在假断链，不在漏报
  （lenses A1）。`mapdiv()` 在 hook 无输出时返回 `EMPTY` 而不是 `0`，
  否则五条反向断言在「hook 根本没输出」时也会全绿，那正是 0.7.20
  撞见的空断言形状。

  变异测试同时补了两个变异体。**第二个第一次跑活下来了**：本地模式那条
  反向用例里 `modules` 是 `{}`，被第二道闸就挡住了，第一道闸根本没承重——
  于是补了「gitlab + 已手写条目号」那条，让它真正承重。

### 已知限制

- **Epic 正文里那 3–5 行目标摘要会过期，且没有任何东西查得出来。**

  Epic 正文的形态是「指针 + 目标摘要」。指针不会过期，摘要会：
  能力图的目标段改了，Epic 正文里那几行仍是改之前的复制品。
  `phase-guard` 查不了，`verify-artifacts` 也查不了——后者只查正文**体量**
  （`EL > ML*2/3` 判「灌了全文」），不查正文**内容**。

  机械检测不了，要语义比对。**这是刻意取舍**：0.7.19 消掉了模块清单那处
  复制（不再抄进 Epic 正文，改用 GitHub 原生的 sub-issue 列表），
  但纯指针的 issue 正文没法看，所以目标摘要保留了下来。
  保留复制就等于保留分叉——上一版没把这个取舍写进来，本条补上。

  绕开办法：改能力图的目标段时顺手改 Epic 正文；或者接受它过期，
  以 `spec/CAPABILITY-MAP.md` 为准。

## [0.7.21] - 2026-08-28

这轮没有等 bug 撞上来，而是**主动问「这套断言到底约束了什么」** ——
往两个 hook 里注入 13 个似是而非的回归，看断言抓不抓得住。
活下来 3 个，两个是真洞。

### 新增

- **`scripts/mutation-check.py`** —— 变异测试。

  0.7.20 撞见过三条空断言（要验的变量为空时也照样通过，而且全绿），
  那次是靠另一个测试红了才顺藤发现的。**靠撞见不是办法。**

  首跑结果：抓到 9 / 活下来 3 / 锚点失效 1。

  每个变异体带**预期裁决**：`killed`（必须被抓到）或 `equivalent`
  （行为等价，活下来才对）。标 `equivalent` 必须写清楚为什么 ——
  否则它就是给漏测发的免死金牌。

  它自己也有一层反向保护：**跑变异之前先确认基线是绿的**。
  没有这一条的话，套件路径写错、环境坏掉会让 subprocess 直接非零退出，
  而本脚本把「非零」读成「变异被抓到」—— **13 个全绿，一次都没真测**
  （lenses B5 的形状）。故意把套件路径改坏验证过：报「⛔ 基线就不是绿的」
  并退 1，不是全绿。

  不接进 `validate.sh`：每个变异体要跑一整套，全跑约 6 分钟。

### 修复（都是变异测试暴露的漏测，不是新 bug）

- **重复的 `Closes #11` 被数成两个 task。**

  去掉 `sort -u` 之后 68 条断言一条都没红。真实后果：amend 后重提、
  revert 再来一遍都会让同一个号出现两次，`TASKS_DONE_HERE` 偏大 →
  `2 ≥ OPEN_TASKS=2` → **提前判 `MODULE_READY`，劝人在模块只做完一半时开 PR**。
  代码本来是对的，缺的是拦住它的断言。

- **归档标记只认前 10 行，这条在 `phase-guard` 侧没有反向用例。**

  把 `head -10` 改成 `head -200`，整套断言一条都没红 —— 而
  `verify-artifacts` 那边早就有「第 10 行之后的『已归档』不算数」。
  又一次「共用判据只有一边有用例」（本仓 CLAUDE.md 明令写着要两边都加，
  这是第四次违反）。

- **`README.md` 的典型流程漏了 `/spec` 那一步。**

  照着做到第 3 步会得到一个 `MAP_ONLY` 断链（「能力图已存在但一份模块
  spec 都没有」）—— **文档把用户送进了自己的检查器要报警的状态。**
  同时写清 3 和 4 可以互换：`/sync-map` 只依赖能力图（0.7.19 起）。

### 裁决为行为等价（不加断言，写下理由）

- 「先捡 issue 号、再判模块分支」这条变异活下来了，但它是**等价的**：
  状态机里每一处 `BRANCH_ISSUE` 的使用都排在 `ON_MODULE_BRANCH = true`
  的分支之后，模块分支上根本走不到。那个 guard 是防御性的、不是承重的 ——
  真正管这件事的是**分支顺序**，而顺序有「module id 带数字仍认模块分支」
  盯着。与其为一个等价变异硬加一条空断言，不如把裁决写下来。

### 测试

111 → 114 个断言（`test-phase-guard.sh` 71 → 74）。三条全部来自变异测试：
重复号只算一次 / 不能提前判 `MODULE_READY` / 第 10 行之后的「已归档」不算数。

## [0.7.20] - 2026-08-28

0.7.19 那条筛选规则**在默认分支不叫 `main`/`master` 的仓库上一个号都拿不到** ——
也就是说它在那些仓库上等于没修。这轮修的是它赖以成立的那半个前提。

### 修复

- **基准分支只认 `main` / `master` 两个名字，且只认本地分支。**

  实测取证（默认分支 `develop`，分支上确实有一条 `Closes #11`）：

  ```
  真实情况: 本分支确实有 1 条 Closes commit -> 1
  hook 怎么说: 本分支还没有带 closing keyword 的 commit
  ```

  号拿不到 = 0.7.19 新增的筛选规则 3 没有数据 = **「刚做完的 task 被重新
  取一遍」那个 bug 在这些仓库上原样存在**。

  两个 hook 现在共用同一个 `default_base()`：
  `origin/HEAD` 指向的名字 → 本地 `main` / `master` → `init.defaultBranch`
  → 远端跟踪 ref。顺序刻意先本地后远端，**常见仓库（有本地 `main`）的解析
  结果与 0.7.19 逐字节相同** —— 只往外扩覆盖面，不动已有行为。
  全部落空仍返回空，调用方一律降级成「不排除任何东西」。

  同一个判据的另外两处也跟上了：skill 规则 3 的兜底命令、`/deliver` 第 2 步。
  后者还补了一句：**基准分支认不出来时要说「认不出来」，不能当成「一条
  `Closes` 都没有」** —— 那会用一个假理由拦住本该交付的模块。

- **`verify-artifacts` 在认不出基准分支时整段静默消失**，连一行 `⏭` 都没有。

  同一个脚本对其余每一处探测失败都老实 `skip`。「没查」和「查过没问题」
  在输出里长得一模一样，正是这个脚本存在的意义要否掉的那种。

### 新增

- **`evals/next-redo.sh`** —— 补上 0.7.19 自己标为「没实跑」的那一半。

  操作三由模型执行、没有脚本入口：新增的筛选规则 3 在 hook 侧有断言
  （号算得对不对、注不注得出来），模型侧「拿到号之后真的跳过了没有」
  一直没有任何东西验过。

  做法是**差分**。两个脚手架只差一条 commit：

  ```
  [对照 fresh ] 分支干净           → 正确答案 #110
  [处理 midway] 已落 Closes #110   → 正确答案 #111，取到 #110 就是 issue #4
  ```

  判据是 `gh` 桩记下来的调用日志，不是 transcript。对照组同时充当脚手架
  自检 —— 它没取到 #110 的话，处理组的结果无从归因，这时给的是
  **没跑起来(2)** 而不是结论。

  2026-08-28 首跑：对照 #110 / 处理 #111，两组都走到了 `--add-assignee`。
  **规则 3 成立。**

- **`evals/next-redo.sh --selftest`** —— 判决器自己的回归，已接进 `validate.sh`。

  真跑那次两组都过了，可**一个永远返回 0 的判决器会打出一模一样的输出**。
  自检喂七组已知输入给判决器（含「处理组把 #110 又取一遍」必须退 1、
  「对照组没取到 #110」必须退 2 而不是退 1）、三组给 `picked()`。
  免费，不调模型。

  这是本仓第一次在写完判据的当场就用坏输入跑了一遍 —— 此前四次
  「新加的防线自己有毛病」都是同一个形状（lenses A2）。

### 测试

106 → 111 个断言：`test-phase-guard.sh` 68 → 71，`test-verify-artifacts.sh`
38 → 40。

**其中一次是抓到自己写的空断言。** 新加的三条 `develop` 断言拿整段注入正文
去 `grep "#11"` —— 而 gh 桩给 11 号挂了 assignee，事实行里那句
「已认领 #11 T1」照样含 `#11`。三条断言在 `DONE_LIST` 为空时**也会通过**，
而且是全绿。改成只对「模块分支:」那一行断言之后，退回旧判据复跑，
两条如期变红、「常见情形」那条仍绿 —— 反向验证过才算数（lenses B1b）。

脚手架自己也踩了一个静默失败：裸仓库不用 `-b` 建的话，它的 HEAD 指着不存在的
`main`，`git remote set-head -a` 报错但被 `>/dev/null 2>&1` 吞掉，
`origin/HEAD` 根本没设上。现在两处脚手架都在设完之后**验一下真的设上了**。

## [0.7.19] - 2026-08-28

这轮修的是**上一轮开出来的三个 issue**（#2 #3 #4）—— 全部落在
`spec-github-bridge` 那四个操作上：hook 这边一直在被回归测试盯着，
skill 那边是纯文字，从来没有任何东西拦得住它写错。

### 修复

- **`/next` 会把刚做完的 task 重新取出来做第二遍。**（#4，唯一的行为缺陷）

  模块级 PR 约定下 task issue 要到 PR 合入默认分支才关，所以做完的 task
  在**整个模块周期里一直是 open**。操作三的筛选规则没有一条挡得住它 ——
  它 open、不被 blocked、assignee 就是自己，四条规则全部放行，
  「取第一个」取到的正是上一轮刚做完的那条。

  把筛选规则当代码跑在一个「模块做到一半」的载荷上，复现如下：

  ```
  规则 1 后: [110, 111, 112]
  规则 2 后: [110, 111]      # 112 被 blocked_by 挡掉
  规则 3 后: [110, 111]      # 110 的 assignee 是自己，不排除
  规则 4 取第一个 →  #110    ← 正是上一轮刚做完的那条
  ```

  号一直在 hook 手里：`TASKS_DONE_HERE` 就是数它数出来的，只是从来没往外
  露过 —— **数据在手里、判据没用它**，和 0.7.15 那个 `MODULE_DONE`
  同一个形状（见 lenses B4）。

  现在 `TASKS_DONE_HERE` 由集合派生，号进注入的事实行；操作三新增筛选
  规则 3「排除本分支已经做完的」，四条改五条，**求交集**后排除。
  `<base>` 取不到（既没有 main 也没有 master）时这条规则**不排除任何东西** ——
  反过来全排会在非常规默认分支名的仓库上一个 task 都取不到，
  而表现出来像「模块已经做完了」。

- **Epic 正文灌了能力图全文，而同一节末尾十几行后就禁止这么做。**（#3）

  操作一步骤 2 写的是 `--body-file spec/CAPABILITY-MAP.md`；同一节末尾
  写着「不要把 spec 全文复制进 issue 正文——spec 会改，复制会分叉」。
  改成指针 + 3-5 行摘要。模块清单也不用抄：sub-issue 列表就是 GitHub
  原生的那份索引，而且它一直是准的。

  检测缺口一并补上：`verify-artifacts` 此前只体检模块 issue 的正文体量，
  **唯一一处流程明确指示粘贴全文的地方（Epic）反而没查**。
  判据盖住了使用者可能犯的错，没盖住发布方自己写下的那条（lenses A3「太窄」）。
  探测失败照样 `skip`，不发没挣来的绿灯。

- **操作一要求的摘要，来自一份那时候还不存在的 spec。**（#2）

  步骤 3 为每个模块建 issue，正文摘要取自 `spec/<module-id>.md`；
  可 hook 在**只有第一个模块有 spec** 时就叫 `/sync-map`，而这一步要为
  全部 N 个模块建 issue —— 从第二个模块起无从执行。

  两句话分开看都对：不该逼人把 N 份 spec 全写完才动 GitHub；issue 正文
  也该有实质内容。接起来才错（lenses C5）。修法不是改先后，是**砍掉这条
  接缝上的依赖**：摘要改取自能力图那一行，操作一从此只依赖
  `spec/CAPABILITY-MAP.md`，谁先谁后都不矛盾。

### 测试

99 → 106 个断言：`test-phase-guard.sh` 64 → 68（列出已做完的号 / 不牵连
未做的 / 无 closing commit 时不冒号 / `BASE` 取不到时不排除任何东西），
`test-verify-artifacts.sh` 35 → 38（Epic 正文全文 → warn、摘要 → 放行、
读不到 → skip）。

`ctx()` 上移到 `chk()` 之后：模块分支那组从此也比对**正文**，
不再只比「阶段|断链数」（lenses B1b —— 畸形正文正是这么躺过很久的）。

### 已知限制

- 操作三由模型执行，**没有脚本入口**，所以新增的筛选规则 3
  和其余四条一样只能靠 skill 文字约束，端到端没有实跑验证。
  判据已经想好：「同一条 task issue 在一个模块周期内被 `--add-assignee`
  两次」—— 但需要一次会花 token 的 eval，本轮没跑。
  **（发版后补上了：`evals/next-redo.sh`，见上面的「未发布」段，首跑通过。）**
- `verify-artifacts` 仍然查不出**重复的 Epic**（task 级重复已可查）。

## [0.7.18] - 2026-08-28

这轮扫 `evals/` —— 两个会真的调模型、花 token 的脚本，此前从没被审过。
它们身上是 **A1 的镜像**：不是产品的探测器误报，是**量具**误报产品有病。

### 修复

- **`claude -p` 跑不起来时，评测会指控产品。**

  两个脚本都把命令的输出丢掉（`>/dev/null 2>&1` / `2>/dev/null`），
  也不看退出码。于是未登录、参数写错、网络断的时候：

  ```
  skill-deferral   → ❌ 没加载 spec-github-bridge        （transcript 是空的）
  module-namespace → ❌ 插件的头号卖点不成立               （tasks/ 空着是因为没跑）
  ```

  实测复现过两者。**后者更危险 —— 它会把一个好功能砍掉。**

  现在评测有**三种结局**，不是两种：通过(0) / 不通过(1) / **没跑起来(2)**。
  第三种在退出码和文案上都跟前两种分开：
  `⏭ 评测没跑起来 —— 没有结论，不要读成「卖点不成立」`。

- **自检验的是仓库那份，评测跑的是装着的那份。**

  脚手架的声明块从仓库 `templates/` 拷，hook 自检拿 `CLAUDE_PLUGIN_ROOT`
  指着仓库跑；而 `claude -p` 加载的是 user scope **装着的**插件。
  两者一旦不一致，「✅ hook 已激活」说的就是另一份代码，结论无从解释 ——
  正是 CHANGELOG 记过的「新约定 + 旧检查器」中间态，这次发生在量具里。

  新增 `evals/_preflight.sh`：跑之前强制核对**装着的插件内容 == 仓库内容**，
  不一致就直接退出，别烧 token。

- **`skill-deferral` 的 B 组 hook 静默此前只 warn。** A 组静默是硬失败，
  理由是「否则整个评测测的是空气」—— B 组靠的正是 hook 注入的那句触发指令，
  同一个理由，此前却只警告。改成对称的硬失败。

- **`--max-turns 8` 太紧。** 历史记录里 A 组是在**第 8 个**工具调用才加载 skill，
  上限当时正好是 8 —— 差一步就会被截断、判成「没加载」的假阴性。抬到 12。

### 新增

- **`evals/*.sh` 补进 CI 的 ShellCheck 范围。** 此前只查
  `plugins/spec-guard/hooks/*.sh` 和 `scripts/*.sh`；会真的调模型的脚本
  反而不查。（`_preflight.sh` 是被 source 的，没有 shebang，
  加了 `# shellcheck shell=bash` 指令。）

  全部干净退 0。

### 说明

- README 的 hook 输出示例注明了采样版本（v0.7.17），版本行会随安装版本变 ——
  否则它每发一版就又变成一处陈旧内容。

## [0.7.17] - 2026-08-28

这轮扫的是**从没被审过的那两块**：CI 和 README。
查出来的第一条是：**CI 从 v0.1.0 至今一次都没跑过。**

### 发现（不是代码 bug，但比代码 bug 更该先说）

- **`.github/workflows/validate.yml` 从未执行过一次。**

  ```
  gh api repos/{owner}/{repo}/actions/runs   → total_count: 0
  gh workflow run validate.yml               → HTTP 422:
      Actions has been disabled for this user.
  ```

  而所有本地信号都说它是好的：workflow 注册状态 `active`，
  `repos/…/actions/permissions` 返回 `enabled: true`（**per-repo 的这个字段
  会骗你**）。`sentinel-livelab` 同样是 0 次 —— 账户级，不是本仓配置问题。

  后果：CI 存在的唯一理由 —— **macOS bash 3.2 matrix** —— 十六个版本里
  从没验过一次。bash 3.2 这一层此前的实际保障只有「本机用 `/bin/bash` 跑那三条」。
  `CLAUDE.md` 里那句「CI 也加了 macOS matrix」已改成实情。
  （README 一直是老实的，写着「需要账户级 Actions 可用才会跑」。）

### 修复

- **ShellCheck 步骤结尾挂着 `|| true`，永远返回 0。** 它跑了、有输出、退出 0 ——
  长得完全像通过。**一个永远返回 0 的校验器和没有校验器没区别。**

  去掉之后（用 `npx shellcheck@0.11.0` 本地实跑）当场抓出 **15 条**：

  | 规则 | 数量 | 是什么 |
  |---|---|---|
  | SC2164 | 12 | 测试脚本里 `cd` 不带 `\|\| exit`。`base()` 之后紧跟 `> CLAUDE.md`、`git add -A` —— cd 一失败就写到**仓库根**上去了 |
  | SC2010 | 2 | `ls \| grep` |
  | SC2034 | 1 | `verify-artifacts.sh` 里的 `L` 是死变量 |

  15 条全修完，shellcheck 干净退 0。CI 那一步改成**阻塞**，版本钉死
  （apt 的版本随发行版漂移，「我验过」和「CI 跑的」就会是两回事）。

  > 钉版本时当场又踩一次同样的坑：先写的是 `npx shellcheck@0.11.0`，
  > **那个版本在 npm 上不存在**（`ETARGET`）—— 0.11.0 是**二进制**的版本，
  > npm 包的版本是 `4.1.0`。要不是跑了一遍，CI 恢复那天会挂在「装不上」，
  > 而不是挂在真问题上。**判据写完不当场跑一遍**，这已经是第五次了。

- **`phase-guard` 数模块 spec 时用的是子串排除。**
  `ls -1 spec/*.md | grep -v "CAPABILITY-MAP"` 会把
  `spec/CAPABILITY-MAP-old.md` 这类也剔掉。改成 glob + 整名相等 ——
  `verify-artifacts` 那边一直是 `grep -v "^CAPABILITY-MAP$"`，两边现在一致。

- **README 停在 0.6.0 之前**（`CLAUDE.md` 每版都跟，README 没有 —— D1 那条）：

  - 断言数写着「19 个 / 21 个」，实际是 64 / 35。**直接删掉数字** ——
    与其在两处记同一个数，不如只留一处（`CLAUDE.md`）
  - 「九个阶段」的表缺 `MODULE_READY` / `MODULE_BRANCH` / `READY (本地模式)` /
    `PLANNED (任务未落库)`，现在补齐并说明基名与模式后缀的关系（共 28 种取值）
  - 违规表第三行还写着「认领了 issue 但分支不含 issue 号 → `Closes #n` 会关错单」，
    那是 **0.6.0 之前**的 task 分支约定。模块级 PR 下「分支不含 issue 号」
    本身就是正常的，照这条读会以为模块分支会被报违规
  - hook 输出示例的字段顺序、`spec-guard: v…` 版本行、结尾那句都对不上，
    换成真实跑出来的

## [0.7.16] - 2026-08-28

拿 0.7.15 刚写下的 A5（「零」有两种成因）回头扫自己的判据层。
**没找到新的产品 bug**，找到的是两处判据本身的毛病。

### 修复

- **三个校验器在「传进零个文件」时打 ✅ 退 0。**

  `check-bash32` / `check-grep-pipe` / `check-gh-json-fields` 都靠
  `$(find …)` 喂文件。「0 处违规」和「0 个文件」在输出和退出码上完全一样 ——
  find 表达式哪天失配（目录改名、文件后缀变了），`validate.sh` 会**全绿地什么都不查**。

  现在零文件直接判失败：`❌ 没有传入任何文件 —— 这不是「没问题」，是「什么都没查」`。

  > 顺带更正一个我自己的错判：我先怀疑 `validate.sh` 会跟着 cwd 跑，
  > 实测**不会** —— 它第 4 行就 `cd` 到仓库根了。所以零文件这条目前只是
  > 潜在的，不是活的。

### 变更

- **`check-command-names.py` 的上游清单不再是冻结快照，改问上游本人。**

  那两个集合（上游命令名、上游 skill 名）原本是手工维护的，注释里明写着
  「上游改名它们不会自己跟上」。而上游就装在本机 ——
  `installed_plugins.json` 的 `installPath` 是权威来源（cache 目录下同时躺着
  版本号和 commit sha 两个目录，挑错就会拿一份不在用的清单当真）。

  现在：
  - 校验集取**并集**（快照 ∪ 上游本人）—— 上游新增的名字不该被判失败
  - 单独抓危险的那个方向：**快照里有、上游已经没有**。这种情况下老逻辑
    照样放行，而文档里那条命令已经会报 Unknown —— 0.4.1 的 `/planning`
    正是这么来的
  - 读不到上游就退回快照，并声明「不代表快照是最新的」

  核对结果：**当前快照与实际上游完全一致**（8 个命令 / 24 个 skill，
  上游 0.6.7）。所以这次没有修好任何东西，只是把「记得去核对」换成了「每次都核对」。

  > 但那份快照的「末次核对：…上游 commit 5a5ea45」与 `installed_plugins.json`
  > 记的 sha 对不上，而且已经无法重建当时哪个是对的。
  > **手工维护的出处说明也会烂，而且烂的时候一样不出声。**

- 新增环境变量 `SPEC_GUARD_UPSTREAM_REGISTRY` 覆盖注册表路径。
  它**不是为了灵活，是为了这条判据自己能被测试** —— 写死 `$HOME` 的话，
  「上游删掉了某个命令」这条反向用例只能靠改真实的用户配置来构造。
  同 `check-readme-sync.py` 那个 root 参数。

### 测试

`test-checkers.sh` 17 → **22**：三个「零文件不算通过」，
加上「对照上游本人放行」/「上游删了 `/plan` 就报快照过期」一正一反
（反向用例的 fake 上游是**从真上游复制再删掉一个命令**生成的，
不写死名单；本机没装上游时整组干净跳过）。

## [0.7.15] - 2026-08-28

体检续：这轮盯的是「任务落库」这一步。它是 skill 四个操作里**唯一没有命令
触发**的一个，也因此是唯一**完全没有产物校验**的一个。
查出来的第一条是这整轮体检里危害最大的。

### 修复

- **一个 task 都没做的模块会被宣告完成。**

  `phase-guard` 此前把「未关闭 task 数 = 0」一律判成 `MODULE_DONE`，
  并建议「推进到下一个模块」。可是那个 0 有两种成因：

  - 建过 N 条、全部关闭 → 模块真做完了
  - **一条都没建过** → 任务从没落库

  两者在那个计数上长得一模一样。实测复现：

  ```
  当前阶段: MODULE_DONE
    - plan: tasks/identity/plan.md=true
    - GitHub: 0 个未关闭 task
  建议下一步: /next 推进到下一个模块（[identity] 已无未关闭任务）
  ```

  plan.md 写着两个任务，GitHub 上一条 sub-issue 都没有，模块被判完成。

  **这是假完成，比假断链更难发现** —— 假断链会招来抱怨，
  假完成长得就像成功，还主动把你推向下一个模块。

  分开两者的信号一直在手里：REST `sub_issues` 返回**所有状态**，
  总数是现成的。现在 `总数 == 0` 判 `PLANNED (任务未落库)` 并报断链，
  指向 skill 的「操作二：任务落库」。事实行也带上了总数。

  > **为什么会漏到这一步**：skill 的操作一/三/四 分别由 `/sync-map`、
  > `/next`、`/deliver` 点名，**操作二没有任何命令、模板或文档引用它**。
  > `/plan` 跑完就没有下一步指路，而 phase-guard 又把这个状态当成了成功。

- **任务落库跟操作一一样会在中途失败后重建。** plan.md 的 Task List 原先是
  「全部建完再一次性回写」。0.7.13 刚给操作一修过同一件事，**操作二没跟上** ——
  又一次「修法只落了一边」，而这次是上一版的作者（我）留下的。
  一个模块建 N 条 issue，中途失败的窗口比操作一还大。
  改成每建成一条立刻把编号写进 Task List，重跑时跳过已有编号的。
  另补一句：用 `--blocked-by` 时建的顺序要让前置先出生。

### 新增

- **`verify-artifacts` 补上任务落库的产物校验**：模块 issue 的 sub-issue 数
  ↔ plan.md 的 `- #<n>` 索引条数。SKILL 的 Verification 里一直写着这条，
  但没有任何东西真去比。它一次盖住两种失败：

  | plan 索引 | sub-issue | 判定 |
  |---|---|---|
  | N > 0 | 0 | ❌ 任务从没落库 |
  | N | M ≠ N | ⚠️ 对不上（落库中途失败重跑的残留？或 plan.md 没回写全） |
  | 0 | M > 0 | ⚠️ plan.md 没写编号，跨会话续接找不到任务 |
  | N | N | ✅ |

  读不到 sub-issue 时 `skip`，不发绿灯也不判失败。

  这补上了 0.7.13 记的那条已知限制的一半：**task 级**的重跑残留现在查得出来，
  Epic 级的仍然查不出（那要跨 Epic 搜索，不在现有判据的形状里）。

### 测试

断言 93 → **99**（phase-guard 62 → 64，verify-artifacts 31 → 35），
含「建过且全部关闭仍要判 MODULE_DONE」和「数一致时放行」两条正向对照 ——
新判据不能变成新的误报源。

`docs/lenses.md` 加 A5：**「零」有两种成因，判据分不开就会报假完成。**
同类形状：grep 没匹配（模式错了还是真没有）、目录为空（清理干净还是没生成）、
diff 为空（没改动还是比错了对象）。

## [0.7.14] - 2026-08-28

体检续：这轮把 skill 里那些**每次 `/next` 都要跑的 gh 命令**拿去对着真 gh
和真仓库跑了一遍。一个硬失败的 bug，一处能砍掉 N 次 API 调用的多余步骤，
一条无从判断的筛选规则。

### 修复

- **`/next` 的「取到后」那条命令每次都会硬失败。**

  操作三写的是：

      gh issue view <n> --json title,body,parent,dependencies

  而 `dependencies` **不是合法字段**（真名叫 `blockedBy`）：

      Unknown JSON field: "dependencies"

  跟陷阱表里那条「`gh issue list --parent` 那个 flag 不存在」是**同一个形状**，
  只是这次躺在正文的操作步骤里。已改成 `blockedBy`（实测通过字段校验）。

### 变更

- **筛选被阻塞任务不再逐个 task 打 API。** 操作三原先要求对每个 task 单独跑
  `gh api .../dependencies/blocked_by`。但 REST `sub_issues` 的每一条里
  已经带了 `issue_dependencies_summary.blocked_by`，数的正好是**未关闭**的
  阻塞者：

  ```
  #11  open  {"blocked_by": 0, "total_blocked_by": 1, ...}   ← 前置 #10 已关闭
  #13  open  {"blocked_by": 1, "total_blocked_by": 1, ...}   ← 前置 #12 仍 open
  ```

  （在 `sentinel-livelab` 上逐条核对过。）一个 9 task 的模块因此省掉 9 次
  round trip，也去掉了一个「模型可能漏查几条」的循环。
  需要知道**是谁**在挡的时候才单独查那一个。

- **删掉筛选规则「排除 `issueType != Task`」。** REST `sub_issues` 的响应里
  根本没有 type 字段，这条规则在那份数据上无从判断；而 `--parent <module>`
  返回的按构造就是 task，skill 自己也写着它「本来就是冗余的」。
  把一条**评估不了**的规则放在有序筛选的第一位，只会逼模型去猜或多打 N 次 API。

  > 核对边界：本账号只有个人仓库（`issueTypes` 不可用）。有 issue types 的
  > 组织仓库上那个字段会不会出现，**没验过** —— 但即使出现，冗余这一点不变。

- Verification 里的 `gh issue view <epic> --json subIssues` 补上取数方式：
  它返回的是 `{nodes, totalCount}` 对象，不是裸数组，直接 `| length` 会得到 `2`。

### 新增

- **`scripts/check-gh-json-fields.py`** —— 校验仓库里写到的
  `gh <issue|pr|repo> view --json <字段>` 都真实存在。

  这个仓库已经**两次**把不存在的东西写进操作步骤，两次都是每跑必败、
  两次都在文档里躺了很久。跟其他 `check-*.py` 不同的是，
  **它的判据不是冻结清单，是问 gh 本人** —— 跑一次
  `gh issue view 1 --json <乱写>` 让 gh 吐出合法字段表。
  实测这一步 gh 在**本地**完成：不需要仓库上下文、不需要网络、不需要登录
  （`GH_HOST` 指向不存在的主机也照常打印）。gh 不可用时干净跳过并声明
  「跳过不代表通过」。

  它当场抓到了上面那个 `dependencies`。

### 测试

`test-checkers.sh` 14 → **17**（含「gh 不可用时干净跳过」的降级用例）。
接进 `validate.sh`，现在每次校验 13 个字段引用。

## [0.7.13] - 2026-08-27

体检续：这轮查的是**四个模型驱动、零测试的命令**（`/sync-map` `/next`
`/deliver` `/phase`）。三处问题，形状相同 ——
**不可逆操作没钉死「作用于什么」，也没记录「做到哪了」。**

### 修复

- **`/setup-convention` 和 `/teardown-convention` 的作用目录跟着 cwd 跑。**

  两个脚本都直接在当前工作目录上动手，而 Bash 的工作目录在会话里会被
  `cd` 改掉。从子目录跑时：

  - setup 把 `spec/ tasks/ .agent/` 和声明块建进**子目录** ——
    项目里于是有两套约定，而 hook 只认根上那套，装了等于没装
  - teardown 去删子目录里并不存在的块，报「什么都没做」退 2，
    根上的约定原封不动 —— **移除报成功却没移除**

  两处都改成先解析项目根再 `cd`，并把作用目录打印出来：

      ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

- **`/phase` 和 `/verify-artifacts` 从子目录跑会报假的「没装约定」。**

  两条命令都写着 `CLAUDE_PROJECT_DIR=$(pwd)`。从子目录跑时 hook 找不到
  CLAUDE.md，静默退 0（`verify-artifacts` 则退 2），命令于是报
  「本项目没有启用 spec-guard 约定，先跑 `/setup-convention`」。

  **假警报本身已经违反第一条不变量，它还会引出一次破坏性操作** ——
  用户照着提示跑 setup，就触发了上面那条。

- **`/sync-map` 中途失败后重跑会建出一套重复的 Epic 和模块 issue。**

  原步骤是「建 Epic → 建 N 个模块 issue → 建依赖 → **最后**写
  `.agent/state.json`」。而这一步在 GitHub 上做不可逆写入，且会中途失败：
  网络、限流、`--type` 在个人仓库上被拒（陷阱表里那条「孤儿 issue」说的就是它）、
  用户按停。任何一次都留下「GitHub 建了 k 个 / `state.json` 干干净净」，
  而 `/sync-map` 的前置判据读的正是 `initiative.issue` —— 它是空的，
  于是重跑从头再来一遍。

  改成**每建成一个 issue 就立刻写回 state.json**，重跑因此可续：
  `initiative.issue` 有值跳过建 Epic，`modules.<id>.issue` 有值跳过该模块。

  > 重复的 issue 可以 `gh issue delete` 删（我上一版说过「删不掉」，那是错的），
  > 但要先人工分辨哪套是哪套，依赖关系和 sub-issue 层级还得重连。

### 测试

断言 91 → **93**：子目录里跑 setup / teardown 必须仍作用于项目根。

### 没做什么

**没有把 `/sync-map` 脚本化。** 它要解析能力图、判断 issue types 可用性、
按依赖表连边，确定性执行的收益还不足以抵掉一个 200 行脚本的维护面 ——
这次治的是它那个具体的重复建 issue 缺陷，不是它的形态。

### 已知限制

- **`verify-artifacts` 查不出重复 Epic。** 它比对的是 `state.json` 指向的
  那个 Epic 的 sub-issue 数与能力图模块数；一次失败重跑残留的**另一套** Epic
  在这个判据之外，所以体检会全绿。上面的增量写回是在**防止**它发生，
  不是在**检测**它。已经发生过的只能人工用 `gh issue list` 对一遍。
- **`/sync-map` 仍是模型驱动，没有回归测试。** 本次只改了它的过程约定。

## [0.7.12] - 2026-08-27

一次整体体检，五处实测复现的 bug。三处是**同一个 0.7.11 的修法只落了一边**，
另两处是**没挣来的绿灯**。

### 修复

- **`phase-guard` 也有 0.7.11 那个「模块 id 带数字」的 bug —— 而且它每轮都跑。**

  0.7.11 修 `verify-artifacts` 时在文件顶部写下「重叠项的判定规则必须两边一致」，
  但只修了那一边。`phase-guard` 的判定顺序是反的：先从分支名捡数字，
  捡到了就不判模块。于是 `feat/oauth2` 里的 `2` 让模块分支判定整条失效：

  ```
  当前阶段: TASK_READY            ← 实际在模块分支上
  建议下一步: /deliver 开 PR（Closes #2）
  ```

  `#2` 是从分支名里捡的，跟这个模块毫无关系；而且它在模块分支上劝你开
  task PR，正是 0.6.0 要治的那件事。同一条分支、同一份 state.json，
  两个脚本结论相反。

  现在两边一律**先判模块、判不中才捡号**。老约定的 task 分支不受影响。

- **本地模式永远够不到「刻意空闲」豁免。**

  `activeModule` 为空的豁免（c37fe46 加的）排在 tracker 分支**之后**，
  而 `tracker=none` 在它前面就把控制流截走了。结果：

  ```
  ⚠ 有 spec 但没有 tasks//plan.md —— 链路在此断开
  建议下一步: /plan 为 [] 拆解任务
  ```

  路径里那个双斜杠和空的 `[]` 就是 `MODULE=""` 漏出来的。
  这不是边角料：本地模式**没有任何命令**负责给第一个模块设 `activeModule`
  （`/sync-map` 是 github 专属），所以它是本地模式跑完 `/spec` 的必经状态。

  豁免上移到所有 tracker 分支之前；「连 state.json 都没有」单独接住，
  不再把空模块名拼进任何路径。

- **`verify-artifacts` 在 gh 读不到 issue 正文时发绿灯。**

  E 段段头写着「探测失败就整段跳过，绝不误报」，同段另外三处（Epic /
  父 issue / PR 正文）失败时都老实 `skip`，只有正文体量比对是拿
  `wc -c` 数管道输出的：gh 失败 → 0 字节 → 落进 else → 打出
  「✅ 正文是摘要而非 spec 全文」。**把「没查成」算成「查过了没问题」，
  而这个脚本存在的意义就是不发这种绿灯。**

- **`teardown` 的自检会因为环境变量没设就整段跳过。**

  `HK="${CLAUDE_PLUGIN_ROOT:-}/hooks/phase-guard.sh"` 没有兜底，
  而 `setup-convention.sh` 一直有 `$HERE` 兜底。「实际跑一遍而不是让人
  相信一句话」是 0.7.9 把 teardown 改成脚本的**唯一理由**，它自己会
  退回成一句话。此前所有 teardown 用例都显式设了这个变量，所以三个版本没人发现。

- **`is_archived` 用了本仓明令禁止的 `cmd | grep -q`**（两个 hook 各一处）。

  `head -10 "$f" | grep -qiE '已归档|ARCHIVED'`：grep 命中即关管道，
  head 吃 SIGPIPE(141)，pipefail 传出 → 归档豁免失效 → 假违规。
  实测门槛是前 10 行约 256KB（真实 todo.md 到不了），**所以这条是卫生
  问题不是活 bug**。值得记的是 `verify-artifacts.sh` 里隔了 80 行就写着
  「herestring：管道 + grep -q 会 SIGPIPE」—— 同一个文件改了一处漏了另一处。

- `setup-convention` 在 `.disabled` 的 tracker 不符时提示「用 `gitlab` 模式重跑」，
  而本脚本只收 `github|local` —— 那个建议做不到。

### 新增

- **`scripts/check-grep-pipe.py`** —— 静态拦 `cmd | grep -q`。
  这条规则写在 CLAUDE.md 里，已经被违反三次（gh `--help`、`find todo.md`、
  `is_archived`），每次都是修一处漏一处。它的姊妹规则 `check-bash32`
  一直有检查器，这条没有。注释里提到该模式是允许的。

### 测试

断言 79 → **91**（`test-phase-guard` 52 → 60，`test-verify-artifacts` 27 → 31），
`test-checkers` 11 → 14。

两条老断言被**改了期望值**：`spec无issue(无remote→本地)` 和
`根目录SPEC(无remote→本地)` 断的正是上面那个 `tasks//plan.md`。
它们只比对「阶段|断链数」、从不看正文，所以那个畸形路径在 52 条断言底下
躺了很久 —— 新增的用例直接对正文做断言。

## [0.7.11] - 2026-08-27

### 修复

- **`verify-artifacts` 的分支检查从 0.6.0 起就留在 task 分支时代，会报假失败。**

  模块 id 自带数字时（`feat/oauth2`），分支名里的 `2` 被 `grep -oE '[0-9]+'`
  当成 task issue 号，于是：

  ```
  ❌ PR 正文没有 Closes #2 —— issue 不会自动关闭
  ```

  而 PR 正文里写的是**正确的** `Closes #5`（模块 issue）。
  **假失败，而「假断链比不报断链危害大得多」是本仓第一条不变量。**

  现在两边判定一致（末段整段相等）：模块分支比对**模块 issue**，
  并统计 `<base>..HEAD` 里带 closing keyword 的 commit 数；
  task 分支保持老规则。

  > **为什么漏了五个版本**：0.6.0 改约定时我判断「verify-artifacts 没有分支
  > 逻辑」——那次 grep 找的是 `BRANCH`，而这里那段变量叫 `BR` / `BRI`。
  > **一次失败的搜索被当成了「这里没有」。**
  > 已把这条补进 lens B1：「我搜过了，那边没有」不算数，判断某处不受影响要靠读。

- `commands/verify-artifacts.md` 两处过期：`/deliver` 前的检查项改成模块级；
  「三项重叠」里「分支 issue 号」改成「分支归属」并写明两边判定必须一致。

- 断言 76 → 79。

## [0.7.10] - 2026-08-27

### 修复

- **0.7.9 自己挖的坑：`setup-convention` 不认识 `state.json.disabled`。**

  teardown 把 `state.json` 改名保留（issue 编号映射删了找不回来）。但 setup
  只看 `state.json` 存不存在 —— 于是「teardown 之后改主意再 setup」会**静默
  建一个空的 state.json**，真正的映射孤零零躺在 `.disabled` 里。

  后果不只是丢数据：模型接着会看到「activeModule 没有对应 issue」→
  建议 `/sync-map` → **在 GitHub 上建出一套重复的 Epic 和模块 issue**。
  而 issue 在 GitHub 上删不掉。

  现在：tracker 一致就**自动恢复**（往返无损）；不一致就**既不恢复也不新建**，
  退非零并说明二选一，`.disabled` 原样保留。

  > 这条是 0.7.9 发布**二十分钟后**发现的，用的是 0.7.9 自己刚补进 lens B1 的
  > 那句话。已把它再推一层：**新增一个此前不存在的状态，也算改概念定义 ——
  > 刚发的改动同样要过这一遍。**

- `setup-convention` 落地阶段出现 ❌ 时会**明确退 1**，此前只打印不改退出码。

- 断言 74 → 76。

## [0.7.9] - 2026-08-27

### 修复

- **`/teardown-convention` 自 0.7.0 起就移除不干净，而且越修越黏。**

  0.7.0 给 hook 加了第二个激活信号 `.agent/state.json`（为 `--no-claude-md`
  零足迹模式）。而 teardown 明确**不删** state.json（里面有 issue 编号映射）——
  于是删完声明块，项目不是「约定被移除」，是**变成了零足迹模式**。

  0.7.5 之后更糟：hook 在零足迹模式下会每轮注入「先加载 `spec-github-bridge`」，
  **移除之后比移除之前更黏**。

  命令文里那句自我验证「无输出即为成功」也就成了假的 —— 实测输出如下：

  ```
  当前阶段: **MAP_ONLY**
  **本项目没有 CLAUDE.md 声明块（零足迹模式）。**
  动 spec、拆任务、取任务、交付之前，先加载 `spec-github-bridge` skill ——
  ```

  这是 lens B1（在一个配置下验证、全局发货）的一个变体：
  **改的不是配置，是「什么算激活」这个概念的定义 —— 而依赖这个概念的东西
  没被列出来重看。**

- **teardown 从模型驱动改成脚本。** 它是插件里**唯一的破坏性操作**
  （删用户 `CLAUDE.md` 里的内容），此前却完全靠模型按 `.md` 里的步骤做，
  零测试 —— 而本仓的规矩是「写文件是幂等性和安全性要求高的操作，
  不能有非确定性」。setup 早就是脚本，teardown 一直不是。

  新的 `hooks/teardown-convention.sh`：

  | 动作 | 说明 |
  |---|---|
  | 删标记之间的内容（含标记） | 标记外一个字节不动；连带收掉多余空行 |
  | `state.json` → `state.json.disabled` | **这一步才是真正的移除**；改名不删除，issue 映射改回原名即可恢复 |
  | 实际跑一遍 `phase-guard.sh` | 而不是让人相信「无输出即为成功」这句话 |

  `--dry-run` 零写入；`--keep-state` 保留原名（**hook 会继续激活**，
  只在确实想切到零足迹模式时用）；没装过的项目退 2。

- 断言 68 → 74（含「teardown 后 CLAUDE.md 逐字回到原样」「teardown 后 hook 真的静默」
  两条 —— 后者正是 0.7.0–0.7.8 一直失败却没人跑的那条）。

## [0.7.8] - 2026-08-27

### 修复

- **hook 崩溃和「未启用」长得一模一样。** `hooks.json` 的命令串结尾是 `|| true`，
  `phase-guard.sh` 非零退出被整个吞掉，宿主收到**空输出** —— 而空输出正是
  「这个项目没启用约定」的正常表现。

  这就是第一次实跑那条教训的另一面：*「一个永远在降级的探测器，和一个坏掉的
  探测器没有区别」* —— 对「崩掉的」同样成立，而且更隐蔽：降级至少还有文案。

  现在非零退出会注入一条合法 JSON 说明「不是未启用，是执行失败」并给出
  `bash -x` 的排查命令。**静默退 0 仍然静默**（有反向用例钉住）。

- **`emit()` 可能吐半截 JSON。** 原先是无条件 `printf` 拼 JSON，
  内嵌的 `python3` 一失败，命令替换就是空字符串，输出变成 `{"…":}`。
  宿主会拒绝整个 hook —— **而拒绝同样是静默的**：一样坏，但更难查。

  改成两条编码路径（jq → python3）都失败时**什么都不输出**。
  宁可静默，也不要形如 JSON 的垃圾。

- 断言 65 → 68。

### 顺带扫过、确认没问题的已知限制

按 0.7.7 那条判断（**「不支持」是限制，「给错指引」是 bug**）把剩下的已知限制
过了一遍：

- **`gh` ≥ 2.94.0** —— 拦得很扎实：`setup-convention` 既比版本号，又**实际验证
  `--parent` 参数存在**（防 PATH 里有第二个 gh），失败即阻塞、零写入。真限制。
- **多人协作无加锁** —— skill 的取任务规则里本来就排除了「已有 assignee 且不是
  自己」的 task，剩下的是同时认领的窄竞态。真限制。
- **Windows 需 WSL / Git Bash** —— 没有 bash 就连 `setup-convention` 也跑不起来，
  从 bash 内部无法自我告知。真限制，且无解。

## [0.7.7] - 2026-08-27

### 修复

- **声明了 `gitlab` / `jira` 的项目会收到 GitHub 专属建议。** 两条路径都在发生：

  | 情况 | 0.7.7 之前说什么 | 问题 |
  |---|---|---|
  | 有条目号 | `PLANNED (gh 不可用，降级判定)` / 「恢复 gh 后 `/next`」 | `gh` 不是不可用，是**跟这个项目无关**，修好了也没用 |
  | 缺条目号 | 「`/sync-map` 把能力图和模块落成 issue」 | 那个命令会去 `gh` 建 **GitHub** issue |

  跟 0.7.6 的零足迹注入是**同一个形状：tracker 盲**，只是换了条代码路径 ——
  非 GitHub tracker 此前从没走过自己的分支，一路掉进为 GitHub 写的兜底里。

  现在它们有独立分支：`SPECED (gitlab)` / `TRACKED (gitlab)` / `BUILDING (gitlab)` /
  `PLANNED (gitlab)`，建议改成「在 `<tracker>` 里认领下一个任务后 `/build`」，
  缺条目号时提示把号写进 `state.json` 而不是跑 `/sync-map`。

  > **「不支持」和「给错指引」是两回事**：前者是限制，写进已知限制就够了；
  > 后者是 bug。这条限制从 0.1 就写着，而它的**表现**错了一路没人看过 ——
  > 因为「已知限制」四个字会让人以为那块已经想过了。

- 断言 61 → 65（含一条反向用例：整份注入里不许出现 `/sync-map` 或「gh 不可用」）。

## [未发布]

### 新增

- **`evals/module-namespace.sh`** —— 验插件的**头号卖点**：
  README 问题①「多需求并行时产物互相覆盖」。

  这条从立项起就写在 README 第一段，是整个插件存在的理由，**从没被行为验证过**。
  单测只验了 hook 的状态机（文件在不在），没验模型拿到约定后**真的会不会**把
  产物放进 `tasks/<module-id>/`。

  挑 local 模式跑，因为它**没有 skill 兜底** —— 13 行的块就是全部约定，
  不 work 就是真不 work。github 模式的两条通路已由 `skill-deferral` 覆盖。

  **2026-08-27 首跑：**

  | | 产物落点 | 命名空间 | 根下单例 |
  |---|---|---|---|
  | 有约定 | `tasks/identity/{plan,todo}.md` | 2/2 | 0 |
  | 无约定 | `tasks/{plan,todo}.md` | 0/2 | **2** |

  对照组精确复现了 README ① 描述的那个 bug。卖点成立。

  判据是**文件系统**不是 transcript —— 模型可以把命名空间说得头头是道然后写进
  `tasks/plan.md`。**看它做了什么，不看它说了什么。**

  > 这次的对照组是「不装插件」的基线，不是我们也要发的另一个配置 ——
  > 所以「对照组表现差」在这里是卖点成立的证据，而不是像 0.7.6 那样的缺陷报告。
  > **两种对照组要分清**，分不清的代价 0.7.5→0.7.6 已经付过一次。

## [0.7.6] - 2026-08-27

### 修复

- **0.7.5 的零足迹注入是 tracker 盲的。** 它给**所有**没写声明块的项目注入
  「先加载 `spec-github-bridge`」—— 包括 `tracker: none` 的本地模式项目。
  而那个 skill 全篇是 `gh issue create` / `--parent` / `--blocked-by` / 模块级 PR，
  对一个压根没有 GitHub 的项目毫无意义，指过去只会让它去建根本不存在的 issue。

  **又一次「在一个配置下验证、全局发货」** —— 0.7.5 的实测只跑了 github 模式，
  本地模式一次没测。这正是 0.7.5 自己刚写下的那条教训（「对照组本身也是一个
  被测配置」）换个方向再现：**被跳过的那个配置，也是要发货的东西。**

  现在按 tracker 分支：github 指向 skill；其余告诉它「本地模式没有对应的 skill，
  把声明块写回去」。

- **`local --no-claude-md` 现在被拒（退出码 2，零写入）。** 这个组合装了等于没装，
  而且比没装更迷惑 —— hook 照常报状态，看着像在工作，实际目录约定无处可放。

- 断言 59 → 61。

### 顺带查过没问题的

- **本地模式模板瘦身没丢任何规则。** 逐条 diff 过 0.6.1 → 0.7.x：27 行压成 13 行，
  五条规则一条不少，还补上了「`/build` 只认三条路径、只有第三条通配」的理由。
  本地模式没有 skill 兜底，丢了就是真丢了，所以这条必须核对。

## [0.7.5] - 2026-08-27

### 修复

- **`--no-claude-md` 零足迹模式此前是残的。** 0.7.0 引入它时，已知限制写的是
  「模型对目录约定的感知晚一步，靠 hook 每轮兜底」。**兜不住** ——
  `evals/skill-deferral.sh` 的 B 组就是这个模式，实测结果：

  > hook 正常激活、状态照常注入，**模型全程没加载 `spec-github-bridge`**，
  > 转头按自己的想法设计表结构、问技术栈去了。

  原因很简单：**hook 注入的是「状态」，而让 skill 被加载的是那句「指令」。**
  0.7.0 把指令留在了声明块里，零足迹模式恰恰没有声明块。

  0.7.5 起 hook 在检测到「无声明块」时把触发指令补进注入内容。
  **只有零足迹项目付这几行的代价，写了声明块的项目一个字都不多**（有反向用例）。

  > 教训：**「另一个机制会兜住」是最容易想当然的一类论断** —— 它听起来像系统
  > 设计而不像假设，所以不会被当成待验证项。这条从 0.7.0 起挂在已知限制里，
  > 写的时候没验，一验就是反的。
  >
  > 更该记的是：**这个结论一直躺在数据里。** B 组的 transcript 早就跑出来了，
  > 当时只读出「声明块起作用了」，没读出「零足迹模式不work」——
  > 同一份数据回答了两个问题，而我只问了一个。

- 断言 57 → 59。

## [0.7.4] - 2026-08-27

### 修复

- **0.7.0 同时改了两个 hook 的激活判据，只给一个加了测试。** `verify-artifacts.sh`
  的「`.agent/state.json` 也算激活信号」这条**漏测了三个版本** —— 也就是说
  `--no-claude-md` 装出来的项目能不能跑 `/verify-artifacts`，一直没人验过。

  补三个断言：零足迹下生效、两个信号都没有时仍退 2（正向那条不能把闸门整个
  拆了）、以及**报「todo.md 与 tracker 并存」时必须同时给出归档豁免办法**。

  最后一条是行为不是措辞：0.7.0 把这条知识从常驻的 15 行 context 挪进了报错
  文案，文案没了的话使用者面对违规无从下手。

  纪律随之收紧：**两个 hook 共用的判据要在两边都加用例。**

- 断言 54 → 57。


### 新增

- **`scripts/test-checkers.sh`** —— 四个 `check-*.py` 的回归套件（11 个断言，
  已接进 `validate.sh`，免费）。每个校验器至少一正一反：喂已知坏输入必须非零
  退出，喂好输入必须零退出。

  **为什么需要它**：一轮之内出过**四次**「新加的防线自己有毛病」——
  `check-command-names` 漏双引号前缀（抓不到它本该抓的那个 bug）、
  `check-readme-sync` 第一版没跑反向用例、发版 sha 核对拿 `HEAD` 比（文档提交
  就误报）、evals 判分把 skill 名写死成裸名（把一次成功判成失败）。

  四次同一个形状：**判据写完没有当场用真实数据跑一遍。**
  「防线本身也要被测试」这条一直写在 `CLAUDE.md` 里，但它是句口号不是套件 ——
  靠人自觉，四次里零次做到。

  纪律随之收紧：**新增 `check-*.py` 必须同时往这个套件里加一正一反。**

  两个刻意的实现选择：

  - `check-readme-sync.py` 现在接受一个可选 root 参数。**不是为了灵活，是为了
    它自己能被测试** —— 写死 `__file__` 的话，反向用例只能靠改真仓库的文件来
    构造，那比不测还糟。
  - bash32 的坏样本在**运行时拼装**，不让 `$VAR）` 这个模式出现在测试脚本源码里。
    用「跳过 `test-*.sh`」的豁免也能过，但那会削掉真实覆盖 —— 测试脚本本身也得
    能在 bash 3.2 上跑。**判据管得太宽和管得太窄一样是缺陷**，这次选的是不放宽。

  还给 `check-command-names` 那条「不查 `hooks/test-*.sh`」的豁免补了正反用例 ——
  0.7.3 刚加的豁免，没有用例的话下次有人收紧范围会静默把它去掉。


- **`evals/skill-deferral.sh`** —— 验 0.7.0 那次瘦身赖以成立的假设：
  **15 行声明块 + 一句触发指令，模型真的会去加载 `spec-github-bridge` 吗？**

  这个假设从 0.7.0 起就在那儿，**一次都没验过** —— 而它不成立的话，那次瘦身
  等于把细则删了。本仓自己的规矩是「标了『没实测』之后就该去测」。

  做法是两个只差一个声明块的脚手架项目、同一句话、headless 跑，从
  stream-json 里看有没有 `Skill(spec-github-bridge)` 的 tool_use。

  **2026-08-27 首跑（n=1）：**

  | | 声明块 | 结果 |
  |---|---|---|
  | A | 15 行 | ✅ 第 8 个工具调用时加载了 skill |
  | B | 无 | ❌ 全程没加载，转而「靠 plan.md 推断」直接设计表结构、问技术栈 |

  两组都有 `.agent/state.json`（0.7.0 起它本身就是 hook 激活信号），
  所以差异**只来自声明块本身**。

  会花 token，**不接进 `validate.sh`**。`--scaffold-only` 是免费自检路径。

  > 判据第一版把 skill 名写死成裸名，而实际是 `spec-guard:spec-github-bridge`，
  > 把一次成功判成了失败 —— 本轮第四次「新加的防线自己有毛病」。已改成按末段比对。

  > `claude plugin eval` 才是第一方格式，但它 early access、本账号未开通
  > （`plugin eval is currently in early access`）。开通后应迁过去。

  未升版本：`evals/` 在 `plugins/spec-guard/` 之外，对使用者零影响。

## [0.7.3] - 2026-08-27

### 新增

- **hook 自报版本。** 每轮注入的事实里多一行 `spec-guard: v<version>`，
  开发副本（直接从仓库跑、没经过 `/plugin` 安装）显示「开发副本」。

  加它的直接原因：`claude plugin update` 之后要**重启**才生效，而「重启了没有 /
  现在跑的是哪一版」此前只能去翻 `~/.claude/plugins/cache/*/.in_use` 标记猜。

  > 实测背景：连发五个版本之后本机装着的仍是 0.5.2，而当时**两个版本目录都有
  > `.in_use`** —— 旧的是会话占着的，新的是刚装上的。靠这个标记根本分不清
  > 「正在跑的是哪个」。

  实现上从 `CLAUDE_PLUGIN_ROOT` 的末段取版本号（装出来的路径形如
  `.../spec-guard/0.7.3`），**纯参数展开、零 fork** —— 这个 hook 每轮都跑，
  预算是 <1s，不能为一行版本号去读文件或起子进程。
  `CLAUDE_PLUGIN_ROOT` 缺失时回落到 `BASH_SOURCE`。

- 断言 52 → 54：未安装时报「开发副本」、安装路径下解析出版本号。

  > 这两个断言不能直接 grep 原始输出：`emit()` 有 jq 和 python3 两条路径，
  > python3 那条会把中文转义成 `\uXXXX`，grep 中文字面量抓不到。必须解 JSON。
  > —— 又一个「测试测的是空气」的近失事故。

### 修复

- **`check-command-names.py` 的判据范围收窄，排除 `hooks/test-*.sh`。**
  它把测试里构造的假路径 `CLAUDE_PLUGIN_ROOT=/x/spec-guard/9.9.9` 当成了
  斜杠命令 `/x`，直接把 `validate.sh` 判红。

  这条判据的自我定位是「**会到达用户眼前**的输出」，而回归测试的输出只给跑测试
  的人看。把测试纳进来，只会逼测试去迁就一个与自己无关的判据 ——
  **判据管得太宽和管得太窄一样是缺陷。**

## [0.7.2] - 2026-08-27

### 修复

- **`docs/design.md` 里有一条现在是错的。** 「额外检测的三种违规」表第三行写着
  *认领了 issue 但分支不含 issue 号 → 大概率在错误分支上工作* —— 那正是 0.6.0
  修掉的那个假断链判据，而设计文档还把它当成正确行为记着。

  这比 README 过期严重：本仓 `CLAUDE.md` 明写「改动前先读 design.md」，
  一份带着已废弃结论的设计文档，会让后面每次改动都建在旧结论上。

  同批修的还有：对象模型表（task 完成 = commit，模块完成 = PR）、
  「三个问题三个答案」（拆成四个，commit 和 PR 各答一个）、
  状态机（补 `MODULE_READY` / 两个模块分支态 / `IDLE(无活跃模块)`）。

- **0.7.1 把实跑的 PR 数写成了 5 个，实际是 4 个**（#65 #67 #70 #72）。
  已在 README 更正，并补上可核对的证据：PR #70 合并于 `13:20:34Z`，
  它 `Closes` 的 issue #69 关闭于 `13:20:35Z`，`reason=COMPLETED`。

  （按本仓惯例不回头改已发布的 0.7.1 条目，在这里更正。）

### 新增

- **`docs/design.md` 决策 6：声明块只放事实，过程进 skill。** 把 0.7.0 那次
  瘦身的完整推理落进设计文档 —— 包括**排掉的两个方案**及其官方依据：
  `@path` import 不减 context（*imported files load at launch*）、
  `.claude/rules/` + `paths:` 在「读到匹配文件」时才触发而约束要更早生效。

  排掉的方案和采用的方案一样重要 —— 没记下来的话，下一个人会再想一遍 `@import`。

- **`docs/walkthrough.md` 第三次实跑。** 前两次的教训都是「插件对项目现状的假设
  错了」；这次不一样 —— **假设没错，是约定自己变了**。

  > 第三条教训:改约定、改状态机、加测试是一个原子操作。分开做的中间态是
  > 「新约定 + 旧检查器」—— 那个状态下工具在对着正确的行为报错。

  顺带记下「怕留痕不是不验证的理由」：`/deliver` 的实测被跳过是因为
  「PR 在 GitHub 上删不掉」，结果一条免责声明在功能可用之后还挂了三个版本。

### 已知限制（补充）

- `design.md` 的「每条结论对应上游源码行号」这条纪律，只覆盖**上游行为**部分。
  决策 6 引的是 Claude Code 官方 memory 文档（会变），没有行号可锚。

## [0.7.1] - 2026-08-27

### 修复

- **README 落后了三个版本，而且是以最难看的方式落后的。** 它把两份模板
  **逐字内嵌**在「手动安装」章节里 —— 那是第二份真相源，从 0.5.x 一路分叉到
  0.7.0 没人发现：README 里躺着一份 106 行的旧块，还写着早已废弃的
  `<type>/<issue-number>-<slug>` 和「每个 task 一个 PR」。

  这个项目自己反复在说「两份真相源必然分叉，而分叉的现象是……」。这次它发生在
  插件自己身上，分叉的还正是**新用户第一眼会照抄的那段**。

- **一条已经不成立的免责声明还挂着。** 已知限制 3 写着「`/deliver` 的 PR 环节
  未经端到端实测」，理由是「PR 在 GitHub 上删不掉」。0.6.0 之后它就不成立了 ——
  在 `sentinel-livelab` 上真跑了 5 个 PR，`gh pr create` → `Closes #n` →
  合入默认分支自动关 issue → 分支清理，全链路验证过。

  **过期的免责声明比过期文档更糟：它在劝退使用者用一个已经证明可用的功能。**

- 另外五处同步到 0.6.x / 0.7.0：激活条件（新增 `.agent/state.json`）、
  命令表（`--replace` / `--no-claude-md`）、`/deliver` 的粒度、典型流程
  （改成模块分支 + `/build auto` + 禁 squash）、行为差异表补「交付粒度」一行。

### 新增

- **`scripts/check-readme-sync.py`** —— 断言 README 内嵌的声明块与
  `templates/*.md` **逐字节一致**，已接入 `validate.sh`。

  内嵌是刻意保留的（不跑命令的人和 agent 要能直接照抄），所以对冲的办法不是
  删掉内嵌，而是让分叉当场报错。README 里用 `<!-- SYNC:<name> BEGIN/END -->`
  圈出内嵌区，校验器比对围栏内容与模板。

  > 按本仓「防线本身也要被测试」的规矩，验过反向用例：往模板里注入一行，
  > 校验器报「README 17 行 / 模板 18 行 分叉了」并退 1；移除后恢复绿。

### 已知限制（补充）

- `check-readme-sync.py` 只管**声明块**这一处内嵌。README 里其他从别处抄来的
  内容（上游 SKILL.md 引文、`state.json` 样例、能力图样例）仍然是手工同步的，
  没有守卫。

## [0.7.0] - 2026-08-27

### 变更（需要重跑 `/setup-convention --replace` 迁移）

- **CLAUDE.md 声明块从 106 行瘦到 15 行**（local 模式 27 → 13）。搬走的过程细则
  全部进了 `spec-github-bridge` skill（219 → 277 行）。

  起因是使用者的实测：接入后项目 CLAUDE.md 321 行，声明块占 108 行 = 34%。
  而官方对 CLAUDE.md 的原话是 **target under 200 lines per CLAUDE.md file.
  Longer files consume more context and reduce adherence.**

  查文档时排掉了一个看起来对的方案：**`@path` import 省不了行数**。官方明说
  splitting into imports *helps organization but doesn't reduce context, since
  imported files load at launch* —— 它只解决维护，不解决占用。

  正解是官方自己给的：*If an entry is a multi-step procedure or only matters for
  one part of the codebase, move it to a **skill** or a path-scoped rule instead.*
  那 106 行里绝大部分是过程，而插件本来就有一个 skill，内容还重复了一半。

  留在 CLAUDE.md 里的只有两样：**推导不出来的事实**（路径、tracker 类型、
  几条硬禁令）+ **一句触发指令**（动 spec/拆任务/取任务/交付之前先加载 skill）。
  触发指令不能省 —— skill 是按需加载的，不写死的话模型可能在没加载 skill 的
  情况下就把 `SPEC.md` 建到根目录了，而那正是这个块当初存在的理由。

  `.claude/rules/` + `paths:` 前缀作用域**没有采用**：它在 Claude 读到匹配文件时
  才触发，而「不要在根目录建 SPEC.md」恰恰要在还没读任何文件时就知道。

### 新增

- **`/setup-convention --replace`** —— 已存在的声明块就地升级到当前模板。
  只替换 `BEGIN`/`END` 之间，标记外一个字节不碰（有反向用例钉住）。
  没有它的话老用户没法迁移：原来遇到已存在的块是直接跳过的。
- **`/setup-convention --no-claude-md`** —— 完全不写声明块。
- **`.agent/state.json` 成为第二个激活信号。** 两个 hook 原先只认 CLAUDE.md 里的
  约定标题，现在「有标题」或「有 state.json」满足其一即可。这是上一条的配套：
  不写声明块的项目也得让 hook 认得出自己管的项目。`.agent/` 是本插件自己的目录，
  拿它当信号不会污染无关仓库 —— 「默认不生效」那条不变量仍然成立。

### 改进

- **把「归档豁免」这条知识挪进报错文案。** 原先它占声明块 15 行常驻 context，
  而它只在报「todo.md 与 tracker 并存」那一刻才有用。现在两个 hook 的报错里都
  带上「在前 10 行内写『已归档』即可豁免」—— **只在真报错时才花 context**。
  顺带发现 HTML 注释是免费的：官方原话 block-level HTML comments *are stripped
  before the content is injected into Claude's context*，所以 BEGIN/END 标记不计成本。

### 已知限制（补充）

- **`--no-claude-md` 模式下模型对目录约定的感知晚一步。** hook 挂在
  `UserPromptSubmit` 上，注入时机其实早于对话，但它注入的是**状态**不是**约定**；
  选这个模式的项目要么自己在别处写一句「动 spec/tasks 前先加载
  `spec-github-bridge`」，要么接受这一点。
- **`--replace` 认的是完整标记行**（`<!-- BEGIN:agent-skills-convention -->`）。
  手工改坏了标记（比如删掉 `<!-- -->`）的项目会被当成「没装过」而追加第二块。

## [0.6.1] - 2026-08-27

### 修复

- **0.6.0 给「禁止 squash」写了个错的理由。** 原话是「squash 把 N 条 message
  压成一条，只有最后一个 issue 会关，其余留在 open」—— 这条是从机制推的
  （0.6.0 的已知限制里标了「没实测」），推错了。

  实查了仓库设置：GitHub 的 squash 默认是
  `squash_merge_commit_message: COMMIT_MESSAGES`，**会把每条 commit message
  拼进压缩后的正文**，那些 `Closes #n` 通常还在、照样生效。

  规矩本身不变，理由换成真的那两条：

  1. 那个拼接依赖一个**可改的仓库设置**（换成 `PR_BODY` 就全丢），合并对话框里的
     正文也随时能手改 —— 拿它当保证等于把 issue 状态挂在一个没人盯着的开关上
  2. `/build auto` 刻意做到一个 task 一条 commit，为的是**任意一点都能干净回滚**；
     squash 压成一条后这个性质当场消失，出事只能整个模块一起 revert

  第 2 条才是硬理由 —— 它跟仓库设置无关，改不掉。

  > 教训：把「没实测」标出来是对的，但标了之后就该去测。这条本来一句
  > `gh api repos/{owner}/{repo} --jq .squash_merge_commit_message` 就能验。

### 已知限制（更正）

- 0.6.0 的「squash 合并没有实测」一条**作废** —— 已查明默认行为。
  仍未实测的是：把 `squash_merge_commit_message` 改成 `PR_BODY` 之后
  closing keyword 是否真的全丢（按字面推断是，没跑过）。

## [0.6.0] - 2026-08-27

### 变更（约定层，会影响已落地的项目）

- **PR 粒度从 task 提到 module。** 原先是「一个 task 一条分支一个 PR」，
  现在是「一个模块一条分支一个 PR，每个 task 一条带 `Closes #n` 的 commit」。

  起因是使用者的实跑反馈：任务拆得细，于是每推进一个 task 就要停下来开 PR、
  等合并，**一个需求被切成 N 个互不相干的合并事件**，连贯性没了。

  查了下这个成本买到了什么 —— 在那个项目上：main 没有分支保护、
  `allow_auto_merge` 是 false、CI 是 `on: push` 也跑、最近 10 个 PR
  从开到合中位数 1 分 20 秒且全是 1 commit、开合是同一个人。也就是说
  PR 既不是评审关口也不是 CI 关口也不是保护关口，唯一买到的是
  `Closes #n` 那条追溯链接 —— 而那条链接，模块级 PR 一样给。

  **上游从来没要求过一个 task 一个 PR。** agent-skills 的 `/build` 到 commit
  为止，`/build auto` 是一路 commit 跑完整个 plan；task 级 PR 是本插件
  0.2.0 自己加的，这次把它收回去。

- **合并策略从此有硬约束：只能 merge commit 或 rebase，不能 squash。**
  task issue 靠 commit message 里的 closing keyword 关闭（官方原话：the issue
  will be closed when you merge the commit into the **default branch**），
  squash 把 N 条 message 压成一条，只有最后一个 issue 会关，其余留在 open，
  而 `/next` 会把它们当成没做完、重新取出来做第二遍。

### 修复

- **模块分支会被报成假断链。** `phase-guard.sh` 的
  「已认领 X 但当前分支不含 issue 号」那条，遇到 `feat/<module-id>` 这种
  不含 issue 号的模块分支必然命中 —— 改约定不改状态机的话，每轮都在报。
  新增 `ON_MODULE_BRANCH` 判定，且是**末段整段匹配**而非子串包含：
  子串匹配下 module id 叫 `a` 时分支 `master` 会被当成模块分支（已加反向用例）。

### 新增

- `phase-guard.sh` 新增 `MODULE_READY` 阶段与 `TASKS_DONE_HERE` 计数。
  模块级 PR 下 task issue 要到合并才关，`OPEN_TASKS` 全程不减 ——
  「这个模块做完没有」只能数 `<默认分支>..HEAD` 里的 closing keyword。
  这个数**只喂「建议下一步」，不进 `broken()`**：数偏了顶多建议早了，
  不会变成一条假断链。
- `/deliver` 开 PR 前先核对 task 覆盖，没覆盖齐就不开、报还差哪几个。
- 断言 40 → 45（`test-phase-guard.sh` 19 → 24，新增 5 条含 2 条反向用例）。

### 已知限制（补充）

- **`TASKS_DONE_HERE` 只认 `main`/`master` 作为基线分支。** 默认分支叫别的
  （`trunk`、`develop`）时它恒为 0，表现是 `MODULE_READY` 永远不出现、
  一直建议「继续取任务」。这是**保守失败**（不会误报断链），但会让人
  自己判断什么时候该开 PR。
- **squash 合并没有实测。** 官方文档只写了 commit message 的 closing keyword
  在合入默认分支时生效，没写 squash 时怎么处理被压掉的 message。
  上面「squash 会漏关 issue」是从机制推的，不是跑出来的 —— 所以约定写成
  「禁止 squash」而不是「squash 时要注意」。

## [0.5.2] - 2026-08-27

### 修复

- **P0：hook 每轮注入的「建议下一步」指向一个不存在的命令。**
  `phase-guard.sh` 三处、`setup-convention.sh` 两处、`verify-artifacts.sh` 一处
  仍写着 `/planning`，模型照着调就报 `Unknown skill: agent-skills:planning`。

  0.4.1 那次 `/planning` → `/plan` 的修复**只扫了 `*.md`**（用的
  `rglob('*.md')`），**shell 脚本一个都没碰** —— 而 `phase-guard.sh` 恰恰是
  每轮发言都注入的那个。一次不完整的替换，比不替换更隐蔽：文档全对了，
  真正到用户眼前的输出还是错的。

### 新增

- `scripts/check-command-names.py` —— 校验**用户可见输出**里提到的斜杠命令
  真实存在，已接入 `validate.sh`。检查范围刻意限定在会到达用户眼前的三处
  （`hooks/*.sh`、`templates/*.md`、`commands/*.md`）；`docs/` 与 CHANGELOG
  不查 —— 它们要能讨论「`/planning` 是错的」这件事本身。

  > 这个 lint 的第一版**漏了双引号前缀**，抓不到 `NEXT="/plan …"` 这种写法，
  > 也就抓不到它本该抓的那个 bug。加断言验证「注入坏名字要报错」之后才发现。
  > **防线本身也要被测试。**

  第二版补齐三处（用户追问「其他斜杠命令你也检查下」后全量审计出来的）：

  - **skill 名此前零覆盖** —— 命令文里的 `invoke <name>` 引用的是 skill，
    和斜杠命令是**两个命名空间**（`/plan` 是命令，`planning-and-task-breakdown`
    是 skill，都存在且不可互换）。现在分开校验。
  - **Claude Code 内建命令**（`/plugin`、`/reload-plugins` 等）加入允许集，
    避免模板里写安装步骤时误报。
  - 两个命名快照标注为**手工维护、会过期**，并接进
    `docs/upstream-analysis.md` 的重新核对清单第 7 条。

## [0.5.1] - 2026-08-26

### 修复

- **「项目在两个 initiative 之间」被误报为断链。** 状态机原先只看
  「有 spec 且无模块 issue」就报断链,不问是不是**刻意空闲**。一个上一批全部交付、
  下一批还没起的项目 —— 7 份 spec、issue 全关、没有在做的活 —— 每轮都被催
  「去把能力图落成 issue」。又是一次假断链。

  现在区分三种情况:

  | state.json | activeModule | 判定 |
  |---|---|---|
  | 存在 | 空 | `IDLE (无活跃模块)` —— **不报断链**,这是刻意声明的空闲 |
  | 存在 | 有值但无 issue | 真断链,文案指名 `activeModule=[x]` |
  | 不存在 | — | 真断链,文案说明是缺 state.json |

  断链文案也从笼统的「没有模块 issue」改为指名道姓,便于定位。

## [0.5.0] - 2026-08-26

### 新增

- **识别归档的任务清单，不再误报。** 检查器原先分不清「归档记录」和「活清单」——
  一个已完成模块的 `todo.md` 是**历史**，把它当成「与 tracker 并存」来报违规是误报。

  约定：文件**前 10 行**内出现 `已归档` 或 `ARCHIVED`（不区分大小写）即视为归档，
  从并存检查和命名空间检查里排除。限定前 10 行是刻意的 —— 只认头部声明，
  避免正文里偶然提到就被误判。

  在一个真实项目上验证：6 份归档 + 根下两份不再报违规，**只剩唯一活的那份被正确指出**。

  这补的是设计上的一个盲区：插件**假设你从零开始**。对已经长出自己体系的项目，
  它原先只会对着历史记录挑毛病 —— 而「假断链比不报断链危害大得多」。

### 已知限制（补充）

- **插件仍假设从零开始。** 约定块是「替换」而非「适配」——如果项目 `CLAUDE.md`
  里已有冲突的目录约定，`/setup-convention` 会**追加**出两套互相矛盾的指令，
  比覆盖更糟（agent 会看到两个冲突的真源）。落地前请先人工核对现有约定。

## [0.4.1] - 2026-08-26

### 修复

- **P0：`gh issue list --parent` 这个 flag 根本不存在。** `--parent` 只在
  `gh issue create` 上；`gh issue list` 有 `parent` / `subIssues` 这两个
  **`--json` 字段**，但没有同名 flag。四处受影响：

  | 位置 | 后果 |
  |---|---|
  | `phase-guard.sh:101` | **GitHub 层从来没跑过**，每次静默落进「gh 不可用，降级判定」 |
  | `verify-artifacts.sh` | Epic ↔ 能力图交叉校验永远 skip |
  | `SKILL.md` 操作三 | `/next` 取任务命令直接 `unknown flag` |
  | `CLAUDE.md` 模板 + README | 使用者照抄照错 |

  全部改用 REST sub-issues 端点
  （`gh api "repos/{owner}/{repo}/issues/<n>/sub_issues"`，`{owner}`/`{repo}`
  占位符自动解析，仓库外干净失败）。REST 返回**所有状态**，已补 `state == "open"` 筛选。

  **12 个 phase-guard 断言全绿却没抓到** —— 它们跑在没有 GitHub 的临时仓库里，
  降级分支正是那里的预期行为，测试恰好覆盖了假象。只有真连 GitHub 才暴露得出来。

- **文档里 22 处命令名写错**：上游的拆解命令在 Claude Code 里叫 **`/plan`**，不是
  `/planning`。上游有两套等价但文件名不同的命令目录 —— `commands/planning.toml`
  与 `.claude/commands/plan.md`，**Claude Code 读的是后者**。照着旧文档敲会得到
  「命令不存在」。（skill 目录名 `planning-and-task-breakdown` 未变，那些路径引用是对的。）

### 新增

- `docs/walkthrough.md` —— 端到端实跑记录。真实仓库、真实产物、真实输出：
  `/setup-convention` → `/sync-map` → `/plan` → `/next` → `/build` →
  `/verify-artifacts`，跑完 6 个 issue 全部 `deleteIssue` 真删除、零残留。

### 变更

- 已知限制 3 从「gh 命令未经端到端实测」收窄为「仅 `/deliver` 的 PR 环节未实测」

### 已知限制（补充）

- **降级必须可观察。** 三条铁律的第 2 条「探测失败就降级，不误报」是对的，
  但一个**永远在降级**的探测器和一个坏掉的探测器没有区别。目前没有机制
  区分「这次降级是对的」和「它一直在降级」。

## [0.4.0] - 2026-08-26

### 新增

- **github 模式自适应 issue types**，个人仓库不再被挡在门外。

  0.3.0 里 `/setup-convention github` 探测到没有 issue types 就**硬阻塞**。
  实测下来这个判断过重了 —— 三个 gh 参数的可用性并不一致：

  | gh 参数 | 依赖的 GitHub 功能 | 个人免费仓库实测 |
  |---|---|---|
  | `--type Feature/Task` | issue types | ❌ `type "Task" not found; available types:`（空） |
  | `--parent` | sub-issues | ✅ 层级建立成功，REST + GraphQL 双向确认 |
  | `--add-blocked-by` | issue dependencies | ✅ 依赖建立成功 |

  **只有 issue types 是组织级的**（GitHub 员工在 community#175785 的原话：
  *available only for organizations ... not for personal repositories*）。
  而 `/next` 的第一条筛选规则「排除 `issueType != Task`」本来就冗余 ——
  模块 issue 的 sub-issue 按构造就是 task，层级已编码了这个身份。

  所以不新增 tracker 模式，改为让 `github` 模式自适应：`/setup-convention`
  探测一次，把结果写进 `.agent/state.json` 的 `issueTypes`，
  `spec-github-bridge` 据此决定加不加 `--type`。**流程一步不少**，
  只失去按 type 跨仓筛选的能力。

- `spec-github-bridge` 增加「issue types 可用性」章节和两条 Common Rationalizations

### 变更

- `/setup-convention github` 在个人仓库上从**阻塞**改为**降级 + 告知**

### 已知限制（补充）

- 硬加 `--type` 会**留下孤儿 issue** —— gh 先把 issue 建出来再校验 type，
  失败时不回滚。实测确认。所以必须读 `state.json` 的 `issueTypes`，不要试错。
- 额度（官方文档）：sub-issue 每个父 issue **100 个**、嵌套 **8 层**、
  每种依赖关系 **50 个**。本插件只用到 3 层，远未触顶。

## [0.3.0] - 2026-08-26

### 新增

- **`/verify-artifacts`** —— 产物落地校验（只读）。`phase-guard` 回答「现在在哪个
  阶段」，它回答「已经落下的产物对不对」。整套约定从头到尾都是**提示词**，
  软指令必须配硬检测，否则跑歪了没人知道。覆盖 9 类检查：

  | 层 | 检查 |
  |---|---|
  | 能力图 | 模板占位符未填 / 评审未勾选 / module id 非 kebab-case |
  | spec | **文件名 ↔ 能力图 module id 比对** |
  | 目录 | 根目录 `SPEC*.md` / `tasks/` 缺命名空间 / `todo.md` 与 tracker 并存 |
  | plan | tracker 模式下仍是 checklist / 没写 tracker 位置 |
  | GitHub | Epic sub-issue 数 ≠ 模块数 / issue 正文粘贴 spec 全文 / PR 缺 `Closes #n` / 分支 task 不属于 activeModule |

  其中 spec 文件名比对补的是最阴险的一类漂移：`phase-guard.sh:80` 只数
  `spec/*.md` 的**数量**，从不跟能力图比对 module id。能力图写 `identity`、
  模型建了 `spec/user-identity.md`，阶段照样往前推，下游全部静默错位。

- `setup-convention.sh` 增加 **issue types 可用性探测**。`--type Feature/Task`
  依赖 GitHub issue types，这是**组织级功能，个人仓库用不了**。原先只查 gh 版本
  和 `--parent` 参数存在性 —— 这两项在个人仓库上一样全绿，然后 `/sync-map`
  的第一条命令就炸。探测不到时降级为警告，绝不假阻塞。
- `test-verify-artifacts.sh` —— 16 个断言，含「合规项目零误报」和「local 模式的
  checkbox 不误报」两条反向用例

### 修复

- **P0：`setup-convention.sh` 的 github 前置检查有 40% 概率假阻塞。**
  `gh issue create --help | grep -q -- "--parent"` —— `grep -q` 命中即关管道，
  还在输出的 `gh` 吃到 SIGPIPE(141)，`set -o pipefail` 把它传出来，判断为假。
  **实测 30 次里 12 次假阻塞**，且错误信息是误导性的「跑 type -a gh 检查 PATH」。
  改 herestring 后 30/30 稳定。
- 同类问题全仓库扫出并修掉 5 处（`setup-convention.sh` ×2、`phase-guard.sh` ×1、
  `validate.sh` ×1、`test-phase-guard.sh` ×1）。其中 `phase-guard.sh:94` 的
  `find tasks -name todo.md | grep -q .` 会漏报「todo.md 与 tracker 并存」。
- CLAUDE.md 加了这条禁令，`/verify-artifacts` 的实现和测试都不用管道

### 已知限制（补充）

- github 模式需要**组织仓库**，个人仓库请用 local 模式
- `verify-artifacts` 的 GitHub 层仍未经端到端实测（缺可用的组织仓库）

## [0.2.1] - 2026-08-26

### 修复

- **P0：macOS 上 hook 静默崩溃。** `$VAR` 后紧跟全角括号（如
  `"…Closes #$BRANCH_ISSUE）"`）时，macOS 自带的 bash 3.2 会把该字符的首字节
  吃进变量名，配合 `set -u` 直接致命退出。共 7 处：

  | 文件 | 影响 |
  |---|---|
  | `phase-guard.sh` ×2 | 进入 `TASK_READY`（准备开 PR 那一刻）hook 就死，且 hook 失败是静默的 |
  | `setup-convention.sh` ×4 | local 模式安装无声失败，`CLAUDE.md` 声明块根本没写进去 |
  | `validate.sh` ×1 | 缺执行位时的提示语 |

  全部改为 `${VAR}`。

### 新增

- `scripts/check-bash32.py` —— 静态检查这一类多字节解析陷阱，已接入 `validate.sh`
- CI 加 macOS matrix 并显式用 `/bin/bash` —— 原先只跑 ubuntu（bash 5，多字节安全），
  所以这个 bug 在 CI 里永远是绿的

### 变更

- 模板里过期的「本块由 install.sh 生成」改为实际的 `/setup-convention`
- README / CLAUDE.md 的测试数量从「12 个场景」更正为 15 个断言
- **明确最低上游版本：commit `5a5ea45`（2026-08-21）。** 更早的版本里
  `spec-driven-development` 的 Phase 0 和 `planning-and-task-breakdown` 的
  Task List Target **根本不存在**（实测 `7829ffd` / 2026-07-26：175 个文件、
  两者全树 0 命中），本插件的五个缺口全部悬空、症状是「Phase 0 永远不触发」。
  已写进 README 依赖章节、`docs/design.md` 参考章节和 `docs/upstream-analysis.md` 顶部
- `docs/upstream-analysis.md` 按 commit `5a5ea45` 重新核对：**五个缺口一个都没被上游补掉**。
  补了结果表、逐条验证命令；修正行号漂移（Task List Target 155→150、三条约束 60-64→59-63）；
  注明上游 `hooks/` 目录新增了 `sdd-cache-*` / `simplify-ignore` 但**均未注册进 `hooks.json`**

## [0.2.0] - 2026-08-26

### 新增

- `hooks/setup-convention.sh` —— **确定性执行**的安装脚本，`/setup-convention`
  改为调用它而不是让 LLM 逐步解释。写文件的幂等性和安全性不能有非确定性。
- `--dry-run` 支持
- `/teardown-convention` —— 移除项目约定，保留用户的 spec/plan 内容
- 完整的手动安装章节（README），含可直接复制的 CLAUDE.md 声明块原文，
  AI agent 可不依赖命令自行完成安装
- setup 脚本的回归测试（dry-run 零写入 / 不覆盖用户内容 / 幂等）

### 修复

- 测试脚本在 `cd` 到临时目录后相对路径失效，导致误报

### 已知限制（补充）

- `spec-github-bridge` 里的 gh 命令未经端到端实测
- 已启用 + `gh` 网络调用的 hook 耗时未实测（无 gh 环境下为 ~154ms）
- 文案硬编码中文
- Windows 需 WSL 或 Git Bash

## [0.1.0] - 2026-08-26

首个版本。

### 新增

- `phase-guard.sh` —— UserPromptSubmit hook，注入链路状态并检测断链
  - 9 个阶段的状态机（IDLE / MAP_ONLY / SPECED / TRACKED / PLANNED / TASK_CLAIMED / BUILDING / TASK_READY / MODULE_DONE）
  - 三种 tracker 模式：`github` / `none` / `other`
  - `gh` 不可用时自动降级，不误报
  - 未声明约定的仓库静默退出
- `/setup-convention` —— 在项目中落地目录约定
- `/phase` —— 主动查询链路状态
- `/sync-map` `/next` `/deliver` —— GitHub Issue 流程命令
- `spec-github-bridge` skill —— 四个操作的完整流程
- 三份模板：GitHub 模式声明块、本地模式声明块、能力图

### 已知限制

- 任务层自动化只覆盖 `github` 和 `none` 两种模式，GitLab / Jira 仅检测到 plan 层
- 需要 `gh` ≥ 2.94.0（`--type` / `--parent` / `--blocked-by`）
