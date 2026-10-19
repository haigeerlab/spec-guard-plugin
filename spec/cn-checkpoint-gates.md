# Spec: cn-checkpoint-gates

<!-- spec-guard: review approved 2cc1f4c8b7a6 -->

## Objective

检查点判据只认以英文 `Checkpoint` 开头的勾选项。使用方的 todo 是中文写的，常见写法是「最终验收（gate）」「G1（gate）」
「检查点 1（gate）：最终验收交审」，这些都不算检查点，于是 `/map --json` 的 `gates.total` 是 0，阶段提示也找不到「下一个 gate」。
演练仓库五个模块的 gate 实际是 1、1、1、1、2 个，`/map` 全读成 0，决策收件箱据此算的「问用户次数」基准全部少算。

本模块让判据同时认这些中文写法。只扩大「哪些行是检查点」，级别怎么读、没标级别怎么算都不变。

登记：2026-10-20 经 `/spec-guard:add-module` 插入能力图，依赖 `checkpoint-default-report`、`map-gate-count`。需求来自接入协调人
转达的 R22 SG-4（决定 71，用户原话「发吧」），协调人给了两种改法由 spec-guard 选：(a) 判据认中文写法；(b) verify-artifacts 对写法
不对的项给提示。本模块选 (a)。冻结期间不发版，只写 CHANGELOG 未发布段。

## Assumptions

1. **改法选 (a)，不做 (b)。** 使用方 todo 本来就是中文，让判据认它比让每个项目改写法省事；做了 (a) 以后 (b) 要提示的情况
   基本不存在，不另加校验。
2. **新的「检查点」识别**（`tasks/<id>/todo.md` 里的勾选项，满足任一条）：
   - 正文以 `Checkpoint` 开头（原有写法，后面不能紧跟英文字母，`Checkpointing` 不算）；
   - 正文以 `检查点` 开头（中文同义词）；
   - 正文冒号前（没有冒号就是整行）标了 `（gate）` 或 `（report）`，全角半角括号、大小写都认，例如「最终验收（gate）」「G1（gate）」。
3. **级别与默认规则不变**：级别照旧从冒号前读；没标级别的检查点里，todo 中最后一个按 gate，其余按 report（`checkpoint-default-report`）。
   所以只写「最终验收」既不以 `Checkpoint`／`检查点` 开头、又没标级别的行**不算**检查点——这种写法要标 `（gate）` 或写成「检查点 N：最终验收」。
4. **已知的副作用**：普通任务若在冒号前标了级别（例如「Task 1（report）：…」），会被当成 report 检查点。它不计入 gate，但如果它排在
   一个没标级别的 `Checkpoint` 之后，那个 `Checkpoint` 就不再是「最后一个检查点」，不再默认按 gate。级别写在冒号后的任务
   （演练仓库里的「Task 1：加开发依赖…（report）」）不受影响。规则文字写明：要停下的最终验收请显式标 `（gate）`。
5. **判据仍只有一处**：只改 `module_stage.py` 的识别正则与 `gate_checkpoints`；`next_gate`、`at_final_gate`、`map_view` 的 `gates`
   都调用它，不在别处另写。`phase-guard.sh` 与 `verify-artifacts.sh` 不直接用检查点判据，代码不改，只在 phase-guard 回归里加正反用例。
6. **`gates` 的含义变化**：同一份中文 todo 的 `gates.total` 会从 0 变成实际数。`interface.json` 从 1.5 升到 1.6，`progressFacts.fields.gates`
   与 `appearsWhen` 写明「1.6 起也认中文写法」；字段名与 JSON 结构不变。PR 合并后通知接入协调人与 decision-inbox。
7. **规则文字**：共享检查点规则「Plan 检查点分级」第一句的例子补上中文写法（`Checkpoint 1（report）`、`检查点 1（report）`、
   `最终验收（gate）`），并加一句「既不以 Checkpoint／检查点 开头、又没标级别的行不算检查点」。复述这一句的约定块模板与文档同步。

## Contract

### `hooks/module_stage.py`

- `CHECKPOINT` 改为认三种写法（第 2 条）；`gate_checkpoints` 对第三种写法要求冒号前确有级别标记。`CHECKPOINT_TIER` 不变。

### `interface.json`（1.5 → 1.6）

- `progressFacts.fields.gates` 与 `appearsWhen` 按第 6 条改写。

### 规则、模板与文档

按第 7 条改；`commands/map.md` 与 `spec-guard-ops` 里 `gates` 的说明若写了「Checkpoint 开头」同步改。

### 不变

- 级别标记的写法与含义；没标级别时的默认规则；`/map` 表格与 JSON 结构；phase-guard 输出格式；verify-artifacts 的检查项。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_map_view.py
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
```

## Testing strategy

- `test_map_view.py`：「最终验收（gate）」「G1（gate）」「检查点 1（gate）：…」「检查点 2：…（最后、未标）」各算 gate；「检查点 1：…（中间、未标）」
  不算；「Task 1：…（report）」（级别在冒号后）不算检查点、不影响最后一个的判定；「最终验收」（不带级别、不以关键词开头）不算；
  `nextGate` 能指向中文写法的 gate。演练仓库五份 todo 的形状各做一个用例，`gates.total` 依次为 1、1、1、1、2。
- `test-phase-guard.sh`：BUILDING 时中文 todo 的「下一个 gate」指向「最终验收（gate）」；只剩它没勾时「最终 gate」判定成立。
- `test_workflow_checkpoints.py`：规则含中文写法的例子与「不算检查点」那句。
- 反向：把识别正则改回只认 `Checkpoint`，上述中文用例变红（手工改坏验证，记入 todo）。

## Boundaries

- **会做**：判据、接口 1.6、规则与文档、两边回归、CHANGELOG 未发布段。
- **先问**：改级别标记或默认规则；在 JSON 里加字段；发版或改版本号。
- **不做**：(b) 的写法校验；发版、升级本机安装副本（冻结期间）。

## Success criteria

- AC1：演练仓库五份 todo 在新判据下 `gates.total` 依次为 1、1、1、1、2，与人工数一致（用 `/map --json` 实测）。
- AC2：英文 `Checkpoint` 写法的原有回归全部照旧通过；`Checkpointing` 仍不算。
- AC3：「下一个 gate」「最终 gate」与 `/map --json` 的 `gates` 对中文写法结果一致，仍只用一个判据函数。
- AC4：`interface.json` 为 1.6，`gates` 说明写明 1.6 的变化；检查器通过。
- AC5：共享检查点规则写明三种写法与「不算检查点」的情况；`validate.sh`、两边回归、`test_map_view.py`、`test_workflow_checkpoints.py` 通过。

## Open questions

- 无。
