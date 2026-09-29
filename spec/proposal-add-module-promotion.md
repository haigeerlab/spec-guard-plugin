# Spec: proposal-add-module-promotion

## Objective

Proposal 流程精简为四步（提交、接受、晋级、收尾）的第二个模块：**晋级改由 `add-module --proposal <id>` 完成**。

现在晋级靠人手工开分支、把新模块那一行插进能力图再合并。证明（`proposal-promotion-proof`）会用 `_matches` 逐字核对
插入的行、依赖与位置是否和 Proposal 声明一致；手工插入很容易对不上——v0.32.0 在一个消费者项目的只读快照上复现到的
`invalid`，正是晋级那一行的职责文字与依赖和声明不一致。

本模块让 add-module 直接从远端已发布的 Proposal 取出 id、职责、依赖与锚点，内嵌预检，并在写入前自检"写进去的内容一定
能被证明"。提交 Proposal 的命令与四步文档的完整改写在模块 `proposal-submit`。

登记：2026-09-29 与 `proposal-label-acceptance`、`proposal-submit` 一同经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-09-30 确认：

1. 用法 `add-module --proposal <id> --platform <github|gitlab> --target <target>`；id、职责、依赖、锚点全部取自远端
   已发布的 Proposal。与 `--id`／`--responsibility`／`--depends-on`／`--anchor` 任一同时出现即报错。
2. 预览与 `--confirm` 各自重新运行现有预检（新鲜的远端事实）；只有 `ready` 才继续，否则原样报告预检的状态与诊断并停下。
3. 本地 `spec/CAPABILITY-MAP.md` 必须与预检 `baseCommit` 上的能力图逐字相同，否则拒绝，并提示先
   `git switch -c <晋级分支> <baseCommit>`。
4. 预览时用证明的 `_matches` 自检插入后的能力图；不满足（例如锚点模块在 Build order 的并行段中、新模块会被插到整段
   之后而不是紧跟锚点）直接拒绝，不改变插入算法。
5. 沿用 add-module 其余规则：当前模块做到一半时拒绝（`--interrupt` 可插队）；`spec/<id>.md` 已存在则拒绝；只写
   `spec/CAPABILITY-MAP.md`，不做 Git 操作，不改 Issue 标签。Proposal 模式下不再给出"本地存在同名 Proposal"的提醒。
6. 不带 `--proposal` 时 add-module 的行为与输出逐字不变；`/spec-guard:proposal-promotion-preflight` 保留为只读预览；
   Codex 的 `spec-guard-ops` 同步提供该入口；`docs/workflow.md` 的"晋级"一步改为使用本命令，完整四步改写在
   `proposal-submit`。
7. 测试沿用临时 Git 远端与 tracker 夹具、不访问网络，并包含一条端到端：add-module 写入 → 提交推到临时远端 → 证明为
   `proved`。

## Contract

### P1 预检复用（`hooks/proposal_promotion_proof.py`）

- 新增一个只读函数（名称实现时定，例如 `promotion_base`），返回预检结果以及 `ready` 时 `baseCommit` 上能力图的原文
  （即池的 `review_map`）与该 Proposal 对象。复用现有 `read_published_pool` 与 `_preflight` 判断，不复制逻辑，
  不新增预检状态；`preflight()` 与 CLI 输出不变。
- 接受可注入的 `tracker_reader`（与 `preflight` 相同），供测试使用。

### P2 `add-module --proposal`（`hooks/module-insert.py`）

- 参数：新增 `--proposal`、`--platform`、`--target`（后两者仅在 `--proposal` 时必填）。`--id`／`--responsibility`／
  `--depends-on`／`--anchor` 改为：不带 `--proposal` 时必填（行为不变），带 `--proposal` 时出现任一即报错。
- 流程（预览与 `--confirm` 相同，`--confirm` 最后才写）：
  1. 调用 P1；非 `ready` → 报错，报告预检的 `state` 与 `diagnostic`（短码），不写任何文件；
  2. 本地能力图原文 ≠ `baseCommit` 上能力图原文 → 报错，提示从 `baseCommit` 开晋级分支；
  3. 以 Proposal 的 `change.module_id`、`responsibility`、`depends_on`、`anchor` 走现有 `preview()` 全部校验（含做到一半、
     `--interrupt`、`spec/<id>.md` 已存在、摘要与顺序不变）；
  4. 解析 `preview()` 生成的新能力图，用证明的 `_matches` 自检；不满足 → 报错，说明插入位置与声明不符（例如锚点在
     并行段中）；
  5. 预览输出在现有内容前加一段：Proposal id、revision、`baseCommit`；不输出"本地存在同名 Proposal"的提醒；
  6. `--confirm` 通过以上全部检查后，沿用现有 `write()` 原子写入，只改 `spec/CAPABILITY-MAP.md`。
