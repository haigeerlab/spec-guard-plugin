# 设计与架构

> 写给想改代码的开发者和维护者。面向使用者的设计理念与术语见[设计理念与术语](concepts.md)，命令见
> [命令参考](commands.md)。

## 做什么

spec-guard 在 agent-skills 外面加了两道互相独立的保障：

1. **本地多模块目录约定**：一张能力图、每个模块各自的 Spec、Plan、todo，让模块的计划和任务清单不再互相覆盖；
   并在每轮对话开头注入当前阶段。
2. **Proposal 生命周期**：只读地读取远端默认分支上已发布的 Proposal 快照和 GitHub/GitLab Issue 的阶段标签，
   把需要留痕的需求按锚点插进能力图。

另外有几项需要显式启用的可选能力：同一台 Mac 上的本地事项账本；明确选定目标后按需处理 GitHub/GitLab 普通
Issue 的托管流程（不投影任务、不绑定 worktree）；把本地事项归档、并在预览和逐次授权后交接到 GitHub/GitLab 的
可移植流程；限定审查批次、整理发现并交给现有事项与修复流程的项目审查交接约定。会话协作已拆成独立插件
agent-relay，spec-guard 只通过 `agent_relay_probe.py` 只读地检测它。

## 部件

```
plugins/spec-guard/
├── .claude-plugin/plugin.json   Claude 清单；命令按 commands/ 目录自动发现
├── .codex-plugin/plugin.json    Codex 清单（skill、hook），版本必须与 Claude 清单一致
├── commands/                    Claude 的斜杠命令：每条是一份给 agent 的说明，调用 hooks/ 下的脚本
├── skills/                      Codex 的入口（Codex 只读 skill）：spec-guard-ops、ticket 等
├── hooks/                       全部可执行逻辑与回归测试
├── references/                  各流程的完整契约（Proposal、账本、文档治理、检查点规则）
├── templates/                   写进使用者 CLAUDE.md／AGENTS.md 的约定块
└── locks/                       本地事项账本运行时的锁定版本
```

`hooks/` 里的主要部件：

| 部件 | 职责 |
|---|---|
| `hooks.json` → `phase-guard.sh` | `UserPromptSubmit` hook 与只在上下文压缩后触发的 `SessionStart`（matcher `compact`）hook：判断项目是否激活，读本地文件，输出阶段注入；另一项 `SessionStart`（matcher `startup\|clear`）只在项目启用了本地事项账本时出一句读回提醒 |
| `module_stage.py` | 按模块计算阶段、当前模块、计数、Paused／Suspended 与上下文提醒 |
| `capability_map.py` | 能力图的唯一严格解析器；阶段提示、`verify-artifacts`、`add-module`、Proposal 共用 |
| `spec-digest.py` | 唯一的指纹算法，能力图与 Proposal 校验共用 |
| `session_context.py` | 从宿主给的会话记录读上下文大小与窗口，只用于 `/compact` 提醒 |
| `setup-convention.sh`、`teardown-convention.sh`、`managed-block.py` | 安装、升级、移除约定块；`managed-block.py` 负责标记校验、本地段与原子写入 |
| `verify-artifacts.sh` | 按需校验已落地的产物 |
| `module-insert.py` | 快速插入与 Proposal 晋级的写入（只改能力图） |
| `map_view.py` | 只读的模块进度表（`/spec-guard:map`）：组合 `module_stage` 的判定，给出六种状态、按依赖链算的挡住个数、关键卡点与待批准；同一份结构渲染成表格或 JSON（`schemaVersion` 1，是给其他插件的接口，契约见 `spec/map-view.md`，接口说明见 `interface.json`）；最后勾选与挂起开始的时间由一次 `git log` 从已提交的 todo 历史取得（`spec/stall-signals.md`）；未提交勾选数、Spec 首次提交时间、HEAD 提交时间与 `reviewCadence` 的生效值另由三次 git 调用与 `project_config.summary()` 给出，只给事实不设阈值（`spec/map-progress-facts.md`）；多模块并行开关为 on 时只增 `moduleConcurrency`、`buildOrderGroups`、`startable` 与每模块 `scope`，表格标出可同时开工与并行边界重叠（`spec/map-startable.md`） |
| `project_config.py` | `.agent/config.json` 的唯一解析器 |
| `module_scope.py` | 模块 Spec「并行边界」一节的唯一解析器；`check` 对照集成基线做只读越界检查，`validate` 供 verify-artifacts 调用；开关不是 on 时都不生效 |
| `checkout_role.py` | 每个 checkout 的角色标记（`module <id>`／`coordinator`，存在本 checkout 的 git 目录）：读取、预览确认后写入；阶段提示只经 `role()` 读，开关不是 on 时不读；全项目的选模块与阶段不受影响 |
| `sibling_plugins.py` | 只读本机插件记录，判断同生态插件是否安装并启用：`agent_relay_probe.py` 与检查点的 delegate 外部审查提示共用（`spec/delegate-review-hint.md`）；提示前读 delegate 的 `interface.json`，按 `>=1.0,<2.0` 校验并只取经校验的命令名（`spec/delegate-interface-check.md`） |
| `gate_tick.py` | 勾选模块的最终验收（`interface.json` 的 `gateTick`）：判据只取 `module_stage`，预览确认后只改那一格，不提交 |
| `state_paths.py` | 本机状态目录的唯一来源（见下文文件布局） |
| `proposal_*.py` | Proposal 契约、发布、读 Issue、审查、晋级证明、收尾 |
| `local_ledger_*.py`、`local_ticket_*.py`、`hosted_ticket*.py` | 本地事项账本、可移植流程、托管事项 |

