# Spec: gate-tick

<!-- spec-guard: review approved 833feb23cb22 -->

## Objective

module-crew 的合并流程合入一个模块后，会在集成分支上把 `tasks/<id>/todo.md` 里唯一一个未勾项勾上，用的是它自己的正则。
这样有两个问题：剩下的那一项不一定是最终验收（例如最终验收已勾、只剩一条「发版后核对」）；最终验收后面还跟着普通任务时又不敢勾。
spec-guard 现有接口帮不上：`gates` 只给每个模块的总数和已勾数，`nextGate` 只给当前模块一个值。

本模块新增一个和 `reviewMark` 同一类的命令 `gateTick`：由 spec-guard 用自己唯一那处判据找出最终验收那一行并勾上，
使用方只决定什么时候调。

登记：2026-10-22 经 `/spec-guard:add-module` 插入能力图，依赖 `review-approval-marker`、`cn-checkpoint-gates`、`checkpoint-default-report`、
`plugin-interface`。需求来自总协调 local_d7434023 转达的 module-crew 职责边界审查第 3 条；用户在本会话选了做法（原话「选 A，新增 gateTick」），
随后确认需求（原话「需求确认，两条按建议」）。账本 MDT20Q5。

## Assumptions

1. **命令形状照 `reviewMark`**：`python3 -B hooks/gate_tick.py --project <项目根> --module <模块 id> [--confirm]`。
   不加 `--confirm` 只预览：打印要勾的那一行、勾完后还剩几个未勾项；加了才写。写入用 `review_mark` 同一个原子写，只改那一格
   `[ ]` → `[x]`，行的其余部分和换行符原样保留。不提交、不推送。
2. **什么时候勾**：用 `module_stage` 的同一处判据（`at_final_gate` 与 `gate_checkpoints`）：模块第一个未勾项正是最后一个 gate 检查点时，
   勾这一行。中文写法（`检查点 …`、`最终验收（gate）`）照样认。它后面的普通任务（发版后核对等）不动，结果里写明还剩几项。
3. **已经勾过**：最后一个 gate 检查点已勾时，什么也不改，退出码 0，打印「已勾过，没有要改的」。重复调用无害。（用户 2026-10-22 确认）
4. **退出码 2、什么也不改的情形**，每种打印一个短码加一句原因：
   - `not-a-module-id`、`map-unreadable`、`not-in-map`（与 `reviewMark` 相同）；
   - `todo-missing`、`todo-unreadable`；
   - `no-gate`：todo 里没有 gate 检查点；
   - `not-at-final-gate`：第一个未勾项不是最后一个 gate（前面还有没做的任务或别的 gate），打印第一个未勾项。
5. **不判断用户有没有批准验收**。调用方必须已有用户对最终验收的批准；接口说明照 `reviewMark` 写明这一点。
6. **`interface.json` 升到 1.7**，新增顶层一节 `gateTick`（command、confirm、exitCodes、notes、contract），已有字段不变。
7. **不做**：斜杠命令和 Codex 技能入口（agent 照旧按共享规则自己勾）；勾非最终的 gate；提交或推送；改 module-crew 的 `merge.py`
   （spec-guard 发版后通知对方自己改）。
8. 单独发 0.83.0（用户 2026-10-22 确认）。版本号与 CHANGELOG 写在本模块的 PR 里。

## Contract

### `hooks/gate_tick.py`（新增）

按第 1～4 条。判据只调用 `module_stage` 的函数，不在本文件另写检查点正则；读写复用 `review_mark` 所用的 `_write_atomic`。

### `interface.json`（1.6 → 1.7）

新增 `gateTick`：
- `command`：`["python3", "-B", "hooks/gate_tick.py", "--project", "<project-root>", "--module", "<module-id>"]`
- `confirm`：只预览，加 `--confirm` 才写
- `exitCodes`：`0` 预览、已写或已勾过；`2` 拒绝（第 4 条各短码）
- `notes`：只勾最终验收那一格；调用方须已有用户对最终验收的批准；不提交
- `contract`：`spec/gate-tick.md`

`interface` 改为 `1.7`；检查器要求的地方同步。

### 文档

`docs/` 里列出接口或命令清单的地方（若有）补一行；CHANGELOG 0.83.0 段。

### 不变

`module_stage` 的判据与阶段提示；`reviewMark` 与其他接口字段；共享检查点规则里「最终 gate 勾选后再提交」的说法。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_gate_tick.py
```

## Testing strategy

`hooks/test_gate_tick.py`（新增，按仓库约定登记到 validate）：
- 正：只剩最终验收 → 预览不改文件、`--confirm` 只改那一格；最终验收后还有「发版后核对」→ 只勾最终验收、报告还剩 1 项；
  中文写法（`最终验收（gate）`、`检查点 2：最终验收`）；CRLF 行尾和行内其他文字原样保留。
- 已勾过 → 退出码 0、文件不变。
- 反：前面还有未勾任务、还有别的 gate 在后面、没有 gate、todo 缺失、模块不在能力图里 → 退出码 2、对应短码、文件不变。
- 判据一致：对同一份 todo，`gateTick` 能勾的情形与阶段提示的「最终 gate」判定一致。
- 接口：`check-interface.py` 认 1.7 与 `gateTick` 一节。
- 变异：把判据换成「唯一未勾项」，「最终验收后还有发版后核对」用例变红（手工改坏验证，记入 todo）。

## Boundaries

- **会做**：新脚本、接口 1.7、测试与登记、CHANGELOG 与版本号 0.83.0。
- **先问**：加斜杠命令或 Codex 入口；让它提交；改判据或阶段提示。
- **不做**：改 module-crew；勾非最终的 gate；判断用户批准。

## Success criteria

- AC1：只剩最终验收（含其后的普通任务）时，`--confirm` 只把最终验收那一格改成 `[x]`，其余内容逐字不变；不加 `--confirm` 不改文件。
- AC2：已勾过时退出码 0、文件不变；第 4 条各情形退出码 2、打印对应短码、文件不变。
- AC3：判据只来自 `module_stage`，与阶段提示的「最终 gate」一致，中文写法可用。
- AC4：`interface.json` 为 1.7，有 `gateTick` 一节；检查器通过。
- AC5：`validate.sh`、两边回归、`test_gate_tick.py` 通过；版本号 0.83.0，CHANGELOG 有对应一段。

## Open questions

- 无。
