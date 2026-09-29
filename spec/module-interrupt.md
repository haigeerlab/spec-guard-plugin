# Spec: module-interrupt

## Objective

当前模块做到一半、却因为要等外部条件而短期内勾不完时，新需求没有合法的办法插到它前面先做。

2026-09-29 在一个消费者项目中实际发生：当前模块已勾大部分任务，剩下的都要等外部条件（例如部署满若干自然日后复核、
在另一台机器上恢复），短期内勾不完；一个已接受的 Proposal 写好了 Spec 与 Plan，但能力图行"要等当前模块完成才能插入"，
新模块整个停住。

插件里挡住它的有三处：

| 位置 | 规则 |
|---|---|
| `hooks/module-insert.py:148` | 当前模块做到一半（既有已勾又有未勾）时拒绝插入："请先完成它" |
| `docs/workflow.md:59` 等文档 | 只在"一个模块做完、或还没开始的检查点"插入新模块；agent 把它当成了硬规则 |
| `hooks/proposal_mainline_review.py:222,334,410` | 主链评审只接受 `module-deliver`、`module-advance` 两种边界 |

在临时项目上验证过：手动把 `activeModule` 指向一个已完成的模块就能绕过插入检查；再把它改成新模块即可开始构建；
新模块完成后阶段提示会指回做到一半的模块。底层能跑通，但要靠伪装当前模块，没有写进文档，而且插队期间阶段提示
完全不提被搁下的模块。

本模块把"插队"做成显式、可预览的正式流程。

登记：2026-09-29 按用户决定经 `/spec-guard:add-module` 快速插入能力图。

## Assumptions

用户已于 2026-09-29 确认：

1. ~~只支持一层插队~~（2026-09-29 检查点时撤回，见下）。

   **修订（2026-09-29，用户决定）：取消一层限制。** 检查点在该消费者项目的真实能力图、Spec 与 todo（只读导出到临时目录）
   上端到端验收时，插队被误拒：项目同时有两个做到一半的模块——当前模块（等外部条件）与一个排在后面、仍在并行推进的模块。
   插件不记录"哪个模块是被插队暂停的"（前提 3：不写 `state.json`），只看 todo 无法区分"被插队暂停"与"本来就在并行推进"，
   层数无法可靠判定。因此 `--interrupt`
   只放宽"当前模块做到一半"这一条；`Paused` 行列出所有做到一半的非当前模块；插队模块完成后按 Build order 回到第一个
   被暂停的模块。
2. 插队必须由用户显式选择（`--interrupt`）；不带它时现有检查不变。
3. add-module 仍然只写 `spec/CAPABILITY-MAP.md`，不写 `.agent/state.json`；需要改 `activeModule` 时在预览里告诉用户。
4. 先做插队；"等待外部条件"的 todo 标记以后按需要再加，不在本模块内。

## Contract

### I1 阶段提示显示被暂停的模块（`hooks/module_stage.py`）

- **被暂停的模块**：当前模块以外、todo 既有已勾又有未勾项的模块（与 module-insert 的"做到一半"同一判据，复用同一函数）。
- 当前阶段为 `NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING` 或 `MODULE_DONE` 时，若存在被暂停的模块，在计数行之后加一行：
  `- Paused: \`<id>\` (<N> unchecked item(s)); resume it after \`<current>\`.`
- `MODULE_DONE` 的下一步：有被暂停的模块时点名它（按 Build order 取第一个），说明"回到它"；没有时沿用现有规则
  （Build order 中第一个未完成模块）。
- 没有被暂停的模块时，所有阶段的输出与现在逐字相同。

### I2 add-module 的插队选项（`hooks/module-insert.py`、`commands/add-module.md`、Codex `spec-guard-ops`）

- 不带 `--interrupt`：行为不变；当前模块做到一半时仍拒绝，拒绝信息补一句可以用 `--interrupt` 显式插队。
- 带 `--interrupt`：
  - 当前模块做到一半时放行；其余所有校验（依赖、锚点、id、已有行不变、Spec 不存在）照旧；
  - 预览写明被暂停的模块及进度（已勾/总数），以及插入后的当前模块；若插入后新模块不会成为当前模块（锚点在
    被暂停模块之后，或 `activeModule` 仍指向被暂停模块），提示用户把 `activeModule` 改为新模块；
  - `--confirm` 重新执行全部校验，仍然只写能力图。
- 当前模块没有做到一半时，`--interrupt` 不改变任何行为。

