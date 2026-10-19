# Spec: checkpoint-default-report

<!-- spec-guard: review approved 7f567a1ab5c5 -->

## Objective

现在 Plan 里没标级别的检查点一律按 `gate`：agent 每到一个这样的检查点就停下等用户确认。上游 agent-skills 在构建中只在测试改不过、
Spec 有歧义、高风险或不可逆时停；用户的原则是「不是高危操作就不该找用户授权」。决定 66 把默认值反过来：没标级别的中间检查点按
`report`（记进 todo 后继续），只有最终验收、推送与不可逆操作停下。

这取代用户此前在 `stop-rule-and-ac` 定下的 S3「检查点默认值不改」。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `checkpoint-tiers`、`map-gate-count`、`stop-rule-and-ac`。需求来自
接入协调人转达的用户决定 66 第 3 条；用户在本会话补定两处：todo 里最后一个检查点没标级别时仍按 gate；`interface.json` 升到 1.4
写明 `gates` 含义变化并通知 decision-inbox。与 `align-upstream-rules`（决定 66 其余各条）一起发 0.79.0，版本号写在那个模块的 PR 里。

## Assumptions

1. **新判据**（只看 `tasks/<id>/todo.md` 里以 `Checkpoint` 开头的勾选项，识别写法不变）：
   - 冒号前标了 `（gate）` → gate；标了 `（report）` → report；
   - 没标级别：是 todo 里**最后一个**检查点 → gate；否则 → report。
   「最后一个」按文件里的位置算，与勾没勾无关；最后一个检查点之后的普通任务（比如发版后的核对）不影响判定。
2. **判据仍只有一处**：`module_stage.py` 的 line 级 `gate_checkpoint` 改为按整份 todo 判定的函数（例如 `gate_checkpoints(text)` 返回
   每个 gate 检查点的标题与是否已勾）；「下一个 gate」（`next_gate`）、「最终 gate」（`at_final_gate`）与 `/map --json` 的 `gates`
   都改用它，不在别处另写判据。
3. **规则文字**：共享检查点规则「Plan 检查点分级」里「未标注的检查点按 `gate` 处理」改为第 1 条的说法；「能自动判定的中间检查点
   可以标 `report`」改为「推送与不可逆操作的检查点必须标明 `gate`；最终验收写在最后一个检查点，标 `gate` 或不标都按 gate」。
   两份约定块模板、`docs/convention-block.md`、`AGENTS.md`、`docs/workflow.md` 与 `spec-guard-ops` 里「未标注按 gate」的说法同步改。
4. **`gates` 的含义变化**：`/map --json` 的 `gates.total`／`done` 改用新判据，所以同一份 todo 的 `total` 可能变小。`interface.json`
   从 1.3 升到 1.4，`progressFacts.fields.gates` 写明新判据，并写一句「1.4 起没标级别的中间检查点不再计入」。字段名与 JSON 结构不变。
   发版后通知 decision-inbox 整改会话（它用 `gates.total` 算基准）。
5. **已在进行中的模块**：升级后，Plan 里没标级别的中间检查点不再停下，这是决定 66 想要的；最终验收因第 1 条的「最后一个」规则
   照旧停。CHANGELOG 写明这一行为变化。
6. `phase-guard.sh` 的输出格式不变（只是「下一个 gate」指向的检查点可能变了）；`/map` 的表格不变。

## Contract

### `hooks/module_stage.py`

- 新判据函数按第 1、2 条；`next_gate`、`_open_gate`／`at_final_gate` 改用它。识别 `Checkpoint` 行与级别的正则不变。

### `hooks/map_view.py`

- `_gates()` 改用新判据函数。

### `interface.json`（1.3 → 1.4）

- `progressFacts.fields.gates` 改写判据并注明 1.4 的变化；`appearsWhen` 写上 1.4。

### 规则、模板与文档

按第 3 条改；`commands/map.md` 与 `spec-guard-ops` 的 `gates` 说明同步改判据。

### 不变

- 检查点的写法与级别标记；`report` 的含义；远端写入须在 gate 写明授权、合并永远由用户；`/map` 表格与 JSON 结构。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_map_view.py
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
```

## Testing strategy

- `test_map_view.py` 的 `GateCountTest`：三个检查点（中间未标、中间标 gate、最后未标）→ 中间未标不算；只有一个未标检查点 → 算 1；
  最后一个标 `report` → 不算；最后一个检查点之后还有普通任务 → 最后检查点仍算；`nextGate` 跳过未标的中间检查点。
- `test-phase-guard.sh`：BUILDING 时「下一个 gate」跳过未标的中间检查点、指向最后一个；「最终 gate」判定（修订过的 Spec 在最终验收
  一并复审）在只剩未标的中间检查点与最后检查点时仍成立。原有用例里依赖「未标即 gate」的期望按新判据改，并逐条说明。
- `test_workflow_checkpoints.py`：规则含新判据的关键句（没标级别的中间检查点按 report、最后一个检查点按 gate、推送与不可逆须标明 gate），
  不再出现「未标注的检查点按 `gate` 处理」。
- 反向：故意让判据把未标的中间检查点算 gate，`GateCountTest` 与阶段提示用例变红。

## Boundaries

- **会做**：判据、两处调用方与 `/map`、接口 1.4、规则与文档、回归。
- **先问**：改检查点写法或级别标记；在 JSON 里加新字段；改 `report` 的含义。
- **不做**：决定 66 的其余各条（归 `align-upstream-rules`）；版本号与 CHANGELOG（随 `align-upstream-rules`）。

## Success criteria

- AC1：没标级别的中间检查点按 report，最后一个检查点没标级别时按 gate，显式标记照旧。
- AC2：「下一个 gate」「最终 gate」与 `/map --json` 的 `gates` 都用同一个判据函数，结果一致。
- AC3：`interface.json` 为 1.4，`gates` 的说明写明新判据与 1.4 的变化；检查器通过。
- AC4：共享检查点规则、四处约定块、`docs/workflow.md`、`spec-guard-ops`、`commands/map.md` 不再写「未标注按 gate」，改为新说法；
  推送与不可逆操作须标明 gate。
- AC5：`validate.sh`、两边回归、`test_map_view.py`、`test_workflow_checkpoints.py` 通过；依赖旧判据而改动的原有期望逐条列出。

## Open questions

- 无。