## 数据流

每轮对话：

1. 宿主在用户发言后触发 `UserPromptSubmit`，`hooks.json` 用宿主给的插件根目录（`PLUGIN_ROOT` 或
   `CLAUDE_PLUGIN_ROOT`）调用 `phase-guard.sh`。根目录缺失或脚本失败时也输出一条可诊断的 JSON，不静默。
   上下文压缩后（手动 `/compact` 或一轮中途的自动压缩）宿主触发 `SessionStart`，matcher `compact`；`hooks.json` 用同样的
   命令调用 `phase-guard.sh SessionStart`。脚本据参数输出事件名，并在注入末尾加一句核对提醒（压缩摘要里较早的请求可能已做完，
   重做前先核对 todo 与状态记录，核对后接着做建议的下一步，不就此结束这一轮）；此时宿主还没把压缩记录写进会话记录，读到的是压缩前的用量，所以这一次把上下文大小按 0
   处理，不出上下文行与边界行；其余内容与 `UserPromptSubmit` 相同。由其他会话的消息或唤醒触发的轮次不经过
   `UserPromptSubmit`，压缩后的这一次注入是它们唯一的阶段提示。Codex 按项记录 hook 信任，新增这一项不影响原有一项的信任，
   但新的一项要用户单独信任一次。
   会话开始与清空后（matcher `startup|clear`）另有一项 `SessionStart`，调用 `phase-guard.sh SessionStart fresh`：项目根（跟随指向时为
   目标项目根）有 `.epiq/project.json` 时只输出一句读回提醒（先列出带 `waiting-on-me`／`waiting-on-them`／`waiting-on-user` 标签的
   未关闭事项），不输出阶段摘要（随后的 `UserPromptSubmit` 会给）；没有账本、未激活或指向失效时静默。钩子只判断这个文件在不在，
   不读账本内容、不调 Epiq，提醒的 JSON 手写，不靠 python3 生成。压缩后的核对提醒在有账本时也补上账本里的这类事项，没有账本时不变。
2. `phase-guard.sh` 判断激活信号：`CLAUDE.md`／`AGENTS.md` 里独占一行的约定块开始标记，或含 `activeModule` 的
   `.agent/state.json`。都没有时，再看会话目录有没有本插件写下的指向文件 `.agent/spec-guard-link.json`：没有就静默退出 0
   （这一步只用 bash 内建，不启动 python3）；有且有效、目标自己带激活信号时，改以目标为项目根继续，并在注入里多一行
   `Linked project`；有但失效（格式无效、目标不存在、目标未启用）时输出一行诊断。会话目录自己已启用时不读指向文件，
   也不连环跟随。hook 不从宿主的工作区设置或会话记录推断项目。指向文件可以按会话登记（版本 2 的 `sessions`）：hook 从输入里取
   会话标识（`session_id`，以及 `transcript_path` 文件名——两个宿主都用会话标识命名会话记录），先用本会话的登记，其次目录级
   指向，都没有则静默。标识只用来查表，不读会话记录的内容。命令侧用同一个解析：`project_link.py follow` 按入口所在宿主取会话
