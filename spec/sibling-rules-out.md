# Spec: sibling-rules-out

<!-- spec-guard: review pending -->

## Objective

决定 D2 定下：只在某个姐妹插件存在时才有意义的规则，归该插件、装了才出现；spec-guard 不留副本，只留单独使用也成立的通用说法与只读接口。
共享检查点规则（`plugins/spec-guard/references/workflow-checkpoints.md`）里还留着三块这样的规则，本模块把它们删掉、换成通用说法：

1. **收件枢纽的话术与批准条件（D9）。** 「交审时说明怎么批准」一条末尾的例外（使用方插件规定只在收件枢纽问时不放复制块、改写
   「去决策收件箱答 #N」），以及整节「经收件枢纽转来的批准」（契约格式、登记的会话、事项号 `#H`、不算批准的清单）。这些规则
   decision-inbox 接入时写进自己的规则段已有（`decisions.md`「核实依据（D2）」）。只留通用一句：
   「批准来源以所装协作插件的规定为准；没装只认当前对话里的明确批准」。
2. **协调会话的合并步骤（D8）。** 「协调会话的批准与合并」一节里的合并做法与失败处理：一次只合一个、只用普通合并、合并后跑完整检查、
   检查失败「用一个新提交撤回这一次合并，不 reset」、冲突退回。最后这条与用户 10-18 批准的 module-crew 重置做法冲突，合并做法
   本来就归 module-crew 自己的 skill 规定。本节只留授权边界（谁写 `approved`、本地合并例外及其条件、换会话后未写成标记的批准作废）
   与「不改写已推送或已被同步的历史」底线。
3. **`moduleConcurrency` 的说明（D8）。** 写明它只管多模块并行的规划事实、不控制协调会话（协调会话由 module-crew 的
   `coordinator up` 开启）；键名不改。

登记：2026-10-22 修复批次 12 个模块之一，经用户批准事项 C65 开模块会话；能力图依赖 `fact-fixes`（它把 `interface.json` 里
收件枢纽复制块那半句留给本模块）。后续 `rules-at-nodes`、`quiet-injection` 改同一份检查点规则，本模块合完它们才开。
依据：`docs/reports/2026-10-22-feature-inventory/decisions.md`（D2、D7、D8、D9、D19）。

## Assumptions

以下是写 Spec 时定下的前提，请在批准时一并确认：

1. **约定块模板不用改。** 能力图这一行写「从约定块与共享检查点规则删去」，但核对过 `templates/claude-block-local.md` 与
   `codex-block-local.md`：里面没有收件枢纽话术、转来批准的条件或合并步骤。唯一沾边的是「几个模块一起审……（或并行开关为 on 时
   由协调会话汇总）」，它属于 spec-guard 自己的并行开关规划层（D8 保留开关），不删。所以约定块模板与它的镜像
   `docs/convention-block.md` 都不动，需要已装项目重跑 `setup-convention --replace` 的情况也就没有。
2. **只删规则、不改代码行为。** 本模块只改说明文字与回归断言；`review_mark.py`、`checkout_role.py`、`module_scope.py`、
   `project_config.py` 等脚本一行不改（核对过：脚本里没有收件枢纽判断，批准来源从来只靠规则文字约束）。
3. **节名「协调会话的批准与合并（moduleConcurrency 为 on 时）」保留。** 删掉合并步骤后本节仍规定「谁做本地合并」的授权边界，
   README、检查点规则与回归里有十来处指向这个节名，改名只会多出改动面。
4. **「批准绑定具体提交」算授权边界，保留。** 它规定的是「用户批的是哪一组提交、任一边变了原批准不再适用」，属于批准有效性，
   不是合并做法；精简成一条。「一次只合一个、按 Build order 逐个」算合并做法，删去。
5. **「不改写已推送或已被同步的历史」取代原来的「不变基、不压缩、不强推」。** 原句禁止一切改写历史，与 module-crew 检查失败时
   把集成分支重置到合并前（只动本机、未推送、未被同步的提交）冲突；新底线只保护已经推送或已被别的会话同步走的提交。
6. **复制块规则怎么办（见「待定」第 1 条）。** 删掉「只在收件枢纽问时不放复制块」的例外后，spec-guard 的规则就成了「总是放复制块」，
   与 decision-inbox、module-crew「在收件箱答、下一步框不放按钮」的规定相反。推荐把通用一句扩成「批准来源与在哪里答复，以所装协作
   插件的规定为准」，让复制块规则在装了协作插件时让位。
