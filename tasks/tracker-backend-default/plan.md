# Plan: tracker-backend-default

依据 [`spec/tracker-backend-default.md`](../../spec/tracker-backend-default.md)。五个 task 串行，
每个 task 一条提交；先写能在当前代码上失败的测试并记录失败输出，再修改到通过。全部在临时目录与
临时项目上测试，不访问网络，不触碰真实项目与用户级目录。

顺序原则：**先立新、后删旧**。Task 1–2 是纯新增，不改变任何既有行为；Task 3–4 才动激活信号与
警告抑制，此时默认值入口已经可用，删除不会留下空档。

每个 task 完成时都运行三条最小验证，并用 `PATH=/usr/bin:/bin` 下的 `python3`（3.9）再跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

注意本模块删除的 `retired_tracker()` 正是 [`tasks/plan-without-todo/plan.md`](../plan-without-todo/plan.md)
Task 4 的产物。那条规则当年是为了不对退役 tracker 项目误报；现在字段本身退役，规则随之失效。
**完成判据（有 plan 且无未勾选项即完成）不属于它，必须逐字保留。**

## Task 1：默认 backend 的读取与 resolve（C5）

- 新增 `hooks/tracker_default.py`：`read_default(root)` 与 `resolve(explicit_backend, explicit_target, default)`，
  以及 `as_json()`。三种 backend 的 `defaultTarget` 形状按 Spec C5 的表固定；`version != 1`、未知 backend、
  形状不符、多余键一律 `invalid` + `tracker-default-invalid`，**不得降级为 `absent`**。
- 新增 `hooks/test_tracker_default.py`：Spec T5 的三正例与八反例、T6 的八行 resolve 判定表逐行断言；
  断言 `as_json` 不含绝对路径与原始异常文本。
- 纯函数，不读 `.agent/state.json`，不执行任何子进程。
- **验收：** 新断言在新增文件前不存在、实现后全部通过；现有回归一条不变。
- **文件：** `tracker_default.py`、`test_tracker_default.py`。

## Task 2：入口 show / set（C6）

- `tracker_default.py` 加 CLI：`show --project --format json`（只读）；
  `set --project --backend {github,gitlab,local} [--host] [--repo] [--project-id] [--confirm]`。
  不带 `--confirm` 只打印改前/改后 JSON 差异；`--confirm` 原子写回 `.agent/tracker.json` 这一个文件
  （保留既有权限，新建 0644）。目标形状不合法则非零退出且不写文件。
- 新增 `commands/tracker-default.md`；`skills/spec-guard-ops/SKILL.md` 增加同名一节；
  `docs/workflow.md` 命令对照增加一行。
- `test_tracker_default.py` 补 Spec T7：预览不改文件（断言内容与 mtime）、`--confirm` 写入且与预览一致、
  非法形状不写、**`.agent/state.json` 在 set 前后逐字相同**。
- **验收：** `python3 scripts/check-command-parity.py` 通过；三条最小验证通过。
- **文件：** `tracker_default.py`、`test_tracker_default.py`、`commands/tracker-default.md`、
  `skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`。

## Task 3：删除退役字段与激活信号改判（C1、C2）

- `setup-convention.sh:97`：写入改为 `{"activeModule":""}`，去掉 `tracker` 与无人读取的 `modules`。
  只在文件不存在时执行的分支结构不变，既有 `state.json` 仍不被改写。
- `phase-guard.sh:28`：`has_state()` 判据改为 `'"activeModule"[[:space:]]*:'`；
  第 18–19 行注释同步改写为「声明块标记，或含 `activeModule` 的 `.agent/state.json`」。
- `test-phase-guard.sh` 按 Spec T1 加六个用例，其中两个在当前代码上必然失败并先记录：
  只有 `{"activeModule":""}` 无声明块 → **注入**；只有 `{"tracker":"none"}` 无声明块 → **不注入**。
- `test-setup-teardown.sh`、`test-hook-entry.sh`：夹具去掉 `"tracker":"none"`；
  按 Spec T4 断言新装项目的 `state.json` 内容恰为 `{"activeModule":""}`，teardown 改名与 `--keep-state` 行为不变。
