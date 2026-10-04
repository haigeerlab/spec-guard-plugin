# Plan: phase-context-sanitization

依据 [`spec/phase-context-sanitization.md`](../../spec/phase-context-sanitization.md)。四个 task 串行，
每个 task 一条提交；先写能在当前代码上失败的测试并记录失败输出，再修改到通过。

分支 `codex/phase-context-sanitization`，基于已合并的 `origin/main`（`45bf439`）。

`limit` 固定为 **80**：本仓库最长的合法 module id 是 29 字符
（`proposal-add-module-promotion`、`authorized-session-delegation`），80 留有充裕余量，
不会把正常诊断截断到难以辨认。这是实测值，不是直觉值。

每个 task 完成时都运行三条最小验证，并用 `PATH=/usr/bin:/bin` 下的 `python3`（3.9）再跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

**本模块只改注入边界的呈现**。阶段取值、完成判据、激活信号三者一个字节都不动——每个 task 的验收
都包含「本仓库输出与改动前逐字相同」这一条，因为本仓库没有 `.agent/state.json`、能力图合法，
两条受影响路径都不该被触发。

## Task 1：`safe_fragment` 与它的单元测试（C1）

- `hooks/module_stage.py` 新增 `safe_fragment(value, limit=80)`：折叠所有空白为单个半角空格并去首尾、
  删除反引号与反斜杠、超长截断并以 `…` 结尾、空值或非字符串返回空串。**不做 HTML/Markdown 转义**
  （注入目标是 agent 上下文，不是浏览器）。
- 新增 `hooks/test_module_stage_sanitization.py` 覆盖 Spec T1；在 `scripts/validate.sh` 登记
  （显式清单，不登记 CI 永远跑不到——这是前两个模块的实测教训）。
- 纯函数，不读文件、不起子进程。
- **验收：** T1 先红后绿；中文输入不被破坏到无法阅读；截断后整串长度不超过 `limit + 1`。
- **文件：** `module_stage.py`、`test_module_stage_sanitization.py`、`scripts/validate.sh`。

## Task 2：`activeModule` 的校验与文案（C2）

- `active_module_state(root) -> (value, state)`，`state ∈ {absent, invalid, present}`，
  有效性复用 `capability_map.MODULE_ID`。`active_module()` 保持原签名，只在 `present` 时返回值，
  既有调用方不动。
- `describe()`：`invalid` 输出固定文案且**不含该值**；`present` 但不在图中时文案不变、值经
  `safe_fragment()`；其余分支逐字不变。
- `test-phase-guard.sh` 按 Spec T2 加五个用例，其中**两个先红**：载荷不得出现在注入文本里、
  必须出现「不是有效的 module id」文案。另加 Assumption 5 的反例：**值无效时 hook 仍然激活**。
- **验收：** 两条先红断言各自先记录失败输出；现有 84 条逐字保留通过。
- **文件：** `module_stage.py`、`test-phase-guard.sh`。

## Task 3：`MapError` 与 ref 名的注入边界（C3、C4）

- `module_stage.py:110` 的 `%s` 改为 `safe_fragment(str(error))`；`:137-138` 的 ref 名同样处理。
- **`capability_map.py` 不改动**：它的 `MapError` 文案也被 `verify-artifacts` 与 `module-insert` 使用，
  那两处是人直接读的终端输出，带原文是对的。净化只发生在注入边界。
- `test-phase-guard.sh` 按 Spec T3：坏 id 含反引号与伪造段落 → `MAP_INVALID` 行不含反引号与换行，
  但仍看得出是哪个 id 坏了（**先红**）；超长坏 id 被截断且整行长度有界。
- 按 Spec T4 加**反例**：`verify-artifacts` 与 `module-insert` 的 `MapError` 输出**仍带原文**。
  这条是防止过度净化——把诊断能力一起杀掉比注入更难察觉。
- **验收：** 先红断言先记录失败输出；反例证明净化没有外溢到终端输出。
- **文件：** `module_stage.py`、`test-phase-guard.sh`、`test-verify-artifacts.sh`。

## Task 4：文档与决策记录（C5）

- `commands/phase.md`：注入文本中来自仓库的值都经过净化；`activeModule` 无效时的新文案。
- `docs/workflow.md` 阶段提示一节：`activeModule` 必须是 kebab-case 模块 id。
- `references/workflow-checkpoints.md`：若涉及注入内容的描述，同步。
- 新增 `docs/decisions/2026-10-04-phase-context-sanitization.md`：两处复现、为什么由本仓库收口
  （`tracker-backend-default` 把激活信号迁到 `activeModule` 上放大了它）、Assumption 1／2 的取舍，
  以及「保留经净化的原文」这个决定。
- `CHANGELOG.md` Unreleased 的 `### 修复`，写明这是**安全修复**并点出行为变化。
- **验收：** `check-command-parity.py` 通过；**反向自查**——Spec 里写下的每一条契约都已落地，
  不只是查「新文档有没有描述不存在的行为」。前一个模块的两条 HIGH 正是这个方向漏掉的。
- **文件：** 四份既有文档 + 一份新决策记录 + CHANGELOG。

## Checkpoint：完成

- 两种 Python 下：`test_module_stage_sanitization.py`、三条最小验证、
  `check-command-parity.py`、`check-acceptance-immutable.py`、
  `evals/codex-plugin-smoke.sh --selftest`、`git diff --check`。
  逐项按 通过／失败／未运行／环境不可用 报告。
- **重跑两个复现脚本**，确认载荷不再进入 `additionalContext`，且各自仍能看出出了什么问题。
- **本仓库零差异**：改动前后 `phase-guard.sh` 与 `verify-artifacts.sh` 输出逐字对比。
- **牙齿检查**（Spec T5）：把 `safe_fragment` 改回恒等函数，T2／T3 的先红用例必须重新变红。
  变异必须作用在值被使用**之前**——上一轮有两次无效变异，过了也说明不了问题。
- 完整代码审查与安全审查；审查发现先复现再修、修后重跑复现。
- 检查点勾选随模块 PR 提交；推送并创建 PR；等待 CI；**不自行合并 main，不自行发版**。
