# Spec: cost-slim-link-follow

<!-- spec-guard: review approved 36d7fb49ea39 -->

## Objective

两件事，来自 2026-10-22 功能盘点的用户决定：

1. **D17 成本报告与派活规则**：派活实验（`build-task-dispatch`）的结论是「在规格化 task 上不能稳定省钱」，用户决定去掉实验相关部分：
   成本报告里识别派活、重派、收回、交回后改等返工信号的逻辑（含匹配 tier-guard 中文提示「第二次失败后的收回」与 `hook error`
   的那段），以及 `setup-convention --dispatch` 写入的派活规则段。保留成本报告「按模块看 token 与主会话轮次」。
2. **D18 项目指向自动跟随**：现在只有阶段注入会跟随 `.agent/spec-guard-link.json`，其余命令要 agent 手动把被指向的项目路径传进去
   （`commands/link-project.md` 第 67 行原文就是「它们目前不会自动跟随指向」）。用户决定：有指向时所有 spec-guard 命令与阶段注入
   用同一套解析自动跟随，输出写明「本次操作的是被指向的项目 `<路径>`」。会话登记不自动清理，本模块不动。

顺带接 `fact-fixes` 的交接：去掉返工信号后，README 中英两份的 cost-report 读取说明跟着收窄（fact-fixes C6 是按去掉之前的实现写的）。

登记：2026-10-22 经用户批准事项 C78 开会话；依赖 `module-cost-report`、`link-per-session`。

## Assumptions

请批准时逐条确认，不同意的直接指出编号：

1. **成本报告保留什么**：每个 task 的主代理 token（按模型、按类别）、主会话轮次、主会话缓存读、子代理 token（按模型）、贡献会话清单、
   「模块完成后的收尾」、`--prices` 折算、无法统计的部分。子代理 token 留着，因为不派活规则也会有子代理（agent 自己调 Agent 工具），
   那是真实花费，删掉会让模块合计偏小。
2. **成本报告去掉什么**：派活次数、重派、收回、交回后改四列；多模块时「有派活 / 没有派活的 task」对照节；读编辑工具路径与 Codex
   `apply_patch` 补丁文件名的代码；匹配 `hook error` 与「第二次失败后的收回」文本的代码。命令描述从「模块成本与返工报告」改为
   「模块成本报告」。
3. **子代理记录覆盖率留着**，列名改为「子代理记录」（有记录的子代理调用 / 全部子代理调用）：有 Agent 调用却找不到子代理文件时，
   不说明就会把未知当 0。区分「被钩子拦下、子代理没起来」的调用改为只看工具结果的**错误标记**（`is_error`），不再读结果正文；
   报错的 Agent 调用不计入分母。
4. **`--json` 字段**：删 `dispatches`、`redispatches`、`reclaims`、`edits_after_handback` 与模块级对照；`dispatches_unrecorded`
   改名 `subagents_unrecorded`，另加 `subagents`（计入分母的子代理调用数）；`coverage` 保留原名与格式。会改 JSON 形状，在 CHANGELOG
   写明（由模块协调整批写）。
5. **派活规则段退役**：`--dispatch`／`--no-dispatch` 两个参数都拒绝（退出 2，「派活规则已退役，未改动任何文件」，与已退役的
   tracker 模式写法相同）；`--replace` 时旧声明块里的派活规则段与标记行一律移除、不需要 `--accept-removals`，预览单独一行说明
   「已退役的派活规则段会被移除」；teardown 照样认得旧规则段。两份规则模板文件保留，只当 `--known` 用、不再写入，文件头注明。
6. **`/spec-guard:config` 不再列 `dispatch` 一项**（它只是汇总显示，不是开关）。
7. **派活实验的历史材料不删**：`spec/build-task-dispatch.md`、`tasks/build-task-dispatch/`、`evals/dispatch-cost/` 原样保留作记录；
   新增 `docs/retirements/build-task-dispatch.md` 说明退役原因、时间与替代（无），`spec/build-task-dispatch.md` 与
   `spec/module-cost-report.md` 各追加一节「修订：D17 退役」。能力图里 `build-task-dispatch` 那一行不动（已完成模块，删行要改公共文件，
   没必要）。
8. **跟随的解析只有一份**：`project_link.py` 新增子命令 `follow`，与钩子共用 `resolve_for`。命令侧的会话标识**按入口所在的宿主取**：
   Claude 的 `commands/*.md` 只传 `CLAUDE_CODE_SESSION_ID`，Codex 的 `spec-guard-ops` 只传 `CODEX_THREAD_ID`，不同时传两个、不猜。
   这放宽了 `link-per-session` Boundaries 里「命令自己猜会话标识」需先问的那条：入口本身就确定了宿主，不算猜。
