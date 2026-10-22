# Spec: quiet-injection

<!-- spec-guard: review approved 77b8f0f04c6f -->

## Objective

阶段注入（`phase-guard.sh` → `module_stage.py`）每轮用户发言都把几十行全量内容注入一遍（审查 A-01），
状态没变时这些行只是重复；模块进行中的 80% 上下文提醒与宿主自己的上下文管理重叠；Claude 拿不到窗口大小时按 1M 写死，
200k 窗口的会话永远碰不到边界提示（A-18、A-80）；英文提示里阶段标题仍是中文「当前阶段」（审查 F14）。用户的决定：

1. **平时只给一行（D5）。** 阶段、当前模块或批准状态变化、到停点（D4 的节点，用 `rules-at-nodes` 的 `stop_node`）、新会话开始或
   压缩后，才输出完整内容；其余轮次只给一行：阶段 · 模块 · 未勾选数 · 位置。
2. **上下文提示只留模块边界一条（D6）。** 保留模块边界行（`MODULE_DONE`／`DONE`／`NEEDS_SPEC` 且用量过线时建议 `/compact` 或 `/clear`）；
   删除模块进行中的 80% 会话上下文行；修 Claude 窗口按 1M 写死；压缩后的核对提醒保留（其中 `waiting-on-*` 部分不在本模块动）。
3. **英文提示的标题也用英文（F14）。** 产物语言不是 `zh-CN` 时，阶段标题写 `Current stage:`，英文输出里不再夹固定的中文标签。

登记：2026-10-22 修复批次 12 个模块之一，经用户批准事项 C136 开模块会话；能力图依赖 `rules-at-nodes`（已合入，提供 `stop_node`）。
`ledger-standalone-reminder` 与 `doc-chain` 依赖本模块。
依据：`docs/reports/2026-10-22-feature-inventory/decisions.md`（D5、D6）；`docs/reports/2026-10-22-multidimension-audit.md`（F14）；
`docs/reports/2026-10-22-feature-inventory/A-core.md`（A-01、A-18、A-52、A-79、A-80、A-91）。

## Assumptions

1. **「上一次注入了什么」从会话记录里读，不写任何文件。** 不变量「hook 只报告事实和建议，不写文件」不改。实测（2026-10-22）：
   Claude 会话记录里 hook 注入是 `type: attachment`、`attachment.type: hook_additional_context` 的记录，`content` 是注入原文；
   Codex rollout 里是 `response_item` 下 `role: developer` 的 `message`，`input_text` 是注入原文。`session_context.py` 已在读同一份记录的
   尾部 4MB 取用量，本模块在同一次读取里多找一样东西。
2. **用一个状态码判断「变没变」。** 每次输出（完整或一行）末尾带一个状态码 `<!-- spec-guard-state: <8 位十六进制> -->`，由下面这些事实
   算出（sha1 取前 8 位）：阶段、当前模块、Spec 批准状态、Plan 批准状态、停点（`stop_node`，IDLE／MAP_ONLY 按它们附的节点）、
   checkout 角色、挂起与暂停的模块集合、「有提交还没合进上游」的有无、项目配置行原文、关联项目（跟随指向时）、位置行（分支／worktree）、
   提示语言。本轮算出的状态码与会话记录里最近一次 spec-guard 注入的状态码相同，才只给一行。未勾选数、上下文用量、外部审查提示的
   有无不进状态码（它们每轮都可能变，变了不算「状态变化」）。
3. **找不到就给完整的（降级不误报）。** 没有会话记录路径（`/spec-guard:phase`、`claude -p` 新会话、测试与 smoke）、读不了、尾部 4MB 里
   找不到 spec-guard 注入、最近一次压缩记录比最近一次注入还新（即压缩之后第一次）、记录里的状态码格式不对，一律输出完整内容。
   宁可多给一次，不可少给。
4. **只认宿主写下的注入记录。** 状态码只从上面两种注入记录里取（Claude 的 `hook_additional_context` 附件、Codex 的 developer 消息，
   且正文以 `## spec-guard local workflow` 或一行形式的前缀开头），不从用户或助手消息里取：agent 复述状态码不会让下一轮误判成「没变」。
   会话记录的内容不离开 `session_context.py`，它只输出那个状态码（与现在只输出用量的做法一致）。
