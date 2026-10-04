# 退役：`.agent/state.json` 的 `tracker` 字段

状态：已退役（2026-10-04，用户决定）。

承接 [`spec-github-bridge-retirement.md`](spec-github-bridge-retirement.md)：那次退役的是远端 tracker
**机制**，这次退役的是它留下的**字段**。

## 退役的是什么

`.agent/state.json` 里的 `tracker` 字段，取值 `none`、`github` 或 `gitlab`，以及同一文件里从未被任何
代码读取过的 `modules` 空对象。

这个字段来自 2026-09-15 之前的远端 tracker 模式：`/plan` 只写 `plan.md`，任务同步成远端 Issue，进度记在
Issue 上，因此那类模块**按设计就没有 `todo.md`**。模式本身随
[`spec-github-bridge-retirement.md`](spec-github-bridge-retirement.md) 退役，字段留了下来。

## 为什么退役

留下来的字段同时承担三个互不相干、彼此矛盾的职责：

| 位置 | 它在那里的作用 | 对同一字段的称呼 |
| --- | --- | --- |
| `hooks/phase-guard.sh` 的 `has_state()` | 两个激活信号之一 | 「已知 tracker 值」——当成现行机制 |
| `hooks/setup-convention.sh` | 每个新装项目都写入 `"tracker":"none"` | 不作说明 |
| `hooks/module_stage.py` 的 `retired_tracker()` | `github`/`gitlab` 时抑制 plan-without-todo 提醒 | 「已退役模式」 |
| `hooks/verify-artifacts.sh` | 对该文件的**存在**发「检测到历史状态文件」 | 「历史状态文件」 |

于是插件一边装这个文件，一边对自己刚装的文件告警；一边把它的值当作现行激活信号，一边在另一处把同样的值
称作已退役。

而 `"tracker":"none"` 是纯粹的魔法字符串：`retired_tracker()` 只认 `github` 与 `gitlab`，`none` 不触发任何
逻辑，它存在的唯一理由就是让 `has_state()` 的正则匹配得上。

## 移除的内容

- `hooks/setup-convention.sh`：新建的 `state.json` 内容由
  `{"tracker":"none","modules":{},"activeModule":""}` 改为 `{"activeModule":""}`。
- `hooks/phase-guard.sh`：`has_state()` 的判据由 `"tracker":"(none|github|gitlab)"` 改为 `"activeModule":`。
  **两个激活信号的数量不变**：声明块，或含 `activeModule` 的 `state.json`。
- `hooks/module_stage.py`：删除 `retired_tracker()` 及其两处调用。
- `hooks/verify-artifacts.sh`：删除同一条抑制；「历史状态文件」告警改为只在确实残留 `tracker` 字段时发出，
  文案改为指出它已退役、可以删除。
- `hooks/test-retire-legacy-tracker-bridge.sh`：新增第三条扫描模式，重新引入该字段的写入
  （`"tracker": "..."`）或读取（`get("tracker")`、`retired_tracker`）都会让扫描变红。
- 回归夹具中顺带携带的 `tracker` 字段；刻意断言退役行为的夹具保留。

**没有移除**：完成判据本身。「有 `tasks/<id>/plan.md` 且没有未勾选项即完成」逐字不变，缺 `todo.md` 仍算完成
（见 [`spec/plan-without-todo.md`](../../spec/plan-without-todo.md)）。删掉的只是**对退役 tracker 项目的
警告抑制**，不是判据。本仓库 13 个有 Plan 无 todo 的历史模块状态不变。

## 迁移

- **绝大多数项目无需动作。** 由 `setup-convention` 装好、声明块还在的项目，激活与阶段输出都不变。
- **`state.json` 里还有 `tracker` 的项目**：`verify-artifacts` 会提示一次，手工从该文件删掉这个键即可。
  删不删都不影响任何判断——没有任何代码再读它。
- **`state.json` 里没有 `activeModule`、也没有声明块的项目**：这是唯一会改变行为的情形，hook 会从注入
  变为静默。两种形态都算：`{"tracker":"none"}`，以及退役前远端 tracker 项目的典型形态
  `{"tracker":"github","modules":{"alpha":{"issue":1}}}`。补上 `activeModule` 键，或重新运行
  `/spec-guard:setup-convention`（Codex：`spec-guard-ops` 的 setup 一节）装回声明块。
  注意 `teardown-convention` 的停用方式不变，仍是把 `state.json` 改名为 `.disabled`；单独删掉 `tracker`
  键**不会**让 hook 停下。
- **`modules` 对象**：从未被读取，留着无害，删掉也无影响。

## 取而代之的是什么

`tracker` 字段曾经混在一起的「项目用哪种工作流」与「事项写去哪」，现在分开了：

- **这个项目装了约定吗** —— 由激活信号回答：声明块，或含 `activeModule` 的 `state.json`。
- **新事项默认写去哪** —— 由 `.agent/tracker.json` 的 `defaultBackend` 与 `defaultTarget` 回答，
  入口是 `/spec-guard:tracker-default`。它只预填预览，不决定写入，不改变已有事项的绑定，
  **也不是激活信号**。详见 [`spec/tracker-backend-default.md`](../../spec/tracker-backend-default.md)
  与 [`docs/decisions/2026-10-04-tracker-backend-default.md`](../decisions/2026-10-04-tracker-backend-default.md)。

两者不是同一根轴：旧字段是项目全局的模式开关，会改变 `/plan` 的产物与阶段判据；新默认值是每条事项各自的
路由参数，不碰 `plan.md`、`todo.md`、能力图或阶段。
