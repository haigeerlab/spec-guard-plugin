# Spec: ledger-standalone-reminder

<!-- spec-guard: review approved dc4ca1558049 -->

## Objective

本地事项账本是「通用的持久记事本」（D10），留在 spec-guard、不拆（D11）。但它的读回提醒现在挂在多模块约定上：`phase-guard.sh`
在项目没有约定块、没有带 `activeModule` 的 `.agent/state.json`、也没有指向文件时，启动 python3 之前就静默退出，
`.epiq/project.json` 根本没人看（`hooks/phase-guard.sh` 的 `inactive_before_python` 与 `LINKED` 两处）。结果是：只启用账本、不用
多模块约定的项目（或 teardown 掉约定、保留账本的项目），会话开始、清空、压缩后都没有「先看 `waiting-on-*`」的提醒，账本记下的
承诺照样会在压缩或清空后丢。

另一半是审查 F8 的文档部分：`local_ledger_adapters.py install-claude`／`install-codex` 会写用户级 Claude MCP 条目、
`~/.claude/settings.json` 的 `permissions.ask` 规则、`~/.codex/config.toml` 的 MCP 表，README 的卸载步骤没提，卸掉插件后这些配置
留下来指向已不存在的运行时。

用户的决定（D11）：

1. **读回提醒不依赖约定启用。** 项目根有 `.epiq/project.json` 就出现，有没有约定块、state、指向文件都一样。
2. **补卸载步骤（F8 文档部分）。** README（中英）与账本命令说明写清：接入过宿主的，卸插件前怎么移除那几处宿主配置；账本数据
   怎么处理。

登记：2026-10-22 修复批次的模块之一，经用户批准事项 C184 开模块会话；能力图依赖 `quiet-injection`（已合入，提供一行形式与状态码）。
依据：`docs/reports/2026-10-22-feature-inventory/decisions.md`（D10、D11）；`docs/reports/2026-10-22-multidimension-audit.md`（F8、G4）。

## Assumptions

1. **「账本提醒」指现有的三处，文字不改。** 现在有账本时出现的是：会话开始与清空后（SessionStart `fresh`）的读回提醒、压缩后
   （SessionStart `compact`）核对提醒里的账本一句、别的会话转来消息那一轮（UserPromptSubmit）的当场记账提醒（receipt hint）。
   三处都以「调用账本工具时都传 `repoRoot` 为 …」结尾。本模块只改它们**什么时候出现**，不改文字。（只做前两处的做法见 Q1。）
2. **只启用账本的项目只出账本提醒，不出阶段内容。** 没有约定块、state、指向文件，但有 `.epiq/project.json` 时：
   - `fresh`：照现在输出读回提醒（与已启用项目逐字相同）。
   - `compact`：只输出压缩后核对提醒的账本版本，去掉「接着做上面的建议下一步」半句（上面没有阶段内容），即
     「上下文刚被压缩：摘要里较早的请求可能已经做完；重做之前先核对账本里未关闭的 `waiting-on-*` 事项。」＋ repoRoot 一句（英文同理）。
     这是本模块唯一新增的文字。
   - UserPromptSubmit：这一轮是别的会话转来的消息时只输出记账提醒一行；其他轮次静默（不出一行形式、不出状态码）。
   已启用约定的项目（含跟随指向）一切照旧。
3. **判定只看文件在不在，且先在 bash 里判。** 与现在一样不读账本内容、不调 Epiq。`inactive_before_python` 把「项目根或输入 cwd 所在
   git 仓库根有 `.epiq/project.json`」也算作「拿不准」，交给后面的流程；只有账本、没有其他信号时，UserPromptSubmit 在启动 python3 之前
   先用 bash 看提示词开头是不是 `<cross-session-message `，不是就直接退出 0，不为每一轮付一次 python3 启动。
4. **语言判定照旧。** 中英文由 `module_stage.py --hint-language` 判（读 `.agent/config.json` 的 `artifactLanguage`）；只启用账本的项目
   多半没有这个配置，就是英文——与现在 `fresh_out` 的行为一致。缺 python3 时 `fresh` 照现在输出英文提醒；`compact` 与 UserPromptSubmit
   在只启用账本、缺 python3 时静默（不像已启用项目那样报「缺 python3 没有阶段注入」：这里本来就没有阶段注入）。