- 错误沿用现有 `InsertError` 与退出码约定；不带 `--proposal` 时输出与退出码逐字不变。

### P3 入口与文档

- `commands/add-module.md`：新增"从已接受的 Proposal 晋级"一节（前提、参数、先预览后确认、被拒时如何处理、从
  `baseCommit` 开分支、合并后跑 `/spec-guard:proposal-promotion-proof`）。
- `skills/spec-guard-ops/SKILL.md`：同步 Codex 入口；`scripts/check-command-parity.py` 通过。
- `commands/proposal-promotion-preflight.md`、`references/proposal-promotion-proof.md`：说明 add-module 复用同一预检。
- `docs/workflow.md`：Proposal 表格"晋级"一步改为 `add-module --proposal`。
- `spec/module-insert.md` 不改（历史 Spec）；`CHANGELOG.md` Unreleased `### 新增`。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_module_insert.py
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
```

## Project structure

```text
plugins/spec-guard/hooks/proposal_promotion_proof.py, test_proposal_promotion_proof.py -> P1
plugins/spec-guard/hooks/module-insert.py, test_module_insert.py                      -> P2
plugins/spec-guard/commands/, skills/spec-guard-ops/, references/, docs/workflow.md,
  CHANGELOG.md                                                                         -> P3
```

## Testing strategy

- 每项先写测试并确认它在当前代码上失败，再修改。
- `test_proposal_promotion_proof.py`：P1 在 `ready` 时返回 `baseCommit` 能力图原文与 Proposal；非 ready 时只返回
  预检结果；`preflight()` 的结果与之一致。
- `test_module_insert.py`（沿用 `test_proposal_promotion_proof.py` 的远端与 tracker 夹具方式，必要时抽出共享 helper）：
  - 正例：已接受且新鲜的 Proposal，本地图与 `baseCommit` 一致 → 预览给出与声明一致的新行与 Build order，不写文件；
    `--confirm` 只改能力图；
  - 端到端：`--confirm` 写入 → 提交并推到临时远端 → `prove_from_remote` 为 `proved`；
  - 反例：预检非 ready（标签 in-review、基线漂移、Proposal 不存在）→ 报错且不写；本地图与 `baseCommit` 不一致 → 报错；
    锚点在并行段中 → `_matches` 自检报错；同时传 `--proposal` 与 `--id` 等 → 报错；缺 `--platform`／`--target` → 报错；
    当前模块做到一半且无 `--interrupt` → 报错；`spec/<id>.md` 已存在 → 报错；
  - 不带 `--proposal` 的全部已有测试保持通过，输出逐字不变。
- 两种 Python（默认 `python3` 3.10 与 `PATH=/usr/bin:/bin` 下的 3.9）下三条最小验证与上述测试都通过。

## Boundaries

- Always：先红后绿；hook 只读、只写 `spec/CAPABILITY-MAP.md` 且仅在 `--confirm`；只依赖 bash／git／python3；
  保留 `from __future__ import annotations`；远端事实只来自现有的固定快照与 tracker 读取。
- Ask first：自动创建晋级分支或提交；改变插入算法以迁就并行段；新增预检状态；写 Issue 标签。
- Never：让 `--proposal` 与手填字段混用；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 已接受且新鲜的 Proposal，从 `baseCommit` 开的分支上运行 `add-module --proposal <id> … --confirm`，提交合并后
  `proposal-promotion-proof` 返回 `proved`（端到端测试覆盖）。
- 预检非 ready、本地图与远端不一致、写入结果无法被证明、字段混用时一律拒绝且不写文件。
- 不带 `--proposal` 时 add-module 行为与输出逐字不变。
- 三条最小验证与 `check-command-parity.py` 在两种 Python 下都通过。

## Open questions

- 无。
