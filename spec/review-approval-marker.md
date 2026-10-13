# Spec: review-approval-marker

<!-- spec-guard: review approved ecf4338a4006 -->

## Objective

阶段判定只看文件在不在：`spec/<id>.md` 一存在就建议写 Plan，`tasks/<id>/plan.md` 一存在就建议继续 build，哪怕这份 Spec
或 Plan 还在等用户审核。这与共享检查点规则里"不要从文件存在、phase 名称或单一退出码推导执行授权"相矛盾。用户的批准
也没有可机读的落点，只能靠 agent 手改文件顶部的一行状态说明，经常忘改。

2026-10-13 一次实地运行（一个宿主会话连续做了多个模块）的审查报告记录了这些后果：计划待审核时阶段提示建议继续实现；
已实施完的模块文件里仍写着待审核；Spec 按口头建议修订后没再给用户过目就写了 Plan；agent 在 `report` 检查点反复停下，
阶段提示从不说明下一个该停的地方。两边宿主共用同一份判定代码，问题与宿主无关。

本模块给 Spec 与 Plan 加一行可机读的评审状态标记，让阶段提示与 `verify-artifacts` 据此报告事实；并在 BUILDING 阶段
写明下一个 `gate` 检查点。

登记：2026-10-13 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-13 确认：

1. **没有标记 = 判定照旧。** 只有写了标记才改变阶段提示；既有项目升级后零影响。没有标记时的建议语改为带条件的中性
   写法（"Spec 获批后再写 Plan"），不再直接催下一步。
2. **批准标记绑定 Spec 内容指纹。** Spec 在批准后内容有变即判为"批准后已修订"，由机器发现，不靠 agent 自觉改回。
   为此新增一个写标记的命令（先预览、确认后写入）。
3. 标记是独占一行的注释，写法与挂起标记 `<!-- spec-guard: suspended -->` 一致，分别写在 `spec/<id>.md` 与
   `tasks/<id>/plan.md`；入库，两边宿主和后续会话都读得到。
4. hook 只读标记。标记由 agent 在用户明确批准后写入；用户的批准原话仍以对话为准，标记只是让后续会话读得到，
   不是授权来源，也不能替代检查点上的确认。
5. 只有当前模块的标记影响阶段提示；已完成的模块不受影响。
6. 不新增阶段名；`NEEDS_SPEC`／`NEEDS_PLAN`／`BUILDING`／`DONE` 的判据与完成判据不变，只增加一行评审事实并替换建议语。
7. `combined` 节奏下一次批准同时标记 Spec 与 Plan。"按需求批量前置审"在 plan.md 写的那句话保留，不被替代。
8. Plan 的批准标记不绑指纹（实现中调整 Plan 是正常的）；Spec 被修订时阶段提示要求先复审 Spec。
9. BUILDING 阶段多一行"下一个 gate 检查点"，取自 todo.md 第一个未勾选的 `gate` 检查点（未标注按 `gate`）；
   解析不出来就不输出这一行。
10. `verify-artifacts` 新增的矛盾检查报警告；标记重复或写法无效报失败，与挂起标记一致。
11. 约定块模板与共享检查点规则各补一句；既有项目重新运行 `setup-convention --replace` 后才拿到新文字。
12. 不在范围内：能力图评审项被一句"继续"整体勾完、已完成模块的返工位置、会话目录与项目目录不一致时的定位。

## Contract

### 标记

独占一行（行首行尾允许空白），每个文件至多一行：

```text
<!-- spec-guard: review pending -->
<!-- spec-guard: review approved <digest> -->     ← 仅 spec/<id>.md，digest 为 12 位十六进制
<!-- spec-guard: review approved -->              ← 仅 tasks/<id>/plan.md
```