7. **`interface.json` 是公共文件。** 其中 `reviewKinds.description` 收件枢纽复制块那半句的改法写在本 Spec（C4），构建时发
   【公共变更请求】由模块协调落地；只改描述文字，接口版本、`reviewKinds` 取值都不动（D9：冻结不扩展）。
8. **和并行模块重叠的镜像文件后改（见「待定」第 2 条）。** `skills/spec-guard-ops/SKILL.md`、`docs/commands.md` 在
   `history-slim`（构建中）与 `config-per-key`（未合入）的独占范围里，`commands/config.md` 在 `config-per-key` 的独占范围里。
   本模块在这些文件里只改各自的一两句镜像，推荐等那两个模块合入集成分支、`module-crew sync` 之后再改。
9. **CHANGELOG 与版本号不在本模块改**，由模块协调整批合完后统一改；更新说明记在 todo 末尾。

## Contract

### C1 收件枢纽话术与转来批准的条件（`references/workflow-checkpoints.md`）

- 「需求确认」一节「可以跳过」条里的「（例如经总协调或收件枢纽转来用户原话）」改为「（例如经所装协作插件转来用户原话）」。
- 「批准标记」一节 `approved` 条：「批准的来源只有两种：用户在当前对话里的明确批准；或按契约转来的【用户答复】，条件见
  「经收件枢纽转来的批准」一节。先预览，给用户看过再 `--confirm`（经收件枢纽批准时按那一节核对）。」改为：
  「批准来源以所装协作插件的规定为准；没装只认当前对话里的明确批准。先预览，给用户看过再 `--confirm`；批准经协作插件转来时，
  预览怎么核对也按该插件的规定。」其余句子不变。
- 「交审要让用户看到内容」条：「名称与顺序和决策收件箱的卡片相同（各类在 session-protocol 契约里的类型代码见 `interface.json`
  的 `reviewKinds`）」改为「名称与顺序与 session-protocol 契约的交审小项一致（各类的类型代码见 `interface.json` 的
  `reviewKinds`）」；删去「决策收件箱把这些缩成卡片，模块会话里不缩。」一句（见「待定」第 3 条）。
- 「交审时说明怎么批准」条：删去从「使用方插件（例如决策收件箱、module-crew）规定要用户决定的事只在收件枢纽问」到
  「（见「经收件枢纽转来的批准」一节）。」的整段（4 行），按「待定」第 1 条的选择补一句。推荐 A 的写法：
  「所装协作插件对在哪里答复另有规定时（例如只在它的收件箱答），以它为准，复制块按它的规定放或不放。」
- 整节「## 经收件枢纽转来的批准」删除。
- 「协调会话的批准与合并」一节里「或经收件枢纽转来，见「经收件枢纽转来的批准」一节」改为「或按所装协作插件的规定转来」。
- 改完后本文件不再出现「收件枢纽」「去决策收件箱答」「总协调」。

### C2 协调会话的合并步骤（同一文件「协调会话的批准与合并（moduleConcurrency 为 on 时）」一节）

- 第二段「本节说明这种分工下谁写批准标记、谁做本地合并」之后加一句：「合并怎么做（命令、顺序、合并后的检查、失败与冲突的处理）
  由运行时（例如 module-crew）规定，本节只规定授权的边界与底线。」「唯一例外」与三个条件原样保留。
- 「汇总交审按模块分组」「协调会话」「批准标记由协调会话写，先核对内容」三段保留（第三段只按 C1 改一处指向）。
- 「本地集成分支的合并」一段改为三条：
  - 批准绑定具体提交：最终验收的消息写明模块 id、模块分支与集成分支当前的提交，用户批准的就是这一组；合并前任一边变了，原批准不再
    适用，要重新交用户确认。
  - 底线：不改写已推送或已被同步的历史（已推送到远端、或已被别的会话同步走的提交，不变基、不压缩、不强推、不重置）。
  - 推送和远端合并（PR／MR）仍然只由用户做，或者按「Plan 检查点分级」在 `gate` 检查点逐项写明授权后才推送。任何批准都推不出
    可以合并 PR。（原句保留）
