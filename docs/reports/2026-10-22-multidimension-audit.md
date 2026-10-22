# spec-guard 多维审查（2026-10-22）

| | |
|---|---|
| 基线 | `85a1f560`（v0.83.1） |
| 上游对照 | agent-skills 本机 0.6.12；`docs/upstream-analysis.md` 已核对到 0.6.13 |
| 方法 | 本机会话记录使用统计 + 主会话读码 + Codex（`gpt-5.6-sol`，effort high）两批只读审查，Codex 每条发现都在主会话对过代码 |
| 范围 | 插件源码、命令、技能、模板、README 与设计文档；未审测试实现与姐妹插件代码 |
| 性质 | 第一段交付：清单、发现、评分。不含修复；修复按第二段逐组插入模块 |

## 1. 使用数据（近 30 天，即会话记录保留的全部）

- 触达 spec-guard 的会话：Claude 使用者项目 171 / 本仓库 168；Codex 使用者项目 112 / 本仓库 34。
- 使用者项目常用：阶段注入（Claude 7,947 次、Codex 1,154 次）、verify-artifacts 344、review-mark 343、
  add-module 32（+ 插入脚本 65）、map 27、documentation-impact 117 / verification 76（几乎都来自一个项目）、本地账本约 100 次。
- 少用：module-suspend 2（+ 脚本 15）、link-project 10、config 3、checkout-role 2。
- 使用者项目零使用：Proposal 五命令（一个使用者项目在窗口外写过 2 份 Proposal）、托管事项 GitHub/GitLab（含本仓库也是 0）、
  local-ticket-portability（1）、cost-report、tracker-default、history-integrity、teardown。
- 代码量：hooks 源码 15.4k 行、测试 21.6k 行；零使用功能的源码约 7k 行（Proposal 2.9k、事项迁移交接 2.4k、托管事项 0.9k、cost-report 0.7k）。
- 注入：Claude 每次中位 651 字、p90 1,268；Codex 中位 1,129、p90 1,839、最长 4,026。状态不变也每轮重复。
  约定块 Claude 7.5KB / Codex 7.1KB，派活规则另加 1.7～2KB；共享检查点规则 `references/workflow-checkpoints.md` 59KB。
- 共享检查点规则的读取：Claude 侧 30 天 12 次 Read；Codex 侧 171 个会话提到它。

## 2. 上游 agent-skills 解决了什么

24 个 skill 覆盖定义→计划→构建→验证→审查→发布全流程，9 个命令（spec、planning、build、test、review、code-simplify、
ship、webperf、constraints），4 个 subagent，若干检查清单；hook 默认不接。与本插件直接相关的上游现状：

- Phase 0 已有能力图与每模块 Spec（`SPEC-<模块>.md`，项目根），允许外部 Spec 系统接管存放；
- planning 仍只有一份 `tasks/plan.md`／`todo.md`，没有模块概念；有「外部 tracker」扩展点；
- 能力图文件名未规定；没有跨轮的阶段感知、中途插入、批准记录。

## 3. spec-guard 在上游之上补了什么

| 层 | 功能 | 对应缺口 | 判定（本审查） |
|---|---|---|---|
| A 核心 | A1 多模块目录约定（setup/teardown/verify） | 能力图位置、plan 互相覆盖 | 保留；约定块瘦身（F1） |
| | A2 每轮阶段注入、/phase | 不知道做到哪 | 保留；降噪（F2） |
| | A3 中途插入模块 add-module | 中途加需求 | 保留 |
| | A4 批准记录 review-mark、gate-tick | 无批准记录 | 保留；收件枢纽呈现规则移出（F5） |
| | A5 进度表 map | 不知道做到哪 | 保留 |
| B 扩展 | B1 module-suspend、link-project、checkout-role/并行开关、config | 多会话多 worktree | suspend/config 保留；link-project 补全或收窄（F10）；checkout-role 归属待议（X3） |
| | B2 文档基线/影响/核验 | — | 保留为可选，修语义（F17） |
| | B3 history-integrity | — | 零使用，候选移除（X1） |
| | B4 上下文提示 | — | 保留，随 F2 降噪 |
| C 外围 | C1 Proposal 五命令 | — | 有窗口外使用，修正确性或移交（F6、F7、X1） |
| | C2 本地账本、ticket、tracker-default、托管事项、迁移 | 上游已有外部 tracker 扩展点 | 账本有真实使用，归属待议；托管事项与迁移候选移除（X1、X2） |
| | C3 cost-report 与派活规则 | — | 候选移交 tier-guard（X3） |
| | C4 姐妹插件接口 | — | 保留只读接口；delegate 提示降噪（F2） |

## 4. 发现（已核实，按严重度）

来源：「主」= 本会话，「C」= Codex，「C→主」= Codex 提出、主会话读码确认。

