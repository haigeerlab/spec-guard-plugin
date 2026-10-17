# Spec: delegate-review-hint

<!-- spec-guard: review pending -->

## Objective

sibling-plugin-hints（0.64.1）在两份约定块模板里各加了一行规则：Spec、Plan 交审或最终验收值得另一个 agent 复核、而且装了
delegate 时，可以提议用它做只读审查。实际使用里这行规则有三个缺口：

1. 约定块只在会话开头读一次，会话进行到后面就被挤远了，交审时基本想不起来；
2. 没有说审查结论该记在哪里，结论说完就散在对话里；
3. 装没装 delegate 只能靠 agent 自己判断。

阶段提示每轮都会注入，而且已经能认出这三个检查点（`review_hint` 认 Spec／Plan 待审，`at_final_gate` 认最终验收）。本模块在
这些检查点、装了 delegate 时，往阶段提示里加一行固定提示，并约定审查结论和用户拒绝各自写在哪里，写过以后就不再提示。

登记：2026-10-17 经 `/spec-guard:add-module` 插入能力图。来源是生态接缝建议，由监测会话转达，用户同意转给本会话（当前插件
所有者）。用户 2026-10-17 在本会话确认了范围和默认取舍（D1–D3 都选 A）。sibling-plugin-hints 把「在阶段提示里加同类提示」列为
Ask first，用户这次的确认就是对这一项的批准。

## Assumptions

1. **由 hook 判断的只有三件事：** 装了 delegate、正处在检查点、这个模块还没有记录。是否真的值得复核由 agent 判断，提示里
   列出判据：跨模块、有取舍、不可逆、信息不足、有接口提案、Task 多。不设机械阈值（D1-A），也不读 tier-guard（它的档位在交审时
   没有记录，tier-guard 负责人已确认）。
2. **只读文件，不调子进程。** 阶段提示每轮都会运行，所以不复用 `agent_relay_probe.py` 的 `codex plugin list`（最多 10 秒）。
   读不到、格式不对或拿不准时，一律按「没装」处理，不出提示。这里「不出提示」是安全的默认值，不是把「探测失败」报成
   「没装」：不对外报告任何状态，只是不加这一行。
3. **三个检查点的认法：**
   - Spec 交审：阶段为 `NEEDS_PLAN`，且 Spec 标记是 `pending` 或 `none`（`none` 用来兼容不打标记的项目）；
   - Plan 交审：阶段为 `BUILDING`，且 Plan 标记是 `pending`；
   - 最终验收：`at_final_gate` 为真。

   不打标记的项目在 Plan 交审时认不出来，就不提示，这一点接受。`revised` 复审不单独提示。
4. **落点（结论写在哪里）：** 统一用一个小节，标题是 `## 外部审查意见`，英文产物写 `## External review`，两种都认。
   - Spec 交审时，写在模块 Spec 里。这时 Spec 还没批准，写进去的内容会一起被审。
   - 之后写在 `tasks/<id>/todo.md`。todo 不参与评审指纹，所以 Spec、Plan 批准以后再写，也不会把它们变成「改过待重审」。

   每条结论按 delegate 审查报告的固定格式（JSON `schema_version` 1）引用，写清：来源（delegate）、后端、`execution_status`、
   `review_outcome`、findings 条数、审查范围指纹（`scope` 的 `baseline` 与 `diff_sha256`），有 unreviewed 时注明。delegate 的报告
   没有严重程度字段（delegate 负责人确认暂不加），这里不写也不推断严重程度。这些是给人看的参考，不是让人批准的内容。
5. **拒绝标记：** 用户说不需要时，agent 在当时该写的那个文件里加一行固定标记 `<!-- spec-guard: external-review declined -->`。
   hook 只读这行标记，不写任何文件，符合「hook 不写文件」的不变量。
6. **每个模块只提示一次：** Spec 或 todo 里，只要「外部审查意见」小节有非空内容，或者有拒绝标记，这个模块的后续检查点都不再
   提示。监测会话希望三个检查点各提一次，这里选每模块一次，是为了少打扰。用户要按检查点分别提示，可以在审本 Spec 时改。
7. **命令名先写死**（D3-A）：Claude 写 `/delegate:review`，Codex 写 `delegate:delegate-routing`。delegate 以后发布了
   interface.json，再另开模块按它的版本校验；本模块不等 delegate。delegate 负责人已说明：即使有 interface.json，里面也只是静态的
   能力声明，后端现在能不能用要靠 `/delegate:doctor` 现场检查。所以「装了」不等于「审查一定能跑」，提示措辞要留这个余地。
8. **约定块模板不改。** 0.64.1 加的那一行继续作为规则原文；本模块只补每轮注入和落点约定。共享检查点规则补一段落点说明。
9. 版本 0.65.0（阶段提示行为有变化），一个 PR。

## Contract

### 安装判断（新文件 `hooks/sibling_plugins.py`，只读、不联网、不调子进程）

`delegate_enabled(project: Path, host: str | None) -> bool`：

- **`host == "codex"`：** 读 `${CODEX_HOME:-~/.codex}/config.toml`，按行扫描（3.9 自带的 Python 没有 `tomllib`），找表头为
  `[plugins."delegate@<任意市场>"]` 的表，表内有 `enabled = true`；同时 `${CODEX_HOME}/plugins/cache/<该市场>/delegate` 目录
  要存在。两条都满足才算 True。
