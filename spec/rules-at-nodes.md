# Spec: rules-at-nodes

<!-- spec-guard: review approved 5c607355746c -->

## Objective

约定块（`templates/claude-block-local.md` 7.5KB、`codex-block-local.md` 7.1KB）一次写进三十多条流程规则，每轮都在上下文里，
其中大半只在某个停点才用得上（交审怎么呈现、各类要点、最终验收的几张表、何时问用户）。决定 D3、D4 定下：这些规则留在
spec-guard，但挂到它的节点上——

1. **途中规则压成常驻短句。** 连续执行中随时可能用到的（UI 自验、任务完成报告、`report` 记入 todo、不可逆操作要停）留在约定块，
   每条一句；另留一句兜底：「停在 gate 前（或要停下问用户前），先加载停点规则对应一节」。
2. **停点规则到节点才注入。** 交审呈现、能力图／Spec／Plan／中途 gate／最终验收各类要点、验收的表格、何时问用户，从约定块移出，
   由阶段注入（`phase-guard.sh` → `module_stage.py`）在当前模块处于对应节点时附上那一节的原文。
3. **补授权两句（D19）。** ①项目自己的规则比 spec-guard 默认授权更严时，以项目为准；②最终 gate 列出的「拟回告」须是可原样发送的
   完整文字，批准 gate 即同意按此发送（对外渠道同样），内容变了要重新给用户看。

登记：2026-10-22 修复批次 12 个模块之一，经用户批准事项 C100 开模块会话；能力图依赖 `sibling-rules-out`（已合入，它删了检查点
规则里的收件枢纽话术，并把「约定块瘦身与按节点注入、补授权两句」留给本模块）。后续 `quiet-injection`（D5：平时只给一行、到停点
才全量）与 `batch-insert-concurrency-hint` 依赖本模块；`doc-chain` 会往最终验收那一节追加文档核验。
依据：`docs/reports/2026-10-22-feature-inventory/decisions.md`（D3、D4、D19）；审查报告 F1、F4（`docs/reports/2026-10-22-multidimension-audit.md`）。

## Assumptions

以下是写 Spec 时定下的前提，请在批准时一并确认：

1. **停点规则放进一个新的小文件，注入原文、不注入指向。** 新建 `plugins/spec-guard/references/node-rules.md`，每个节点一节（见 C2）。
   阶段注入到节点时把那一节原文附在阶段输出里。不只给「去读某一节」的指向，理由：`rules-in-context`（0.63.4）实测过，agent 很少
   回读规则文件（一个 6 小时的真实会话只在开头读过一次），审查 F4 也记了 Claude 侧 30 天只 Read 了 12 次；注入原文，节点上的规则
   就在当轮上下文里。`workflow-checkpoints.md` 仍是完整细则，`node-rules.md` 是它的节点摘要，开头写明「冲突时以共享检查点规则为准」，
   回归断言两边的关键短语一致（AC6）。
2. **这推翻了 `rules-in-context` 的一个做法。** 它把三条交审规则写进约定块原文（交审要点在确认框之前、最终验收附 Spec 差异、验收后
   接着写下一份 Spec），理由是「agent 每轮都看得到」。本模块把它们移进停点规则，在节点由阶段注入带进当轮上下文，目的不变、
   位置改变；`test_the_review_rules_live_in_the_convention_block` 改为断言这三条出现在对应节点的注入里。`spec/rules-in-context.md`
   本身不改（已完成模块的记录）。
3. **节点由阶段注入已有的判定识别，只看当前模块。** 不新增状态文件：
   - 能力图审阅：没有能力图（`IDLE`）。
   - Spec 交审：当前模块 `NEEDS_SPEC`，或 Spec 标记为 `pending`、`revised`（构建中被改、未到最终验收）。
   - Plan 交审：`NEEDS_PLAN`，或 Plan 标记为 `pending`。
   - 中途 gate：`BUILDING`，todo 第一个未勾项是 `gate` 检查点、但不是最后一个 gate（`next_gate` 与 `at_final_gate` 现有判定）。
   - 最终验收：`BUILDING` 且 `at_final_gate` 为真。
   - 其余情形（构建途中、`MODULE_DONE`、`DONE`、`MAP_ONLY` 以外的诊断态）不附停点规则。`MAP_ONLY` 时下一步是写第一份 Spec，按
     Spec 交审附。
   同一轮只附一节；一轮同时满足两个时取上面列表里靠后的（例如 `combined` 节奏下 Spec 待批准且在写 Plan，附 Plan 交审；
   Plan 交审那一节写明 `combined` 时 Spec 的五项也要给）。