9. **跟随范围**：除 `link-project` 自己（它管理的就是会话目录里的指向文件）外的所有命令都跟随，包括 `setup-convention` 与
   `teardown-convention`（两者本来就先预览后确认，预览里会写明操作的是被指向的项目）。
10. **跟随失败时停下，不退回会话目录**：指向文件格式无效、目标不存在、目标未启用时，命令退出 2，诊断文字与阶段注入的失效诊断相同；
    不悄悄改成操作会话目录。会话目录没有指向文件、或只有别的会话的登记时，照现行行为操作会话目录本身。
11. **没有关闭跟随的开关**：同一目录里做别的项目的会话，按 `link-per-session` 的用法给自己登记一条（会话登记优先于目录级指向）。
12. **cost-report 跟随后读的是被指向项目的会话记录**：在会话目录里运行的会话，宿主把记录存在会话目录名下、`cwd` 也是会话目录，
    这部分本模块不归到被指向的项目，在「无法统计的部分」固定写一句。要统计它们需另开模块。
13. 版本号与 CHANGELOG 由模块协调整批统一改；本模块的更新说明写在 todo 末尾。

## Contract

### C1 成本报告瘦身（`hooks/module_cost_report.py`）

- 删除：`EDIT_TOOLS`、`HOOK_DENIAL`、`RECLAIM_MARK`、`PATCH_FILE` 与相关读取；`_claude_events` 只返回「工具调用 id → 是否报错」与
  用户提问时间（收尾用）；Codex 线程不再收集编辑路径。
- `build_report` 每个 task：`main`、`sub`、`guardian`、`main_turns`、`sessions`、`subagents`、`subagents_unrecorded`、`coverage`；
  报错的 Agent 调用（Claude）不计入 `subagents`；Codex 的 `spawn_agent` 全部计入（宿主没有对应的错误标记）。
- 人读表格列：task、主会话轮次、主代理 token、主会话缓存读、子代理 token、子代理记录；有价格时金额列照旧。删除对照节。
- 「无法统计的部分」固定说明改为：子代理（含 Codex 子线程）的全部用量计到发起它的 task；在指向别处的会话目录里运行的会话不计入
  （假设 12）；其余未提供类别、无法归属会话的说明照旧。删掉「交回后改」与「收回」两条。
- 模块文档字符串、`argparse` 描述改为「只读的模块成本报告」。
- 其余行为（时间窗、去重、Codex 累计值求差、guardian 单列、收尾、价格、退出码、隐私）逐字不变。

### C2 派活规则退役（`hooks/setup-convention.sh`、`hooks/project_config.py`、两份规则模板）

- `setup-convention.sh`：`--dispatch`／`--no-dispatch` → 退出 2，stderr 一行退役说明，不改文件。`block_content` 只写基础模板。
  `--replace` 时若旧块含派活标记行，预览与实际输出都多一行「已退役的派活规则段会被移除」；两份规则模板仍作为 `--known` 传给
  `managed-block.py`，所以这些行不需要 `--accept-removals`。删 `dispatch_status` 那行输出。
- `teardown-convention.sh`：不变（仍把规则模板作 `--known`）。
- `project_config.py`：删 `dispatch` 项、`DISPATCH_MARKER` 与 `_dispatch`。
- 规则模板文件头加一行 HTML 注释：已退役，仅供识别旧声明块。

### C3 跟随解析（`hooks/project_link.py`）

```text
project_link.py follow --from <会话目录> [--session <标识>]
```

- 用 `resolve_for(会话目录, [标识])`（钩子用的同一个函数）：
  - `none` → stdout 打印会话目录自身（取 realpath），退出 0，无额外输出；
  - `ok` 且目标已启用 → stdout 打印目标路径，stderr 打印「本次操作的是被指向的项目 `<路径>`（来源：本会话的登记／目录级指向，
    指向文件 `<会话目录>/.agent/spec-guard-link.json`）」，退出 0；
  - `ok` 但目标未启用、`missing`、`invalid`、读取失败 → stdout 为空，stderr 打印与阶段注入同义的失效诊断与修复办法，退出 2。
- 「已启用」判定复用 `enabled()`；路径显示复用现有的清洗。
- 会话目录本身已启用 spec-guard 时不看指向文件，直接打印会话目录（与钩子「自己有激活信号就不跟随」一致）。

### C4 命令入口（Claude `commands/*.md`）