- 删去：「一次只合一个……每合一个都重新核对下一个」「只用普通合并，不改写历史：不变基、不压缩、不强推。合并后跑……完整检查」
  「检查失败时：用一个新提交撤回这一次合并，不 reset……也不继续合下一个」「合并有冲突时不由协调会话解决，退回给模块会话」
  「具体命令和顺序由运行时决定；本节只规定授权的边界和这些底线」（并入第二段那句）。
- 「协调会话被替换时」一段原样保留。

### C3 `moduleConcurrency` 的说明

- `commands/config.md` 配置表 `moduleConcurrency` 一行：「本身不开会话、不建 worktree、不发消息、不合并，运行时归 module-crew 插件」
  之后加「；不控制协调会话：协调会话由 module-crew 的 `coordinator up` 开启，与本开关无关」。
- `skills/spec-guard-ops/SKILL.md` config 一节 `moduleConcurrency` 条：「本身不开会话、不建 worktree」之后加同义一句。
- 键名、取值、默认值与 `project_config.py` 不变。

### C4 `interface.json`（公共文件，经【公共变更请求】落地）

`reviewKinds.description` 中「the recommended reply sits in one copyable code block, except when a consumer plugin requires that
the user's decisions be asked only in the hub (or relayed there through a coordinating session): then the content is still shown in
full, but there is no copy block, only a line pointing to the hub ("去决策收件箱答 #N", or "去决策收件箱答" without an item number)」
改为「the recommended reply sits in one copyable code block unless the installed collaboration plugin rules where the user answers」
（按「待定」第 1 条选 B 时改为「the recommended reply sits in one copyable code block」）。其他字段、`version` 不变。

### C5 镜像说明

- `commands/review-mark.md`：「交审要让用户看到内容」条里「名称与顺序同决策收件箱的卡片」改为「名称与顺序同 session-protocol 契约
  的交审小项」，「使用方插件规定……改写“去决策收件箱答 #N”」一句换成 C1 补的那句；`approved` 条「批准的来源只有两种：……
  「经收件枢纽转来的批准」一节」换成 C1 的通用一句。
- `skills/spec-guard-ops/SKILL.md` 的 review-mark 一节、`docs/commands.md` 的 review-mark 一段：同样替换（「待定」第 2 条决定何时改）。
- `docs/workflow.md`「批准要留下记录」一段：「接了收件枢纽（例如 decision-inbox）时……都不算。」两行改为「装了协作插件（例如
  decision-inbox）时，从哪里来的批准算数以它的规定为准；没装只认你在当前对话里的明确批准。」
- README 中英两份不改：它只指向节名「协调会话的批准与合并」，并说「远端合并始终由你来做」，删改后仍然成立。

### C6 回归（`hooks/test_workflow_checkpoints.py`）

- `test_how_to_approve_uses_one_copy_block`：去掉对收件枢纽例外各短语的断言，改为断言 C1 补的那句存在。
- `test_review_sections_follow_the_card_order`：「决策收件箱把这些缩成卡片」换成「session-protocol 契约的交审小项」。
- `test_mirrors_follow_the_card_sections`：去掉「去决策收件箱答」，改为断言「以所装协作插件的规定为准」。
- 协调会话一节的 `test_section_states_every_floor`：去掉「一次只合一个」「Build order」「新提交撤回」「不 reset」「停止后续合并」
  「不自动重试」「不算完成」「冲突」「退回」，加「不改写已推送或已被同步的历史」「由运行时」；另加反向断言：本节不含
  「新提交撤回」「不 reset」「一次只合一个」。
- `HubRelayedApprovalTests` 整类删除，换成一个反向用例：检查点规则、`review-mark.md`、`SKILL.md`、`docs/commands.md`、
  `docs/workflow.md` 都不含「收件枢纽」「去决策收件箱答」「经收件枢纽转来的批准」，且都含通用一句「以所装协作插件的规定为准」。
- 新增：`config.md` 与 `SKILL.md` 的 `moduleConcurrency` 说明含「不控制协调会话」与「`coordinator up`」。

## Acceptance criteria

- **AC1** `workflow-checkpoints.md` 不再含「收件枢纽」「去决策收件箱答」「总协调」，没有「## 经收件枢纽转来的批准」一节；
  `approved` 条含通用一句「批准来源以所装协作插件的规定为准；没装只认当前对话里的明确批准」。
- **AC2** 「协调会话的批准与合并」一节不再含「新提交撤回」「不 reset」「一次只合一个」「合并后跑」；仍含「唯一例外」与三个条件、
  谁写 `approved`、批准绑定具体提交、「不改写已推送或已被同步的历史」、推送与远端合并只由用户、换会话后未写成标记的批准要重新取得。
