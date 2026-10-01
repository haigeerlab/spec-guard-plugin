# 使用流程

这一页讲三件事：新项目怎么从零开始、项目做到一半来了新需求怎么加进能力图、能力图有哪些规则。
名词解释见[设计理念与术语](concepts.md)。

## 新项目：从零到交付

新项目**不写 Proposal**。Proposal 需要引用远端 main 上已有的能力图，新项目还没有能力图，直接按下面的步骤走。

1. **安装约定。** Claude Code 里运行 `/spec-guard:setup-convention`；Codex 里说「用 spec-guard 在这个项目安装约定」，
   由 `spec-guard-ops` skill 执行。都会先预览，你确认后才写文件。写入的是：

   ```text
   CLAUDE.md 或 AGENTS.md 里的约定块   # 告诉 agent 多模块的目录规则
   spec/CAPABILITY-MAP.md               # 能力图模板
   .agent/state.json                    # 只记录当前模块
   ```

2. **写能力图并评审。** 用 agent-skills 的 `/spec` 做 Phase 0：列出模块、职责、依赖和一行 Build order。
   人工确认模块边界清楚、依赖单向无环，再往下走。
3. **按 Build order 逐个模块推进。** 每个模块依次是：
   - 写 `spec/<模块>.md` 并评审；
   - 用 `/plan` 生成 `tasks/<模块>/plan.md` 和 `todo.md`；
   - 用 `/build` 逐项实现，每完成一项勾掉一项。
4. **切到下一个模块。** 当前模块的 todo 全部勾完后，把 `.agent/state.json` 的 `activeModule` 改成下一个模块。

整个过程中不用自己记进度，每轮对话开头 hook 都会告诉 agent 现在到了哪一步。

若项目已明确采用可用的 Local 事项账本，并决定实施一个可追踪需求或修复，
先用 `ticket` 入口查重并取得事项 ID，再开始编码；Spec 和 Plan 可随后细化。
探索、讨论与无需追踪的小操作不强制建事项。Local 完成时把代码引用和验证结果
写回事项，经明确授权关闭后读回状态；本地不要求 PR/MR。

### 阶段提示

| 阶段 | 意思 | 下一步 |
|---|---|---|
| `IDLE` | 还没有能力图 | 写能力图并人工评审 |
| `MAP_INVALID` | 能力图格式不对，比如 Build order 不是恰好一行 | 用 `/spec-guard:verify-artifacts` 查原因 |
| `MAP_ONLY` | 有能力图，还没有任何模块 Spec | 写第一个模块的 Spec |
| `NEEDS_SPEC` | 当前模块缺 Spec | 写 `spec/<模块>.md` |
| `NEEDS_PLAN` | 当前模块有 Spec、缺 Plan | 用 `/plan` 生成 plan 和 todo |
| `BUILDING` | todo 还有 N 项没勾 | 继续 `/build` |
| `MODULE_DONE` | `activeModule` 指向的模块已完成，但还有别的模块没做完 | 把 `activeModule` 改成提示里点名的下一个模块；有被暂停的模块时点名它 |
| `DONE` | 全部模块都已完成 | 新需求用 `/spec-guard:add-module` 插入；`activeModule` 还指着已完成模块时可以清掉 |
| `UNKNOWN` | 阶段算不出来 | 用 `/spec-guard:verify-artifacts` 查原因 |

有 Plan 但没有 `todo.md` 的模块按已完成计（历史上已交付的模块常是这种写法，所以判据不变）。DONE 汇总会显示这类模块的数量，可用 `/spec-guard:verify-artifacts` 查看具体模块。插队或新加的模块如果只有 Plan、没有 `todo.md`，会被读成已完成；把 `activeModule` 指向它时阶段提示会多一行提醒，补上 `tasks/<模块>/todo.md` 列出剩余任务即可。

当前模块取 `.agent/state.json` 的 `activeModule`，没设置时按 Build order 取第一个没完成的模块。
随时想看完整状态，用 `/spec-guard:phase`。
存在被暂停的模块（见「插队」）时，`NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MODULE_DONE` 下会多一行 `Paused: …`。

## 已有项目：加新需求

项目做到一半冒出新需求时，有两种方式把它作为新模块加进能力图：

| 方式 | 适合 | 步骤 |
|---|---|---|
| **快速插入**（默认） | 个人或小团队，需求已经理顺 | 一次预览、一次确认 |
| **Proposal** | 需要在 Issue 上留下评审与接受的记录，或需要多人确认 | 四步（提交、接受、晋级、收尾），要先做一次性准备 |