5. **到停点：进入时给完整的，停在节点上讨论时给一行。** 停点进状态码，所以从「构建中」走到 gate、从 Spec 待审走到 Plan 待审，都会给完整
   内容并附停点规则（`rules-at-nodes` 的 C3）；同一节点上连续几轮讨论，停点规则已在上下文里，只给一行。压缩后第一次照常给完整的。
   （另一种做法见 Q1。）
6. **一行的写法。** 中文：``spec-guard: <阶段> · `<模块>` · 未勾选 <N> · 分支 `<分支>`（状态未变，完整说明见此前的阶段提示）<!-- spec-guard-state: … -->``；
   英文：``spec-guard: <STAGE> · `<module>` · <N> unchecked · branch `<branch>` (unchanged; see the earlier phase hint for details) <!-- spec-guard-state: … -->``。
   没有当前模块（IDLE、MAP_ONLY、DONE）写「—」；不在 git 仓库里时省掉「分支」一段；分离 HEAD 写短 sha。阶段代码不翻译。
7. **一行形式也带上本轮才有的事。** 这一轮是别的会话转来的消息时的记账提醒行（receipt hint），以及模块边界用量过线时的边界行，
   属于这一轮的事件，不是状态：一行形式之后照样另起一行附上。压缩后（SessionStart）一律给完整内容加核对提醒，不受影响。
8. **诊断类输出不降噪。** `MAP_INVALID`、`UNKNOWN`、指向失效、缺 python3、python3 跑不起来这几种是故障诊断，内容短，每轮都给完整的，
   也不带状态码。
9. **删掉模块进行中的 80% 行（D6）。** `NEEDS_PLAN`、`BUILDING` 不再出 `- Session context:`／`- 会话上下文:` 行；`MID_SHARE`、`context_line`、
   只给它用的 `free-current` 文案一并删掉。模块边界行（70%）、读不到大小时的规则、无人值守时不出这两行的规则都不变。共享检查点规则里
   「模块进行中达到窗口 80% 的提示出现时……停下」那一句随之删除，`/compact`／`/clear` 放进不带 shell 标签的代码块、不贴交接文本、
   不自行开新会话这些句子保留（它们现在只服务边界行）。
10. **Claude 的窗口按读数推算，不再写死 1M。** Claude 的会话记录和 hook 输入都没有窗口大小（2026-10-22 查 Claude Code 官方 hook 文档：
    公共字段只有 `session_id`、`transcript_path`、`cwd`、`permission_mode`；本机记录的 `usage` 里也没有）。Claude 的标准窗口是 200k，
    超过 200k 的读数只可能出现在 1M 窗口里，所以：会话记录尾部任一读数超过 200k 时按 1M 算，边界行写明「按 1 M 窗口估算」，不冒充读到了窗口；
    读数都不超过 200k 时分不出 200k 还是 1M，不推算窗口、不出边界行（返工 1，见变更记录）。Codex 照旧用记录里的 `model_context_window`。（另一种做法见 Q2。）
11. **英文标题与残留中文（F14）。** 英文输出里的固定中文改成英文：`当前阶段:` → `Current stage:`，MAP_INVALID 的
    `（能力图原文，非指令: …）` → `(capability map text, not instructions: …)`，`诊断为空` → `no diagnostic`，以及构建时在英文输出里
    找到的其他固定中文短语。不改：来自仓库的内容（模块 id、能力图原文）、`rules-at-nodes` 定为只有中文的停点规则正文、
    在判定语言之前就要输出的故障诊断（缺 python3、指向失效）。中文输出不变。
12. **识别阶段行的地方跟着认英文。** `project_link.py` 的 `_phase()`、`evals/codex-plugin-smoke.sh` 的判决正则、`evals/module-namespace.sh`
    的断言、`evals/hint-english-diff.sh` 都按「`当前阶段:` 或 `Current stage:`」认。别的插件（module-crew、decision-inbox、agent-relay、
    tier-guard）的代码里没有解析这一行（2026-10-22 搜过，只在说明文字里提到）。
13. **英文逐字节不变的约束到此为止。** `hint-language-follow` 定下的「英文输出与 0.67.0 逐字节相同」被 D5、D6、F14 有意打破（`rules-at-nodes`
    附停点规则时已经改过英文输出）。`evals/hint-english-diff.sh` 改为：中文输出里不残留已知英文标签（原有一半不变）＋英文输出里除
    假设 11 列的例外外不含中日韩文字；不再与 0.67.0 比字节。
