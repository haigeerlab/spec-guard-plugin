# Spec: map-table-count-diagnostic

## Objective

自观测报告 F-1203（本地事项 E0F51J9）：一个项目的能力图有 3 张表头为 `Module id` 的表，阶段提示连续报
`MAP_INVALID` 约一周，报错只有一句「必须恰好有一个模块表」。判定是对的，但报错既不说找到几张，也不说在哪，
用户只能自己翻文件。复核时推翻了「这是插件旧版本留下的格式」的猜测：插件历史上从未往能力图写过多余的模块表，
所以本模块不做格式迁移，只让报错可定位。

同时修正自观测报告的一处噪声：F-1203 的 114 次里混入了一个刻意构造坏能力图的测试临时目录。

登记：2026-10-09 按用户决定经 `/spec-guard:add-module` 插入能力图，依赖 `phase-and-verification`（报错经
阶段提示与 verify-artifacts 呈现）、`self-observation-report`（脚本改动）。随 0.55.0 一起发布。

## Assumptions

用户已于 2026-10-09 确认：

1. 判定不变：仍然是恰好一张模块表才有效；只改报错文本。
2. 报错同时出现在阶段提示（`MAP_INVALID` 行）和 verify-artifacts（`能力图无效:`），两边由同一个 `MapError`
   提供，不各自拼文本。
3. 自观测报告排除临时目录里的项目，并在报告里说明排除了多少段。

## Contract

### C1 模块表计数报错（`hooks/capability_map.py`）

- 严格模式与历史模式（`validate_graph=False`）两处「模块表数量不对」的报错，统一由一个函数生成：
  - 0 张：`没有模块表（需要恰好一张表头为 Module id 的表）`；
  - ≥2 张：`必须恰好有一个模块表，找到 <N> 张：第 <a>、<b>、<c> 行`。行号是表头所在的文件行号（从 1 开始），
    最多列 5 个，超过时以 `等` 结尾。
- 围栏代码块内的表照旧不计（行号仍按原文件计）。
- 历史模式只在 ≥2 张时报错（0 张合法，行为不变）。
- 报错长度在 `module_stage.FRAGMENT_LIMIT`（200）之内，阶段提示不会截断它。

### C2 自观测报告排除临时目录（`scripts/self_report.py`）

- 项目 realpath 位于 `/private/tmp/`、`/private/var/folders/`、`/tmp/`、`/var/folders/` 之下的注入事件不参与信号计算。
- 报告头部写明「已排除临时目录中的 N 段」，`--json` 增加 `excluded_temp`。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_capability_map.py
python3 -B scripts/test_self_report.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Project structure

```text
plugins/spec-guard/hooks/capability_map.py         -> C1
plugins/spec-guard/hooks/test_capability_map.py    -> C1 单元回归（新建，登记 validate.sh）
plugins/spec-guard/hooks/test-phase-guard.sh       -> C1 阶段提示回归
plugins/spec-guard/hooks/test-verify-artifacts.sh  -> C1 verify-artifacts 回归
scripts/self_report.py, scripts/test_self_report.py -> C2
```

## Testing strategy

先写测试并确认在当前代码上失败，再实现：

- 单元：三张表（第 3、7、11 行）→ 报错含 `找到 3 张：第 3、7、11 行`；7 张 → 只列 5 个行号并以 `等` 结尾；
  0 张 → `没有模块表`；围栏代码块里的表不计且行号不偏移；历史模式 2 张报同样格式，0 张不报错；
  报错长度 ≤ 200。
- phase-guard：两张模块表的夹具，阶段提示含 `MAP_INVALID` 与 `找到 2 张：第`。
- verify-artifacts：同一夹具，输出含 `能力图无效:` 与 `找到 2 张：第`。
- self_report：`/private/tmp/...` 项目的 `MAP_INVALID` 不出现在发现项中，报告与 `--json` 给出排除数。
- 默认 `python3` 与 `/usr/bin/python3` 3.9 下通过。

## Boundaries

- Always：两边回归同步；报错只含行号与数量，不回显表内容。
- Ask first：改变「恰好一张」的判定；自动合并多张表；改阶段提示的建议行。
- Never：在插件仓库文件、提交或 PR 中写出消费者项目名。

## Success criteria

- 用 F-1203 的情形（3 张模块表）在合成夹具上复现，阶段提示与 verify-artifacts 都能直接指出三张表所在行。
- 本机重跑 `scripts/self_report.py`，F-1203 不再包含临时目录项目，报告写明排除数。
