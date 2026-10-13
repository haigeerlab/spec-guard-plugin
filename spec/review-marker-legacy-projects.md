# Spec: review-marker-legacy-projects

<!-- spec-guard: review approved 680f79cc6e52 -->

## Objective

0.57.0 的评审状态标记（`review-approval-marker`）定下一条原则：没有标记的文件判定照旧，既有项目不必补标记。发版当天在
既有项目上的实地使用暴露出两处与这条原则不一致的地方，以及一处用户摩擦：

1. **Next gate 在没有标记的 Plan 上加重了误导。** BUILDING 阶段新增的那一行写着“keep going until it”。Plan 实际还在
   等用户审核、只是没有标记时，这句话是在一份未获批准的计划上催促连续执行，比 0.56.0 只说“continue build”更强。
2. **拒绝促成了一次没有问过用户的批准。** Spec 是旧版本时期确认的、没有标记；`review_mark.py` 因此拒绝单独把 Plan 标为
   已批准。agent 随即把 Spec 也标为已批准并写入指纹，依据是用户早前一句含糊的答复，而用户这次批准的只是 Plan。
3. **用户第一次被挡时不知道规则变了。** 用户习惯用“继续”表示同意，连输两次都没被记为批准，第三次改口才通过；
   agent 是在用户说了“继续”之后才解释，给的示范句也比实际需要的长。

本模块修正前两处的行为，并把第三处写进规则文字。不改任何判定：阶段名、五种评审状态、`verify-artifacts` 的检查都不动。

登记：2026-10-13 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-13 确认：

1. **Spec 没有标记时，允许单独把 Plan 标为已批准。** “没有标记 = 判定照旧”，它就不该挡住别的操作；拒绝本身是 agent 去补记
   Spec 批准的动因。Spec 为待审核、已修订、标记无效或读不了时仍然拒绝。
2. **Next gate 用中性措辞。** Plan 没有评审标记时，这一行只指出 todo 里第一个未勾选的 `gate` 检查点，并说明 Plan 没有
   评审标记、用户尚未批准时先等批准。Plan 已批准时保持 0.57.0 的文字。不采用“没有标记就不输出”，那会丢掉它对既有项目的
   提示价值。
3. **规则文本补一条“既有项目”**：不得把此前含糊的答复补记成批准；要给既有的 Spec 或 Plan 补标记，先预览并向用户
   单独确认一次。
4. **请求审核时就说明怎么批准。** 规则要求 agent 在把 Spec 或 Plan 交给用户审核的那一刻说明：回复“批准”即可，
   “继续”不会被记为批准；示范用最短的可接受说法。
5. 不改判定：阶段名、完成判据、五种评审状态、`verify-artifacts` 的检查与输出都不变。
6. 版本 0.57.1，一个 PR。
7. 不在范围内：Plan 的批准绑定指纹（有意不绑）；“继续不算批准”扩展到 Spec、Plan 之外的确认；Claude 安装副本上读取
   包外文件的四条测试；跨目录项目定位。

## Contract

### Next gate

BUILDING 且建议语为“继续 build”时仍输出一行 `- Next gate: <标题>`，后半句按当前模块 Plan 的评审状态取：

| Plan 状态 | 后半句 |
|---|---|
| `approved` | 与 0.57.0 逐字相同：`keep going until it; a `report` checkpoint is recorded in the todo and passed without stopping.` |
| `none` | 中性说明：这是 todo 里第一个未勾选的 `gate` 检查点；Plan 没有评审标记，用户尚未批准时先等批准再构建。不含“keep going”。 |

其余状态（`pending`、`invalid`、读不了，或 Spec 为 `pending`／`revised`／`invalid`）在 0.57.0 已不输出这一行或不建议继续，不变。
这一行仍只含固定文字与清洗后的检查点标题。

### `review_mark.py`

`--target plan --state approved` 时按 Spec 的评审状态决定：

| Spec 状态 | 行为 |
|---|---|
| `approved` | 照常（不变） |
| `none`（没有标记，或 Spec 文件不存在） | **允许**。预览与写入结果里多一行说明：Spec 没有评审标记，本次只记录 Plan 的批准 |
| `pending`、`revised`、`invalid`、读不了 | 拒绝（退出码 2、不写文件）。拒绝信息写明：Spec 的批准需要用户针对这份 Spec 单独明确确认；Plan 的批准或此前的“继续”不覆盖它；先把 Spec 交用户审核 |

`--target both`、`--target spec`、`--state pending` 的行为不变。批准时已有的那句提醒（标记是记录、不是授权来源）不变。

### 规则文本

`references/workflow-checkpoints.md` 的「评审状态标记」一节：

- 新增“请求审核时说明怎么批准”：交审的那一刻告诉用户回复“批准”即可、“继续”不会被记为批准；不要等用户说了“继续”再解释。
- 新增“既有项目”：没有标记的 Spec 或 Plan 不必补标记；要补时先预览并向用户单独确认一次，不得依据此前含糊的答复补记；
  Spec 没有标记不妨碍单独记录 Plan 的批准。

`commands/review-mark.md` 与 `spec-guard-ops` 的 review-mark 一节同步这两点和上表的拒绝条件。`docs/commands.md` 的拒绝条件、
`docs/troubleshooting.md` 的 Next gate 一行、CHANGELOG `[0.57.1]`。约定块模板不改。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_review_marker.py
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先改测试并确认在 0.57.0 的代码上失败，再实现。
- `test-phase-guard.sh`：Plan 无标记时 Next gate 是中性措辞且不含“keep going”；Plan 已批准时与 0.57.0 逐字相同；
  Plan 待审核时仍不输出。现有“无标记”用例的期望值随之更新，已批准的用例期望值不改。
- `test_review_marker.py`：Spec 无标记时单独批准 Plan 成功、Spec 文件未被改动、输出含那句说明；Spec 为待审核、已修订、
  标记无效时各拒绝一例且拒绝信息含“单独明确确认”的要求；原有“Spec 无标记时拒绝”的用例改为上述期望。
- `test_workflow_checkpoints.py`：两条新规则的关键词在场。
- `test-verify-artifacts.sh` 不改，全部通过即证明输出未变。
- 宿主行为：发版后在两份安装副本上用临时项目看 Plan 无标记与已批准两种状态的 Next gate，并各在一次真实会话里读到。

## Boundaries

- Always：hook 只读；Plan 已批准时 Next gate 逐字不变；共享判据同时更新阶段提示的正反回归。
- Ask first：没有标记时不输出 Next gate；放宽 Spec 为待审核或已修订时对 Plan 批准的拒绝；改动五种评审状态或
  `verify-artifacts` 的输出。
- Never：让命令替用户推断批准；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- Plan 没有评审标记的项目，BUILDING 阶段的注入不再出现“keep going until it”。
- Spec 没有标记时可以单独记录 Plan 的批准，Spec 文件不被改动。
- Spec 待审核、已修订或标记无效时仍不能批准 Plan，拒绝信息说明 Spec 需要单独确认。
- 规则文字要求交审时就说明“批准”与“继续”的区别，并禁止从含糊答复补记批准。
- 三条最小验证与 ShellCheck 全部通过。

## Open questions

- 无。