- **其他情况：** 走 Claude 的记录。`${CLAUDE_CONFIG_DIR:-~/.claude}/plugins/installed_plugins.json` 里要有 `delegate@…`
  条目，并且合并后的 `enabledPlugins` 里它为 `true`。settings 的合并顺序与 `agent_relay_probe.py` 相同：用户级 → 项目
  `settings.json` → 主检出的 `settings.local.json` → 项目 `settings.local.json`；带 `projectPath` 的条目只对该项目算数。
  这段判断从 `agent_relay_probe.claude_root` 抽成带插件名参数的共享函数，两边共用，不复制实现；`agent_relay_probe` 的对外
  行为和输出不变。
- 任何异常都返回 False。

### 阶段提示（`module_stage.py`）

处在上面认定的检查点、`delegate_enabled` 为真、而且这个模块还没有记录时，在 Review 行之后加一行（固定措辞，只代入已校验的
模块 id 和文件路径，不代入文件里的文字）：

> - External review (from delegate, installed): if this <Spec|Plan|final acceptance> deserves a second agent's read-only
>   review (cross-module, trade-offs, irreversible, missing information, an interface proposal, many tasks), you may
>   propose <`/delegate:review`|`delegate:delegate-routing`> (whether it can run is decided by `/delegate:doctor`); start it
>   only after the user agrees. Findings are advisory, not the user's approval. Record them under `## 外部审查意见` in `<spec/<id>.md|tasks/<id>/todo.md>`, or add
>   `<!-- spec-guard: external-review declined -->` there if the user declines; either one stops this line for the module.

这一行不改变建议的下一步，不改变阶段判定。

### 共享检查点规则与文档

- `references/workflow-checkpoints.md` 在交审一节补一段：「外部审查意见」小节的位置；每条结论按 delegate 报告格式引用哪些
  字段（来源、后端、`execution_status`、`review_outcome`、findings 条数、`scope` 指纹，不写严重程度）；拒绝标记的写法；
  「只作参考，不算批准」；delegate 跑不起来时，记一行未能执行及原因即可，不算拒绝。
- `docs/design.md` 的部件表加 `sibling_plugins.py`；数据流里注明阶段提示会只读本机插件记录。
- CHANGELOG 记一条「新增」。

## Commands

```bash
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
python3 -m unittest discover -s plugins/spec-guard/hooks -p 'test_sibling_plugins.py'
python3 plugins/spec-guard/hooks/test_agent_relay_probe.py
/bin/bash scripts/validate.sh
```

## Testing strategy

- **测试隔离（先做）：** `test-phase-guard.sh` 和相关 Python 测试默认把 `CLAUDE_CONFIG_DIR`、`CODEX_HOME` 指向空的临时目录，
  这样本机真装了 delegate 也不会改变现有断言。先确认改造后现有断言全部仍然通过。
- **新增 `test_sibling_plugins.py`（先写失败的测试）：**
  - Claude 侧：已装且启用 → True；已装但未启用 → False；`projectPath` 指向别的项目 → False；记录文件损坏 → False。
  - Codex 侧：表里 `enabled = true` 且缓存目录存在 → True；`enabled = false` → False；有表但缓存目录不存在 → False；
    config 读不出 → False。
- **`test-phase-guard.sh` 正反例：**
  - 三个检查点各一个正例：装了 delegate 时出现这一行，入口命令按宿主写对。
  - 反例：没装 → 不出现；Spec 或 todo 里「外部审查意见」小节有内容 → 不出现；有拒绝标记 → 不出现；小节标题在但内容为空
    → 仍出现；不在检查点（构建中段）→ 不出现。
- `test_agent_relay_probe.py` 不改断言，确认抽出共享函数以后仍然全绿。
- 在草稿副本上改坏一处（比如把拒绝标记的判断删掉），确认断言变红，再复原。
- 发版后：在装了 delegate 的 Claude Code 和 Codex 临时项目里各走一次 Spec 交审，看这一行是否出现、agent 是否只提议不自行发起；
  再在没装 delegate 的项目里确认阶段提示与现在逐字相同。

## Boundaries

- Always：没装或判断不了时输出与现在逐字相同；只提议，不自动发起；hook 不写文件；探测不调子进程、不联网。
- Ask first：按检查点分别提示（而不是每模块一次）；读 delegate 的 interface.json 或审查结果文件；在 `/spec-guard:map`
  里显示这一项（由 plugin-interface 做）。
- Never：把 delegate 写成依赖；把 delegate 的结论当成用户批准，或据此写评审标记；读 tier-guard 的数据；在仓库、提交或 PR 里
  写消费者项目的名称或路径。

## Success criteria

1. 装了 delegate 的项目，在三个检查点的阶段提示里出现这一行，入口命令按宿主写对；写了「外部审查意见」或拒绝标记以后，
   这一行不再出现。
2. 没装 delegate 的项目（包括记录读不出的情况），阶段提示逐字不变；现有回归全绿。
3. 阶段提示每轮不调子进程；`agent_relay_probe.py` 的对外行为不变。
4. 共享检查点规则里写清了落点、写法和「只作参考」。