- **AC3** `config.md` 与 `SKILL.md` 的 `moduleConcurrency` 说明写明不控制协调会话、协调会话由 module-crew `coordinator up` 开启；
  键名与 `project_config.py` 未改（`git diff` 不含该脚本）。
- **AC4** `interface.json` 合法 JSON，`version` 与 `reviewKinds` 取值不变，`reviewKinds.description` 不再含「去决策收件箱答」与
  「hub」；接口相关回归全绿。（经【公共变更请求】落地后核对）
- **AC5** `review-mark.md`、`SKILL.md`、`docs/commands.md`、`docs/workflow.md` 与检查点规则说法一致：都不含收件枢纽话术，都含通用一句。
- **AC6** 约定块模板（`templates/*-block-*.md`）与 `docs/convention-block.md` 未改（`git diff --stat` 不含它们）。
- **AC7** C6 列出的回归改动与新增用例全绿。手工变异：把「新提交撤回、不 reset」一句放回协调会话一节、把「经收件枢纽转来的批准」
  节标题放回检查点规则，对应反向断言各自变红。
- **AC8** `scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿。

## Boundaries

- **会做**：C1～C6；todo 末尾记更新说明（供协调整批写 CHANGELOG），注明已装项目无须重跑 `setup-convention`。
- **先问再做**：发现别处还有只在姐妹插件存在时才有意义的规则（本 Spec 没列到的）——记下交模块协调，不顺手删。
- **不做**：约定块瘦身与停点规则按节点注入（归 `rules-at-nodes`）；补授权两句（D19，归 `rules-at-nodes`）；waiting-on-* 压缩提醒
  （D6，归 `quiet-injection` 等）；改 `checkout-role`、`gateTick`、`module_scope`（D8 留作接口与规划层）；改 decision-inbox、
  module-crew 或 session-protocol 仓库；改版本号与 CHANGELOG；重装或更新本机 spec-guard。

## 并行边界

- 独占：`spec/sibling-rules-out.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/commands/review-mark.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`docs/workflow.md`
- 公共：无

## 边界外的文件

`plugins/spec-guard/interface.json` 经【公共变更请求】由模块协调落地；`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、
`docs/commands.md`、`plugins/spec-guard/commands/config.md` 分属 `history-slim`、`config-per-key` 的独占范围，按「待定」第 2 条在它们
合入后改，届时越界检查会把这三个文件标为「超出并行边界」，最终验收时逐个说明。

## 待定（请在批准时选）

1. **删掉「只在收件枢纽问时不放复制块」之后，复制块规则怎么写**
   - **A（推荐）通用一句同时管「在哪里答复」**：如 C1，补「所装协作插件对在哪里答复另有规定时，以它为准，复制块按它的规定放或不放」。
     不点任何插件的名字和话术，装了 decision-inbox 时不会和它「只在收件箱答」的规定打架。
   - **B 只留 D9 那一句（只管批准来源）**：复制块规则恢复成「总是放」，与协作插件冲突时靠 agent 自己判断。改动最少，但规则字面上
     互相矛盾。
2. **和并行模块重叠的三个文件什么时候改**
   - **A（推荐）最后改**：先做独占文件；`SKILL.md`、`docs/commands.md`、`config.md` 的几句等 `history-slim` 与 `config-per-key`
     合入集成分支、`module-crew sync` 后再改（Plan 里设一个 `gate`：两者没合入就停下发【等待其他会话】）。不会和它们冲突，代价是
     本模块可能要等。
   - **B 现在就改**：只改那几句，合并时冲突交 sync 处理。不用等，但三个文件同时被三个模块改，冲突与越界都要逐个说明。
3. **「决策收件箱的卡片」这类点名也一起改掉吗**
   - **A（推荐）改**：如 C1、C5，改成「session-protocol 契约的交审小项」，删「决策收件箱把这些缩成卡片」。D9 要求小项名称与
     session-protocol 一致，按契约命名比按某个插件的界面命名更准。
   - **B 不改**：只删 D9 点名的话术与条件，这几处保留。范围最小，但检查点规则里仍点名一个姐妹插件的界面。

## 文档建议

只改说明类文档（`docs/workflow.md`、`docs/commands.md`）与插件内规则文本；README 不改（理由见 C5）；项目没有文档基线，不需要文档影响登记。
