# Capability Map: Spec Guard

## 目标

Spec Guard 是 agent-skills 的配套插件。本图是整个插件的唯一能力图：新需求在模块检查点经带校验的快速插入加进本图，
需要留痕时改走 Proposal（经主链评审与人工接受后插入）；两种方式都按声明的锚点插到已有模块之后或追加到末尾，不为每个
需求另建一张图；只有与本插件无关的独立产品才另起能力图。

插件的能力分四类：只读的 Proposal 生命周期（共享事实只来自远端默认分支快照，GitHub/GitLab 只作为只读 Proposal Issue
来源，不创建或修改 Issue、PR、分支或任务）；防止多模块产物互相覆盖的本地约定，以及只报告事实的阶段注入与产物校验；
在检查点把新模块校验后插进能力图的快速插入；可核验的能力历史与显式的文档治理；以及需显式启用的本机协作邮箱与本地事项账本，二者都不替代、不同步远端 Issue。
各模块的登记来源写在其模块 Spec 中。

## 模块

| Module id | Responsibility | Depends on |
|---|---|---|
| proposal-contract | 定义并严格校验 Proposal v1/v2 文档、内容绑定 revision、阶段标签、能力图基准摘要和受支持变更类型。 | — |
| proposal-publication | 只从远端默认分支的固定快照读取一个已发布 Proposal 或候选池，拒绝把其他 worktree 的本地文件当作共享事实。 | proposal-contract |
| proposal-tracker-read | 用最小的 GitHub/GitLab 只读适配器核验普通 Proposal Issue 的唯一 revision marker 与唯一阶段，不使用旧 bridge。 | proposal-contract |
| proposal-review | 汇总发布、tracker 与当前能力图事实，给出与人工授权分离的 freshness/stale/blocked/unknown 结果。 | proposal-publication, proposal-tracker-read |
| proposal-promotion-proof | 对 Proposal 晋级核验 Issue 阶段、新鲜度、首次纳入提交及声明行与位置，并给出证明或诊断。 | proposal-review |
| collaboration-messaging | Provide a private same-Mac mailbox and host adapters for direct Claude Code and Codex session communication. | — |
| collaboration-safe-defaults | 协作会话默认不绑定唤醒、自动批准会话禁止绑定，并用回归锁定 native-only 安全边界。 | collaboration-messaging |
| local-ticket-ledger | Provide an optional local-first, worktree-shared ticket ledger and narrow Claude Code/Codex access without imposing workflow ownership or project topology. | — |
| ledger-dependency-lock | 用插件附带的 lockfile 与 npm ci 安装本地事项账本运行时，并校验全部依赖的完整性。 | local-ticket-ledger |
| local-convention | Install and remove the local multi-module directory convention and its managed declaration block, without touching user specs or plans. | — |
| phase-and-verification | Inject the current phase for activated projects and verify landed artifacts read-only, degrading to unverified when probes fail. | local-convention, proposal-contract |
| module-insert | At a module checkpoint, validate and insert one new module into the capability map with a spec skeleton, after previewing and explicit confirmation. | local-convention, phase-and-verification |
| capability-history | Keep verifiable history of archived capability maps and artifacts, with read-only verify and audit, append-only corrections, and migration preview. | proposal-contract |
| documentation-baseline | 定义显式启用的项目级文档基线协议、解析事实和初始化入口 | — |
| documentation-impact | 在模块 Spec、Plan 与交付前表达并收口对文档基线的遵循、补全、变更或不适用结论 | documentation-baseline |
| documentation-verification | 提供只读核验、保守提醒和跨宿主回归，确保缺失或未知不被伪装为文档完成 | documentation-baseline, documentation-impact |
| audit-remediation | 修复项目审计中已核实、不改变设计的缺陷：假成功、诊断丢失、Codex 路由与校验缺口、文档漂移。 | proposal-promotion-proof, collaboration-messaging, local-convention, module-insert, capability-history, documentation-verification |
| done-stage-split | 把阶段提示里的 DONE 拆成两种：当前模块已完成但还有别的模块未完成、全部模块已完成，各给出正确的下一步。 | phase-and-verification, module-insert |
| module-interrupt | 支持显式插队：当前模块做到一半时，经预览确认把新模块插到它前面，阶段提示持续显示被暂停的模块，插队模块完成后回到它。 | module-insert, done-stage-split |
| plan-without-todo | 有 Plan 却没有 todo.md 的模块会被判为已完成：阶段提示与 verify-artifacts 对此给出警告，完成判据保持不变，避免新插入的模块被误当成已完成。 | phase-and-verification, module-interrupt |
| proposal-pool-isolation | Proposal 池中已晋级（模块已在能力图中）的 Proposal 不再参与基线校验，使一个基线失效的历史 Proposal 不会让整个池失效；验收记录指纹与 policy 摘要不变。 | proposal-publication, proposal-promotion-proof |
| proposal-label-acceptance | Proposal 的接受只看 Issue 标签 proposal-stage:accepted 与评审新鲜度；晋级证明以 Proposal 基线提交为起点并接受只改能力图的晋级提交；删除主链裁决命令、策略文件与验收记录要求，已有文件保持可读。 | proposal-pool-isolation |
| proposal-add-module-promotion | add-module --proposal <id> 按已发布 Proposal 声明的 id、职责、依赖与锚点插入能力图，内嵌远端预检（已接受、新鲜、模块未在图中），预览后确认写入。 | proposal-label-acceptance |
| proposal-submit | 生成 Proposal 文档并自动计算基线、模块摘要与 revision，输出开 Issue 的现成命令；把使用流程、README 与发版流程改写为提交、接受、晋级、收尾四步。 | proposal-add-module-promotion |
| promotion-proof-diagnostics | 晋级证明因晋级行与声明不符或改动了其他模块行被拒时，给出对应诊断码、晋级提交与不一致的字段；其余结果与输出不变。 | proposal-add-module-promotion |
| insert-existing-spec | add-module 在 spec/<id>.md 已存在时不再拒绝插入，改为在预览中提示插入后阶段为 NEEDS_PLAN、未评审的 Spec 须先评审；其余校验与写入范围不变。 | module-insert, proposal-add-module-promotion |
| ledger-worktree-owner | 本地账本 status 检出 Epiq 状态 worktree 被同一 projectId 的另一个仓库占用时，报告占用者与处理办法，而不是让账本调用以 git worktree 报错失败；状态检查仍只读。 | local-ticket-ledger, ledger-dependency-lock |
| done-unmerged-hint | 阶段为 DONE 或 MODULE_DONE 且当前分支有提交尚未进入本地已知的远端默认分支时，阶段提示追加未合并提交数并建议先推送合并；只读、不联网，探测失败时不提示。 | phase-and-verification, done-stage-split |
| git-fixture-template | Proposal 与晋级相关测试的临时 git 夹具每个测试类只构建一次模板、每个测试复制一份并修正远端地址，缩短 validate.sh 耗时；测试的断言、隔离与覆盖不变，产品代码不改。 | proposal-promotion-proof, proposal-submit |
| local-ticket-portability | Verify and restore complete Local ticket context, then explicitly hand off selected tickets to a chosen GitHub or GitLab Issue with resumable per-ticket reconciliation. | local-ticket-ledger, ledger-worktree-owner |
| retired-module-separation | 把已退役 Proposal 模块从当前能力图移出，保留可核验的历史 Spec、Plan 与快照，并让现行依赖和阶段提示只引用活跃模块。 | capability-history, proposal-label-acceptance, phase-and-verification |
| audit-handoff | 给项目级审查定义有限批次、发现项收束和按现行事项边界交接的规则，复用 agent-skills 修复流程。 | local-convention, phase-and-verification, local-ticket-ledger |
| hosted-ticket-workflow | 按需把已确认缺陷受理到明确选择的 GitHub/GitLab 普通 Issue，并在代码交付后逐项读回与收尾，不恢复旧 tracker bridge。 | audit-handoff |
| authorized-session-delegation | Create and coordinate bounded same-Mac Claude Code or Codex review and development sessions under explicit task, batch, or session authorization. | collaboration-messaging |
| host-native-session-routing | 为同宿主 Claude Code/Codex 会话选择受支持的原生双向通道，并在不可用时显式使用持久 bridge，保持统一调度与现有授权边界。 | collaboration-messaging, authorized-session-delegation |
| tracker-backend-default | 删除已退役的 .agent/state.json tracker 字段、其激活信号与警告抑制，改用单一用途的项目级默认 backend 与精确目标；默认值只预填预览，不决定写入、不改变已有事项绑定，也不作为激活信号。 | phase-and-verification, plan-without-todo, hosted-ticket-workflow |
| proposal-closeout | 在新鲜 promotion proof 为 proved 后，按显式或由项目默认解析出的 Local/GitHub/GitLab 绑定，预览并经授权写入 Proposal 收尾记录、把阶段改为 promoted 并关闭事项再读回；三个后端共享同一个纯状态机，只有适配器不同，不改变共享事实源。 | proposal-promotion-proof, tracker-backend-default, local-ticket-ledger |
| phase-context-sanitization | 校验注入阶段提示的标识符与诊断文本：activeModule 必须是 kebab-case 模块 id，能力图解析错误不把原文带进 additionalContext；阶段取值与完成判据不变。 | phase-and-verification, plan-without-todo, tracker-backend-default |
| build-task-dispatch | 可选的约定块规则（默认关闭）：/build 把 todo 中非 Checkpoint 的 task 交给子代理并带 tier-guard 档位标记，验收、提交、勾选与停止问人留在主代理 | local-convention |
| module-cost-report | 只读的模块成本与返工报告：离线读取 Claude Code transcript 与 Codex rollout，按模块与 task 汇总主代理和子代理的 token（按模型、类别）、派活次数与返工信号，可选按用户价格表折算等价金额；不写文件、不依赖 tier-guard | local-convention, build-task-dispatch |
| fresh-session-hint | 阶段提示建议开新会话：当前模块刚完成（MODULE_DONE / DONE）时建议在新会话开始下一个模块，宿主会话记录显示主会话上下文超过阈值时提示上下文已很长，并在每个阶段注入当前分支与 worktree；只读，读不到会话记录时不提示。 | phase-and-verification, done-stage-split |
| session-handoff | 只读的会话交接命令：从仓库文件与 git 拼出可直接粘贴的交接文本（仓库路径、分支与 worktree、HEAD、阶段与模块计数、最新发布证据中 not-verified 的项、当前分支未合并提交，末尾留“下一步：____”），不写文件、不读会话记录内容；Claude 与 Codex 在整条提示词精确等于该命令时由 UserPromptSubmit 本地作答、不调用模型，阶段提示的 Module boundary 行改为指向它，阶段判定不变。 | phase-and-verification, done-unmerged-hint, fresh-session-hint |
| context-hint-thresholds | 上下文提醒改为按模块分档：模块完成（MODULE_DONE / DONE）时上下文达到窗口 50% 才提示在新会话开始下一个模块，模块进行中只在达到窗口 80% 时作为安全阀提示；Codex 取会话记录里的窗口大小，Claude 拿不到窗口时按固定 token 数判断；低于阈值不出上下文行，只读与读不到就不提示的规则不变。 | fresh-session-hint, session-handoff |
| checkpoint-tiers | 共享检查点规则与约定块增加三条：Plan 的检查点标为 gate（停下等确认）或 report（记入 todo 后直接继续），推送与开 PR 只在 Plan 的 gate 检查点写明授权时免问；一个需求拆成多个模块时可一次批量审完全部 Spec 与 Plan，之后按 Build order 连续构建；涉及 UI 的检查点先由 AI 用浏览器或电脑操作自验、缺工具时提前提醒，人做最后兜底。只改规则文本与回归，不改 hook 判定。 | local-convention, context-hint-thresholds |
| collaboration-interface | Define the public collaboration interface, with current and hardening-target columns, that the split into agent-relay is checked against. | collaboration-messaging, authorized-session-delegation, host-native-session-routing |