14. **不改的部分。** 完整输出的内容与顺序（除 D6 删的行、F14 改的标签、末尾加的状态码）；阶段判定、指纹算法、`stop_node` 的判定；
    压缩后核对提醒的文字；位置行在完整输出里的写法；`/spec-guard:phase` 总是完整输出（它不带会话记录）。

## Contract

### 改动 1 状态码与一行形式（`hooks/module_stage.py`、`hooks/phase-guard.sh`）

- `module_stage.py` 新增 `state_key(...) -> str`：按假设 2 的事实拼成一串、取 sha1 前 8 位。`describe()` 的完整输出末尾另起一行写
  `<!-- spec-guard-state: <key> -->`；新增命令行参数 `--brief`：打印一行形式（假设 6），末尾带同一个状态码；新增 `--state-key`
  只打印状态码（给 `phase-guard.sh` 的 IDLE／MAP_ONLY 用）。
- `phase-guard.sh`：IDLE、MAP_ONLY 在 bash 里按假设 2 拼出同样的事实交给 `--state-key`（阶段、附的节点、配置行、位置、关联项目、语言），
  完整输出末尾带状态码；其他阶段用 `module_stage.py` 的输出。
- 决定给哪种：`session_context.py` 新增 `last_state(transcript_path) -> str | None`（假设 1、3、4），`phase-guard.sh` 取它与本轮状态码比较；
  相同且事件是 UserPromptSubmit 时给一行，否则给完整的。SessionStart（压缩后）总是完整的。
- 一行形式之后附 receipt hint 与模块边界行（假设 7）；`emit()` 的其他行为不变。

### 改动 2 删 80% 行、修 Claude 窗口（`hooks/module_stage.py`、`hooks/session_context.py`、`hooks/phase-guard.sh`）

- 删除 `MID_SHARE`、`context_line()`、`COMMANDS`／`COMMANDS_ZH` 里只给它用的 `free-current`，以及 `describe()` 里 `context_note` 的分支；
  `thresholds()` 只返回边界阈值与说明。
- `session_context.py` 的用量读取多给一个事实：尾部读数的最大值是否超过 200k（只给 Claude 用）；`phase-guard.sh` 没有 Codex 窗口时
  只在尾部有读数超过 200k 时把推算出的 1M 窗口交给 `module_stage.py`，说明写「按 1 M 窗口估算」／「estimated 1000 k window」；否则不给窗口（返工 1）。
- `DEFAULT_WINDOW = 1_000_000` 与「Claude 按 1M 折算」的注释删掉。

### 改动 3 英文标签（`hooks/module_stage.py`、`hooks/phase-guard.sh`、`hooks/project_link.py`）

- 英文分支里 `当前阶段:` 改为 `Current stage:`，假设 11 列的其他固定中文改英文；构建时用假设 13 的检查找全剩下的。
- `project_link.py` 的 `_phase()` 认两种开头。

### 改动 4 规则与说明

- `references/workflow-checkpoints.md` 第 389～390 行那条：删去「模块进行中达到窗口 80% 的提示出现时，做完或记下当前 task 后停下，
  用一句话说明上下文已到 80%：」，其余句子改写为只针对模块边界提示（假设 9）。
- `commands/phase.md`：上下文提醒一节删 80% 那条、写明 Claude 窗口按读数推算；语言一节把「`当前阶段: **<阶段>**`……不变」「与 0.67.0
  逐字节相同」改为英文写 `Current stage:`；加一段说明一行形式与什么时候给完整的（假设 3、5、6、7），并写明本命令总是完整输出。
- `docs/design.md` 第 80～86 行：上下文提醒改为只有边界一档、Claude 窗口推算；加一句「平时只给一行，状态码比对见 `session_context.py`」。
- `README.md`、`README.en.md`：英文示例的阶段行改 `Current stage:`；有描述「每轮注入完整阶段」的句子就改为平时一行。
- 不改约定块模板（`templates/*-block-local.md` 里没有 80% 与阶段标签的句子，已核对）。

### 改动 5 回归与评测