5. **`.epiq/project.json` 也可能是独立使用 Epiq 写下的。** 装了 spec-guard、又在项目里单独用 Epiq 的人，也会看到这三处提醒；提醒只建议
   列出 `waiting-on-*` 标签的事项，没有就继续，代价是每次会话开始多一句话。接受，不另加判据或开关（D11 原话就是「有 `.epiq/project.json`
   就出现」）。
6. **不变量的措辞要跟着改。** 「hook 默认不生效；没有激活信号的项目必须静默退出」改为：没有激活信号、也没有 `.epiq/project.json` 的
   项目必须静默；只有账本的项目只出上面三处账本提醒。`docs/design.md` 第 159 行与第 69～74 行按此改；仓库根 `CLAUDE.md` 不变量一节的同一条
   一并改（它不属于全局配置、锁文件、迁移、测试资源四类公共文件，列入独占；协调判定为公共文件时改走【公共变更请求】）。
7. **卸载步骤只写说明，不新增移除命令。** 审查 F8 归入 G4「说明修正」只取文档部分；`host_config_removal.py` 的移除函数 2026-10-08
   已有意删掉，命令说明也写着「本阶段没有删除账本命令」。所以写成用户自己照做的步骤，每一步给可原样运行的宿主命令：
   - Claude Code：`claude mcp remove --scope user spec-guard-local-ledger`；从 `~/.claude/settings.json` 的 `permissions.ask` 里删掉
     以 `mcp__spec-guard-local-ledger__` 开头的规则（列出规则名单的来源：`local_ledger_adapters.py claude` 的只读输出）。
   - Codex：`codex mcp remove spec_guard_local_ledger`，或手动删掉 `~/.codex/config.toml` 里 `[mcp_servers.spec_guard_local_ledger]`
     那一整张表。
   - 受管运行时 `~/.spec-guard/local-ticket-ledger/runtime`（设了 `SPEC_GUARD_STATE_DIR` 时在那下面）：不再用账本时可以删。
   - 账本数据（项目里的 `.epiq/`、`__epiq_state__` 状态 worktree、`~/.epiq-global`）是你的记录，卸载**不需要**删；要保留就别动，
     要带走先用 `local-ticket-portability` 归档。
   `codex mcp remove` 按表名删、`claude mcp remove --scope user` 能删 `add --scope user` 写下的条目，这两点在构建时用临时
   `CODEX_HOME`／`CLAUDE_CONFIG_DIR` 实测后才写进文档；实测不符就改写成手动删除的步骤。
8. **卸载顺序。** 先移除宿主配置、再卸插件：插件卸掉后 `local_ledger_adapters.py` 就不在了，查不到规则名单。README 现有的两步之间
   插入这一步，只对「接入过宿主的」适用。
9. **teardown 之后提醒还在。** `teardown-convention` 保留账本；改完后 teardown 掉约定、账本还在的项目，仍会看到账本提醒。在
   `commands/teardown-convention.md` 写一句：要连提醒一起停，见 README 卸载里账本那一步（停用账本本身仍不在本模块范围）。

## Contract

### 改动 1 只启用账本时的三处提醒（`hooks/phase-guard.sh`）

- 新增 bash 函数 `has_ledger`（`[ -f "${1:-.}/.epiq/project.json" ]`）。`inactive_before_python` 在 ROOT 与 cwd 所在仓库根的判断里
  加上它。
- `cd "$ROOT"` 之后、`LINKED` 判定处：没有约定块与 state 时，先看指向文件（有就照旧跟随，账本按目标项目判）；没有指向文件但
  `has_ledger` 时进入「只有账本」分支，按假设 2 输出后退出：
  - `fresh` → 现有 `fresh_out`；
  - `compact` → 新的账本核对提醒（中英两版，语言按假设 4）；
  - UserPromptSubmit → 先在 bash 看 `RAW` 是否以 `<cross-session-message ` 开头（hook 输入是 JSON，判断落在 `"prompt"` 字段的开头），
    不是就退出 0；是就复用现有 `receipt_hint`（`session_context.py --received` 做准确判定），有输出才 emit 一段只含这一行的 JSON。
