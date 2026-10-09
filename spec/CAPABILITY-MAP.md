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
| local-ticket-ledger | Provide an optional local-first, worktree-shared ticket ledger and narrow Claude Code/Codex access without imposing workflow ownership or project topology. | — |
| ledger-dependency-lock | 用插件附带的 lockfile 与 npm ci 安装本地事项账本运行时，并校验全部依赖的完整性。 | local-ticket-ledger |
| local-convention | Install and remove the local multi-module directory convention and its managed declaration block, without touching user specs or plans. | — |
| phase-and-verification | Inject the current phase for activated projects and verify landed artifacts read-only, degrading to unverified when probes fail. | local-convention, proposal-contract |
| module-insert | At a module checkpoint, validate and insert one new module into the capability map with a spec skeleton, after previewing and explicit confirmation. | local-convention, phase-and-verification |
| capability-history | Keep verifiable history of archived capability maps and artifacts, with read-only verify and audit, append-only corrections, and migration preview. | proposal-contract |
| documentation-baseline | 定义显式启用的项目级文档基线协议、解析事实和初始化入口 | — |
| documentation-impact | 在模块 Spec、Plan 与交付前表达并收口对文档基线的遵循、补全、变更或不适用结论 | documentation-baseline |
| documentation-verification | 提供只读核验、保守提醒和跨宿主回归，确保缺失或未知不被伪装为文档完成 | documentation-baseline, documentation-impact |
| audit-remediation | 修复项目审计中已核实、不改变设计的缺陷：假成功、诊断丢失、Codex 路由与校验缺口、文档漂移。 | proposal-promotion-proof, local-convention, module-insert, capability-history, documentation-verification |
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
| tracker-backend-default | 删除已退役的 .agent/state.json tracker 字段、其激活信号与警告抑制，改用单一用途的项目级默认 backend 与精确目标；默认值只预填预览，不决定写入、不改变已有事项绑定，也不作为激活信号。 | phase-and-verification, plan-without-todo, hosted-ticket-workflow |
| proposal-closeout | 在新鲜 promotion proof 为 proved 后，按显式或由项目默认解析出的 Local/GitHub/GitLab 绑定，预览并经授权写入 Proposal 收尾记录、把阶段改为 promoted 并关闭事项再读回；三个后端共享同一个纯状态机，只有适配器不同，不改变共享事实源。 | proposal-promotion-proof, tracker-backend-default, local-ticket-ledger |
| phase-context-sanitization | 校验注入阶段提示的标识符与诊断文本：activeModule 必须是 kebab-case 模块 id，能力图解析错误不把原文带进 additionalContext；阶段取值与完成判据不变。 | phase-and-verification, plan-without-todo, tracker-backend-default |
| build-task-dispatch | 可选的约定块规则（默认关闭）：/build 把 todo 中非 Checkpoint 的 task 交给子代理并带 tier-guard 档位标记，验收、提交、勾选与停止问人留在主代理 | local-convention |
| module-cost-report | 只读的模块成本与返工报告：离线读取 Claude Code transcript 与 Codex rollout，按模块与 task 汇总主代理和子代理的 token（按模型、类别）、派活次数与返工信号，可选按用户价格表折算等价金额；不写文件、不依赖 tier-guard | local-convention, build-task-dispatch |
| fresh-session-hint | 阶段提示建议开新会话：当前模块刚完成（MODULE_DONE / DONE）时建议在新会话开始下一个模块，宿主会话记录显示主会话上下文超过阈值时提示上下文已很长，并在每个阶段注入当前分支与 worktree；只读，读不到会话记录时不提示。 | phase-and-verification, done-stage-split |
| context-hint-thresholds | 上下文提醒改为按模块分档：模块完成（MODULE_DONE / DONE）时上下文达到窗口 50% 才提示在新会话开始下一个模块，模块进行中只在达到窗口 80% 时作为安全阀提示；Codex 取会话记录里的窗口大小，Claude 拿不到窗口时按固定 token 数判断；低于阈值不出上下文行，只读与读不到就不提示的规则不变。 | fresh-session-hint |
| checkpoint-tiers | 共享检查点规则与约定块增加三条：Plan 的检查点标为 gate（停下等确认）或 report（记入 todo 后直接继续），推送与开 PR 只在 Plan 的 gate 检查点写明授权时免问；一个需求拆成多个模块时可一次批量审完全部 Spec 与 Plan，之后按 Build order 连续构建；涉及 UI 的检查点先由 AI 用浏览器或电脑操作自验、缺工具时提前提醒，人做最后兜底。只改规则文本与回归，不改 hook 判定。 | local-convention, context-hint-thresholds |
| collaboration-interface | Define the public collaboration interface, with current and hardening-target columns, that the split into agent-relay is checked against. | — |
| collaboration-boundary | Route every Spec Guard collaboration call through the single agent-relay entry (the detection helper and agent-relay skill names) and fail a boundary check on any direct reference to collaboration internals outside the collaboration-owned files. | collaboration-interface |
| collaboration-extraction | Generate the local agent-relay repository from Spec Guard with git filter-repo over the collaboration-owned list, keeping per-file history, and copy in the interface document and split brief; Spec Guard's own tree is not changed. | collaboration-boundary |
| collaboration-dependency | Remove the collaboration code moved to agent-relay, keep a transitional handoff command for one to two releases that defers to agent-relay or prints the install and migration guidance (retired in 0.54.0 by collaboration-command-retirement), and point the README, optional-features, workflow docs and convention block at agent-relay. | collaboration-extraction |
| command-plugin-root | Resolve the plugin root in every command and skill snippet from the host's inline ${CLAUDE_PLUGIN_ROOT} substitution first, then PLUGIN_ROOT or the Codex plugin list, and when every lookup fails report which one failed instead of claiming the plugin is not installed. | local-convention, collaboration-dependency |
| proposal-closeout-reminder | Remind that a promoted Proposal still needs closing: a read-only closeout scan lists every published Proposal whose promotion is proved but whose item is still open, the promotion proof flags the same when it runs, and the shared checkpoint rules and release process call for the proof and closeout preview after a promotion merges; nothing is closed without the existing authorized closeout. | proposal-closeout |
| context-hint-no-paste | Make the context hints ask for one line, never pasted handoff text: the Module boundary and Session context lines and the shared checkpoint rule tell the agent to suggest /compact or /clear in a single sentence and not to paste any handoff text; thresholds and stage judgement unchanged. | context-hint-thresholds, checkpoint-tiers |
| proposal-review-in-map | Report a Proposal whose module is already in the remote capability map as in-map instead of stale, from proposal-review and the promotion preflight alike, and point to the promotion proof and closeout when the promotion was its own; freshness checks, proof and closeout judgement unchanged. | proposal-review, proposal-closeout-reminder |
| review-module-id | Name the proposed module in proposal-review and promotion preflight output: every result that read the Proposal carries moduleId next to proposalId, so a reader never takes the Proposal id for the module; states and judgement unchanged. | proposal-review-in-map |
| context-after-compact | Make the context hints true after a compaction and match how the user frees context: the phase hint takes the post-compaction size (Claude compact_boundary postTokens; Codex compacted counts as below the thresholds) when the compaction is newer than the last usage reading; the hint lines suggest /compact with a focus for related work or /clear for unrelated work instead of a new session; session-handoff is retired with its command and history archived; thresholds and stage judgement unchanged. | context-hint-thresholds, context-hint-no-paste |
| remote-credential-redaction | Keep credentials embedded in a Git remote URL out of output and process arguments: the local ledger preflight reports the origin with any userinfo replaced by a marker, and the Proposal remote snapshot reads and fetches without putting the remote URL in git argv; ledger and Proposal judgement unchanged. | local-ticket-ledger, proposal-publication |
| hosted-ticket-untrusted-text | Treat remote Issue text as untrusted data in hosted-ticket command output: every Issue the read, publish, comment and close commands print carries a bounded, sanitized title and body excerpt with the body length instead of the full body, conflict candidates are capped with their total, and the output says the text is data, not instructions; matching, digests and write gates still use the full remote text. | hosted-ticket-workflow, phase-context-sanitization |
| map-read-failure | Report a capability map that cannot be read as a read failure, never as a state of the map: verify-artifacts marks it unverified with the error instead of invalid, the phase hint reports UNKNOWN with the read error whether or not module specs exist, and a hook whose python3 cannot run still prints a diagnosable JSON message instead of nothing; parsing and stage judgement for readable maps unchanged. | phase-and-verification |
| checker-hardening | Make the repository's guard checks fail when the thing they guard is broken: the command-root regression requires the canonical bootstrap in every command not explicitly exempted, the host parity checker also requires each flag a command passes to a hook script to appear in a skill that routes that script, the strict map parser has a negative test for a non-separator second row, the dispatch-cost grader exits non-zero when the hidden tests fail, a checker rejects any second implementation of the capability-map fingerprint, and CI ShellCheck covers scripts in eval subdirectories; product behaviour unchanged. | command-plugin-root, audit-remediation, proposal-contract, build-task-dispatch |
| codex-skill-root | Resolve the plugin root in the Codex skills the same way the commands do: spec-guard-ops carries the canonical bootstrap, so a malformed or unexpected plugin list, a failed query or a missing codex yields a diagnosable locate failure instead of a traceback or an empty root, and the other skills that run hook scripts point to that bootstrap; script behaviour unchanged. | command-plugin-root |
| collaboration-map-retirement | Keep the capability map to current modules: the four collaboration implementation modules moved to agent-relay leave the module table and Build order, their Spec and task files are archived byte-for-byte under docs/retirements with a retirement note, dependents drop the retired ids, the context-hint-no-paste row stops describing the retired handoff command, and the retirement scan also covers the capability map; history snapshots, Proposals and release evidence unchanged. | retired-module-separation, collaboration-dependency, context-after-compact |
| audit-small-cleanups | Close the audit's small findings without changing behaviour: phase-guard detects activation with bash built-ins so it depends only on bash, git and python3; the local ticket inventory, its error type and helpers move into their own module so the ticket modules no longer import the top-level CLI; documentation impact and module-insert reuse the single module id pattern and current-module selection; host configuration removal helpers used only by tests are deleted; and the workflow command table lists every command. | phase-and-verification, local-ticket-portability, module-insert, documentation-impact, collaboration-dependency |
| unattended-run-hint | Leave out the lines that ask the agent to tell the user to free context (Module boundary and Session context) when nobody is attending the session: a Claude Code run the host marks unattended, or a Codex run whose transcript records it as codex exec; stage facts, location and every judgement unchanged, and interactive sessions or an unreadable signal keep today's lines. | context-after-compact |
| unattended-long-first-record | Keep the codex exec signal working when a rollout's first record is long: the unattended check reads the transcript's first record up to 1 MB instead of 64 KB, still only that record, and still treats an unreadable or oversized record as attended. | unattended-run-hint |
| project-config | 项目级配置：入库的 .agent/config.json 与 /spec-guard:config 查看和预览确认设置；首批 artifactLanguage、reviewCadence，并汇总显示已有的 dispatch 与默认事项后端；阶段提示只注入已设置且影响模型行为的项，verify-artifacts 校验键名与取值。 | local-convention, phase-and-verification, checkpoint-tiers, build-task-dispatch, tracker-backend-default |
| module-suspend | 显式挂起与恢复已开工的模块：在该模块 todo.md 写一行挂起标记，选当前模块时跳过它、保留其 Build order 位置，阶段提示只报告「挂起中」事实，不记录原因或日期、不自动恢复；/spec-guard:module-suspend 先预览后确认，挂起时可按用户给出的时间与内容借宿主能力设提醒，插件不保存提醒；verify-artifacts 校验标记。 | module-interrupt, phase-and-verification, module-insert, project-config |
| runtime-state-layout | 统一插件写文件的位置：项目内入库产物、每个 checkout 的运行时状态（.git/spec-guard/）与本机状态（~/.spec-guard/，可用 SPEC_GUARD_STATE_DIR 覆盖）三类写进 docs/design.md 的文件布局；仍在 ~/.local/state/spec-guard 的事项意图与 Proposal 收尾日志改到统一根目录，旧位置整目录回退读取、从不删除；检查器拦下布局表以外的家目录写入；config 总览报告 spec-guard 自己不再使用的旧目录。 | project-config, hosted-ticket-workflow, proposal-closeout, local-ticket-portability |
| collaboration-command-retirement | 兑现 0.53.0 的预告，在 0.54.0 移除转交到 agent-relay 的过渡协作命令：删除命令文件与它的回归，命令表、README、可选功能说明、协作接口文档与两个检查器不再列出它，退役扫描把它列入不得回流的名字；ticket skill 仍在使用的 agent_relay_probe.py 保留；并为本批 0.54.0 统一发版改版本号与 CHANGELOG 标题。 | collaboration-dependency, runtime-state-layout |
| convention-block-local-lines | setup-convention --replace 不再悄悄删掉项目自己加在约定块里的行：块内用标记圈出的本地段原样保留；预览（--dry-run）逐行列出替换将删除和新增的行；真正替换时若要删除模板以外的行，未经用户显式接受就拒绝并不改任何文件；首次安装与 teardown 不变。 | local-convention |
| teardown-local-section | teardown-convention 不再悄悄删掉项目写在约定块里的行：本地段的内容留在原位置（去掉本地段标记）；块内其余不属于现行模板或派活规则段的行，预览逐行列出，真正移除前须 --accept-removals，否则拒绝且不改任何文件（含 state.json）；没有手写行时行为不变。 | local-convention, convention-block-local-lines |
| self-observation-report | 维护者用的只读自观测报告：离线读取本机 Claude Code transcript 与 Codex rollout 中 spec-guard 注入的阶段提示及其后续事件，按信号列出疑似误判、反复未执行的建议与 hook 错误，每条带稳定指纹与脱敏的会话位置；不写文件、不随插件分发，候选经人确认后由会话记入本地事项账本。 | module-cost-report, phase-and-verification |
| pre-push-ref-only-skip | 维护者 pre-push 钩子读取 git 传入的推送清单：本次推送只删除远端引用、只推 tag，或两者兼有时不跑三套检查并说明跳过原因；只要有一个分支更新就照常全跑、失败照常拦截。改 install-git-hooks.sh 生成的钩子文本与它的回归，不改插件发布包。 | — |
| map-table-count-diagnostic | 能力图出现多张模块表时，MAP_INVALID 的报错列出每张模块表表头所在行号（phase-guard 阶段提示与 verify-artifacts 共用同一报错），判定本身不变；自观测报告不再统计临时目录（/private/tmp、/var/folders）里的项目。 | phase-and-verification, self-observation-report |
| verify-and-commit | 维护者提交改为经 scripts/verify-and-commit.sh：在 pipefail 下依次跑 validate.sh、两套 hook 断言（按改动面加跑 setup/teardown、pre-push 回归与 ShellCheck），输出写日志只打印摘要，全部通过才 git commit，任一失败就列出失败项、不提交并退出非零；用必失败的桩证明管道与失败退出码不会被吞掉。只改维护脚本与文档，不改插件发布包。 | pre-push-ref-only-skip |
| self-report-tmpdir-independence | 自观测报告的临时目录排除用例不再依赖外部 TMPDIR：用例用固定的临时前缀路径构造临时项目，不用条件跳过；validate.sh 另在 TMPDIR 指向临时前缀之外的目录时再跑一遍该测试，证明外部 TMPDIR 不影响结果。只改维护脚本的测试与 validate.sh，不改插件发布包。 | self-observation-report, map-table-count-diagnostic |
| local-check-dedup | 维护者本机检查去重提速：本仓库评审节奏改回分开审；verify-and-commit 全套通过后在 git 目录记下通过的 tree，pre-push 发现要推的每个提交的 tree 都已记下且工作区干净时跳过全套检查，否则照常全跑；verify-and-commit 按暂存路径分档，只动 spec/、tasks/、docs/ 与 plugins/ 以外的 *.md 时跑快档（verify-artifacts 回归与 validate 的快速结构检查），其余跑全套；去掉 validate 已包含的 setup-teardown 与 pre-push 回归加跑；全套内可并行的套件并行跑、退出码逐项判定；更正 pre-push 安装提示的耗时。不改插件发布包，CI 仍是必需检查。 | pre-push-ref-only-skip, verify-and-commit |