4. **兜底一句覆盖「轮中到达节点」。** 阶段注入只在每轮开始（UserPromptSubmit）和压缩后运行；`/build` 连续执行时，agent 常在
   一轮中途才走到 gate，那一轮开头注入的还是途中状态。所以约定块常驻一句：「停在 gate 前、交审前或要停下问用户前，先读停点规则里
   对应的一节」，并写明文件位置：共享检查点规则开头加一行指向 `node-rules.md`（同目录相对链接），约定块写「`spec-guard:spec-guard-ops`
   的停点规则」。D4 原话只说「停在 gate 前」，这里把交审前与问用户前也写进兜底，请确认。
5. **并行开关下的角色视图不附停点规则。** checkout 标了角色（模块会话、协调会话）时，阶段输出现在就不出批准提示与外部审查行
   （`role_kind` 判断），交审格式由所装协作插件规定；停点规则同样不附，兜底一句照常常驻。串行（没有角色）时才附。
6. **停点规则只有中文。** 约定块、共享检查点规则现在都只有中文；`artifactLanguage` 不是 `zh-CN` 的项目，阶段输出的其余部分照旧
   用英文，附上的停点规则一节仍是中文。翻译不在本模块范围。
7. **常驻短句保留的条目（C1 逐条列出）。** 目录与产物约定、`activeModule`、事项账本入口、项目级审查、需求确认、批准标记的
   pending／approved 一句、变更记录、宿主确认指路、承诺记账、对外通道先给草稿、产物语言与配置都留，压成一句；它们是任何时候都可能
   用到、或是目录约定本身，不属于某个停点。审查报告 G2「拆成可选规则包」不在本模块：D4 定的是按节点注入，不是按包开关。
8. **约定块体积目标。** Claude 模板 ≤ 4000 字节、Codex 模板 ≤ 3800 字节（现 7530 / 7097）；每个停点规则一节 ≤ 2600 字节，
   最终验收一节允许到 3200 字节（它要列三张表、证据、Spec 差异、拟回告与下一步）。超了就再压，不放宽。
9. **D19 两句的落点。** ①写进共享检查点规则「Plan 检查点分级」的「批 Plan 按范围授权」条末、约定块授权短句、Plan 交审一节；
   ②写进「需求来源与回告」的「回告」段（替换「对象、渠道、内容（……）」那条的写法）与最终验收一节。外部渠道原有的「邮件、公开评论
   先给草稿，用户答应才发」不变：最终 gate 里给出的全文就是草稿，批准 gate 即答应；到发送时内容和批准时不同，重新给用户看。
10. **只改说明文字与阶段注入，不改判定。** `review_state`、`next_gate`、`at_final_gate`、`gate_checkpoints` 与指纹算法一行不改；
    新增的只是「按节点取一节文字附上」。
11. **CHANGELOG 与版本号不在本模块改**，由模块协调整批合完后统一改；更新说明记在 todo 末尾。

## Contract

### C1 约定块瘦身（`templates/claude-block-local.md`、`templates/codex-block-local.md`，镜像 `docs/convention-block.md`、本仓库 `AGENTS.md`）

两份模板结构相同，命令写法按宿主（与现行差异一致：Codex 写 `spec-guard-ops` 的某一节、`delegate:delegate-routing` 等）。
块头两行、`<!-- BEGIN/END -->` 与本地段规则不变。条目按下表处理（「现行」指 0.83.2 模板里的条目，按出现顺序）：