两种方式都只**新增**模块。修改、删除或调整已有模块的顺序，直接改能力图并人工评审。

### 快速插入

在一个模块做完、还没开始的检查点（或显式插队，见下一节），把理顺的需求上下文交给 agent，运行 `/spec-guard:add-module`
（Codex 里说「用 spec-guard 插入一个新模块」）：

如果这项工作已选择 Local 账本，先按上面的受理规则取得或沿用事项 ID。
`add-module` 只管理能力图，不创建事项。

1. agent 读能力图，提出新模块的 id、职责、依赖和插入位置（`after:<某模块>` 或 `end`），每项说明理由；
2. 命令预览：给出新行、新 Build order、能力图改动对比，以及插入后当前模块会不会变；
3. 你确认后才写入。只改 `spec/CAPABILITY-MAP.md`，不建文件、不动 `tasks/` 和 `.agent/state.json`，也不做 Git 操作；
4. 新模块排到当前位置时，阶段变为 `NEEDS_SPEC`，接着照常写并评审它的 Spec，再 Plan、Build。

命令会先校验，任何一条不满足就拒绝，什么都不写：

- 当前模块做到一半（todo 里既有已勾、又有未勾的项）——唯一的例外是显式加 `--interrupt` 插队，见下一节；
- 依赖不存在、依赖排在插入位置之后、出现循环依赖，或 id 重复、不是 kebab-case；
- 插入会改动 `## 目标`、已有模块行，或已有模块在 Build order 中的先后。

若 `spec/<id>.md` 已存在，预览会提示插入后为 `NEEDS_PLAN`；先确认这份 Spec 已评审，再确认写入。

### 插队

当前模块做到一半、剩下的都要等外部条件（比如部署满七天后的复核），而新需求需要先做时，可以显式插队：

```text
/spec-guard:add-module … --interrupt
```

Codex 里用 `spec-guard-ops` 的 `add-module`，带同样的 `--interrupt` 参数。

- 预览会写明被暂停的模块及进度（`已勾 X/Y`），以及插入后的当前模块。新模块不会成为当前模块时
  （锚点在被暂停模块之后，或 `activeModule` 仍指向它），预览提示把 `.agent/state.json` 的 `activeModule` 改为新模块；
  命令本身仍只写 `spec/CAPABILITY-MAP.md`；
- 插入后，每轮阶段行都带 `Paused: …`，提醒被暂停的模块还没做完；
- 插队模块做完后，`MODULE_DONE` 会提示回到被暂停的模块，把 `activeModule` 改回它即可；
- 其他模块同时做到一半（并行推进）不影响插队；它们都会出现在 `Paused` 行里，插队模块做完后按 Build order 回到第一个被暂停的模块；
- 不带 `--interrupt` 时行为不变，当前模块做到一半仍然拒绝；当前模块没有做到一半时，`--interrupt` 不改变任何行为。

Proposal 路径同样适用。
晋级合并后，如果新模块没有成为当前模块，把 `activeModule` 改为它。

### Proposal（需要留痕时）

```text
提交（写草稿 → proposal-submit → 合进 main → 开 Issue）→ 接受（评审 → 改标签）
     → 晋级（add-module --proposal 插进能力图 → 合并）→ 收尾（证明 → 改标签）
```

| # | 步骤 | 谁来做 | 怎么做 |
|---|---|---|---|
| 1 | 提交 | agent + 命令 + 人 | agent 按[模板](../plugins/spec-guard/references/proposal-contract.md)写草稿 `spec/proposals/<id>.md`；运行 `/spec-guard:proposal-submit --draft spec/proposals/<id>.md --platform <github\|gitlab>` 预览，确认后加 `--confirm`，命令从远端 main 补全基线一节并算出 revision，只改这一份草稿；经 PR 把草稿合进 main（发布，只在本地或分支上都不算）；再用命令打印的现成命令开 Issue（标签 `proposal`、`proposal-stage:published`）。改了草稿，重跑一遍即可重算 revision |
| 2 | 接受 | 命令 + 人 | `/spec-guard:proposal-review` 报告 Proposal 是否新鲜、过期或被卡住；人把 Issue 标签改成 `proposal-stage:accepted`。接受只看这个标签加一次新鲜评审（基线未漂移、模块还不在能力图里、依赖齐全、锚点有效） |
| 3 | 晋级 | 人 + 命令 | 从预检给出的 `baseCommit` 开晋级分支，运行 `/spec-guard:add-module --proposal <id> --platform … --target …`（Codex 同等入口），预览确认后加 `--confirm` 写入能力图，提交并合并。`/spec-guard:proposal-promotion-preflight` 可作只读预览。命令会自检写入结果能通过收尾的证明；能力图里加上这一行就够了，Spec 与 Plan 之后按正常流程补 |
| 4 | 收尾 | 命令 + 人 | `/spec-guard:proposal-promotion-proof`：从 Proposal 的基线提交起沿远端默认分支找到第一个纳入该模块的提交，核对它与声明一致。证明为 `proved` 后，人把标签改成 `proposal-stage:promoted`；改成 promoted 之后重跑仍会得到 `proved` |