围栏代码块（``` 或 ~~~）里的行是示例，不算标记，也照常计入内容指纹。每个文件的评审状态：

| 状态 | 条件 |
|---|---|
| `none` | 没有以 `<!-- spec-guard: review` 开头的行 |
| `pending` | 恰有一行 pending 标记 |
| `approved` | 恰有一行 approved 标记；Spec 还要求其 digest 等于当前内容指纹 |
| `revised` | 仅 Spec：approved 标记的 digest 与当前内容指纹不同 |
| `invalid` | 多于一行，或以该前缀开头却不符合上面三种写法（含 Spec 的 approved 缺 digest、Plan 的 approved 带 digest） |

内容指纹对去掉标记行后的文件全文计算。算法只在 `hooks/spec-digest.py` 里（新增按文本求指纹的入口，复用其现有哈希与
长度），其他脚本只调用它，不复制、不内联。

`pending` 可以由 agent 在写出 Spec 或 Plan 时直接写入；`approved` 只通过下面的命令写入。

### 阶段提示（只对当前模块）

在计数行之后加一行 `- Review: …`，并按下表给出建议语。表中没列出的组合（两份文件都是 `approved`）输出与现行逐字相同。

| 阶段 | 状态 | Review 行 | Suggested next step |
|---|---|---|---|
| NEEDS_PLAN | Spec `none` | 不输出 | 现行文字后加"once the Spec is approved by the user" |
| NEEDS_PLAN | Spec `pending`，节奏 `separate` | Spec 待用户审核 | 等待用户审核 Spec；不写 Plan |
| NEEDS_PLAN | Spec `pending`，节奏 `combined` | Spec 待用户审核 | 写出 Plan 与 todo，与 Spec 一起交用户一次审核 |
| NEEDS_PLAN | Spec `revised` | Spec 在批准后已修订 | 把修订后的 Spec 交用户复审；不写 Plan |
| BUILDING | Spec `pending`／`revised` | 同上两种 | 等待用户审核 Spec；不继续 build |
| BUILDING | Plan `pending` | Plan 待用户审核 | 等待用户审核 Plan；不继续 build |
| BUILDING | 其余 | 不输出 | 现行文字 |
| 任一 | 任一文件 `invalid` | 标记无效，指出文件 | 运行 verify-artifacts 查看；评审状态按未知处理，不建议继续 |

`NEEDS_SPEC`、`MODULE_DONE`、`DONE` 的输出不变。挂起、插队、上下文提示等其他行不变。Review 行与建议语只含固定文字
和已校验的模块 id，不带文件原文。

### 下一个 gate

BUILDING 且建议语为"继续 build"时，多输出一行 `- Next gate: <标题>`：todo.md 中第一个未勾选、标题以 `Checkpoint` 开头
且标为 `gate` 或未标注级别的条目，标题截到固定长度并做与其他注入相同的清洗。没有这样的条目或解析不出来时不输出。

### 写标记的命令

`/spec-guard:review-mark`（Codex：`spec-guard-ops` 的对应动作），实现为 `hooks/review_mark.py`：

```text
review_mark.py --project <root> --module <id> --target <spec|plan|both> --state <pending|approved> [--confirm]
```

- 默认只预览：输出每个文件的 diff、Spec 的当前指纹，以及写入后各文件的评审状态；带 `--confirm` 才写入并读回。
  目标已是所求状态时说明无需改动并正常退出。
- 只增改标记这一行：已有标记行原地替换，没有则插在第一行标题之后（文件不以标题开头时放在最前）；其余内容逐字不变。
- 拒绝并说明原因：模块不在能力图上；目标文件不存在；标记 `invalid`；把 Plan 标为 `approved` 而 Spec 不是 `approved`。
- 不执行 Git 或远端操作，不改 `.agent/state.json`、todo.md 或能力图。
- 命令文本写明：`approved` 只在用户于当前对话明确批准该 Spec 或 Plan 之后才写；agent 不得为了消除阶段提示而自行批准。

### verify-artifacts

没有任何标记的项目输出与现行逐字相同。有标记时：

- 失败：某文件的标记 `invalid`。
- 警告：Spec 或 Plan 为 `pending` 而该模块 todo.md 已有勾选项；Spec 为 `revised`。
- 通过：汇总一行"评审标记有效：N 个文件"。
- 检查没有正常运行时报"未验证"，不报通过也不报失败。

判据只来自与阶段提示相同的那份模块代码。

### 规则文本与文档

- `references/workflow-checkpoints.md` 新增一节「评审状态标记」：标记的含义、谁在什么时候写、Spec 修订后须复审、
  标记不是授权来源；「Plan 检查点分级」补一句：Plan 获批后连续执行到下一个 `gate`，`report` 不结束回合。
- 两份约定块模板各加一行指向该节。
- `docs/commands.md`、`docs/workflow.md`、`spec-guard-ops` 技能、CHANGELOG `[未发布]`；版本号随 0.57.0。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_review_marker.py
python3 -B plugins/spec-guard/hooks/spec-digest.py --selftest
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先写测试并确认在当前代码上失败，再实现。
- `test_review_marker.py`：五种状态各一例；指纹不受标记行本身影响、受其余任一字符影响；命令的预览不写文件、
  `--confirm` 只改标记行且可重复执行；四种拒绝各一例。
- `test-phase-guard.sh`：上表每一行一例；**无标记项目的 NEEDS_SPEC／BUILDING／MODULE_DONE／DONE 输出逐字不变**
  （NEEDS_PLAN 仅多出约定的那半句）；非当前模块的标记不影响输出；Next gate 的有、无、未标注、解析失败四例；
  注入仍是宿主接受的 JSON。
- `test-verify-artifacts.sh`：失败、两种警告、通过、未验证各一例；无标记项目输出逐字不变。
- 判据是否真能拦住回归：在草稿副本上分别改坏状态判定、指纹排除标记行、`revised` 判定三处，确认相应断言变红。
- 宿主行为：发版后在两边宿主的临时消费者项目上各走一遍"写 Spec → pending → 批准 → 修订 → revised"，记录实际注入；
  静态与单元测试不表述为宿主行为验收。

## Boundaries

- Always：hook 与 `verify-artifacts` 只读；无标记项目行为不变；探测失败报未验证；`phase-guard` 只依赖 bash、git、python3；
  共享判据同时更新阶段提示、`verify-artifacts` 与两边的正反回归。
- Ask first：新增阶段名或改变完成判据；让没有标记的产物被判为待审核；给 Plan 的批准也绑指纹；让命令之外的入口写
  `approved`。
- Never：hook 写标记或任何文件；agent 未经用户明确批准写 `approved`；在 `spec-digest.py` 之外实现指纹；在 Spec、代码、
  测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 当前模块的 Spec 或 Plan 标为待审核时，阶段提示报告等待审核，不再建议写 Plan 或继续 build。
- Spec 在批准后被改动，阶段提示与 `verify-artifacts` 都能指出，无需 agent 手动改标记。
- BUILDING 阶段的注入写明下一个 `gate` 检查点。
- 没有任何标记的既有项目：除 NEEDS_PLAN 建议语多出的半句、BUILDING 阶段在 todo 有未勾选 `gate` 检查点时多出的
  Next gate 一行外，阶段提示与 `verify-artifacts` 输出逐字不变。
- 写 `approved` 只有一个入口，先预览后确认，只改标记行。
- 三条最小验证与 ShellCheck 全部通过。

## Open questions

- 无。