| 现行条目 | 处理 |
|---|---|
| 能力图与模块 spec 路径；不要在根建 `SPEC.md`；产物隔离；`/build` 取任务；切换 `activeModule` | 保留原文（目录约定本身） |
| 事项账本先用 `spec-guard:ticket` 查重 | 保留，压成一句 |
| 项目级审查按共享检查点规则限定批次 | 保留，压成一句 |
| 托管 Issue 用 `hosted-ticket-workflow` | 保留，压成一句 |
| 阶段交接或停止时加载共享检查点规则 | 并入兜底一句 |
| Plan 检查点 `gate`／`report` 与默认级别 | 常驻短句：「`report` 检查点把验证结果记入 todo 后继续；没标级别的中间检查点按 `report`，最后一个检查点按 `gate`，推送与不可逆操作须标 `gate`、到了要停」 |
| 批 Plan 即按范围授权 | 常驻短句，末尾加 D19①：「项目自己的规则更严时以项目为准」；「只问用户的情形」移到停点规则 |
| 需求确认 | 保留，压成一句 |
| 交审呈现要点、只给链接不算交审 | 移到停点规则（Spec 交审、Plan 交审、能力图审阅） |
| 提议 delegate 只读审查 | 移出：阶段注入在这三个节点本来就出外部审查行（`external_review_hint`），停点规则相应一节保留一句 |
| UI 自验 | 常驻短句：「任务改到用户看得到的界面时，在这个任务里打开页面对照预期验证并写清看了什么；没有自验记录或“UI 未验证＋原因”不能勾完成」 |
| 最终验收的文件、提交、依赖表格 | 移到停点规则（最终验收）；「任务做完的结果带文件数与提交号」作为常驻短句保留 |
| 文档建议 | 移到停点规则（能力图审阅、Spec 交审） |
| 同一模块、同一目标第二次过不去 | 移到停点规则（中途 gate、最终验收），兜底一句覆盖「要停下问用户前」 |
| 宿主确认指路 | 保留，压成一句 |
| AC 编号与按编号给证据 | 移到停点规则（Spec 交审、最终验收） |
| 批准标记 pending／`review-mark` 记 approved | 常驻短句：「交审的 Spec、Plan 标 `pending`，用户明确批准后才用 review-mark 记 `approved`」；细则移到停点规则 |
| 已批准文件改动记「变更记录」 | 保留，压成一句 |
| 回告来源、用 agent-relay 发消息 | 移到停点规则（最终验收），连同 D19② |
| 承诺记账（`waiting-on-*`）与当场记账 | 两条合成一句常驻 |
| 替用户承诺先问；对外通道先给草稿 | 保留，压成一句 |
| 一次一个模块交审、按模块分组 | 移到停点规则（Spec 交审、Plan 交审） |
| 交审要点写在确认框之前 | 移到停点规则（每个交审类节点都写） |
| 最终验收附 Spec 差异一次批 | 移到停点规则（最终验收） |
| 验收后直接写下一个模块的 Spec | 移到停点规则（最终验收） |
| 产物语言与批准节奏以 `.agent/config.json` 为准 | 保留 |
| （新增）兜底一句 | 「停在 gate 前、交审前或要停下问用户前，先读 `spec-guard:spec-guard-ops` 停点规则里对应的一节（能力图审阅、Spec 交审、Plan 交审、中途 gate、最终验收）；阶段提示在节点上会直接附上它」 |

`docs/convention-block.md` 内嵌块与 Claude 模板逐字节一致（`check-readme-sync.py` 照旧检查）。本仓库 `AGENTS.md` 的 Codex 块用工作区的
`setup-convention.sh local --host=codex --replace --accept-removals` 升级（本地段原样保留），不手改。

### C2 停点规则（新文件 `plugins/spec-guard/references/node-rules.md`）

开头两句：本文件是共享检查点规则在各节点的摘要，阶段提示到节点时附上对应一节；与 `workflow-checkpoints.md` 冲突时以后者为准。
之后五节，标题固定（阶段注入按标题取节）：

- `## 能力图审阅`：在对话正文、确认框之前给出三项（拆成哪些模块、先后顺序、文档建议，README 一定表态）；需求先确认说完；一次看全
  所有模块不算合并交审；怎么批准（选项与后果、推荐理由、推荐答复放一个可复制代码块；协作插件另有规定以它为准）。
- `## Spec 交审`：五项（目标；做／不做；要你确认的假设；验收标准按 AC1、AC2… 逐条全列；附带的小决定）＋「注意：」「批了会怎样：」；
  文档建议有才提；交审要点写在本轮正文、确认框之前，只给链接不算；文件标 `pending`，批准后先 review-mark 再动手；一次只放一个模块，
  合并交审按模块分组；值得复核时可提议 delegate 只读审查（不算批准）；怎么批准（同上）；批准来源以所装协作插件的规定为准，没装只认
  当前对话里的明确批准。
