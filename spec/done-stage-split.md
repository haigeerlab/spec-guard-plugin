# Spec: done-stage-split

## Objective

阶段提示里的 `当前阶段: **DONE**` 现在同时表示两件不同的事：

- `activeModule` 指向的模块已完成，但能力图里还有未完成的模块（`module_stage.py` 第 79 行，下一步是切换模块）；
- 能力图里全部模块都已完成（第 69 行，下一步是用 `/spec-guard:add-module` 插入新需求）。

2026-09-29 在临时项目上复现了三种情况：

| 情况 | 现在的输出 | 问题 |
|---|---|---|
| A：alpha 完成、beta 缺 Plan、`activeModule=alpha` | `DONE`，"`alpha` is done; set activeModule to the next module" | 项目没做完却报 DONE；没有点名 beta |
| B：全部完成、`activeModule` 仍为 alpha | 同上 | 没有下一个模块，提示是错的；也不指向 add-module |
| C：全部完成、无 `activeModule` | `DONE`，指向 add-module | 正确 |

agent 与用户只看阶段行，无法区分"切下一个模块"和"项目已完成"；情况 B 还会把 agent 引向一个不存在的模块。

本模块把两种含义拆成两个阶段标签，并让每种情况给出正确的下一步。

登记：2026-09-29 按用户决定经 `/spec-guard:add-module` 快速插入能力图，来源是项目审计 P3 "phase.md 的 DONE 含义"。

## Assumptions

用户已于 2026-09-29 确认：

1. 新增阶段 `MODULE_DONE`：`activeModule` 指向一个已完成模块，且能力图里还有未完成模块。下一步点名 Build order 中
   第一个未完成的模块（例如"把 activeModule 设为 `beta`"）。
2. `DONE` 只表示全部模块已完成，与 `activeModule` 指向哪里无关。情况 B 报 `DONE`、指向 add-module，并附一条说明：
   `activeModule` 仍指向已完成的模块，可以清除。
3. 兼容性：`DONE` 的含义只收窄、不扩大，把 `DONE` 当"全部完成"的 agent 或脚本不会被误导；`MODULE_DONE` 是新增标签。
4. `module-insert` 的检查点判定（`_current_module`、`_half_done`）不变，只把写入后的阶段提示改成同样的两种标签。
5. `verify-artifacts` 不涉及 DONE 判据，不改；"修改共享判据时同步两边"的不变量在这里不适用，只改 phase-guard 一侧的回归。

## Contract

### S1 阶段判定（`hooks/module_stage.py`）

- 单个模块的状态（`module_state`）不变：有 Plan 且无未勾选项时仍记为 `DONE`，全局计数 `Done N` 的含义不变。
- `describe` 的项目级阶段：
  - 所有模块都完成 → `当前阶段: **DONE**`，沿用现在的全部完成提示（add-module、可选 Proposal、全局计数）。
    若 `activeModule` 指向一个已完成模块，额外加一行说明：`activeModule` `<id>` 已完成，可以清除。
  - `activeModule` 指向已完成模块、且还有未完成模块 → `当前阶段: **MODULE_DONE**`，`Current module` 仍为该模块
    （来源 `activeModule`），下一步写明 Build order 中第一个未完成的模块 id，以及它自身所处的阶段。
  - 其余情况（当前模块为 `NEEDS_SPEC`／`NEEDS_PLAN`／`BUILDING`）输出不变。
- `activeModule` 不在能力图中的回退与提示不变。

### S2 模块插入的阶段提示（`hooks/module-insert.py`）

- `--confirm` 写入后的 `当前阶段提示` 与 S1 使用同一判定：全部完成报 `DONE`；`activeModule` 指向已完成模块且仍有
  未完成模块时报 `MODULE_DONE`。不复制 S1 的算法，改为复用 `module_stage` 的函数。
- 预览与检查点校验的行为不变。

### S3 文档

- `commands/phase.md` 与 `docs/workflow.md` 的阶段表：新增 `MODULE_DONE` 一行，`DONE` 改为只表示全部完成。
- `README.md` 第 74 行的阶段顺序说明补上 `MODULE_DONE`。
- `spec/phase-and-verification.md` 的阶段列表补上 `MODULE_DONE`。
- `CHANGELOG.md` Unreleased：用户可见的阶段变化，以及"以 `DONE` 判断全部完成"的依赖方不受影响。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
python3 -B plugins/spec-guard/hooks/test_module_insert.py
/usr/bin/python3 -B plugins/spec-guard/hooks/test_module_insert.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Project structure

```text
plugins/spec-guard/hooks/module_stage.py        -> S1：阶段判定与提示
plugins/spec-guard/hooks/test-phase-guard.sh    -> S1 回归（情况 A、B、C 与不变的阶段）
plugins/spec-guard/hooks/module-insert.py       -> S2：写入后的阶段提示
plugins/spec-guard/hooks/test_module_insert.py  -> S2 回归
plugins/spec-guard/commands/phase.md, docs/workflow.md, README.md,
  spec/phase-and-verification.md, CHANGELOG.md  -> S3
```

## Testing strategy

- 每项先写测试并确认它在当前代码上失败，再修改。
- `test-phase-guard.sh`（经真实 hook 输出 JSON 断言）：
  - 情况 A：报 `MODULE_DONE`，下一步点名 `beta` 及其阶段，且不含 `当前阶段: **DONE**`；
  - 情况 B：报 `DONE`，指向 add-module，并含 activeModule 可清除的说明；
  - 情况 C：输出与现在一致；
  - 已有的 `NEEDS_SPEC`／`NEEDS_PLAN`／`BUILDING`／`MAP_INVALID`／`UNKNOWN` 断言全部保留。
- `test_module_insert.py`：在 `activeModule` 指向已完成模块的项目里插入新模块，写入后的提示与 S1 一致；全部完成时仍报 `DONE`。
- 两种 Python（默认 `python3` 3.10 与 `/usr/bin/python3` 3.9）下三条最小验证都通过。

## Boundaries

- Always：先红后绿；复用 `module_stage` 的判定，不在 module-insert 中复制；hook 只读、输出合法 JSON。
- Ask first：改变单个模块的完成判据；改动 `activeModule` 的回退规则；让 hook 自动修改 `.agent/state.json`。
- Never：hook 写文件；把 `MODULE_DONE` 当作全部完成；删除或改名已有阶段标签。

## Success criteria

- 情况 A 报 `MODULE_DONE` 并点名下一个未完成模块；情况 B 报 `DONE` 并指向 add-module；情况 C 不变。
- 阶段行里的 `DONE` 只在全部模块完成时出现。
- module-insert 写入后的阶段提示与 phase-guard 一致。
- 文档的阶段表列出 `MODULE_DONE`，`DONE` 只描述全部完成。
- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过。