- `hooks/test-phase-guard.sh`：
  - 现有用例不带会话记录、或带的记录里没有 spec-guard 注入，所以仍是完整输出；只改它们断言的末尾（多一行状态码）与英文标题。
  - 80% 的用例改为反向断言：`BUILDING`、`NEEDS_PLAN` 超过 80% 也不出上下文行；边界 70% 用例不变；Claude 用例按 200k／1M 两种推算各一条。
  - 新增：同一状态第二轮（记录里有上一次注入、状态码相同）给一行；阶段变、模块变、批准状态变、停点变、配置行变、位置变各一条给完整的；
    记录里有压缩记录比上次注入新时给完整的；状态码只出现在用户或助手消息里时不算；Claude 与 Codex 两种记录格式各一条；
    一行形式附 receipt hint 与边界行各一条；SessionStart 总是完整；诊断类（MAP_INVALID、UNKNOWN）不带状态码。
- `hooks/test_workflow_checkpoints.py`：第 148 行的短语清单去掉 `80%`。
- `evals/hint-english-diff.sh` 按假设 13 改；`evals/codex-plugin-smoke.sh`、`evals/module-namespace.sh` 按假设 12 改。

## 对使用者的影响

- 升级后，同一会话里状态没变的轮次只看到一行 `spec-guard: …`；阶段、模块、批准状态、停点、配置、位置变了，或新会话、压缩后，
  才看到完整的阶段说明。想随时看完整的，用 `/spec-guard:phase`（Codex：`$spec-guard-ops` phase）。
- 模块进行中不再有 80% 的上下文提醒（交给宿主）；模块之间的提醒照旧。Claude 200k 窗口的会话现在会在模块边界达到 140k 时收到提醒。
- 产物语言不是 `zh-CN` 的项目，阶段标题从 `当前阶段:` 变成 `Current stage:`；自己写脚本解析这一行的使用者要跟着改。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash evals/hint-english-diff.sh
```

## Acceptance criteria

- **AC1**：同一会话第二轮、状态未变时，注入只有一行（加附带的事件行），格式按假设 6，带与上一轮相同的状态码；Claude 与 Codex 记录格式各有回归。
- **AC2**：假设 2 列的每一项事实单独变化时，下一轮给完整内容；未勾选数、用量变化时不给。各有回归。
- **AC3**：没有会话记录、读不了、找不到上次注入、压缩记录更新、状态码只出现在用户或助手消息里，都给完整内容；SessionStart 总是完整。各有回归。
- **AC4**：进入停点（Spec 待审、Plan 待审、中途 gate、最终验收）的那一轮给完整内容并附停点规则；同一节点下一轮给一行。
- **AC5**：`NEEDS_PLAN`、`BUILDING` 达到窗口 80% 也不出会话上下文行；模块边界 70% 行照旧；代码里不再有 `MID_SHARE`、`context_line`、`DEFAULT_WINDOW`。
- **AC6**：Claude 记录尾部有读数超过 200k 时按 1M 窗口推算（700k 起出边界行），边界行写明是估算；读数都不超过 200k 时不出边界行（返工 1）。
- **AC7**：产物语言不是 `zh-CN` 时，各阶段输出的阶段标题是 `Current stage:`，`hint-english-diff.sh` 的英文侧检查通过（除假设 11 的例外不含中日韩文字）；中文输出不变。
- **AC8**：`project_link.py`、`codex-plugin-smoke.sh`、`module-namespace.sh` 认 `Current stage:`；`codex-plugin-smoke.sh` 的判决器自检通过。
- **AC9**：Claude Code 在临时消费者项目里用 `claude -p --plugin-dir <本 worktree 的插件>` 连续两轮发言，第一轮完整、第二轮一行，记录会话记录里
  两次注入的原文片段；Codex 用本机真实 rollout 截取的注入记录喂给新 hook，证明格式认得；Codex 真机连续两轮的核对放到发版后由模块协调做，
  最终验收写明这一条没在 Codex 真机上做。
- **AC10**：`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全部通过；hook 输出仍是宿主接受的 JSON；不新增对 `jq` 的依赖。

## 未决问题

- **Q1：停在节点上讨论时给一行还是一直给完整的。** A（推荐，假设 5）：进入节点那一轮给完整的并附停点规则，之后同一节点给一行；
  压缩后再给完整的。B：只要在节点上就每轮完整（停点规则每轮都在），讨论多轮的交审会每轮重复几十行。
