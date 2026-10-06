# Spec: context-hint-thresholds

## Objective

fresh-session-hint 在主会话上下文超过 200k token 后，每一轮都提示开新会话，不论当前模块是否做完。用户反馈（2026-10-06）：
一个需求可能由几个连续模块组成，模块中途换会话要重读正在改的代码、写交接、还可能丢掉未落盘的决定，重建成本最高；
模块边界换会话几乎不丢东西。提醒应以模块为单位，并且只在上下文确实到达设定阈值时出现。

本模块把上下文提醒改为两档：模块完成时达到窗口 50% 才建议在新会话开始下一个模块；模块进行中只在达到窗口 80% 时
作为安全阀提示，避免撞上窗口上限或被宿主压缩。

登记：2026-10-06 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-06 确认：

1. **模块进行中**（`NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`）：上下文达到窗口 80% 才出上下文行；低于不出。
2. **模块完成时**（`MODULE_DONE`、`DONE`）：
   - 达到窗口 50%：出 Module boundary 行并附上下文大小；
   - 低于 50%：不出 Module boundary 行；
   - 读不到上下文大小：保留现行 Module boundary 行（不带大小）。
   模块完成时不再单独出上下文行，大小并入 Module boundary 行。
3. **窗口大小**：Codex 取会话记录 `token_count` 事件的 `info.model_context_window`（2026-10-06 在本机真实 rollout 实测为
   258400）；Claude 会话记录只有模型名、没有窗口大小，按 1M 窗口折算为固定的 500,000 / 800,000 token。代价：200k 窗口的
   Claude 模型基本不会出现提醒。
4. 阈值写死，不开放配置；hook 只读，不记"已提醒过"；会话记录读取规则（末尾 4 MiB、跳过子代理与用量为 0 的记录）、
   阶段判定、位置行均不变。
5. 检查点分级与批量前置审不在本模块范围。

本 Spec 依据实测补充：

6. 判定用"达到"（≥）：tokens ≥ ⌈窗口 × 比例⌉。Codex 的窗口取同一条 `token_count` 记录里的值；该字段缺失、为 0 或不是
   正整数时按 Claude 的固定数处理。
7. **输出文字**（英文，与现有行风格一致；N 为四舍五入到千的整数，T 为阈值说明）：
   - 模块完成且达到 50%：
     `- Module boundary: this session's context is about N k tokens (T); start the next piece of work in a new session; run /spec-guard:handoff (Codex: spec-guard handoff) for paste-ready handoff text. This stage summary carries over, the conversation does not need to.`
   - 模块进行中且达到 80%：
     `- Session context: about N k tokens in the last turn (T); every turn re-reads it. Finish or record the current task, then continue in a new session with /spec-guard:handoff (Codex: spec-guard handoff).`
   - T：有窗口时为 `at or over 50% of the 258 k window` / `at or over 80% of the 258 k window`（窗口同样按千取整）；
     无窗口时为 `at or over 500 k` / `at or over 800 k`。
   - 读不到大小时的 Module boundary 行与现行文字逐字相同。

## Contract

- `hooks/session_context.py`：
  - 新增 `context_usage(transcript_path) -> tuple[int, int | None] | None`：返回 (token 数, 窗口)；Claude 记录窗口为 `None`，
    Codex 取同条记录的 `model_context_window`。`context_tokens()` 保持原签名，改为取它的第一项。
  - 命令行输出由两行变三行：token 数、位置行、窗口（无则空行）。前两行含义不变。
- `hooks/module_stage.py`：`describe(root, context_tokens=None, context_window=None)`；命令行新增可选 `--context-window N`。
  按第 1、2、6、7 条决定 Module boundary 行与上下文行；删除 `CONTEXT_THRESHOLD = 200_000` 的单档判定。
- `hooks/phase-guard.sh`：读第三行，传 `--context-window`；其余不变。
- `commands/phase.md`、`docs/workflow.md` 中描述提醒条件的文字同步；CHANGELOG `[未发布]`。
- 输出仍是宿主接受的 JSON；只依赖 bash、git、python3。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_session_context.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先写测试并确认在当前代码上失败，再改实现。
- `test_session_context.py`：Codex 记录返回窗口；窗口缺失 / 0 / 非整数 → `None`；Claude 记录窗口为 `None`；命令行三行。
- `test-phase-guard.sh`（构造的会话记录）：
  - BUILDING：Claude 799,999 无上下文行、800,000 有；Codex 窗口 258,400 时 206,719 无、206,720 有（⌈258400 × 0.8⌉）；
  - DONE / MODULE_DONE：Claude 499,999 无 Module boundary 行、500,000 有且带大小；Codex 129,200 有、129,199 无；
    读不到记录 → 现行 Module boundary 行逐字不变；模块完成时不出单独的上下文行；
  - 已有用例中依赖 200k 单档的断言按新规则更新，其余逐字不变。
- 两种 Python 下最小验证通过。
- Checkpoint：安装版在真实 Claude Code 会话里确认模块进行中低于 800k 不再出现上下文行。

## Boundaries

- Always：先红后绿；hook 只读；读不到就按第 2 条保守处理。
- Ask first：开放阈值配置；为 Claude 推断窗口大小（如按模型名猜）；写任何文件。
- Never：在输出中带出会话原文；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 模块进行中，上下文低于窗口 80%（Claude 800k）时不再每轮提示。
- 模块完成时，上下文达到窗口 50%（Claude 500k）才建议开新会话，并给出大小；低于时不提示；读不到大小时保持现行提示。
- 阶段判定、位置行与其余输出不变。

## Open questions

- 无。