- 只有账本时的输出都不以 `## spec-guard local workflow` 开头、不带状态码，所以不会被 `quiet-injection` 的 `last_state` 当成上一次阶段注入。
- 已启用、跟随指向、指向失效、诊断类输出，代码路径不变。

### 改动 2 文档

- `README.md`、`README.en.md` 的「卸载」：在 teardown 与卸插件之间插入「接入过宿主的，先移除账本的宿主配置」一步（假设 7、8），
  写明账本数据不用删。隐私一节（README 第 157 行附近）「启用了本地事项账本的项目，钩子只看 `.epiq/project.json` 在不在」补一句
  「没有启用约定也会出读回提醒」。
- `commands/local-ticket-ledger.md` 末尾「本阶段没有删除账本命令」一段之后加「移除宿主配置」小节，内容同假设 7；
  `skills/local-ticket-ledger-ops/SKILL.md`（Codex 入口）对应加一段。
- `references/local-ticket-ledger-runtime.md` 的宿主接入一节加一句指向上面的移除步骤。
- `docs/optional-features.md` 本地事项账本一节：加一句「不用多模块约定也会有读回提醒」。
- `docs/design.md`：第 69～74 行的 SessionStart／激活说明与第 159 行不变量按假设 6 改。
- `commands/teardown-convention.md`：按假设 9 加一句。
- 仓库根 `CLAUDE.md`：不变量一节「hook 默认不生效」一条按假设 6 改。

### 改动 3 回归（`hooks/test-phase-guard.sh`）

- 把现有用例「未激活的目录有账本文件时 fresh 也静默」改为反向：只有账本的目录 `fresh` 出读回提醒（中英各一，repoRoot 为该目录）。
- 新增：只有账本时 `compact` 只出账本核对提醒（中英各一）；只有账本时普通 UserPromptSubmit 静默且退出 0；只有账本、提示词是
  `<cross-session-message …>` 时只出记账提醒一行；只有账本、缺 python3 时 `fresh` 出英文提醒、其他两处静默；
  hook 输入 cwd 在只有账本的仓库子目录里、宿主 ROOT 是别处时也认得（bash 快速判定那条路径）；
  既无账本也无其他信号时三种事件都静默（原有断言保留）；已启用项目的三处输出与改前逐字相同（复用现有用例）。
- `scripts/validate.sh` 里的 Codex smoke 判决器若有「未激活必须静默」的断言，按假设 6 调整（构建时核对，没有就不动）。

## 对使用者的影响

- 只用本地事项账本、没装多模块约定（或 teardown 掉了约定）的项目，升级后在会话开始、清空、压缩后会看到账本读回提醒，别的会话
  转来消息时会看到记账提醒；平时每轮没有任何注入。
- 没有账本也没有约定的项目，照旧什么都不出。已启用约定的项目，什么都不变。
- 接入过宿主的账本用户，卸载 spec-guard 前多一步：按 README 移除账本的宿主 MCP 配置与 ask 规则；账本数据保留。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Acceptance criteria

- **AC1**：只有 `.epiq/project.json`、没有约定块、state、指向文件的项目，SessionStart `fresh` 输出与已启用项目逐字相同的读回提醒；中英各有回归。
- **AC2**：同样的项目，SessionStart `compact` 只输出账本核对提醒（假设 2 的文字＋repoRoot 一句），不含阶段内容；中英各有回归。
- **AC3**：同样的项目，普通 UserPromptSubmit 无输出、退出 0；提示词以 `<cross-session-message ` 开头时只输出记账提醒一行；各有回归。
- **AC4**：既无账本也无其他激活信号的目录，三种事件都静默、退出 0；已启用约定的项目三处输出与改前逐字相同（现有用例全部通过）。
- **AC5**：只有账本时的输出不带 `spec-guard-state` 状态码、不以 `## spec-guard local workflow` 开头；缺 python3 时按假设 4 降级；各有回归。
- **AC6**：README（中英）卸载一节、`commands/local-ticket-ledger.md`、`local-ticket-ledger-ops` 技能写明移除宿主配置的步骤，命令名、条目名、
  表名与 `local_ledger_adapters.py` 的常量一致；`claude mcp remove` 与 `codex mcp remove` 的写法在临时配置目录里实测过，最终验收附实测输出。
