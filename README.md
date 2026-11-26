# spec-guard

简体中文 | [English](README.en.md)

spec-guard 是 [agent-skills](https://github.com/addyosmani/agent-skills) 的配套插件，支持 Claude Code 和 Codex。
agent-skills 的 `/spec` 已能把需求拆成能力图和每个模块的 Spec，但 `/plan` 每次都写同一份 `tasks/plan.md`／`todo.md`，
模块之间会互相覆盖，下一轮也不知道做到了哪。spec-guard 让每个模块各有自己的 Spec、Plan 和 todo，并在每轮对话开头
告诉 agent 现在该做哪个模块、做到了哪一步。

## 使用场景与边界

**适合**：已经在用 agent-skills，项目会拆成多个模块，或者有多个 agent、多个 worktree 并行开发。

**不太需要**：单文件脚本或一次性小改动，agent-skills 自带的单 Spec 流程就够了。

它解决三个问题：

| 问题 | spec-guard 的做法 |
|---|---|
| 多个模块共用一份 `tasks/plan.md`，第二个模块起互相覆盖 | 多模块目录约定：一张能力图，每个模块各自的 Spec、Plan、todo |
| agent 不知道现在该做哪个模块、做到哪一步 | 每轮对话开头自动注入当前阶段，例如「`NEEDS_PLAN`：去给 `billing` 写 plan」 |
| 做到一半冒出新需求，手改能力图容易改坏 | 快速插入：在检查点提出新模块，校验、预览、经你确认后插进能力图 |

边界：

- 安装后**不会自动生效**，只在运行过 setup 的项目里工作；其他项目完全静默。
- 阶段提示只报告事实、给出建议，不写文件、不改远端。
- 写能力图、建事项、改 GitHub/GitLab 之类的操作都先预览，经你明确确认才执行。

## 职责边界

spec-guard 只做一件事，分三层：
- 逐模块开发：一个需求按能力图拆成模块，每个模块有自己的需求、方案、Plan 和 todo，每轮告诉 agent 做到了哪、该在哪停下等你；
- 随时可压缩不丢事实：阶段、批准和答应过的事都落在文件或本地账本里，压缩、换会话后照样接得上；
- 从本地到 GitHub/GitLab 的最后一公里：需要在远端留痕的需求和事项，经你确认写进 Issue，读回核对、按证据关闭。

它负责：多模块约定、阶段提示与停点、插入新模块、批准记录、新流程的需求确认与技术方案审查、合并前验证判据（含多模块联调）、里程碑与挂起、项目配置与接管档位、并行开发的边界与越界检查、进度表、文档核验、产物校验；压缩后恢复、本地事项账本；Proposal、GitHub/GitLab 日常事项及其交接。

## 核心概念

- **能力图** `spec/CAPABILITY-MAP.md`：一张表列出全部模块、职责与依赖，外加一行 Build order（构建顺序）。
- **模块**：能力图里的一行。每个模块有 `spec/<模块>.md`（Spec）和 `tasks/<模块>/plan.md`、`todo.md`。
- **阶段**：spec-guard 根据这些文件推断当前进度，例如 `MAP_ONLY`（只有能力图）、`NEEDS_PLAN`、`BUILDING`、
  `MODULE_DONE`、`DONE`，注入给 agent：状态变了、新会话或压缩后给完整说明，其余轮次只给一行。
- **快速插入与 Proposal**：做到一半加需求，可以在检查点直接插入模块；需要留痕、审查时走 Proposal 流程。

术语和设计理由见[设计理念与术语](docs/concepts.md)。

## 前置条件

- 已安装 [agent-skills](https://github.com/addyosmani/agent-skills) 插件：`/spec`、`/plan`、`/build` 这些命令都来自它，spec-guard 不提供。安装方法以
  [它的 README](https://github.com/addyosmani/agent-skills#quick-start) 为准，写这一段时（2026-10-28）是：
  - Claude Code：`/plugin marketplace add addyosmani/agent-skills`，再 `/plugin install agent-skills@addy-agent-skills`；
  - Codex：`codex plugin marketplace add addyosmani/agent-skills`，再 `codex plugin add agent-skills@agent-skills`。Codex 里没有这些斜杠命令，
    用 `@spec-driven-development` 这类写法调用对应的 skill；
- `bash`、`git`、`python3`（3.9 及以上，macOS 自带的即可）；
- 宿主：Claude Code，或 Codex（CLI 或桌面 App）；
- 可选：用 Proposal 或托管日常事项时需要登录 `gh`（GitHub）或 `glab`（GitLab）；用本地事项账本时需要 macOS 和
  Node.js。

## 快速开始

**1. 安装插件**

| Claude Code | Codex |
|---|---|
| `/plugin marketplace add haigeerlab/spec-guard-plugin` | `codex plugin marketplace add haigeerlab/spec-guard-plugin --ref v0.98.0` |
| `/plugin install spec-guard@spec-guard-marketplace` | `codex plugin add spec-guard@spec-guard-marketplace` |
| 开新会话，在 `/hooks` 里查看并信任 spec-guard 的 `UserPromptSubmit` 与两项 `SessionStart` hook | Codex 0.164 起：在命令行版 `codex` 的 `/hooks` 里批准 spec-guard 的 3 个 hook，再开新会话（见[更新与卸载](#更新与卸载)）；更早的版本开新会话即可 |

Codex 的 `--ref` 填[最新发布版](https://github.com/haigeerlab/spec-guard-plugin/releases)的版本号。

**2. 在项目里启用**

| Claude Code | Codex |
|---|---|
| 运行 `/spec-guard:setup-convention`，看预览，确认后写入 | 对 agent 说“用 spec-guard-ops 在这个项目里安装约定”，看预览，确认后写入 |

setup 会建 `spec/`、`tasks/`，并在 `CLAUDE.md`（Codex 是 `AGENTS.md`）里写入一段[约定块](docs/convention-block.md)。

**3. 开始一个多模块项目**

用 agent-skills 的 `/spec` 写能力图，然后逐个模块写 Spec、用 `/plan` 生成计划、用 `/build` 实现。每一步该做什么，
阶段提示会告诉 agent。

**最短路径**：装插件 → 在项目里运行一次 setup → 正常和 agent 对话，跟着阶段提示走。

完整流程、每个阶段的含义和两种加需求的方式见[使用流程](docs/workflow.md)。第一次用，建议先看[上手：走完第一个模块](docs/getting-started.md)：
用一个小例子从安装走到第一个模块验收，每一步都附 agent 收到的阶段提示，还有「你做什么、agent 做什么」对照表和可选能力的选用指引。

## 功能一览

| 类别 | 命令（Claude Code） | 作用 |
|---|---|---|
| 约定与阶段 | `/spec-guard:setup-convention` | 在项目里安装多模块约定；`--replace` 升级约定块，`--dry-run` 只预览 |
| | `/spec-guard:teardown-convention` | 移除约定，保留你的 Spec 和 plan |
| | `/spec-guard:phase` | 查看当前阶段和建议的下一步 |
| | `/spec-guard:verify-artifacts` | 校验能力图、模块 Spec、批准标记、用法草案等产物 |
| | `/spec-guard:config` | 查看或设置项目配置（产物语言、批准节奏等，全部键见命令参考） |
| | `/spec-guard:review-mark` | 记录 Spec、Plan 的批准状态；你回复批准后由 agent 来用 |
| | `/spec-guard:milestone-mark` | 记录用法草案的一个里程碑已确认；你判定通过后由 agent 来用 |
| | `/spec-guard:module-suspend` | 挂起或恢复在等外部条件的模块 |
| | `/spec-guard:link-project` | 会话目录不是项目目录时，指向实际的项目 |
| 加需求 | `/spec-guard:add-module` | 在检查点把新需求作为模块插进能力图（预览后确认） |
| | `/spec-guard:proposal-submit`、`proposal-review`、`proposal-promotion-preflight`、`proposal-promotion-proof`、`proposal-closeout` | 需要在 Issue 上留痕时走 Proposal 流程：提交、审查、预检、证明、收尾 |
| 事项 | `/spec-guard:ticket` | 用自然语言记 bug、需求；明确选 GitHub/GitLab 时走托管流程。没启用本地事项账本时只做诊断、给出启用步骤，见[可选能力](docs/optional-features.md#本地事项账本) |
| | `/spec-guard:local-ticket-ledger` | 查看或启用本地事项账本 |
| | `/spec-guard:local-ticket-portability` | 核验、归档、恢复或交接本地事项 |
| | `/spec-guard:tracker-default` | 设置项目默认的事项后端，只用于预填预览 |
| 文档治理与历史 | `/spec-guard:documentation-baseline`、`documentation-impact`、`documentation-verification` | 文档基线、模块的文档影响与交付核验 |
| | `/spec-guard:history-integrity` | 核对旧版本留下的能力历史 |
| 报告 | `/spec-guard:map` | 模块进度表：状态、审查、关键卡点（只算挂起造成的阻塞） |
| | `/spec-guard:cost-report` | 按 task 统计主代理与子代理的 token 与主会话轮次 |
| 多模块并行 | `/spec-guard:checkout-role` | 并行开关打开时给每个 checkout 标角色 |

Codex 不加载斜杠命令，对 agent 说一句话即可，例如「用 spec-guard-ops 查看阶段」。每条命令的参数、输出和 Codex 里怎么说，
见[命令参考](docs/commands.md)。

## 运行效果与自检

启用后，发一句话给 agent，它会在上下文里看到类似这样的阶段提示：

```text
## spec-guard local workflow

Current stage: **NEEDS_PLAN**

- Capability map: present
- Current module: `billing` (next in Build order)
- Modules 3 · Specs 2 · Plans 1 · In progress 0 · Done 1

Suggested next step: create `tasks/billing/plan.md` and `tasks/billing/todo.md` (for example with `/plan`).
```

自检：

- 运行 `/spec-guard:phase`，能看到同样的阶段信息；
- 运行 `/spec-guard:verify-artifacts`，结果应为全部通过；
- 在没运行过 setup 的项目里，hook 什么都不输出，这是正常的。

## 更新与卸载

**更新**

| Claude Code | Codex |
|---|---|
| `claude plugin marketplace update spec-guard-marketplace` | 把 `~/.codex/config.toml` 里 `[marketplaces.spec-guard-marketplace]` 的 `ref` 改成新版本 |
| `claude plugin update spec-guard@spec-guard-marketplace`，然后重开会话 | `codex plugin marketplace upgrade`，然后开新会话 |

Claude Code 在会话开始时就定下了插件目录：不重开会话，已开着的会话里命令仍调用旧版本的脚本，钩子却可能已是新版本，
两个版本混用。

Codex 0.164 起，hook 的批准绑定在插件内容上：每次安装或升级 spec-guard 后，它的 3 个 hook（`UserPromptSubmit` 1 个、
`SessionStart` 2 个）都要重新批准，否则会被跳过、不报错，阶段提示不再出现。做法：

1. 在终端启动命令行版 `codex`，它会提示有 hook 需要审查（Hooks need review）；
2. 进入 `/hooks`，批准 spec-guard 的 3 个 hook；
3. 开新会话。已经开着的会话要重开。

Codex 桌面版可能不弹这个提示；用桌面版时没有阶段提示，就到命令行版 `codex` 的 `/hooks` 里批准。
`codex plugin marketplace upgrade` 会一起更新所有 marketplace，其他插件的 hook 也会出现在待批准列表里。

Codex 0.164 之前，只有新增的 `SessionStart` hook 要信任一次并重启 Codex：从 0.60.x 或更早升级的，
是压缩后注入的那一项；从 0.68.x 或更早升级的，还有会话开始与清空后的那一项。

已经装过旧版约定块的项目，更新插件后先预览 `/spec-guard:setup-convention --replace --dry-run`，确认后再替换。
在约定块所在的那一侧运行：块在 `AGENTS.md` 就加 `--host=codex`，`CLAUDE.md` 与 `AGENTS.md` 都有块就两边各跑一次；
目标文件里没有块时 `--replace` 会拒绝并提示该用哪一侧，不会新建。
块里自己写的规则放进本地段（`<!-- BEGIN:spec-guard-local -->` … `<!-- END:spec-guard-local -->`），替换时会保留。

**卸载**

1. 先在每个用过的项目里运行 `/spec-guard:teardown-convention`（先 `--dry-run` 预览），移除约定块并停用阶段提示；
   你的 `spec/`、`tasks/` 会保留。
2. 用过本地事项账本、并把它接入过宿主的，卸插件之前先移除账本写进宿主的配置（没接入过就跳过）：
   - Claude Code：运行 `claude mcp remove --scope user spec-guard-local-ledger`，再从 `~/.claude/settings.json` 的
     `permissions.ask` 里删掉以 `mcp__spec-guard-local-ledger__` 开头的 10 条规则；
   - Codex：运行 `codex mcp remove spec_guard_local_ledger`（或手动删掉 `~/.codex/config.toml` 里
     `[mcp_servers.spec_guard_local_ledger]` 那一整张表）；
   - 不再用账本时，可以删掉受管运行时 `~/.spec-guard/local-ticket-ledger/runtime`（设了 `SPEC_GUARD_STATE_DIR` 时在那下面）。

   账本数据（项目里的 `.epiq/`、`__epiq_state__` 状态 worktree、`~/.epiq-global`）是你的记录，卸载不需要删；要带走先用
   `local-ticket-portability` 归档。
3. 再卸载插件：Claude Code 用 `claude plugin uninstall spec-guard@spec-guard-marketplace`；Codex 用
   `codex plugin remove spec-guard@spec-guard-marketplace`，不再需要这个来源时再
   `codex plugin marketplace remove spec-guard-marketplace`。

## 多模块需求：用法草案与里程碑停点

一个需求拆成 2 个及以上模块时，spec-guard 让你在开工前看清做出来怎么用，并分段验证，不等全部做完才第一次拼起来用。

1. **提需求**：你描述需求，agent 总结、你确认说完。下一轮交审里同时看到能力图新行和用法草案 `spec/usage/<需求>.md`：有哪些入口、各归哪个模块、
   两三个典型用法、分几个里程碑；拆漏或拆多会在交审里写明。批准后 `/spec-guard:verify-artifacts` 检查草案结构和 Build order 顺序。
2. **中途补模块**：用 `/spec-guard:add-module` 插入时，预览写明锚点在哪份草案的哪个里程碑，提醒你把新模块加进里程碑表；
   排错顺序或归了两个里程碑，`verify-artifacts` 会报出来。
3. **一个里程碑做完**：这个里程碑最后一个模块验收、发版之后，阶段提示报「里程碑停点」，agent 不直接开下一个模块，而是用安装后的版本
   按这个里程碑的典型用法实际跑一遍，把命令与输出摆给你。你说通过，agent 用 `/spec-guard:milestone-mark` 预览、你确认后在草案里记下，
   阶段提示才转到下一个模块；你说不通过，就在本里程碑补任务，或回头改草案和后面还没开工的模块。

格式见 `templates/USAGE.md`，细则见共享检查点规则的「用法草案」一节。单模块需求不出草案；没有 `spec/usage/` 的项目一切照旧。

## 自动接管（可选）

默认每份 Spec（新流程叫需求文档）、技术方案、最终验收都由你批，合并、发布也由你做。想少介入时，可以给项目或单个模块设「接管档位」，
把其中几步交给第二审查者和 autopilot。不设档位的项目一切照旧。

**新流程模块**（需求文档带 `<!-- spec-guard: flow v2 tier=… -->` 一行）按「需求文档 → 技术方案 → 回归测试文档 → Plan → 实现 → 合并前验证」走：
需求永远由你在对话里确认；技术方案按规则交第二审查者审（碰了老逻辑、项目开了 `designReview`），重要需求的技术方案永远由你批；
技术方案放行后写回归测试文档：每条用例写步骤、预期、执行方式（`command`／`script`／`ai-operate`／`manual`）与证据，每条成功标准都要有用例，
碰了老文件就把受影响的老功能列进去（bug、小改动的用例写在需求文档里，bug 修完补一条）；写得不对时 verify-artifacts 判失败、阶段提示列出问题。
Plan 写完即自动批准，越界、碰 T4 路径、不可逆操作照旧停下问你。合并前由**不是作者**的会话（autopilot）照回归文档逐条执行，
结论分「通过」「通过但附意见」「不通过」三档，只拦能证明的问题（失败的运行、用户会遇到的 bug、跑不过的检查、改错的文档），风格类意见只记下、不拦。
没有这一行的老模块照旧规则（Spec → Plan → todo）。

1. **设档位**：对 agent 说「技术方案让第二审查者审过就行」之类的话，agent 用 `/spec-guard:config` 预览三项（技术方案、合并、发布）各由谁做，
   你确认后写进 `.agent/config.json`（`takeover`，单个模块用 `moduleTakeover`）。预设有 `none`（全由你做；每份技术方案都由你批）、
   `design`（第二审查者审过即放行技术方案）、`merge`（再加合并自动），也可以逐项自定义。放宽一次只升一档。
   旧档位照旧能读：`plan` 读作 `none`，老模块仍由 Codex 批 Plan；`plan` 改成 `design` 要你的原话。
2. **审查怎么做**：第二审查者用 /delegate:review 审技术方案，最多两轮，第二轮只核对上一轮；两轮还有阻断或没有可用的审查者就交你。
   老模块交给 Codex 的 Spec 或 Plan 同样两轮为限，没有阻断意见才记 `codex-approved`，不会自己审自己。
   **合并前验证**（新流程模块）：写代码的会话开工时记下自己是作者；非作者执行回归后写一份报告（格式见 [`plugins/spec-guard/references/verification-report.md`](plugins/spec-guard/references/verification-report.md)），
   spec-guard 校验它是否成立——每条用例都有结果、手工用例有你的原话、结论与用例一致、执行者不是作者、结论绑定当时的补丁与回归文档（改了就作废）——
   成立才记下，记录写在 git 目录、不进提交。合并交给自动化的新流程模块，有当前、通过的结论才算过最终验收；合并由你决定的模块，验收时会告诉你结论
   （没有结论也会说明，由你决定）。老模块合并交给自动化时，最终验收仍由 Codex 凭三样证据做：Codex 审最终补丁无阻断、autopilot 由非作者在同一提交上跑过检查、
   两者都是当前提交。
3. **哪些永远由你批**：能力图；需求确认；判为重要需求的需求文档、Spec 与技术方案（同批拆出多个模块、跨模块、碰高风险路径，由规则判定，不由 agent 自己判）；
   老模块里「预先声明」有内容的 Plan。测试改不红、Spec 没覆盖的决定、高风险不可逆操作、改到声明范围之外，都照旧停下问你。
4. **出事自动降档**：autopilot 或 module-crew 发现问题时，用只许收窄的入口把档位往严里改一格并记下原因；你想恢复，用 config 说一句，一次升一档。

`/spec-guard:map --json` 每个模块报出生效档位（`takeover`，重要需求的技术方案已算成由你批）、实际由谁批（`reviewApprovedBy`、`designApproval`）、
是否重要需求（`important`）、合并前验证结论（`verification`，多模块需求的联调回归在顶层 `usageVerification`）和老模块的 Codex 验收记录（`acceptance`），
供 autopilot、module-crew 读。规则原文见共享检查点规则的「自治档位与底线」「批准标记」
「技术方案审查」几节和「新流程模块按回归文档做合并前验证」一条。

## 多模块并行（可选）

默认情况下 spec-guard 一次推进一个模块。模块多而且彼此独立时，可以让几个会话同时各做一个模块：spec-guard 负责**规划**，开会话、建 worktree、
发消息、合并这些**运行**的事交给配套插件 module-crew。spec-guard 不依赖它：没装 module-crew 时，打开开关只得到下面这些规划层的规则。
不打开开关时，下面这些都不出现，一切照旧。

1. 用 `/spec-guard:config` 把 `moduleConcurrency` 设为 `on`（团队成员都升级到 0.68.0 以后再开，更早的版本会把整份配置判为无效；0.84.0 起遇到不认识的键只忽略那个键）。
2. 能力图审阅时，agent 会多给一段并行评估：哪些模块可以写成 Build order 的逗号组、哪些值得往前挪。
3. 每个模块的 Spec 加一节「并行边界」，写明它独占哪些目录；`verify-artifacts` 检查格式，最终验收时用越界检查标出改到边界外的文件。
4. `/spec-guard:map` 列出可同时开工的模块、并行边界的重叠，以及各模块 worktree 的进度。
5. `/spec-guard:checkout-role` 给每个 checkout 标角色：模块 checkout 的阶段提示只指向自己的模块，协调 checkout 不建议构建。

谁写批准标记、谁做本地合并，共享检查点规则里有专门一节（「协调会话的批准与合并」）：远端合并始终由你在对话里决定，你说『合并』后由会话执行。

## 对外接口

其他插件要读进度和审查状态时，看插件根目录的 `interface.json`：登记的每个入口（只读命令、多模块并行用到的开关与检查等）的
格式版本、退出码和取值含义都写在里面，按接口版本检查即可。说明见 [docs/design.md](docs/design.md)「对外接口」。

## 数据与隐私

- **读什么**：
  - 每轮对话开头，钩子只读当前项目里的能力图、模块 Spec、Plan、todo、`.agent/` 下的配置和本地 git 引用（不 fetch）。
  - 在交审检查点，还会读本机的插件记录，看 delegate 装没装。
  - 宿主给的会话记录只读尾部：最近的用量数字（在模块边界提示释放上下文）、钩子自己上一次注入的状态码（状态没变就只给一行）
    和压缩标记；Codex 另读第一条记录，判断是不是无人值守运行。不读你和 agent 的对话内容。
  - 启用了本地事项账本的项目，钩子只看 `.epiq/project.json` 在不在，不读账本内容。
  - 没有启用约定、只有账本的项目，也会在会话开始、清空、压缩后和别的会话转来消息时出账本提醒。
- **写什么**：钩子不写任何文件。命令在你看过预览、明确确认后才写：项目里的 `spec/`、`tasks/`、`.agent/` 和
  `CLAUDE.md`／`AGENTS.md` 的约定块；本机状态写在 `~/.spec-guard/`（可用 `SPEC_GUARD_STATE_DIR` 改位置）。
- **什么时候联网**：只在你明确调用下面这些功能时。Proposal 相关命令、选了 GitHub/GitLab 的 `ticket`、本地事项的
  归档、恢复与交接，通过本机的 `gh`／`glab` 和 `git ls-remote`／`git fetch` 访问 GitHub／GitLab，用的是它们已有的登录；
  启用本地事项账本时，用 `npm ci` 按随包的锁文件安装运行时。钩子和 `map`、`phase`、`verify-artifacts`、`review-mark`、
  `cost-report` 等其余命令不联网。
- **统计与上传**：`cost-report` 离线读本机 Claude Code（`~/.claude/projects/`）和 Codex（`~/.codex/sessions/`）的会话
  记录，用到其中的 token 计数、用户提问时间（切出模块收尾）、工具调用是否报错与子代理派生关系（把子代理用量归到发起它的 task）；
  这些只在本次运行的内存里用来归到各个 task，输出只有计数，不打印会话内容，结果只显示在终端。插件没有遥测，不向任何
  地方上报数据。

细节见[设计与架构](docs/design.md)。

## 故障排查

| 现象 | 先检查 |
|---|---|
| 阶段提示没有出现 | 这个项目运行过 setup 吗？Claude Code 里在 `/hooks` 信任 hook 了吗？Codex 0.164 起升级后在命令行版 `codex` 的 `/hooks` 重新批准了吗？装好插件后开新会话了吗？ |
| 阶段是 `MAP_INVALID` | 运行 `/spec-guard:verify-artifacts`，它会指出能力图哪里不对，例如模块表多于一张时列出每张表头的行号 |
| 提示说“python3 不可用”或“python3 无法运行” | 确认 `python3 --version` 是 3.9 以上，且宿主启动时的 PATH 里能找到它；修好后下一轮自动恢复 |
| Codex 里没有 spec-guard | 运行 `codex plugin list`，确认 spec-guard 已安装且启用；改了 `ref` 后要 `codex plugin marketplace upgrade` |

更多情况（`UNKNOWN`、`Paused`、`Suspended` 等提示的含义）见[故障排查](docs/troubleshooting.md)。

## 架构与文档导航

**使用者**

- [上手：走完第一个模块](docs/getting-started.md)：实跑的小例子、谁做什么、可选能力怎么选
- [使用流程](docs/workflow.md)：从零到交付、两种加需求的方式
- [命令参考](docs/commands.md)：全部命令的参数、输出与 Codex 对照
- [故障排查](docs/troubleshooting.md)
- [设计理念与术语](docs/concepts.md)
- [可选能力](docs/optional-features.md)：本地事项账本、文档治理、能力历史；会话协作已移到独立插件 agent-relay
- [约定块](docs/convention-block.md)：setup 写进 `CLAUDE.md`／`AGENTS.md` 的内容
- [迁移说明](docs/migrations/)、[更新日志](CHANGELOG.md)

**开发者**

- [设计与架构](docs/design.md)
- [贡献指南](CONTRIBUTING.md)
- [设计决定](docs/decisions/)

**维护者**（发版与仓库维护，使用插件不需要读）：[维护者工作方式](docs/maintainer-workflow.md)、
[发版流程](docs/release-process.md)、[故障模式与审查方法](docs/lenses.md)、[上游分析](docs/upstream-analysis.md)。

本仓库也用 spec-guard 管理自己的开发：根目录的 `spec/`、`tasks/` 是本仓库自用的模块记录，不是给使用者复制的模板。

## 开发、贡献与反馈

- 发现 bug 或想提需求：在 [GitHub Issues](https://github.com/haigeerlab/spec-guard-plugin/issues) 用对应模板提交，
  怎么写得清楚见[贡献指南](CONTRIBUTING.md)。
- 发现安全漏洞：不要公开提 issue，按[安全策略](SECURITY.md)私密报告。
- 想改代码：先读[贡献指南](CONTRIBUTING.md)和[设计与架构](docs/design.md)。
- 维护者文档见上面的“维护者”一组。

## 许可

[MIT](LICENSE)
