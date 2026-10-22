# Todo: sibling-rules-out

- [x] Task 0：同步批准标记、提交 Plan 与 todo — Spec（C70）与 Plan（C80）由模块协调带批准标记提交到集成分支（a2ace6b、7bc62ee），按开工通知 C81 `module-crew sync`（HEAD 1e93e92），各取集成分支版本，与交审版只差标记一行；validate、phase-guard、verify-artifacts 全过。
- [x] Task 1：回归先红（C6） — `test_workflow_checkpoints.py`：三处断言换成通用句与「session-protocol 契约的交审小项」；协调会话一节去掉合并步骤短语、加「不改写已推送或已被同步的历史」「由运行时」，另加 `test_section_leaves_merge_steps_to_the_runtime` 反向用例；`HubRelayedApprovalTests` 换成 `SiblingRulesOutTests`（五份文件无收件枢纽话术且有通用句、approved 条与协调会话一节的指向、review-mark 与 SKILL 仍认当前对话、moduleConcurrency 说明、约定块模板无收件枢纽）。改前文字上 17 处红，全因旧文字还在。全仓 grep 被删短语：现行文件只有 Spec 列出的七份与 interface.json。
- [x] Task 2：检查点规则（C1、C2） — 需求确认的例子、approved 条通用句、交审小项按契约命名、删「决策收件箱把这些缩成卡片」、复制块例外换成通用句、删「经收件枢纽转来的批准」整节；协调会话一节加「合并怎么做由运行时规定」，合并段只留批准绑定提交、历史底线、推送与远端合并只由用户。grep 收件枢纽／去决策收件箱答／总协调／新提交撤回／不 reset 无输出。删去的合并段原文见下方「改前原文」。
- [x] Task 3：独占范围内的镜像（C5 前半） — `review-mark.md` 交审小项命名、复制块句与 approved 条；`docs/workflow.md`「批准要留下记录」两行换成通用句。
- [x] Task 4：与已合入模块重叠的三个文件（C3、C5 后半） — `SKILL.md` review-mark 一节三处与 config 一节 moduleConcurrency 条；`docs/commands.md` review-mark 一段；`config.md` 配置表 moduleConcurrency 一行加「不控制协调会话：协调会话由 module-crew 的 `coordinator up` 开启，与本开关无关」。`test_workflow_checkpoints.py` 67 例全过；未改 project_config.py、templates/、docs/convention-block.md。
- [x] Checkpoint 1（report）：变异核对 — 在 scratchpad 里 `mktemp -d` 建的三份副本（`git archive HEAD plugins docs`）上各改一处：协调会话一节放回「检查失败时：用一个新提交撤回这一次合并，不 reset」→ `test_section_leaves_merge_steps_to_the_runtime` 红；检查点规则放回「## 经收件枢纽转来的批准」节标题 → `test_no_hub_wording_or_relayed_approval_conditions`（workflow-checkpoints.md）红；`config.md` 删掉「不控制协调会话」那句 → `test_module_concurrency_does_not_control_the_coordinator`（config.md）红。三次另有同样 8 个 ERROR，是副本里缺 AGENTS.md 等根文件所致，与变异无关。副本的删除被宿主拒绝，留在本会话 scratchpad，不在仓库里。
- [ ] Task 5：公共变更请求（C4）
- [ ] Task 6：合入集成分支并跑完整检查
- [ ] Checkpoint 2（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **变更**：共享检查点规则不再写只在姐妹插件存在时才有意义的规则（决定 D2、D8、D9）。删去收件枢纽话术（「去决策收件箱答 #N」）与
> 「经收件枢纽转来的批准」一节，改为通用一句：批准来源与在哪里答复以所装协作插件的规定为准，没装只认当前对话里的明确批准。
> 「协调会话的批准与合并」一节只留授权边界与「不改写已推送或已被同步的历史」底线，合并做法与失败处理（含旧的「新提交撤回、不 reset」）
> 由 module-crew 规定。`moduleConcurrency` 的说明写明不控制协调会话。约定块模板未变，已装项目无须重跑 `setup-convention`。

## 改前原文（Task 2 删去的协调会话合并段，供最终验收对照）

> - 一次只合一个模块。多个模块都在等时按 Build order 逐个处理，每合一个都重新核对下一个。
> - 只用普通合并，不改写历史：不变基、不压缩、不强推。合并后跑项目 Spec 里 Commands 一节的完整检查。
> - 检查失败时：用一个新提交撤回这一次合并，不 reset，不碰集成分支上其他模块的提交；撤回后停止后续合并，再跑一次完整检查，确认回到合并前的状态；
>   把模块退回给模块会话，这个模块不算完成。撤回本身冲突、被拒绝或结果不明时，停下报告，不自动重试，也不继续合下一个。
> - 合并有冲突时不由协调会话解决，退回给模块会话。
> - 具体命令和顺序由运行时决定；本节只规定授权的边界和这些底线。