- **AC7**：`docs/design.md` 的激活说明与不变量、`teardown-convention.md`、`optional-features.md` 按假设 6、9 更新；仓库根 `CLAUDE.md` 不变量一条
  同步改（假设 6）。
- **AC8**：`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全部通过；hook 输出仍是宿主接受的 JSON；不新增 `jq` 依赖；
  `phase-guard.sh` 改动跑过 ShellCheck。
- **AC9**：Claude Code 在只有账本的临时项目里用 `claude -p --plugin-dir <本 worktree 的插件>` 开一个新会话，会话记录里出现读回提醒；
  Codex 真机核对放到发版后由模块协调做，最终验收写明这一条没在 Codex 真机上做。

## 未决问题

- **Q1：只启用账本时出哪几处提醒。** A（推荐，假设 1、2）：三处都出——读回提醒、压缩后核对、别的会话来消息时的记账提醒；它们都是
  账本「不丢承诺」的同一件事，平时每轮仍然静默。B：只出读回提醒与压缩后核对（D11 原话「读回提醒」的最窄读法），来消息时的记账提醒
  仍只在启用约定的项目里出。
- **Q2：卸载步骤要不要做成命令。** A（推荐，假设 7）：只写文档步骤，用户自己照做；移除函数 10-08 有意删过，这次不加回。
  B：给 `local_ledger_adapters.py` 加 `remove-claude`／`remove-codex`（预览＋`--confirm-remove`），文档改为调用它——多一套要维护的
  写宿主配置代码，超出 F8 归入的「说明修正」。

## Boundaries

- **会做**：改动 1～3；todo 末尾记更新说明与「对使用者的影响」。
- **先问再做**：实测发现 `claude mcp remove`／`codex mcp remove` 删不掉 spec-guard 写下的条目、需要改写成别的步骤之外的做法；
  只有账本的分支需要读账本内容或调 Epiq 才能做；发现别的插件依赖「未启用约定就静默」。
- **不做**：改三处提醒的文字（假设 2 新增的那一句除外）；新增卸载或删除账本的命令；动账本数据；给提醒加开关或配置项；
  改阶段判定、状态码与一行形式（`quiet-injection`）；改其他插件的仓库；改版本号与 CHANGELOG；重装或更新本机 spec-guard；
  在本机真实宿主配置上跑移除命令（只在临时配置目录里实测）。

## 并行边界

- 独占：`spec/ledger-standalone-reminder.md`、`tasks/ledger-standalone-reminder/plan.md`、`tasks/ledger-standalone-reminder/todo.md`、`plugins/spec-guard/hooks/phase-guard.sh`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/commands/local-ticket-ledger.md`、`plugins/spec-guard/commands/teardown-convention.md`、`plugins/spec-guard/skills/local-ticket-ledger-ops/SKILL.md`、`plugins/spec-guard/references/local-ticket-ledger-runtime.md`、`docs/optional-features.md`、`docs/design.md`、`README.md`、`README.en.md`、`CLAUDE.md`
- 公共：无

## 与在开模块的重叠

- `doc-chain` 同时开发，往最终验收停点注入追加内容、写文档链说明：可能也碰 `phase-guard.sh`、`test-phase-guard.sh`、`docs/design.md`、
  `README.md`／`README.en.md`。本模块在这些文件里只动账本提醒的分支、卸载一节与激活说明；具体重叠由模块协调对照 `doc-chain` 的并行边界核对后交用户定。
- `quiet-injection` 已合入集成分支，本分支从它之后切出；本模块不改它的状态码、一行形式与 `session_context.py`，只复用 `receipt_hint`。