- `## Plan 交审`：四项（分几步；会改哪些文件；风险；中途会停下来问你的地方，列出 `gate` 并写明是否含推送与开 PR）＋「注意：」
  「批了会怎样：」（连续执行到哪个 `gate`）；`combined` 节奏下先写 Spec 五项；批 Plan 即按范围授权的内容与「项目自己的规则更严时
  以项目为准」（D19①）；只在哪几类情况停下问用户（现行清单原样列出）；交审呈现、标记、一次一个模块、怎么批准同 Spec 交审（各写一句）。
- `## 中途 gate`：三项（做到哪了；为什么停在这；接下来要做的那一步）＋「注意：」「批了会怎样：」；开头五件事落在这三项里；
  只问用户的情形；同一模块、同一目标第二次过不去时停下给选项与代价（挂起并先开可开工模块、接受风险、换方案、一次列全所需权限），
  不按默认推荐重试；宿主确认指路不算问用户做决定。
- `## 最终验收`：四项（做了什么；验收结果按 AC 编号逐条给证据与完整检查结果；改了哪些文件——文档表在最前、文件表、提交表、新增依赖与
  锁文件，没有写“无”，超出 Plan 影响面或并行边界的单独标出；Spec 中途改过吗——改过就原样附差异并写明一次批准同时批准修订后的 Spec）
  ＋「注意：」「批了会怎样：」；拟回告：对象、渠道与**可原样发送的完整文字**，批准本 gate 即同意按此发送（对外渠道同样），到发送时
  内容变了要重新给用户看（D19②）；批准后先 review-mark 记 Spec（如修订过）、再勾选这个 gate 与状态记录并一并提交；推送、开 PR 另按
  gate 写明的授权；验收获批后下一个模块已在能力图里且用户没说停，直接写它的 Spec 并交审，验收消息预告这一步并提示可先 `/compact`。

每节只写规则本身，不写示例；体积按假设 8。

### C3 阶段注入附停点规则（`hooks/module_stage.py`，`phase-guard.sh` 的 IDLE／MAP_ONLY 分支）

- `module_stage.py` 新增两个函数，作为后续模块（`quiet-injection` 判「到停点」、`doc-chain` 往最终验收追加）的接口：
  - `stop_node(root, module, stage, spec_review, plan_review) -> str | None`：按假设 3 返回 `"map-review"`、`"spec-review"`、
    `"plan-review"`、`"mid-gate"`、`"final-gate"` 或 `None`；读不到 todo、认不出检查点时按现有判定降级（`next_gate` 为空即不算 gate 节点）。
  - `node_rules(kind) -> str`：从插件自己的 `references/node-rules.md` 取对应标题的一节原文（到下一个 `## ` 为止）；文件缺失、读不了、
    没有这一节时返回空串，阶段输出照旧、不报错（降级不误报）。
- `describe()`：串行（`role_kind` 既不是 `module` 也不是 `coordinator`）且 `stop_node` 非空时，在「建议下一步」之后另起一段附上：
  `停点规则（<节点名>）：` 加该节正文（英文提示写 `Stop rules (<node>):`，正文仍是中文）。其余输出逐字不变。
- 命令行新增 `--node-rules <kind>`，只打印该节（空时不打印）；`phase-guard.sh` 的 `IDLE` 分支在建议下一步之后用它附 `map-review`，
  `MAP_ONLY` 分支附 `spec-review`（中英两个分支都附）。取不到时不附，输出与改前逐字相同。
- 不改 `phase-guard.sh` 的其他段落（「关联项目」四段归 `cost-slim-link-follow`）。

### C4 共享检查点规则（`references/workflow-checkpoints.md`）

- 开头「五件事」之前加一行：「各节点的摘要见同目录 [停点规则](node-rules.md)，阶段提示到节点时会附上对应一节；两者冲突时以本文件为准。」
- 「Plan 检查点分级」的「批 Plan 按范围授权」条末加 D19①：「项目自己的规则（项目的 `CLAUDE.md`／`AGENTS.md`、项目约定）比这里更严时，
  以项目为准。」
- 「需求来源与回告」的「回告」段：「最终 gate 交审时列「拟回告」：对象、渠道、内容（……）。没有就写“无”。批准最终 gate 即批准回告，
  到了用得上的时刻按批准的内容发。」改为：「最终 gate 交审时列「拟回告」：对象、渠道，以及可以原样发送的完整文字（做完了什么、版本号或
  提交号、怎么用、与原约定的不同），不写概述。没有就写“无”。批准最终 gate 即同意按这段文字发送，对外渠道（邮件、公开评论等）同样；
  到了用得上的时刻，内容要变（例如版本号定了、做法变了）就把改后的全文重新给用户看，用户答应后再发。」