晋级之后，这个模块就和其他模块一样进入 Spec → Plan → Build。`proposal-submit` 只在 `--confirm` 时写草稿；评审、预检、证明只读；晋级命令只写能力图；Issue、标签、分支与提交都由人来改。

### Proposal 文档怎么写

由 agent 按[格式规范与草稿模板](../plugins/spec-guard/references/proposal-contract.md)写草稿。需要自己写的是：

- **Summary**：要解决什么问题，为什么它是一个独立模块；
- **Integration intent**：问题、范围内、范围外、安全边界、依赖假设、验收意图；
- **Change**：新模块的 id、职责、依赖，以及插入位置 `after:<某模块>` 或 `end`；
- **Tracker contract**：对应 Issue 的约定。

**Capability map baseline**（写作时远端 main 上能力图的版本和各模块的摘要）与首行标记里的 revision 由
`proposal-submit` 填写，不要手算；草稿里可以省略基线一节，revision 先写 64 个 `0`。

可以参考本仓库的实例 [`spec/proposals/local-ticket-ledger.md`](../spec/proposals/local-ticket-ledger.md)。

### 用 Proposal 之前的一次性准备

- 装好并登录 GitHub CLI（`gh`），GitLab 项目则是 `glab`。命令只读 Issue，不写。
- 远端默认分支上的能力图需要有 `## 目标` 一节。

## 能力图的规则

- **每个项目只有一张在用的能力图**，路径固定为 `spec/CAPABILITY-MAP.md`。阶段提示和产物校验都只认这一张。
- **新需求插进同一张图**：用快速插入或 Proposal，按锚点插到某个模块后面或追加到末尾，不再为新需求另开一张图。
- **和当前项目无关的独立产品**，另开一个项目，用它自己的能力图。
- **改 `## 目标` 要慎重**：这一节的摘要是 Proposal 评审的基准，改了会让所有已发布的 Proposal 判为过期。
  只是追加模块时不用改它。
- **旧版本留下的归档图**在 `spec/history/`，只读核验，见[可选能力](optional-features.md#能力历史)。

## 命令对照

Codex 不加载插件的斜杠命令，对应功能通过 skill 调用，用自然语言描述要做的事即可。

| 功能 | Claude Code | Codex |
|---|---|---|
| 安装或移除约定 | `/spec-guard:setup-convention`、`/spec-guard:teardown-convention` | `spec-guard-ops` skill 的 setup、teardown 一节 |
| 查看阶段、校验产物 | `/spec-guard:phase`、`/spec-guard:verify-artifacts` | `spec-guard-ops` skill |
| 快速插入新模块 | `/spec-guard:add-module` | `spec-guard-ops` skill 的 add-module 一节 |
| Proposal 提交、评审、预检、证明（晋级用 `add-module --proposal`） | `/spec-guard:proposal-submit`、`proposal-review`、`proposal-promotion-preflight`、`proposal-promotion-proof` | `spec-guard-ops` skill 的 proposal 一节 |
| 文档治理 | `/spec-guard:documentation-*` 三条命令 | `spec-guard-ops` skill |
| 能力历史（含审计与 `correct` 补正） | `/spec-guard:history-integrity` | `spec-guard-ops` skill 的 history 一节 |
| 协作信箱 | `/spec-guard:collaboration`、`collab` skill | `collab`、`collaboration-ops` skill |
| 本地事项 | `/spec-guard:local-ticket-ledger`、`/spec-guard:ticket` | `local-ticket-ledger-ops`、`ticket` skill |

## 移除

`/spec-guard:teardown-convention` 删掉 `CLAUDE.md` 里的约定块（标记之外不动），并把 `.agent/state.json` 改名为
`.agent/state.json.disabled`，阶段提示随之停止。能力图、Spec、Plan 都保留。先加 `--dry-run` 可以只看会改什么。