### I3 Proposal 主链评审接受插队边界（`hooks/proposal_mainline_review.py`、`hooks/proposal_boundary_guidance.py`）

- `--boundary` 增加取值 `module-interrupt`：主链评审与候选读取在此边界下与另外两种边界做同样的检查；boundary 不进入
  验收记录（attestation）与 policy 摘要，已有记录不受影响。
- 边界提醒（boundary guidance）对 `module-interrupt` 同样给出非阻断提醒。

### I4 文档

- `docs/workflow.md`：检查点规则改为"模块做完、还没开始，或显式插队时"；新增"插队"一节：何时用、预览内容、改
  `activeModule`、插队模块完成后回到被暂停的模块；Proposal 晋级在插队时同样适用（晋级后把 `activeModule` 改为新模块）。
- `commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`：`--interrupt` 的用法与确认要求。
- `commands/phase.md`：说明 `Paused` 行。
- `commands/proposal-mainline-review.md`、`commands/proposal-mainline-candidates.md`、`references/proposal-mainline-review.md`：
  边界取值加入 `module-interrupt`。
- `CHANGELOG.md` Unreleased。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_module_insert.py
python3 -B plugins/spec-guard/hooks/test_proposal_mainline_review.py
python3 -B plugins/spec-guard/hooks/test_proposal_boundary_guidance.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
python3 scripts/check-command-parity.py
```

## Project structure

```text
plugins/spec-guard/hooks/module_stage.py                -> I1：被暂停模块判定与 Paused 行
plugins/spec-guard/hooks/test-phase-guard.sh            -> I1 回归
plugins/spec-guard/hooks/module-insert.py               -> I2：--interrupt
plugins/spec-guard/hooks/test_module_insert.py          -> I2 回归
plugins/spec-guard/hooks/proposal_mainline_review.py,
  proposal_boundary_guidance.py 及其测试               -> I3
plugins/spec-guard/commands/*.md, skills/spec-guard-ops/SKILL.md,
  references/proposal-mainline-review.md, docs/workflow.md, CHANGELOG.md -> I4
```

## Testing strategy

- 每项先写测试并确认它在当前代码上失败，再修改。
- `test-phase-guard.sh`（经真实 hook 输出 JSON）：
  - 被暂停模块存在时，`NEEDS_SPEC`／`BUILDING`／`MODULE_DONE` 都带 `Paused` 行；
  - 插队模块完成后 `MODULE_DONE` 点名被暂停的模块；
  - 没有被暂停模块时输出与现在一致（已有 37 个用例全部保留）。
- `test_module_insert.py`：
  - 不带 `--interrupt` 仍拒绝，且拒绝信息提到 `--interrupt`；
  - 带 `--interrupt` 时放行，预览含被暂停模块与进度；锚点在被暂停模块之后或 `activeModule` 指向它时，预览提示改 `activeModule`；
  - 已有别的做到一半的模块（并行推进）时，`--interrupt` 仍然放行，预览照常；
  - 其余校验在 `--interrupt` 下照旧拒绝；
  - 端到端：插队 → 新模块成为当前模块并显示 `Paused` → 新模块完成 → 阶段指回被暂停的模块。
- 主链评审测试：`module-interrupt` 被接受，与 `module-advance` 得到相同结论；未知取值仍为 `mainline-boundary-invalid`。
- 两种 Python（默认 `python3` 3.10 与 `/usr/bin/python3` 3.9）下三条最小验证都通过。

## Boundaries

- Always：先红后绿；插队只能显式选择；复用"做到一半"的同一判据，不复制；hook 只读、输出合法 JSON。
- Ask first：自动修改 `.agent/state.json`；新增"等待外部条件"的 todo 标记；改变单个模块的完成判据。
- Never：不带 `--interrupt` 时放宽现有检查；add-module 写能力图以外的文件；让 boundary 进入验收记录或 policy 摘要。

## Success criteria

- 在"当前模块做到一半且要等外部条件"的项目里，用户能用一次预览、一次确认把新模块插到前面，
  随后阶段提示指向新模块并一直显示被暂停的模块；新模块完成后阶段提示指回被暂停的模块。
- 不带 `--interrupt` 时所有现有行为不变；另有模块在并行推进时仍能插队（在消费者项目的真实能力图副本上复现通过）。
- Proposal 主链评审可以在插队边界进行，已有验收记录不受影响。
- 文档说明插队流程，不再把"只在检查点插入"写成无例外的规则。
- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过。