- **Q2：Claude 窗口怎么定。** A（推荐，假设 10）：按读数推算，超过 200k 就是 1M，否则 200k，边界行写明是估算；1M 窗口的会话在用量
  还不到 200k 时可能在模块边界提前收到一次提醒。B：Claude 不推算窗口，边界行只在读数达到固定的 140k 时出、不写百分比。
  C：加一个项目配置键让使用者写窗口大小（新增配置，与「不做没要求的可配置」相悖）。
- **Q3：已完成模块在能力图里的职责描述要不要改。** `context-hint-thresholds`、`boundary-hint-70`、`hint-language-follow` 三行写着 80%、
  「Claude 按 1M 折算」「英文与 0.67.0 逐字节相同」。A（推荐）：不改，那是各模块当时做了什么；现行行为以本模块那一行与本 Spec 为准。
  B：经【公共变更请求】把三行改成现行行为。

## Boundaries

- **会做**：改动 1～5；todo 末尾记更新说明与「对使用者的影响」。
- **先问再做**：状态码要写进文件才能做（违反假设 1）；真实宿主的注入记录格式与假设 1 不符；一行形式要比假设 6 多带别的内容；
  找到依赖英文输出逐字不变的外部使用方。
- **不做**：压缩后核对提醒里 `waiting-on-*` 部分（D2 那一侧）；本地账本读回提醒不依赖约定启用（归 `ledger-standalone-reminder`）；
  文档核验接进最终验收（归 `doc-chain`）；改阶段判定、`stop_node`、指纹算法；改停点规则正文或给它出英文版；给提示加开关或配置项；
  改其他插件的仓库；改版本号与 CHANGELOG；重装或更新本机 spec-guard。

## 并行边界

- 独占：`spec/quiet-injection.md`、`tasks/quiet-injection/plan.md`、`tasks/quiet-injection/todo.md`、`plugins/spec-guard/hooks/phase-guard.sh`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/session_context.py`、`plugins/spec-guard/hooks/project_link.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/commands/phase.md`、`docs/design.md`、`README.md`、`README.en.md`、`evals/hint-english-diff.sh`、`evals/codex-plugin-smoke.sh`、`evals/module-namespace.sh`
- 公共：无

## 与在开模块的重叠

- `ledger-standalone-reminder`（在本模块之后）改 `phase-guard.sh` 的账本读回提醒；`doc-chain`（在本模块之后）往最终验收的停点注入追加内容，
  会碰 `module_stage.py`。它们开工时本模块已合入，后开的一方先 `module-crew sync`。
- `rules-at-nodes` 已合入集成分支，本分支从它之后切出；本模块不改它新增的 `node-rules.md` 与 `test_stop_rules.py`，只调用 `stop_node`。

## 变更记录

- 2026-10-22：AC9 由「Claude Code 与 Codex 真实宿主各连续两轮」改为「Claude 用 `claude -p --plugin-dir` 跑两轮；Codex 用真实 rollout 片段验证格式，
  真机两轮放到发版后由模块协调做」。原因：本机两个宿主装的是已发布版，本 Spec 不许重装本机插件，Codex 没有不安装就加载工作区插件的办法。
  来源：用户批准 Plan（事项 C145）时对 Plan 未决问题 Q1 选 A，并要求在此记一行（经模块协调 sg-coord 转达，消息 #10374）
- 2026-10-23（返工 1，账本 0W0ZWWT）：假设 10、Contract 与 AC6 改为「Claude 尾部有读数超过 200k 才按 1M 估算，否则不出边界行」，删去按 200k
  估算。原因：Claude 记录读不出窗口，按 200k 估算让 1M 会话在 140k～200k 之间必然误报模块边界（协调会话 164k、179k 各一次，DONE 每轮重复）。
  代价：200k 窗口的 Claude 会话不再有模块边界提醒，交给宿主管理。来源：用户本人（「0W0ZWWT 并进 0.84.1：Claude 读不到窗口时不再按 200k
  估算触发模块边界提醒（读不准就不报，或读数过 200k 才按 1M 判）」；批准返工 Plan 时「接受 200k 会话不再有边界提醒」）。