| # | 级别 | 问题 | 位置 | 来源 |
|---|---|---|---|---|
| F1 | 高 | 约定块 7.5KB 一次写入二十多条流程规则（UI 自验、验收文件表、承诺记账、回告来源、对外通道草稿、宿主确认指路、批 Plan 即授权提交与装包等），多为作者自己的工作习惯，除派活规则外不能逐项关闭；只想解决 plan 覆盖的使用者也要全盘接受 | `templates/claude-block-local.md:8-57`、`templates/codex-block-local.md:5-57`、`hooks/setup-convention.sh:100-105` | 主 + C |
| F2 | 高 | 阶段注入每轮重复、不去重、没有项目级开关；BUILDING 实测 1,268 字里 delegate 外审提示约 550 字（43%），在 Spec/Plan 待审与最终验收期间每轮重复，直到 todo 里记下结果或拒绝行 | `hooks/hooks.json:3-8`、`hooks/module_stage.py:631-662` | 主 + C |
| F3 | 高 | 外围功能边界扩张：约 7k 行源码服务近 30 天零使用的功能（Proposal、托管事项、迁移交接、cost-report、history），维护面、版本兼容与上手成本都被它们拉高 | `docs/design.md:8-18,53-54` | 主 + C |
| F4 | 中 | 约定块十几处写「细则见共享检查点规则」，规则文件 59KB；Claude 侧 30 天只 Read 12 次，细则在 Claude 上大多没有生效，Codex 侧每次读入又是两万字级别的上下文 | `references/workflow-checkpoints.md`、约定块各行 | 主 |
| F5 | 中 | 决策收件箱的卡片呈现与 session-protocol 消息格式（【用户答复】、`#H`、「转自」、「去决策收件箱答 #N」）写进了 spec-guard 的 review-mark 与检查点规则；「哪种批准来源有效」属于 spec-guard，怎么呈现属于 decision-inbox | `commands/review-mark.md:62-70`、`references/workflow-checkpoints.md:159-199,316-366`、`interface.json:187-188` | 主 |
| F6 | 中 | Proposal 收尾在 `finally` 里删除锁文件，等待旧 inode 的进程与新建锁文件的进程可以同时进入远端写入 | `hooks/proposal_closeout.py:361-377` | C→主 |
| F7 | 中 | Proposal 读取 GitLab 事项不带 `--hostname`，自建实例与 glab 默认主机不同时读错实例；closeout 一侧已固定主机 | `hooks/proposal_tracker_read.py:251-264` 对照 `hooks/proposal_closeout_gitlab.py:35-43` | C→主 |
| F8 | 中 | 本地账本安装会写 Claude MCP、Claude ask 规则与 Codex MCP 表，但没有卸载路径，README 的卸载步骤也没提，卸掉插件后留下失效配置 | `hooks/local_ledger_adapters.py:90-132`、`hooks/host_config_removal.py:1-5`、`README.md:127-133` | C→主 |
| F9 | 中 | 项目配置一个键未知或非法就整份失效（产物语言等一起退回默认），旧版遇到新键即触发 | `hooks/project_config.py:63-73`、`commands/config.md:59,87-89` | C→主 |
| F10 | 中 | link-project 只有阶段注入跟随指向，其他命令仍要手动替换项目路径 | `commands/link-project.md:67` | C→主 |
| F11 | 中 | 本地交接的 GitLab 查询不限定 `issue_type=issue`，会把其他类型一并纳入；三套 GitHub/GitLab 读取实现已出现分叉 | `hooks/local_ticket_gitlab.py:57-61` 对照 `hooks/hosted_ticket_provider.py:241-265` | C→主 |
| F12 | 中 | README 说 cost-report「只统计 token 与轮次」，实现还读工具结果文本、编辑路径与派活关系（仍只在本机、只打印终端） | `README.md:163-164`、`hooks/module_cost_report.py:149-174,327-337` | C→主 |
| F13 | 低 | README「agent-skills 默认一个项目只有一份 Spec」已过时（上游 Phase 0 已有每模块 Spec），真缺口是 plan 隔离与阶段续接 | `README.md:5-7` | 主 + C |
| F14 | 低 | 没设产物语言（英文提示）时，阶段标题仍是中文「当前阶段」 | `hooks/phase-guard.sh:287-378`、`hooks/module_stage.py:398` | 主 |
| F15 | 低（取舍） | 有 Plan 无 todo.md 的模块按已完成计，只给警告；这是 `plan-without-todo` 有意的决定，未见真实误判 | `hooks/module_stage.py:103-125` | C，降级 |
| F16 | 低（取舍） | gateTick 写最终验收勾选时信任调用方已获批准，与 review-mark 同一模型 | `hooks/gate_tick.py:3-7` | C，降级 |
| F17 | 低 | documentation-verification 只要 evidence 非空就报 `ready`，名称容易被读成「文档已核验」；设计文档对基线路径的写法与实现（`docs/DOCUMENTATION-BASELINE.md`）不一致 | `hooks/documentation_verification.py:63-95`、`docs/design.md:189` | C→主 |
| F18 | 低 | Proposal 池枚举在 `git show` 失败时抛 TypeError；history 不校验 `event.at`，迁移写入 `imported` 后无法合法补正 | `hooks/proposal_publication.py:288-295`、`hooks/capability-history.py:101-125,173-174` | C（采信，未重跑） |