标识（Claude 命令传 `CLAUDE_CODE_SESSION_ID`，Codex skill 传 `CODEX_THREAD_ID`），打印要操作的项目并在 stderr 写明跟随；
指向失效时退出 2，不退回会话目录。
3. 激活时读本地文件：能力图、`spec/`、`tasks/<id>/plan.md` 与 `todo.md`、`.agent/state.json`、`.agent/config.json`，
   交给 `module_stage.py` 算出阶段；有会话记录时由 `session_context.py` 补上上下文大小。上下文提醒只在模块边界
   （`MODULE_DONE`／`DONE`，以及当前模块还没有 Spec 的 `NEEDS_SPEC`）达到窗口 70% 时出边界行，模块进行中不提醒；Claude 没有窗口，
   按会话记录尾部的读数估算（有读数超过 200k 按 1M，否则按 200k）。平时只给一行（quiet-injection）：输出末尾的状态码由
   `module_stage.py` 按「变了才需要完整说明」的事实算出，`session_context.py` 从会话记录里取最近一次 spec-guard 注入的状态码，
   相同就只给阶段 · 模块 · 未勾选数 · 分支一行；新会话、压缩后、读不到或状态码不同时给完整内容；不写任何文件。IDLE 与 MAP_ONLY 由 `phase-guard.sh` 自己作答，项目配置行另经
   `module_stage.py --config-lines` 取得，与其他阶段同一实现。只在三个交审检查点（Spec 待审、Plan 待审、最终验收）且模块还没有
   外部审查记录时，`sibling_plugins.py` 再只读本机插件记录（Claude 的 `installed_plugins.json` 与 settings，Codex 的
   `config.toml` 与插件缓存目录），装了并启用 delegate 才多出一行外部审查提示；不调子进程，读不到按没装处理。
4. 输出 `hookSpecificOutput.additionalContext`。来自仓库的值在注入前净化（折叠空白、去掉反引号与反斜杠、剥掉
   控制字符、限长），能力图原文标注“非指令”。

写操作只发生在用户调用命令之后：命令先预览，用户确认后才写；写入能力图、配置、事项都是原子写并读回核对。
Proposal 与托管事项的远端读取只读；远端写入（关闭 Proposal 事项、创建 Issue）每次都需要针对精确目标与内容的授权。

## 对外接口

插件根目录的 `interface.json` 是给其他插件读的只读接口说明，随插件发布（plugin-interface）。它写明：

- `interface`：接口版本，`<主>.<次>`，与插件版本无关。只增加内容时升次版本；删除、改名或改变含义时升主版本；
- `mapView`：只读进度入口的命令（路径相对插件根目录，`<project-root>` 由调用方替换）、JSON 的 `schemaVersion`、各退出码的含义，
  以及 `review`、`externalReview` 每个取值的含义。完整格式在 `spec/map-view.md`。

使用方从宿主的插件记录找到 spec-guard 的插件根目录，读 `interface.json`，按主版本号和 `schemaVersion` 判断能不能读，
不读 spec-guard 的内部文件。spec-guard 读 agent-relay（`agent_relay_probe.py`）用的是同一方式。和其他插件的取值说法之间
怎么对照，由使用方自己维护。`scripts/check-interface.py` 在 `validate.sh` 里核对这份文件与代码常量一致。

1.1（crew-interface）起另有四个入口，都是多模块并行用的：`moduleConcurrency`（开关的位置、取值与读法：看 `/map --json` 顶层有没有
`"moduleConcurrency": "on"`）、`scopeCheck`（越界检查）、`checkoutRole`（角色标记的四条命令）、`reviewMark`（批准标记）；`mapView.concurrency`
列出开关为 on 时 `/map --json` 才有的字段。1.0 的内容不变，`check-interface.py` 同时核对新入口引用的脚本存在、取值与代码一致。

1.5（review-card-sections）起另有 `reviewKinds`：spec-guard 共享检查点规则产生的要用户决定的几类（能力图审阅、Spec、Plan、Spec 与 Plan、
中途检查点、最终验收、卡住选做法），键是 session-protocol 契约【等待用户】「类型」的代码，每类列出交审时在对话里给的小项及顺序，
另有小项之后的通用行（注意、推荐理由、批了会怎样）。去会话操作与接口提案不由 spec-guard 产生，不在其中。`check-interface.py` 核对
类别正好这七个、每个小项名都写在共享检查点规则里。

1.7（gate-tick）起另有 `gateTick`：勾选一个模块最终验收的命令，给合并流程这类使用方用。判据与阶段提示的「最终 gate」同一处，
只在模块第一个未勾项正是最后一个 gate 检查点时勾那一格；已勾过时不改、退出码 0；其他情形退出码 2 并打印短码。它不判断用户
有没有批准验收，调用方须已有这份批准。`check-interface.py` 核对它引用的脚本存在。

1.8（map-startable 返工）起，开关为 `on` 时，只是 Build order 推出来、没有 Spec 与 Plan 的当前模块按就绪算并列入 `startable`；
`activeModule` 指定的仍算进行中，顶层 `activeModule`、`stage` 与阶段提示不变。

