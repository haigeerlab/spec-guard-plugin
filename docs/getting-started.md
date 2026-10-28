# 上手：走完第一个模块

这一页用一个虚构的小项目，从安装约定一路走到第一个模块验收通过，每一步都贴出 agent 收到的阶段提示，让你知道会发生什么、
哪些事要你来做。安装插件和前置条件见 [README](../README.md#快速开始)；每个阶段的含义见[使用流程](workflow.md#阶段提示)。

下面的输出取自 0.85.0，在一个临时项目里实际跑出来，只做了三处处理：「位置」一行里的路径换成了 `<项目目录>`；装了 delegate
插件时才出现的「外部审查」一行删掉了；到了停点时末尾附的停点规则原文（很长）用一句话代替。插件以后改了提示文字，以实际看到的为准。
例子的产物语言是 `zh-CN`，所以提示是中文；没设或设成别的语言时提示是英文。阶段名（`MAP_ONLY`、`BUILDING` 这些）在两种语言里都一样、
不翻译：`/spec-guard:map --json` 的 `stage` 字段用的也是这些名字，其他插件按它们读，中英文项目对照排查时也对得上。

## 先弄清：`/spec` 和能力图是什么关系

agent-skills 的 `/spec` 在需求能拆成几块时会先做 Phase 0：列出模块、职责、依赖和构建顺序，也就是能力图。上游给了能力图的模板，
但没定文件放哪、叫什么，还让模块 Spec 放在项目根、叫 `SPEC-<module>.md`（见[上游分析](upstream-analysis.md)）。spec-guard 把这些定死：

- 能力图固定是 `spec/CAPABILITY-MAP.md`，整个项目只有这一张；
- 里面恰好一张表头为 `Module id`、`Responsibility`、`Depends on` 的模块表，外加一行 `Build order: a → b → c`；
- 每个模块的 Spec 放 `spec/<模块 id>.md`，Plan 与 todo 放 `tasks/<模块 id>/`，不在项目根放 `SPEC*.md`。

setup 写进 `CLAUDE.md`／`AGENTS.md` 的[约定块](convention-block.md)会把这些告诉 agent，所以你照常用 `/spec`、`/plan`、`/build` 就行，
文件会落在上面这些位置。

Codex 里没有这些斜杠命令，用 `@` 直接调用它们背后的 skill（见 agent-skills 的 Codex 说明）：

| Claude Code | Codex |
|---|---|
| `/spec` | `@spec-driven-development` |
| `/plan` | `@planning-and-task-breakdown` |
| `/build` | `@incremental-implementation`（配合 `@test-driven-development`） |

也可以直接描述要做的事（例如「给 note-store 写 Plan」），让 Codex 自己选 skill。下文用 Claude Code 的写法。

## 例子：记事工具 note-app

一个给自己用的命令行记事工具，拆成三个模块：`note-store`（存储）→ `note-api`（搜索与排序）→ `note-cli`（命令行）。下面只走第一个模块。

### 1. 安装约定

Claude Code 里运行 `/spec-guard:setup-convention`，看过预览后确认；Codex 里对 agent 说「用 spec-guard-ops 在这个项目里安装约定」。
写入后的输出：

```text
═══ Spec Guard local convention ═══
  ✅ created .agent/state.json (local only)
  ✅ created spec/CAPABILITY-MAP.md
  ✅ updated CLAUDE.md
Next: review the capability map, then write module specs and local task lists.
Optional: set the artifact language with /spec-guard:config (Codex: spec-guard-ops config).
Review cadence: `separate` (default) reviews the Spec, then the Plan, one approval each -- for work with many decisions or high risk;
  `combined` presents the Spec and the Plan together for one approval -- for small, fast steps. Set it with the same config command.
```

之后对 agent 说任何一句话，它都会在上下文开头收到阶段提示。刚装好时能力图还是模板（里面有 `example-a`、`example-b` 两个示例模块），
所以阶段已经是 `MAP_ONLY`：

```text
## spec-guard local workflow

位置: 分支 `main` · worktree `<项目目录>`。请用户审阅或确认时，向用户说明这个位置。

当前阶段: **MAP_ONLY**

- 能力图: 已有
- 模块 Spec: 没有
- 产物语言: `zh-CN` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。

建议下一步: 先跟用户确认第一个模块的需求已说完，再在 `spec/` 下写第一份模块 Spec 并交审。

停点规则（Spec 交审）：……（这里附上停点规则里「Spec 交审」一节的原文，此处省略）
```

### 2. 写能力图并审阅

你说出需求，agent 先总结一遍、问你说完没有；你确认后，它用 `/spec` 写能力图交给你审阅。例子的能力图：

```markdown
# Capability Map: note-app

## 目标

一个本地记事工具：在命令行里记下、列出和搜索笔记，数据存在本机文件里，给自己用。

## 模块

| Module id | Responsibility | Depends on |
|---|---|---|
| note-store | 把笔记存成本机 JSON 文件，提供增、查、列出 | — |
| note-api | 在存储之上提供按关键字搜索与按时间排序 | note-store |
| note-cli | 命令行入口：`note add`、`note list`、`note find` | note-api |

Build order: note-store → note-api → note-cli
```

你批准后，agent 在 `.agent/state.json` 里把 `activeModule` 设为第一个模块 `note-store`。这时跑 `/spec-guard:verify-artifacts`：

```text
✅ 能力图存在
  ✅ 没有根目录 spec 漂移
  ✅ 能力图通过严格解析
  ✅ 项目配置有效

结果: 4 通过 · 0 警告 · 0 失败
```

### 3. 写第一个模块的 Spec 并交审

agent 写 `spec/note-store.md`，验收标准按 AC1、AC2… 编号，并在文件里标一行 `<!-- spec-guard: review pending -->`（待批准）：

```markdown
# Spec: note-store

<!-- spec-guard: review pending -->

## 目标

把笔记存成本机的一个 JSON 文件，给上层模块提供增加、按 id 读取、列出全部三种操作。

## 边界

- 总是做：写文件前先写临时文件再改名，避免写到一半损坏。
- 先问：要改存储格式时。
- 不做：搜索与排序（归 note-api）、命令行（归 note-cli）、多机同步。

## 假设

1. 数据文件放在 `~/.note-app/notes.json`，单用户使用。
2. 笔记 id 用递增整数。

## 验收标准

- AC1：`add(text)` 返回新笔记的 id，再次启动后仍能读到。
- AC2：`get(id)` 读不存在的 id 时返回空，不抛异常。
- AC3：`list()` 按创建顺序返回全部笔记。
- AC4：写入中途中断时，原文件内容不损坏。

## 变更记录
```

Spec 文件一出现，阶段就算到了 `NEEDS_PLAN`；但它还待批准，阶段提示会让 agent 先停下等你：

```text
## spec-guard local workflow

位置: 分支 `main` · worktree `<项目目录>`。请用户审阅或确认时，向用户说明这个位置。

当前阶段: **NEEDS_PLAN**

- 能力图: 已有
- 当前模块: `note-store`（activeModule）
- 模块 3 · Spec 1 · Plan 0 · 进行中 0 · 已完成 0
- 批准: Spec `spec/note-store.md` 正在等用户批准。
- 产物语言: `zh-CN` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。

建议下一步: 等用户审阅 `spec/note-store.md`；先不要写 Plan。用户批准后，用 `/spec-guard:review-mark` (Codex: spec-guard-ops review-mark) 记下来。

停点规则（Spec 交审）：……（这里附上停点规则里「Spec 交审」一节的原文，此处省略）
```

agent 会在对话里把目标、边界、假设、验收标准逐项摆给你看，推荐的答复放在一个可复制的代码块里。下面是一段**示意**（不是实跑输出），
按停点规则「Spec 交审」的小项与顺序写成：

````markdown
## Spec 交审：spec/note-store.md

**目标**：把笔记存成本机的一个 JSON 文件，给上层模块提供增加、按 id 读取、列出全部三种操作。

**边界**
- 总是做：写文件前先写临时文件再改名，避免写到一半损坏。
- 先问：要改存储格式时。
- 不做：搜索与排序（归 note-api）、命令行（归 note-cli）、多机同步。

**要你确认的假设**
1. 数据文件放在 `~/.note-app/notes.json`，单用户使用。
2. 笔记 id 用递增整数。

**验收标准**
- AC1：`add(text)` 返回新笔记的 id，再次启动后仍能读到。
- AC2：`get(id)` 读不存在的 id 时返回空，不抛异常。
- AC3：`list()` 按创建顺序返回全部笔记。
- AC4：写入中途中断时，原文件内容不损坏。

注意：无。

批了会怎样：先把 Spec 记为已批准，再写 Plan 交审；Plan 批准之前不写代码。

推荐理由：范围小、边界清楚，可以直接批。

```
批准
```
````

### 4. 你批准 Spec

你回复「批准」（什么话算批准，见[使用流程](workflow.md#检查点交审与批准)里的「什么算批准」），agent 用 `/spec-guard:review-mark` 把标记改成已批准（先给你看预览）。阶段提示转为让它写 Plan：

```text
## spec-guard local workflow

位置: 分支 `main` · worktree `<项目目录>`。请用户审阅或确认时，向用户说明这个位置。

当前阶段: **NEEDS_PLAN**

- 能力图: 已有
- 当前模块: `note-store`（activeModule）
- 模块 3 · Spec 1 · Plan 0 · 进行中 0 · 已完成 0
- 产物语言: `zh-CN` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。

建议下一步: 写 `tasks/note-store/plan.md` 和 `tasks/note-store/todo.md`（例如用 `/plan`）。

停点规则（Plan 交审）：……（这里附上停点规则里「Plan 交审」一节的原文，此处省略）
```

### 5. 写 Plan 与 todo 并交审

`/plan` 生成 `tasks/note-store/plan.md` 与 `todo.md`。检查点标 `report`（把结果记进 todo 后直接继续）或 `gate`（停下等你），
最后一个检查点是最终验收：

```markdown
# Plan: note-store

<!-- spec-guard: review pending -->

依据 `spec/note-store.md`。

## Task List

### Task 1：读写 JSON 文件（AC1、AC3）
- 验证：单元测试先红后绿。

### Task 2：按 id 读取（AC2）
- 验证：单元测试覆盖不存在的 id。

### Checkpoint 1（report）：跑全部单元测试
- 结果记入 todo，直接继续。

### Task 3：临时文件加改名的安全写入（AC4）
- 验证：模拟中途中断，原文件不变。

### Checkpoint 2（gate）：最终验收
- 逐条给 AC 证据、改动文件与提交；你批准后才算完成。
```

```markdown
# Todo: note-store

- [ ] Task 1：读写 JSON 文件（AC1、AC3）
- [ ] Task 2：按 id 读取（AC2）
- [ ] Checkpoint 1（report）：跑全部单元测试
- [ ] Task 3：临时文件加改名的安全写入（AC4）
- [ ] Checkpoint 2（gate）：最终验收
```

todo 一出现，阶段就是 `BUILDING`；但 Plan 还待批准，阶段提示让 agent 先等：

```text
## spec-guard local workflow

位置: 分支 `main` · worktree `<项目目录>`。请用户审阅或确认时，向用户说明这个位置。

当前阶段: **BUILDING**

- 能力图: 已有
- 当前模块: `note-store`（activeModule）
- 模块 3 · Spec 1 · Plan 1 · 进行中 1 · 已完成 0
- 批准: Plan `tasks/note-store/plan.md` 正在等用户批准。
- 产物语言: `zh-CN` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。

建议下一步: 等用户审阅 `tasks/note-store/plan.md`；不要继续构建。用户批准后，用 `/spec-guard:review-mark` (Codex: spec-guard-ops review-mark) 记下来。

停点规则（Plan 交审）：……（这里附上停点规则里「Plan 交审」一节的原文，此处省略）
```

### 6. 你批准 Plan，agent 开始实现

批准 Plan 就授权了范围内的常规操作（改仓库文件、跑测试与构建、本地提交、构建需要的装包），不再逐次问你。阶段提示写出下一个
要停下的检查点：

```text
## spec-guard local workflow

位置: 分支 `main` · worktree `<项目目录>`。请用户审阅或确认时，向用户说明这个位置。

当前阶段: **BUILDING**

- 能力图: 已有
- 当前模块: `note-store`（activeModule）
- 模块 3 · Spec 1 · Plan 1 · 进行中 1 · 已完成 0
- 下一个 gate: Checkpoint 2（gate）：最终验收 — 一直做到它为止；`report` 检查点记进 todo 后直接通过，不停下。
- 产物语言: `zh-CN` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。

建议下一步: 继续用 `/build` 构建 `note-store`：`tasks/note-store/todo.md` 里还有 5 个未勾选项。

<!-- spec-guard-state: 776626c9 -->
```

`Checkpoint 1（report）` 不会停下：agent 把测试结果记进 todo 就继续。

末尾那行 `<!-- spec-guard-state: … -->` 是状态码：下一轮状态没变时，hook 只给一行，不再重复整段：

```text
spec-guard: BUILDING · `note-store` · 未勾选 5 · 分支 `main`（状态未变，完整说明见此前的阶段提示） <!-- spec-guard-state: 776626c9 -->
```

随时想看完整内容，运行 `/spec-guard:phase`。

### 7. 最终验收

前面的任务都勾完后，只剩最终验收这一项。阶段提示附上「最终验收」的停点规则，agent 停下来，把逐条 AC 的证据、改动文件表和提交表
摆给你：

```text
## spec-guard local workflow

位置: 分支 `main` · worktree `<项目目录>`。请用户审阅或确认时，向用户说明这个位置。

当前阶段: **BUILDING**

- 能力图: 已有
- 当前模块: `note-store`（activeModule）
- 模块 3 · Spec 1 · Plan 1 · 进行中 1 · 已完成 0
- 下一个 gate: Checkpoint 2（gate）：最终验收 — 一直做到它为止；`report` 检查点记进 todo 后直接通过，不停下。
- 产物语言: `zh-CN` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。

建议下一步: 继续用 `/build` 构建 `note-store`：`tasks/note-store/todo.md` 里还有 1 个未勾选项。

停点规则（最终验收）：……（这里附上停点规则里「最终验收」一节的原文，此处省略）
```

### 8. 你批准验收，模块完成

agent 勾上最后一项并提交，阶段变为 `MODULE_DONE`：

```text
## spec-guard local workflow

位置: 分支 `main` · worktree `<项目目录>`。请用户审阅或确认时，向用户说明这个位置。

当前阶段: **MODULE_DONE**

- 能力图: 已有
- 当前模块: `note-store`（activeModule）
- 模块 3 · Spec 1 · Plan 1 · 进行中 0 · 已完成 1
- 产物语言: `zh-CN` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。

建议下一步: `note-store` 已完成；Build order 中下一个未完成的模块是 `note-api`（NEEDS_SPEC）。开始构建前把 activeModule 设为它。

<!-- spec-guard-state: 39a9b8f9 -->
```

这时 `/spec-guard:map` 的进度表：

```text
Capability Map: note-app · 3 个模块 · ✅ 1 🔨 0 ⏸ 0 ⛔ 0 🟢 1 ○ 1 · 2026-10-28 11:46
关键卡点：无
待批准：无
未合入主线：判断不了；未推送：判断不了

| 位 | 模块 | 作用 | 状态 | 审查 |
|---|---|---|---|---|
| 1 | note-store | 把笔记存成本机 JSON 文件，提供增、查、列出 | ✅ 已完成 | Spec ✔ Plan ✔ |
| 2 | note-api | 在存储之上提供按关键字搜索与按时间排序 | 🟢 可以开始 | — |
| 3 | 1 个未就绪 | | ○ | |
```

图例（✅ 已完成、🔨 进行中、⏸ 挂起、⛔ 阻塞、🟢 可以开始、○ 未就绪）见[命令参考](commands.md#spec-guardmap)。已完成与未就绪的模块默认折叠，
所以 `note-cli` 只显示成「1 个未就绪」；加 `--all` 全部展开。表头的「判断不了」是因为这个临时项目没有远端，
分支也没有上游；推送过、设了上游之后，会写出未合入主线与未推送的提交数。

### 9. 进入下一个模块

验收获批后，agent 把 `activeModule` 改成 `note-api`，接着写它的 Spec，不再停下问「要不要开始」：

```text
## spec-guard local workflow

位置: 分支 `main` · worktree `<项目目录>`。请用户审阅或确认时，向用户说明这个位置。

当前阶段: **NEEDS_SPEC**

- 能力图: 已有
- 当前模块: `note-api`（activeModule）
- 模块 3 · Spec 1 · Plan 1 · 进行中 0 · 已完成 1
- 产物语言: `zh-CN` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。

建议下一步: 写 `spec/note-api.md` 并交审。

停点规则（Spec 交审）：……（这里附上停点规则里「Spec 交审」一节的原文，此处省略）
```

之后的模块照第 3～8 步重复。

## 你做什么，agent 自动做什么

| 事情 | 谁来做 | 你要输入命令吗 |
|---|---|---|
| 在项目里安装约定 | 你（或让 agent 跑） | 是：`/spec-guard:setup-convention`，Codex 说「用 spec-guard-ops 在这个项目里安装约定」 |
| 确认需求说完 | agent 总结，你确认 | 否，回复「说完了」或补充 |
| 批准能力图、Spec、Plan | 你 | 否，回复交审消息里推荐的那句话；「继续」不算批准 |
| 标「待批准」、批准后写「已批准」标记 | agent（`/spec-guard:review-mark`） | 否 |
| 勾 todo | agent，每做完一项勾一项 | 否 |
| 切换 `activeModule` | agent，按阶段提示改 | 否 |
| 已批准的文件被改时记「变更记录」 | agent，再交你复审 | 否 |
| 最终验收 | agent 列证据，你批准 | 否，回复「验收通过」这类明确的话 |
| 推送、开 PR | agent，只在 Plan 的 `gate` 写明授权时 | 否 |
| 合并 | 你 | 是，在 GitHub／GitLab 上合并 |
| 回告提需求的人 | agent 拟好文字，你批准后发 | 否 |
| 记下「有人在等的事」（启用了本地事项账本时） | agent，收到就记，不先问你 | 否；要不要做仍由你定 |

## 可选能力：什么时候开

| 能力 | 该开 | 别开 | 怎么开 |
|---|---|---|---|
| Proposal | 要在 Issue 上留下「谁审查、谁接受了这个新模块」的记录。判断方法：事后有人会问「这个模块是谁批准加的」吗？例如需求是别的团队提的、要能查到是谁在 Issue 上接受的；或者一个新模块要几位维护者都点头 | 新项目（还没有能力图）；自己或小团队的项目、需求已经理顺，没人需要事后查批准记录——用快速插入，一次预览、一次确认就够了 | 登录 `gh`／`glab`，按[使用流程](workflow.md#proposal需要留痕时)的四步走 |
| 本地事项账本 | 没有 GitHub/GitLab Issue 可用，想在本地记 bug 和需求；想让「有人在等的事」在会话清空后还找得回 | 已经在用 GitHub/GitLab Issue；不在 macOS 上 | `/spec-guard:local-ticket-ledger`，需要 macOS 与 Node.js 18+，见[可选能力](optional-features.md#本地事项账本) |
| 多模块并行 | 模块多、彼此独立，想让几个会话同时各做一个 | 模块依赖成一条链；团队里还有人用 0.68.0 以前的版本 | `/spec-guard:config` 把 `moduleConcurrency` 设为 `on`；开会话、建 worktree、合并这些运行层的事归 module-crew，见 [README](../README.md#多模块并行可选) |
| 文档治理 | 需求文档、架构文档或使用手册本身也是交付物、也要审查。判断方法：改一个功能时，是不是必须同步改某份文档、并让人审过它？例如项目有对外的 API 文档或使用手册，每次改功能都要跟着改；或者需求文档是验收的依据 | 文档只是代码的附带说明：只有 README 和代码注释，没人单独审文档 | `/spec-guard:documentation-baseline` 建 `docs/DOCUMENTATION-BASELINE.md`，见[可选能力](optional-features.md#文档治理) |
| 项目指向 | 会话开在需求文档之类的目录，实际改的是别处的仓库 | 能直接在项目目录里开会话 | `/spec-guard:link-project set --project <路径>` |
| 挂起 | 已开工的模块剩下的都在等外部条件（例如上线后观察一周），想先做别的 | 模块还没开工（直接调整 Build order 或用 `add-module --interrupt` 插队） | `/spec-guard:module-suspend --suspend <模块> --reason "<原因>"` |

## 只用 agent-skills、不装 spec-guard 会碰到什么

- 几个模块共用一份 `tasks/plan.md` 和 `todo.md`。上游 0.6.8 起，`/plan` 发现还有没勾完的任务时会停下来问，不会静默覆盖，但它仍然没有
  模块的概念：要么每次被打断确认，要么靠你记住哪份计划属于哪个模块。
- 每轮对话 agent 都要重新摸索现在做到哪个模块、哪一步，没有人告诉它。
- 做到一半冒出的新需求没有固定的地方登记，也没有校验它该插在哪、依赖对不对。

项目只有一个模块、或者只是一次性的小改动时，这些都不是问题，用 agent-skills 自带的单 Spec 流程就够了。设计理由见[设计理念与术语](concepts.md)。
