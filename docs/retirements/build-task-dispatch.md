# 退役：build-task-dispatch 派活规则与成本报告的返工信号

状态：已退役。2026-10-22 由模块 `cost-slim-link-follow` 去掉（功能盘点决定 D17）。

## 退役的是什么

- `setup-convention --dispatch`／`--no-dispatch`：在约定块基础模板之后加一段可选规则，让 `/build` 把非 Checkpoint 的 task
  交给一个子代理做 RED → GREEN → 回归 → 构建，派活 prompt 带 tier-guard 档位标记（0.44.0 引入，模块 `build-task-dispatch`）。
- `cost-report` 里只为这项实验服务的部分：派活次数、重派、收回（匹配 tier-guard 的「第二次失败后的收回」与 `hook error`）、
  交回后主代理改动的文件数（读编辑工具路径与 Codex `apply_patch` 的文件名），以及多模块时「有派活 / 没派活」的对照。

## 为什么退役

对照实验与 2026-10-06 的联调都没有证明派活能稳定省钱：规格明确的小 task 派出去更贵，主会话轮次也不降（记录在
[`spec/build-task-dispatch.md`](../../spec/build-task-dispatch.md) 的验收记录与修订节）。规则因此一直是「实验性、默认关闭」。
用户在 2026-10-22 的功能盘点里决定去掉实验相关部分，只保留成本报告「按模块看 token 与主会话轮次」。

## 现在的行为

- `--dispatch`／`--no-dispatch` 被拒（退出 2，不写文件）。旧项目的约定块里还带着规则段时，`--replace` 移除整段、不需要
  `--accept-removals`，预览单列 `retired build-task-dispatch rule section will be removed`；teardown 照样认得它。两份规则模板
  （`templates/{claude,codex}-dispatch-rule.md`）只为识别旧块保留，不再写入。
- `cost-report` 仍按 task 统计主代理与子代理的 token、主会话轮次与子代理记录覆盖率；`--json` 去掉 `dispatches`、`redispatches`、
  `reclaims`、`edits_after_handback` 与 `comparison`，`dispatches_unrecorded` 改名 `subagents_unrecorded`，新增 `subagents`。
  报错的 Agent 调用只看工具结果的错误标记来排除，不读结果正文。
- `/spec-guard:config` 不再列 `dispatch`。

## 保留的历史材料

`spec/build-task-dispatch.md`、`tasks/build-task-dispatch/` 与 `evals/dispatch-cost/`（含各次运行的成本结果）原样保留，只作实验记录；
其中「现行」说法按当时理解。能力图里 `build-task-dispatch` 那一行作为已完成模块保留。
