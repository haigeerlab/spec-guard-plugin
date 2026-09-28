# 使用流程

这一页讲三件事：新项目怎么从零开始、项目做到一半来了新需求怎么走 Proposal、能力图有哪些规则。
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

### 阶段提示

| 阶段 | 意思 | 下一步 |
|---|---|---|
| `IDLE` | 还没有能力图 | 写能力图并人工评审 |
| `MAP_INVALID` | 能力图格式不对，比如 Build order 不是恰好一行 | 用 `/spec-guard:verify-artifacts` 查原因 |
| `MAP_ONLY` | 有能力图，还没有任何模块 Spec | 写第一个模块的 Spec |
| `NEEDS_SPEC` | 当前模块缺 Spec | 写 `spec/<模块>.md` |
| `NEEDS_PLAN` | 当前模块有 Spec、缺 Plan | 用 `/plan` 生成 plan 和 todo |
| `BUILDING` | todo 还有 N 项没勾 | 继续 `/build` |
| `DONE` | 当前模块或全部模块已完成 | 切到下一个模块；全部完成后，新需求走 Proposal |
| `UNKNOWN` | 阶段算不出来 | 用 `/spec-guard:verify-artifacts` 查原因 |

当前模块取 `.agent/state.json` 的 `activeModule`，没设置时按 Build order 取第一个没完成的模块。
随时想看完整状态，用 `/spec-guard:phase`。

## 已有项目：新需求走 Proposal

Proposal 只做一件事：**给已有的能力图新增一个独立模块**。修改、删除或调整已有模块的顺序都不走 Proposal，
直接改能力图并人工评审。

```text
写 Proposal → 合进 main（发布）→ 开 Issue → 评审 → 主链裁决 → 人工接受
     → 预检 → 人工晋级（插进能力图）→ 合并 → 证明已纳入
```

| # | 步骤 | 谁来做 | 怎么做 |
|---|---|---|---|
| 1 | 写 Proposal | 人或 agent | 写 `spec/proposals/<id>.md`，格式见下文 |
| 2 | 发布 | 人 | 合进远端 main。只在本地或只在分支上都不算发布 |
| 3 | 开 Issue | 人 | 在 GitHub 或 GitLab 开 Issue，正文放同一行身份标记，打上 `proposal` 和 `proposal-stage:published` |
| 4 | 评审 | 命令 | `/spec-guard:proposal-review`：报告 Proposal 是否新鲜、过期或被卡住 |
| 5 | 主链裁决 | 命令，在主链上运行 | 模块交付完的节点上运行 `/spec-guard:proposal-mainline-candidates` 看候选，再用 `/spec-guard:proposal-mainline-review` 给出结论。它只给结论，不会替你接受 |
| 6 | 人工接受 | 人 | 写入验收记录 `spec/proposal-acceptances/<id>-<revision>.json`，并把 Issue 标签改成 `proposal-stage:accepted` |
| 7 | 预检 | 命令 | `/spec-guard:proposal-promotion-preflight`：重读远端最新状态，确认可以晋级 |
| 8 | 晋级 | 人 | 开晋级分支，把新模块按锚点插进能力图，补上它的 Spec 和 Plan，然后合并 |
| 9 | 证明 | 命令 | `/spec-guard:proposal-promotion-proof`：核对新模块已按声明纳入。通过后，人工把标签改成 `proposal-stage:promoted` |

晋级之后，这个模块就和其他模块一样进入 Spec → Plan → Build。命令从头到尾只读：Issue、标签、分支、能力图都由人来改。

### Proposal 文档怎么写

目前**没有一键生成 Proposal 的命令**，由 agent 按[格式规范](../plugins/spec-guard/references/proposal-contract.md)手写。
文档包含：

- **Summary**：要解决什么问题，为什么它是一个独立模块；
- **Integration intent**：问题、范围内、范围外、安全边界、依赖假设、验收意图；
- **Capability map baseline**：写作时远端 main 上能力图的版本和各模块的摘要，用 `hooks/spec-digest.py` 计算。
  评审时据此判断能力图在 Proposal 写完后有没有被改过；
- **Change**：新模块的 id、职责、依赖，以及插入位置 `after:<某模块>` 或 `end`；
- **Tracker contract**：对应 Issue 的约定。

首行下面的身份标记带 revision，也就是文档内容的 SHA-256。内容改了要重新计算：

```bash
python3 -c "import sys; sys.path.insert(0, '<插件目录>/hooks'); import proposal_contract as c; print(c.compute_revision('spec/proposals/<id>.md'))"
```

可以参考本仓库的实例 [`spec/proposals/collaboration-messaging.md`](../spec/proposals/collaboration-messaging.md)。

### 用 Proposal 之前的一次性准备

- 装好并登录 GitHub CLI（`gh`），GitLab 项目则是 `glab`。命令只读 Issue，不写。
- 在远端 main 上放一份主链策略 `spec/proposal-mainline-policy.json`，并建一条受保护的主链分支，默认叫
  `integration/mainline`。主链要跟上 main：每次发布后把它快进到 main，否则主链裁决会报
  `mainline-review-commit-not-ancestor`。可以参考本仓库的[策略文件](../spec/proposal-mainline-policy.json)。

## 能力图的规则

- **每个项目只有一张在用的能力图**，路径固定为 `spec/CAPABILITY-MAP.md`。阶段提示和产物校验都只认这一张。
- **新需求插进同一张图**：按 Proposal 声明的锚点插到某个模块后面，或追加到末尾，不再为新需求另开一张图。
- **和当前项目无关的独立产品**，另开一个项目，用它自己的能力图。
- **改 `## 目标` 要慎重**：这一节的摘要是 Proposal 评审的基准，改了会让所有已发布的 Proposal 判为过期。
  只是追加模块时不用改它。
- **旧版本留下的归档图**在 `spec/history/`，只读核验，见[可选能力](optional-features.md#能力历史)。

## 命令对照

Codex 不加载插件的斜杠命令，对应功能通过 skill 调用，用自然语言描述要做的事即可。

| 功能 | Claude Code | Codex |
|---|---|---|
| 安装或移除约定 | `/spec-guard:setup-convention`、`/spec-guard:teardown-convention` | `spec-guard-ops` skill |
| 查看阶段、校验产物 | `/spec-guard:phase`、`/spec-guard:verify-artifacts` | `spec-guard-ops` skill |
| Proposal 评审、主链、预检、证明 | `/spec-guard:proposal-*` 五条命令 | `spec-guard-ops` skill 的 proposal 一节 |
| 文档治理 | `/spec-guard:documentation-*` 三条命令 | `spec-guard-ops` skill |
| 能力历史 | `/spec-guard:history-integrity` | `spec-guard-ops` skill |
| 协作信箱 | `/spec-guard:collaboration`、`collab` skill | `collab`、`collaboration-ops` skill |
| 本地事项 | `/spec-guard:local-ticket-ledger`、`/spec-guard:ticket` | `local-ticket-ledger-ops`、`ticket` skill |

## 移除

`/spec-guard:teardown-convention` 删掉 `CLAUDE.md` 里的约定块（标记之外不动），并把 `.agent/state.json` 改名为
`.agent/state.json.disabled`，阶段提示随之停止。能力图、Spec、Plan 都保留。先加 `--dry-run` 可以只看会改什么。