- 现在的 `PROJECT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"` 一律改为先取会话目录再跟随：

  ```bash
  FROM="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  PROJECT="$(python3 -B "$ROOT/hooks/project_link.py" follow --from "$FROM" --session "${CLAUDE_CODE_SESSION_ID:-}")" || exit 2
  ```

  覆盖：add-module、checkout-role、config、cost-report、documentation-baseline、documentation-impact、documentation-verification、
  history-integrity、map、module-suspend、phase、proposal-closeout、proposal-submit、review-mark、tracker-default、verify-artifacts；
  用 `--project .` 的 proposal-review、proposal-promotion-preflight、proposal-promotion-proof 改为 `--project "$PROJECT"`；
  setup-convention、teardown-convention 以 `CLAUDE_PROJECT_DIR="$PROJECT"` 调脚本；ticket、local-ticket-ledger、
  local-ticket-portability 的 `repoRoot`／项目根取 `$PROJECT`。`link-project` 不改。
- 每个命令说明里加一句：stderr 出现「本次操作的是被指向的项目」时，回复用户时照原文转述这一句。
- `link-project.md` 第 67 行改为：其他命令与阶段注入会自动跟随指向，输出里写明操作的是哪个项目。

### C5 Codex 入口（`skills/spec-guard-ops/SKILL.md` 及其他 skill）

- 取项目根的那一处改为同样的 `follow` 调用，`--session "${CODEX_THREAD_ID:-}"`；各节沿用 `$PROJECT`。
- link-project 一节同 C4 改写跟随说明。

### C6 阶段注入的措辞（`hooks/phase-guard.sh`）

- 「关联项目」／「Linked project」四种文字里的「运行 spec-guard 命令时把这个路径作为项目传入」（及英文对应句）改为
  「spec-guard 命令会自动跟随到这个项目」；目录级指向那句里「忽略这里的阶段，传入你自己的项目路径」改为「用 `link-project` 给本会话
  登记自己的项目」。解析逻辑不变。
- 这会改动 `link-per-session` 承诺的「来源为 directory 时与 0.58.2 逐字相同」，在 `spec/link-per-session.md` 追加「修订：D18 自动跟随」说明。

### C7 文档

- README 中英两份「统计与上传」：cost-report 用到的只剩 token 计数、用户提问时间（切模块收尾）、工具调用是否报错与子代理派生关系
  （把子代理用量归到发起它的 task）；去掉「编辑过的文件路径」与「工具调用结果（判断被拒与交回时间）」。README 里若提到 `--dispatch`
  一并去掉。
- `commands/cost-report.md`、`docs/commands.md`（setup 参数、cost-report 描述与对照表行）、`docs/workflow.md`（可选派活一段与「怎么看
  省没省钱」一段改为成本报告的简短说明）、`commands/setup-convention.md`、`commands/config.md`（dispatch 一行）、`docs/design.md`
  （若提到派活规则或跟随）、`docs/troubleshooting.md`（若提到需手动传项目路径）。
- `docs/retirements/build-task-dispatch.md`；`spec/build-task-dispatch.md`、`spec/module-cost-report.md`、`spec/link-per-session.md` 的修订节。

### C8 公共文件（发【公共变更请求】，不自己改）

- `plugins/spec-guard/interface.json`：cost-report 与 setup-convention 的描述若含「返工」「dispatch」，改为新描述（构建时实查，
  当前 grep 未命中，可能不需要）。
- CHANGELOG、版本号由模块协调整批改；更新说明写在 todo 末尾。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_module_cost_report.py
python3 -B plugins/spec-guard/hooks/test_project_link.py
python3 -B plugins/spec-guard/hooks/test_project_config.py
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
/bin/bash scripts/validate.sh
```

## Project structure

```text
plugins/spec-guard/hooks/module_cost_report.py, test_module_cost_report.py   -> C1
plugins/spec-guard/hooks/setup-convention.sh, project_config.py,
  templates/{claude,codex}-dispatch-rule.md, test-setup-teardown.sh,
  test_project_config.py                                                    -> C2
