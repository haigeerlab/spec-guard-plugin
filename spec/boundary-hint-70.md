# Spec: boundary-hint-70

<!-- spec-guard: review approved 4110204c1707 -->

## Objective

context-hint-thresholds 把模块边界的释放上下文提示定在窗口 50%，依据只是“模块之间换会话几乎不丢东西”，没有按成本算过。
用户反馈（2026-10-16）：50% 很快就到，压缩后又从约 10%（系统提示与工具定义约 85k 加摘要）起步，很快再到，一过阈值每轮都提示，
太频繁；希望接近宿主自己的警示区间再提示。

2026-10-16 按官方价格（Opus 5.5：读缓存 $0.20、1 小时写缓存 $8、输出 $20 每百万 token，1M 窗口不加价）与一个真实长会话的
316 次请求估算：压缩一次约 $0.6–0.7；按每次请求上下文涨约 1.5k、压缩后回到约 100k 计，模块边界在 50% / 70% / 80% 提示时，
平均每次请求约 $0.091 / $0.110 / $0.120，70% 比 50% 多约 21%，提醒与压缩间隔从约 270 次请求拉长到约 400 次。用户选 70%。

本模块把模块边界那一档从 50% 改为 70%，模块进行中那一档仍是 80%。

登记：2026-10-16 经 `/spec-guard:add-module` 插入能力图。需求由用户在插件所有者会话直接提出。

## Assumptions

用户已于 2026-10-16 确认：

1. 模块边界（`MODULE_DONE`、`DONE`、`NEEDS_SPEC`）：上下文达到窗口 **70%** 出带大小的 Module boundary 行，低于不出；
   读不到大小时仍出不带大小的那一行（不变）。
2. 模块进行中（`NEEDS_PLAN`、`BUILDING`）：仍为 80%，不变。
3. 窗口：Codex 仍取会话记录里的 `model_context_window`；Claude 仍按 1M 折算，固定数由 500,000 改为 **700,000**（800,000 不变）。
4. 判定仍用“达到”（≥ ⌈窗口 × 比例⌉）；阈值仍写死、不开放配置；hook 只读、不记“已提醒过”；提示句式不变，只有阈值说明随之变化。
5. 版本 0.63.5，一个 PR。

## Contract

- `hooks/module_stage.py`：`BOUNDARY_SHARE` 0.5 → 0.7；`thresholds()` 有窗口时的边界值改为 ⌈窗口 × 7 / 10⌉，说明文字
  `at or over 70% of the N k window`；无窗口时为 `at or over 700 k`。80% 一档与其余输出逐字不变。
- 文档中写明 50% / 500k 的地方改为 70% / 700k：`commands/phase.md`、`references/workflow-checkpoints.md`（连续构建一段）、
  `docs/design.md`；CHANGELOG `[0.63.5]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.63.5。
- 输出仍是宿主接受的 JSON；只依赖 bash、git、python3。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先改测试并确认在当前代码上失败，再改实现。
- `test-phase-guard.sh` 中按 50% 写的断言改为 70%：
  - Claude：DONE、MODULE_DONE、NEEDS_SPEC 在 699,999 不出边界行、700,000 出且说明为 `at or over 700 k`；新增 500,000 时不出
    （原来出），证明旧阈值已失效；800k 以上的现有用例只改说明文字。
  - Codex（窗口 258,400）：180,880 出、说明为 `at or over 70% of the 258 k window`；180,879 不出；原 129,200 的用例改为不出。
  - BUILDING 80% 的用例逐字不变。
- 变异：把 `BOUNDARY_SHARE` 改回 0.5，新增的“500k 不出”与“699,999 不出”变红。
- 三套核心回归与 `validate.sh` 全绿。

## Boundaries

- Always：先红后绿；hook 只读；读不到大小时的保守行为不变。
- Ask first：改动 80% 一档；开放阈值配置；为 Claude 按模型名推断窗口。
- Never：在仓库、提交或 PR 里写消费者项目的名称或路径。

## Success criteria

1. 模块边界的提示在 70% 出现、低于 70% 不出，Claude 与 Codex 两边都有正反用例。
2. 模块进行中 80% 一档与现在逐字相同。
3. 三套核心回归与 `validate.sh` 全绿；变异有断言变红。
4. 文档里不再有把模块边界写成 50% / 500k 的说法（CHANGELOG 历史条目与发版记录除外）。

## Open questions

- 无。