Build order: proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-promotion-proof → collaboration-messaging → collaboration-safe-defaults → local-ticket-ledger → ledger-dependency-lock → local-convention → phase-and-verification → module-insert → capability-history → documentation-baseline → documentation-impact → documentation-verification → audit-remediation → done-stage-split → module-interrupt → plan-without-todo → proposal-pool-isolation → proposal-label-acceptance → proposal-add-module-promotion → proposal-submit → promotion-proof-diagnostics → insert-existing-spec → ledger-worktree-owner → done-unmerged-hint → git-fixture-template → local-ticket-portability → retired-module-separation → audit-handoff → hosted-ticket-workflow → authorized-session-delegation → host-native-session-routing → tracker-backend-default → proposal-closeout → phase-context-sanitization → build-task-dispatch → module-cost-report → fresh-session-hint → session-handoff → context-hint-thresholds → checkpoint-tiers → collaboration-interface

---

## 评审记录

- [x] 模块边界确认（砍掉或替换一个模块，不需要重写其他模块的需求）
- [x] 依赖方向单向无环（互相依赖 = 它们本来就是一个模块）
- [x] module id 已定稿（kebab-case，之后绝不改名 —— 同一个 id 同时是
      `spec/<id>.md`、`tasks/<id>/`、`state.json`、`feat/<id>` 分支和 issue 标题的名字，
      其中后两处改不动）
- [x] 构建顺序符合依赖拓扑

评审人：用户与 Codex（Proposal 模块，2026-09-15）；用户（改为全插件一张图并登记账本，2026-09-28；
补登本地约定、阶段与校验、能力历史、文档治理，2026-09-28）