- **验收：** 两个新断言先红后绿；现有 phase-guard 全部用例保留通过。
- **文件：** `setup-convention.sh`、`phase-guard.sh`、`test-phase-guard.sh`、`test-setup-teardown.sh`、
  `test-hook-entry.sh`。

## Task 4：删除警告抑制、重新界定历史告警、退役扫描（C3、C4、T8）

- `module_stage.py`：删 `retired_tracker()`（:55-57）与两处调用（:128、:134）。
  **`module_state` 的完成判据、`stage` 取值、计数行、提醒行文案、`Paused` 行逐字不变。**
- `verify-artifacts.sh`：内嵌 Python 去掉 `retired_tracker` 的 import 与 `and not retired_tracker(root)`；
  第 92–93 行的告警改为只在 `.agent/state.json` 确实含 `tracker` 键时发出，文案给出删除指引。
- `test-verify-artifacts.sh` 按 Spec T2、T3：`tracker=github`/`gitlab` 夹具下**仍然**发缺 todo 汇总（先红）；
  `{"activeModule":""}` 下**不发**历史状态告警（先红）；含 `tracker` 键时发告警；无文件时不发。
- `test-retire-legacy-tracker-bridge.sh` 加断言：已发布插件表面不再出现 `"tracker"[[:space:]]*:` 的读写
  （退役说明与历史报告排除在扫描范围外）。
- **验收：** 三条先红断言各自先记录失败输出再转绿；本仓库（无 `state.json`）的阶段注入与
  `verify-artifacts` 输出与改动前**逐字相同**。
- **文件：** `module_stage.py`、`verify-artifacts.sh`、`test-verify-artifacts.sh`、
  `test-retire-legacy-tracker-bridge.sh`。

## Task 5：文档与退役说明（C7）

- 新增 `docs/retirements/state-tracker-field.md`：退役了什么、为什么、移除清单、迁移
  （手工删 `.agent/state.json` 的 `tracker` 键；无此键的项目无需动作）。
- 新增 `docs/decisions/2026-10-04-tracker-backend-default.md`：记录「默认值 ≠ 权威」的区分、五条不变量，
  并写明本决策**修订** `spec/hosted-ticket-workflow.md` 的「不新增项目级 Tracker 配置」一条，其余条款继续有效。
- `spec/plan-without-todo.md`「修订：已退役的远端 tracker 模式」一节改写为指向退役说明并说明抑制逻辑已删除；
  **完成判据的表述逐字不变**。
- `docs/workflow.md`：安装约定写入的文件清单更新；阶段提示一节说明两个激活信号。
- `docs/concepts.md`：术语表补 `backend`、`精确目标`、`source authority`，并写明 `activeModule` 是书签、
  阶段每轮实时推导。
- `CHANGELOG.md` Unreleased 的 `### 移除` 与 `### 新增`。
- **验收：** `validate.sh` 与 `check-command-parity.py` 通过；退役说明结构对齐 `claude-desktop-mcpb.md`。
- **文件：** 两份新文档 + 四份既有文档。

## Checkpoint：完成

- 三条最小验证 + `test_tracker_default.py` + `test-setup-teardown.sh` + `test-hook-entry.sh` +
  `evals/codex-plugin-smoke.sh --selftest` + `git diff --check`，在默认 `python3` 与
  `PATH=/usr/bin:/bin` 的 3.9 下各跑一遍，逐项按 通过/失败/未运行/环境不可用 报告。
- 在临时项目上实跑三种情形并记录输出：全新 `setup-convention` → `{"activeModule":""}` 且阶段注入正常；
  只有 `{"tracker":"none"}` → 静默；`.agent/tracker.json` 三种 backend 的 `show` 与 `resolve`。
- 在本仓库核对：阶段注入与 `verify-artifacts` 输出与改动前逐字相同（本仓库无 `state.json`，
  因此删除 `retired_tracker()` 应当零差异）。
- 代码审查与安全审查；检查点勾选随模块 PR 一起提交；等待 CI；**不自行合并 main**。