- 其他小节不动。

### C5 镜像与说明

- `docs/workflow.md` 第 94 行附近「这几条也写在约定块里：……才会拿到新行」改为说明：这几条现在在停点规则里，阶段提示到最终验收时
  附上；升级插件后重跑 `setup-convention --replace` 让约定块变短（见「对使用者的影响」）。
- `commands/setup-convention.md`：在 `--replace` 说明后加一句「从 0.83 及更早的模板升级时，删掉的行都标 `[needs --accept-removals]`，
  它们已移到停点规则，确认后加 `--accept-removals`」。
- README 中英两份只在描述约定块内容的句子过时时改（核对过当前只链接 `docs/convention-block.md`，预计不改）。

### C6 回归

- `hooks/test_workflow_checkpoints.py`：所有对 `*-block-local.md` 断言「停点规则」短语的用例（交审呈现、验收表格、文档建议、AC 编号、
  第二次过不去、确认框之前、Spec 差异、下一份 Spec、delegate 提示等）改为断言 `node-rules.md` 对应一节含这些短语；对模板改为断言
  常驻短句（UI 自验三短语、`report` 记入 todo、不可逆要停、按范围授权、项目更严以项目为准、兜底一句、批准标记一句）与「不含」
  已移出的长条目（例如「本模块的提交（提交号＋一句话）」「单独一张表放在最前」）。`block_surfaces()` 照旧含 `AGENTS.md` 与
  `docs/convention-block.md`。
- 新增：`node-rules.md` 五节标题齐全、各节体积在假设 8 以内；两份模板体积在假设 8 以内；检查点规则含指向 `node-rules.md` 的一行、
  D19① 一句、D19② 的「可以原样发送的完整文字」「重新给用户看」。
- 新增一致性断言：`node-rules.md` 每节的关键短语（例如 Spec 交审的五项名称、最终验收的「文档改动：无」「新增依赖、锁文件改动：无」）
  在 `workflow-checkpoints.md` 里也出现。
- 新建 `hooks/test_stop_rules.py`，并在 `scripts/validate.sh` 的检查清单里登记一行（与 `test_gate_tick.py` 同样写法）：`stop_node` 对五种节点与 `None` 各一例；`node_rules` 对缺文件、缺节返回空；
  `describe()` 在串行最终验收时含「停点规则（最终验收）：」与「可以原样发送的完整文字」，角色视图（模块、协调）不含；BUILDING 途中不含。
- `hooks/test-phase-guard.sh`：`IDLE` 输出含「停点规则（能力图审阅）：」、`MAP_ONLY` 含「停点规则（Spec 交审）：」；把 `node-rules.md`
  挪走后两者都不出、退出码 0、JSON 合法。
- `test_ticket_entry.py`、`test_hosted_ticket_entry.py`：只断言 `ticket`、`hosted-ticket-workflow` 入口仍在模板里，预计不用改；
  断言失败再按 C1 的保留条目调整。

## 对使用者的影响

- **已装项目要重跑 `setup-convention --replace` 才变短。** 不重跑时旧的长约定块照旧有效：规则与停点注入重复，多占上下文，但不互相矛盾
  （停点规则是同一套规则的摘要，补上的 D19 两句只是更严）。
- **升级步骤**：先 `/spec-guard:setup-convention --replace --dry-run`，旧模板删掉的行会标 `[needs --accept-removals]`；要保留其中某几行的，
  先移进本地段；确认后 `--replace --accept-removals`。Codex 同样（`setup-convention local --host=codex …`）。
- **新行为**：阶段提示到能力图审阅、Spec 交审、Plan 交审、中途 gate、最终验收时多出一段「停点规则（…）」；串行项目才有，
  并行开关下标了角色的 checkout 没有。