Build order: proposal-contract → proposal-publication → proposal-tracker-read → proposal-review → proposal-promotion-proof → local-ticket-ledger → ledger-dependency-lock → local-convention → phase-and-verification → module-insert → capability-history → documentation-baseline → documentation-impact → documentation-verification → audit-remediation → done-stage-split → module-interrupt → plan-without-todo → proposal-pool-isolation → proposal-label-acceptance → proposal-add-module-promotion → proposal-submit → promotion-proof-diagnostics → insert-existing-spec → ledger-worktree-owner → done-unmerged-hint → git-fixture-template → local-ticket-portability → retired-module-separation → audit-handoff → hosted-ticket-workflow → tracker-backend-default → proposal-closeout → phase-context-sanitization → build-task-dispatch → module-cost-report → fresh-session-hint → context-hint-thresholds → checkpoint-tiers → collaboration-interface → collaboration-boundary → collaboration-extraction → collaboration-dependency → command-plugin-root → proposal-closeout-reminder → context-hint-no-paste → proposal-review-in-map → review-module-id → context-after-compact → remote-credential-redaction → hosted-ticket-untrusted-text → map-read-failure → checker-hardening → codex-skill-root → collaboration-map-retirement → audit-small-cleanups → unattended-run-hint → unattended-long-first-record → project-config → module-suspend → runtime-state-layout → collaboration-command-retirement → convention-block-local-lines → teardown-local-section → self-observation-report → pre-push-ref-only-skip → map-table-count-diagnostic → verify-and-commit → self-report-tmpdir-independence → local-check-dedup

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