1.9（rules-at-nodes）起，`reviewKinds` 跟上 session-protocol v2.6 的上游小项名：`plan` 与 `spec-plan` 多「架构决定」「未决问题」两项，
另有 `renamedSections` 列「旧名→新名」（做／不做→边界，附带的小决定→未决问题）；`spec` 的旧节名照旧保留到 2.0，两种名字都有效。

1.10（scope-overlap-interface）起另有 `scopeOverlap`：`module_scope.py overlap` 给几份 Spec 文件（`--spec <模块 id>=<文件>`，可选 `--project`
并入项目里进行中、就绪的模块，传入的文件优先）返回两两的独占重叠与各自来源，不受多模块并行开关限制；解析与重叠判定和 `startable.conflicts`
是同一份（`module_scope.parse` 与 `module_scope.overlap`）。用来在 Spec 还没落到集成分支时就查重叠。`check-interface.py` 核对它引用的脚本
存在、错误码与代码一致。

### 规划层与运行层

多模块并行分两层，交接点只有 `interface.json` 列出的这些命令和 `/map --json`：

| | spec-guard（规划层） | module-crew（运行层） |
|---|---|---|
| 读 | 能力图、Spec、Plan、todo、`.agent/config.json`、本 checkout 与本机其他 worktree 的角色标记 | `interface.json`、`/map --json`、越界检查的 JSON |
| 写 | 只经命令、预览确认后写：配置、批准标记、角色标记、最终验收的勾 | 开会话、建 worktree、发消息、合并；按需调用 spec-guard 的写入命令 |
| 判断 | 能否开工、边界是否重叠、阶段与批准状态 | 开哪几个、什么时候合、失败怎么退 |

spec-guard 不开会话、不建 worktree、不合并；hook 只读。开关不是 on 时，规划层的新东西都不出现。

## 两个宿主的差异

| | Claude Code | Codex |
|---|---|---|
| 入口 | 斜杠命令 `/spec-guard:*`（`commands/`） | skill（`skills/`），用自然语言调用；不加载命令 |
| 阶段注入 | 同一份 `hooks/hooks.json`；首次使用需在 `/hooks` 信任 | 同一份 `hooks/hooks.json` |
| 插件根目录 | `CLAUDE_PLUGIN_ROOT`，命令里由宿主代入 | `PLUGIN_ROOT`；命令片段找不到时查询 `codex plugin list` |
| 约定块 | `CLAUDE.md` 的 `agent-skills-convention` 块 | `AGENTS.md` 的 `spec-guard-codex-convention` 块 |
| 上下文窗口 | 会话记录不带窗口大小，按 1M 窗口折算阈值 | 从会话记录读取窗口 |
| 其他 | | 默认的 workspace-write 沙箱不允许写 `.git`，提交需要提权批准 |

命令与 skill 的路由一致性由 `scripts/check-command-parity.py` 检查：每条命令引用的脚本都要有 skill 能走到。

## 不变量

- hook 默认不生效；没有激活信号、也没有本地事项账本（`.epiq/project.json`）的项目必须静默退出；只有账本的项目只出账本提醒（会话开始与清空后、压缩后、别的会话转来消息时），不出阶段内容。会话目录的指向文件是第三种激活信号，同样只由本插件的命令写下；
  它失效时报诊断，因为用户已经声明过要用。
- 探测失败必须降级，不能把环境故障说成链路断裂；“读不到”报 `unknown`，不当作“没有”。
- hook 只报告事实和建议，不写文件、不改远端状态。
- `hooks/spec-digest.py` 是唯一指纹算法，`capability_map.py` 是唯一能力图解析器，不得复制或内联。
- `phase-guard.sh` 只依赖 `bash`、`git`、`python3`，不引入 `jq` 之类的硬依赖。
- 修改共享判据时，`phase-guard` 与 `verify-artifacts` 两边一起改，并各有正反回归。
- 所有 hook 输出必须是宿主接受的 JSON；不用 `cmd | grep -q`，避免 SIGPIPE。
- 兼容 macOS 自带的 bash 3.2 与 python 3.9。

## Proposal 边界

`spec/CAPABILITY-MAP.md` 是唯一的能力图：已接受的 Proposal 按声明的锚点或末尾插入模块，不另建图。Proposal v2 用
revision 摘要绑定已发布内容。“接受”是人写的 Issue 阶段标签（`proposal-stage:accepted`）加上对远端默认分支的一次新鲜
审查；不读主线策略、验收凭证或权威身份。合并后的证明从 Proposal 的基线提交出发，在晋级提交的父提交上判断新鲜度。