- **拟回告变严**：最终验收要给可原样发送的全文，不再只列「内容要点」。
- 更新说明记在 todo 末尾，供模块协调整批写 CHANGELOG。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 plugins/spec-guard/hooks/test_stop_rules.py
python3 scripts/check-readme-sync.py
```

## Acceptance criteria

- **AC1** 两份约定块模板不再含已移出的停点条目（「单独一张表放在最前」「本模块的提交（提交号＋一句话）」「确认框之前」「附上 Spec 的改动差异」
  「直接写它的 Spec」「同一模块、同一目标」「AC1、AC2」「交审一次只放一个模块」），含 C1 列的常驻短句与兜底一句；Claude 模板 ≤ 4000 字节、
  Codex 模板 ≤ 3800 字节（`wc -c`）。
- **AC2** `docs/convention-block.md` 与 Claude 模板一致（`check-readme-sync.py` 通过）；本仓库 `AGENTS.md` 的 Codex 块与 Codex 模板一致，
  本地段原样保留。
- **AC3** `references/node-rules.md` 有五节，标题与 C2 一致，每节含 C2 列出的规则要素；体积在假设 8 以内。
- **AC4** 串行项目里，五种节点的阶段输出各附对应一节（「停点规则（<节点名>）：」+ 正文），构建途中、`MODULE_DONE`、`DONE` 不附；
  并行开关下标了角色的 checkout 不附；`node-rules.md` 缺失时不附且输出与改前逐字相同、JSON 合法。
- **AC5** 检查点规则：开头有指向 `node-rules.md` 的一行；「批 Plan 按范围授权」条含「项目自己的规则……更严时，以项目为准」；「回告」段含
  「可以原样发送的完整文字」「同意按这段文字发送」「重新给用户看」；`node-rules.md` 的最终验收与 Plan 交审两节含对应句子。
- **AC6** 一致性回归：`node-rules.md` 每节的关键短语在 `workflow-checkpoints.md` 中都有。手工变异：从 `node-rules.md` 删去最终验收的
  「文档改动：无」、从模板删去兜底一句、把「单独一张表放在最前」放回模板，对应断言各自变红。
- **AC7** `review_state`、`next_gate`、`at_final_gate`、`gate_checkpoints`、`spec-digest.py` 未改（`git diff` 不含这些函数体的改动）。
- **AC8** C6 列出的回归改动与新增用例全绿；`scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿。

## Boundaries

- **会做**：C1～C6；todo 末尾记更新说明与「对使用者的影响」。
- **先问再做**：停点注入要改 `phase-guard.sh` 的 IDLE／MAP_ONLY 以外的结构；体积目标压不到假设 8；发现别的条目归属拿不准（停点还是常驻）。
- **不做**：D5 的平时只给一行、状态变了才全量（归 `quiet-injection`）；D6 上下文提示（归 `quiet-injection`）；文档核验接进最终验收（归 `doc-chain`）；
  拆成可选规则包（审查 G2，不在 D4 范围）；停点规则的英文版；改 `review_state` 等判定与指纹算法；改 `rules-in-context` 等已完成模块的 Spec；
  改 decision-inbox、module-crew、session-protocol 仓库；改版本号与 CHANGELOG；重装或更新本机 spec-guard。

## 并行边界

- 独占：`spec/rules-at-nodes.md`、`tasks/rules-at-nodes/plan.md`、`tasks/rules-at-nodes/todo.md`、`plugins/spec-guard/templates/claude-block-local.md`、`plugins/spec-guard/templates/codex-block-local.md`、`plugins/spec-guard/references/node-rules.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/test_stop_rules.py`、`scripts/validate.sh`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/hooks/test_ticket_entry.py`、`plugins/spec-guard/hooks/test_hosted_ticket_entry.py`、`docs/convention-block.md`、`AGENTS.md`
- 公共：无

## 与在开模块的重叠

- `cost-slim-link-follow`（与本模块并列）独占下面这些文件，本模块只改所列部分：`plugins/spec-guard/hooks/phase-guard.sh`（只改 IDLE／MAP_ONLY
  四个分支末尾附停点规则；它只改「关联项目」四段）、`plugins/spec-guard/hooks/test-phase-guard.sh`（只加 C6 那几条断言）、
  `plugins/spec-guard/commands/setup-convention.md`（只加 C5 一句）、`docs/workflow.md`（只改 C5 那一段）、`README.md`、`README.en.md`
  （预计不改）。后合入的一方先 `module-crew sync`，冲突以集成分支为底手工合并。
- 独占清单里 `node-rules.md`、`test_stop_rules.py` 是新建文件；`scripts/validate.sh` 只加登记一行。`interface.json` 不改：停点规则是
  插件内部文件，不进接口；CHANGELOG、两份 `plugin.json`、`marketplace.json`、`.agent/state.json` 由模块协调统一改。
- `quiet-injection`（在本模块之后）也改 `phase-guard.sh`、`module_stage.py`：它用本模块的 `stop_node` 判「到停点」。