10-08 架构审查的 20 条发现已全部关闭（抽查 F10、F14、F15、F17、F18、F19 确认）。

> **后续：** 本报告之后进行了一轮逐项需求核对，结论见 [决定记录](2026-10-22-feature-inventory/decisions.md)。第 5 节的候选去向与第 7 节的修复分组已被它取代：Proposal、远端事项与本地账本全部保留在本插件，不移除、不拆分。

## 5. 需要跨插件协商的项（不在本仓库单方面处理）

| # | 项 | 现状 | 候选去向 |
|---|---|---|---|
| X1 | Proposal 生命周期、history-integrity | Proposal 窗口外有使用；history 零使用 | Proposal 留在本插件但冻结新增，或移交决策类插件；history 移除 |
| X2 | 本地账本、ticket、托管事项、迁移交接 | 账本约 100 次真实使用（多个项目）；托管事项零使用 | 账本整体拆成独立插件（参照 agent-relay 拆分）；托管事项移除；迁移随账本走 |
| X3 | cost-report、派活规则、checkout-role | cost-report 本仓库自用；checkout-role 2 次 | cost-report 与派活归 tier-guard；checkout-role 归 module-crew，spec-guard 只留规划层并行判断 |
| X4 | 收件枢纽呈现规则（F5） | 写在 spec-guard | 呈现规则归 decision-inbox，spec-guard 只留批准来源的判定 |

## 6. 评分

| 维度 | 权重 | 主 | Codex 第 1 批 | Codex 第 2 批 | 主的证据 |
|---|---|---|---|---|---|
| 上游补充价值 | 20 | 4 | 4 | 4 | plan 隔离、阶段续接、中途插入、批准记录是上游真缺口；社区未见每轮注入阶段的插件；目录与 Proposal 类能力 spec-kit、OpenSpec 已有 |
| 职责边界 | 15 | 2 | 2 | 2 | F1、F3、F5、X1～X4 |
| 简洁度 | 15 | 2 | 1 | 1 | 约 45% 源码零使用；59KB 规则；140 个模块 |
| 灵活性 | 15 | 3 | 2 | 2 | 默认不生效、三个配置键；但约定块整块强制、注入不能关（F1、F2、F9） |
| 可靠性 | 15 | 3 | 3 | 3 | 测试 21.6k 行、10-08 审查全关；F6～F11 为外围正确性问题 |
| 上手成本 | 10 | 3 | 2 | 3 | README 最短路径清楚；Codex 升级要重新信任 hook，外围要 Node、gh/glab；未做全新项目实跑 |
| 运行开销 | 10 | 2 | 1 | 2 | F2、F4 与约定块体积 |
| **总分** | 100 | **56** | **46** | **50** | 按「权重 × 分 ÷ 5」 |

三份评分没有相差 2 分及以上的维度。分档：三份都落在「及格」或以下——核心补缺明确，分数主要被边界、简洁度和开销拉低。

**定位结论**：作为 agent-skills 的补充，A1～A5 补的是真缺口，社区里没有现成的同类插件把「每模块 plan 隔离」和「每轮阶段续接」接到 agent-skills 上，这部分是优秀的；但插件在核心之外长出了事项系统、发布流程、成本分析和姐妹插件的工作流规则，后者大多零使用，且把作者个人习惯写成了所有使用者的默认规则。

## 7. 第二段修复分组（每组一个 add-module、一个 PR，由用户挑选）

| 组 | 内容 | 覆盖 |
|---|---|---|
| G1 | 注入降噪：状态不变时只出一行短状态或静默，新增项目级开关；delegate 提示每个检查点只出一次 | F2、F14 |
| G2 | 约定块瘦身：核心块只留目录、当前模块、批准标记与入口；其余规则拆成可选规则包，setup 预览显示体积 | F1、F4 |
| G3 | 配置逐键容错 | F9 |
| G4 | 说明修正：README 上游描述、cost-report 读取范围、文档基线路径、documentation 的 ready 语义说明、账本卸载步骤 | F8（文档部分）、F12、F13、F17 |
| G5 | Proposal 正确性：锁不删、GitLab 绑定主机、`git show` 失败诊断（仅在决定保留 Proposal 时做） | F6、F7、F18 |
| G6 | link-project：其他命令一致跟随，或收窄为只给阶段提示并在文档写明 | F10 |
| — | X1～X4 先与相关插件负责方协商，定了再各自插入模块 | F3、F5、F11 |

## 附：社区同类方案

- [GitHub Spec Kit](https://docs.plannotator.ai/frameworks/github-spec-kit.md)：每个功能一个 `specs/<功能>/` 目录（spec、plan、tasks）。
- [OpenSpec](https://github.com/Fission-AI/OpenSpec)：每个变更一个文件夹，提案→实施→归档，与本插件的 Proposal 同类。
- 每轮注入当前阶段：未找到现成插件（[hook 注入的通用做法](https://scottspence.com/posts/how-to-make-claude-code-follow-hook-instructions)）。