tracker 适配器只读，只按显式给出的容器里的完整身份标记找回 Proposal Issue。预检与合并后证明都只读，既不能创建
晋级分支，也不能改能力图或 tracker 状态。

## 本地边界

本地约定把模块文档放在 `spec/` 与 `tasks/<module-id>/` 下。`.agent/state.json` 只记录本地的当前模块，不是 Proposal 池，
Proposal 代码从不读它。已开工、在等外部条件的模块可以用 `todo.md` 里的一行标记挂起：保留 Build order 位置，选当前
模块时跳过，只有用户恢复时才回来；可用 `--reason` 在标记下记一行原因，挂起时长不另存，由进度表从 git 历史读出；提醒（如果有）放在宿主里。Spec 与 Plan 各可带一行批准状态
标记（待批准／已批准，Spec 的批准带内容指纹）：阶段判定仍只看文件与勾选，标记只改当前模块的建议语与 `verify-artifacts`
的报告；hook 只读它，写入只经 `review_mark.py` 预览确认。标记是记录，不是授权来源。

## 项目配置

`.agent/config.json` 是入库的项目配置，团队与两个宿主共用一份。`project_config.py` 是唯一解析器，阶段提示、
`verify-artifacts` 与 `/spec-guard:config` 都调用它。文件不存在时什么都不变；问题用固定的问题代码报告，键和值不会进入
注入上下文（它们是仓库内容）。只有文件本身坏了（`project_config.STRUCTURAL`：读不了、不是 JSON、顶层不是对象、`version`
不对）才所有设置都不生效；不认识的键和取值不合法的键只让那个键失效，其余照常（`spec/config-per-key.md`）。目前的项有 `artifactLanguage`（新写的 Spec、Plan、todo
正文的语言，结构关键字不变；恰好为 `zh-CN` 时阶段提示的说明文字也用中文，判据是 `module_stage.hint_language`，
phase-guard 与 `session_context.py` 的位置行都向它取，其他值的提示与 0.67.0 逐字节相同）、`reviewCadence`（默认 `separate`，`combined` 时一个模块的 Spec 与 Plan 一起审）与
`moduleConcurrency`（多模块并行开关，默认 `off`；规划层的并行规则只在 `on` 时生效，`off`、未设置、取值无效或文件无效时所有输出与
引入开关前逐字相同）。其他代码只通过 `project_config.module_concurrency()` 读这个开关，不自己解析。
默认事项后端有自己的位置，这里只汇总显示。

## 文件布局（File layout）

spec-guard 写在哪里、谁能删什么。`scripts/check-state-paths.py` 确保 hooks 里的家目录路径只来自 `state_paths.py`，
以及读取宿主自身配置。

| 类别 | 路径 | 入库 | 谁写 | 怎么删 |
|---|---|---|---|---|
| 项目产物 | `spec/`、`tasks/<id>/`、`CLAUDE.md`／`AGENTS.md` 里的约定块、`.agent/config.json`、`.agent/tracker.json`、`DOCUMENTATION-BASELINE.md`、`.epiq/project.json` | 是 | 预览并确认后的命令 | 通过命令；teardown 保留 Spec 与 Plan |
| 历史归档 | `spec/history/`、`tasks/history/`、`.agent/history/`、`spec/CAPABILITY-HISTORY.json` | 是 | 只有一次性的历史迁移 | 永不删除：账本按哈希固定每个文件 |
| 每个 checkout 的状态 | `.agent/state.json`（当前模块）；新的状态一律放在 `$(git rev-parse --git-path spec-guard)` 下 | 否 | 构建流程；本地锁 | 随意 |
| 本机状态 | `~/.spec-guard/` 或 `$SPEC_GUARD_STATE_DIR`：`local-ticket-ledger/runtime`、`local-ticket-portability`、`hosted-ticket-intents`、`proposal-closeout` | 否 | 账本安装、交接、托管事项写入、Proposal 收尾 | 运行时可重装；日志与意图只在没有待完成的写入时删，它们用来防重复 |

`~/.local/state/spec-guard/hosted-ticket-intents` 与 `.../proposal-closeout` 在新目录不存在时整目录回退读取，不搬运、
不删除。`~/.spec-guard/native-collaboration`、`session-delegation`、`collaboration` 属于 agent-relay，不属于 spec-guard。

## 已退役的边界

v0.14 时代可写的远端 tracker 桥不属于本产品，也没有藏在兼容路径后面：远端投影、选择、绑定、投递与同步预览都已
移除。历史记录作为不可改的证据保留。完整的决定、迁移规则与验收条件见[退役说明](retirements/spec-github-bridge-retirement.md)。
