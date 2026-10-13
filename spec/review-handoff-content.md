# Spec: review-handoff-content

<!-- spec-guard: review approved 55cd6cb400c2 -->

## Objective

0.57.0 的评审状态标记规定了“什么回复算批准”，没有规定“交审时必须让用户看到什么”。2026-10-13 两个互不相干的会话的
只读统计显示：agent 交审时在对话里只写一句概述加文件链接。其中一个会话 16 次正式交审，正文中位数约 230 字，内容是
“已生成某某 Plan 加几条任务标题加请审核”；没有一次给出 Spec 的范围、关键决策、假设、验收标准，或 Plan 各任务的验证
方式与检查点类型。另一个会话约 2 小时 7 个模块、约 25 次批准，用户原话是没有看到 Spec、Plan、任务的内容。标记、指纹与
`verify-artifacts` 全部通过——批准是在用户没看到内容的情况下合规地发生的。

这是规则缺口，不是使用错误：评审规则与约定块模板里都没有“交审时在对话正文呈现内容”的要求，0.57.1 加的“交审时就告诉
用户回复‘批准’即可”还把交审文案进一步压短了。同一批观察里的另一面：默认的分开审在快节奏项目里变成高频往返，而能解决它的
合并审节奏早已存在，agent 从未向用户提过。

本模块规定交审必须呈现的内容，让记录批准的命令提醒一次，并让合并审这个选项被看见。

登记：2026-10-13 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-13 确认：

1. Spec 交审要在对话里呈现：目标、范围内与范围外、关键决策与取舍、假设、验收标准、未决问题。
2. Plan 交审要呈现：任务与各自的验证方式、检查点及其类型（`gate`／`report`）、影响面、风险。
3. 短文件可以贴全文；长文件给要点加文件链接。只给链接或只给一句概述不算交审。
4. 每次交审写明这次批准授权什么。
5. 合并审下一次交审同时呈现 Spec 与 Plan 两份的要点，并说明一次批准同时批准两份。
6. `review-mark` 的提醒只是提醒：预览多出文件行数与指纹，以及一句确认用户已在对话里看到内容；不新增拒绝条件。
7. 合并审的提示只说一次：分开审节奏下，一个会话里第一次交审时说明可以改为合并审，之后不再提；靠规则文字约束，钩子不计数。
8. 接入完成时的输出写明评审节奏的两种取值与各自适合的情况。
9. 不改任何判定：评审状态、阶段、`verify-artifacts` 的输出都不变。既有项目重新运行 `setup-convention --replace` 后拿到
   新的约定块文字。
10. 版本 0.58.1，一个 PR。
11. 不做：机器验证用户是否看过；处理已经发生的批准。

## Contract

### 规则文字

`references/workflow-checkpoints.md` 的「评审状态标记」一节新增“交审要让用户看到内容”，要点：

- 交审是把内容放到用户面前，不是通知用户文件写好了。在对话正文里给出：
  - **Spec**：目标；范围内与范围外；关键决策与取舍；假设；验收标准；未决问题。
  - **Plan**：每个任务与它的验证方式；检查点及其类型（`gate` 停下、`report` 继续）；影响面（会改哪些地方）；风险。
- 短文件可以贴全文；长文件给上述要点并附文件位置。只给链接、只给一句概述、只列任务标题都不算交审。
- 写明这次批准授权什么（例如批准 Spec 之后写 Plan；批准 Plan 之后连续执行到哪个 `gate`、是否含推送与开 PR）。
- `combined` 节奏下一次交审同时呈现两份的要点，并说明一次批准同时批准 Spec 与 Plan。
- 用户没有在对话里看到内容时给出的批准不记为 `approved`：先补上内容再请用户确认。
- 原有的“请求审核时说明怎么批准”保留，并注明它是在呈现内容之后的一句，不能替代内容。

同一文件的「评审节奏」一节新增：`separate` 节奏下，agent 在一个会话里第一次交审时说明一次——这个项目也可以改为 `combined`
（Spec 与 Plan 一起审、一次批准），用 `/spec-guard:config` 设置；之后不再重复。

两份约定块模板（`claude-block-local.md`、`codex-block-local.md`）里讲评审标记的那一行补半句：交审时在对话里呈现内容要点，
只给链接不算交审。`docs/convention-block.md` 同步。

### `review_mark.py`

`--state approved` 的预览与写入输出里，对每个目标文件多一行：文件的行数，以及（Spec）将写入的指纹；另加固定的一句提醒：
写入前确认用户已在对话里看到这份文件的内容要点，只给过链接或一句概述时先补上内容。不新增拒绝条件，退出码与写入行为不变。
`--state pending` 的输出不变。

### 接入输出

`setup-convention.sh` 完成时现有的 `Optional:` 一行改为说明评审节奏的两种取值：`separate`（默认，Spec 批准后再写 Plan、
各审一次，适合决策多或风险高的工作）与 `combined`（Spec 与 Plan 一起审、一次批准，适合小步快走），用 config 命令设置。
产物语言的说明保留。

### 文档与版本

`commands/review-mark.md`、`spec-guard-ops` 的 review-mark 一节同步规则要点；`docs/workflow.md` 讲评审的一段补充；
`docs/commands.md` 的 review-mark 条目；CHANGELOG `[0.58.1]`；版本号 0.58.1。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 -B plugins/spec-guard/hooks/test_review_marker.py
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先改测试并确认在现有代码上失败，再改文字与输出。
- `test_workflow_checkpoints.py`：「评审状态标记」含 Spec 的六个要点、Plan 的四个要点、“只给链接不算交审”“授权什么”
  “没有看到内容时不记为 approved”；「评审节奏」含“第一次交审时说明一次”与 config 命令；两份约定块模板各含“呈现内容要点”
  与“只给链接不算交审”。
- `test_review_marker.py`：`approved` 的预览含文件行数与那句提醒，Spec 另含指纹；`pending` 的输出不含；退出码与写入结果
  不变（现有用例全部通过）。
- `test-setup-teardown.sh`：接入完成的输出含 `separate` 与 `combined` 两种取值的说明。
- `test-phase-guard.sh`、`test-verify-artifacts.sh` 不改，全部通过即证明判定与输出未变。
- 宿主行为：发版后在两边各一次真实会话里，让 agent 在临时项目写一份 Spec 并交审，核对它的交审正文是否含范围、决策、
  验收标准而不只是链接。静态断言只证明规则可被找到，不表述为行为验收。

## Boundaries

- Always：只改规则文字、命令输出与接入输出；评审状态与阶段的判定不变；先红后绿。
- Ask first：让 `review-mark` 因“未呈现内容”而拒绝；让钩子统计批准次数或提示节奏；改默认的评审节奏。
- Never：声称机器能验证用户看过内容；替用户把已有的批准判为无效；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的
  名称、模块或编号。

## Success criteria

- 规则与两份约定块模板都写明交审要呈现哪些内容、只给链接不算交审、要写明授权范围。
- `review-mark` 写已批准时提醒一次确认用户已看到内容，行为不变。
- 分开审节奏下用户能在第一次交审与接入完成时得知合并审这个选项。
- 评审状态、阶段与 `verify-artifacts` 的输出不变；三条最小验证与 ShellCheck 全部通过。
- 真实会话里 agent 的交审正文包含 Spec 的范围、关键决策与验收标准。

## Open questions

- 无。