plugins/spec-guard/hooks/project_link.py, test_project_link.py              -> C3
plugins/spec-guard/commands/*.md（除 link-project 的取根逻辑）                -> C4
plugins/spec-guard/skills/*/SKILL.md                                        -> C5
plugins/spec-guard/hooks/phase-guard.sh, test-phase-guard.sh                -> C6
README.md, README.en.md, docs/*, spec/{build-task-dispatch,module-cost-report,link-per-session}.md -> C7
```

## Testing strategy

先写测试并确认在当前代码上失败，再实现。

- cost-report：原「返工信号」用例改为断言输出与 `--json` 里**没有**派活、重派、收回、交回后改与对照节；报错的 Agent 调用不计入
  `subagents`、有子代理文件的调用计入、无文件的计入 `subagents_unrecorded`；工具结果正文里含「第二次失败后的收回」「hook error」时
  输出不受影响；其余用例（去重、时间窗、Codex、收尾、价格、隐私）原样通过。
- setup：`--dispatch`、`--no-dispatch` 各退出 2 且文件不变；旧块带派活段时 `--replace`（不加 `--accept-removals`）移除整段、预览有退役行；
  新建的块不含派活标记；teardown 仍能移除带派活段的旧块。
- config：`show` 不再出现 `dispatch`。
- follow：无指向文件 → 打印会话目录、退出 0、stderr 为空；目录级指向 → 打印目标、stderr 含「本次操作的是被指向的项目」与来源；
  本会话登记优先于目录级；只有别的会话的登记 → 会话目录；目标未启用、目标不存在、格式无效 → 退出 2、stdout 空；会话目录自己已启用 →
  不跟随。变异：不优先查会话登记、失败时退回会话目录，两者都要让测试变红。
- 命令入口：一个检查（放进现有 parity 或 validate 的检查器）确认除 `link-project` 外的命令都经 `follow` 取项目根，没有残留的直接
  `CLAUDE_PROJECT_DIR` 取根写法。
- 阶段注入：四种「关联项目」文字更新；解析行为与失效诊断不变。
- 宿主行为：构建末尾在一个临时会话目录里指向一个临时启用项目，用安装前的工作区源码按命令里的写法跑 `map` 与 `review-mark` 预览，
  确认输出写明被指向的项目；真实宿主验证随发版做。

## Boundaries

- Always：只读的仍只读；跟随失败就停下并说明；输出写明操作的是哪个项目；隐私口径不放宽。
- Ask first：给跟随加关闭开关；自动清理会话登记；把会话目录里的会话记录归到被指向项目；删除派活实验的历史材料；从能力图删
  `build-task-dispatch` 行。
- Never：跟随失败时悄悄操作会话目录；命令同时取两个宿主的会话标识；在 Spec、代码、测试、提交信息中写入使用者项目的名称、路径或编号。

## 并行边界

- 独占：`plugins/spec-guard/hooks/module_cost_report.py`、`plugins/spec-guard/hooks/test_module_cost_report.py`、`plugins/spec-guard/hooks/project_link.py`、`plugins/spec-guard/hooks/test_project_link.py`、`plugins/spec-guard/hooks/setup-convention.sh`、`plugins/spec-guard/hooks/test-setup-teardown.sh`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/hooks/phase-guard.sh`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/templates/claude-dispatch-rule.md`、`plugins/spec-guard/templates/codex-dispatch-rule.md`、`plugins/spec-guard/commands/`、`plugins/spec-guard/skills/`、`scripts/check-command-parity.py`、`README.md`、`README.en.md`、`docs/commands.md`、`docs/workflow.md`、`docs/design.md`、`docs/troubleshooting.md`、`docs/retirements/build-task-dispatch.md`、`spec/build-task-dispatch.md`、`spec/module-cost-report.md`、`spec/link-per-session.md`
- 公共：无

## 与在开模块的重叠

- `sibling-rules-out`（在开，Build order 在本模块之前）也改 `skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`、`docs/commands.md`、
  `commands/config.md`。本模块只改其中的取根代码、派活与成本报告段落、link-project 一节；等它合入后先 `module-crew sync` 再动这些文件，
  冲突以集成分支为底手工合并。
- `rules-at-nodes`（与本模块并列）与 `quiet-injection`（在本模块之后）也改 `hooks/phase-guard.sh`、`test-phase-guard.sh`。本模块只改
  「关联项目」四段文字（C6）与对应断言，不碰注入结构、`module_stage.py` 与约定块模板；若 `rules-at-nodes` 先合入，sync 后再改。
- 公共文件：`plugins/spec-guard/interface.json` 视 C8 实查结果发【公共变更请求】；CHANGELOG、两份 `plugin.json`、`marketplace.json`、
  `spec/CAPABILITY-MAP.md`、`.agent/state.json` 不改。

## Success criteria

- cost-report 的人读与 JSON 输出不再含派活、重派、收回、交回后改与对照；主代理、子代理 token、主会话轮次与收尾与改前一致（同一夹具对比）。
- `setup-convention --dispatch` 被拒；带派活段的旧块经 `--replace` 后干净移除；`config show` 不再列 dispatch。
- 在有指向的会话目录里，除 `link-project` 外的命令都操作被指向的项目，并输出「本次操作的是被指向的项目 `<路径>`」；指向失效时命令停下并给出诊断。
- README 中英 cost-report 读取说明与实现一致；Commands 一节全部通过，含 ShellCheck。

## Open questions

- 无。上面的假设 1～13 即待确认项。
