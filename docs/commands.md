# 命令参考

spec-guard 在 Claude Code 里提供 21 条斜杠命令。Codex 不加载斜杠命令，同样的功能通过 skill 用自然语言调用，
对照见文末的[命令对照](#命令对照)。每条命令的完整说明以 `plugins/spec-guard/commands/<命令>.md` 为准。

几条共同规则：

- **先预览，确认后才写。** 会写文件或远端的命令默认只预览；看过预览、明确确认后才带 `--confirm` 或去掉
  `--dry-run` 再跑一次。改了参数要重新预览。
- **原样转述。** 命令输出由 agent 原样转述给你，被拒绝时说明是哪条校验失败，不自行改参数重试。
- **定位失败不等于没安装。** 找不到插件根目录时，命令会说明是哪一步查询失败并退出 2。

## 约定与阶段

### `/spec-guard:setup-convention`

参数：`[local] [--dry-run] [--replace [--accept-removals]] [--dispatch|--no-dispatch]`

在当前项目安装多模块约定：建 `spec/`、`tasks/`、`.agent/state.json`，在 `CLAUDE.md`（Codex 是 `AGENTS.md`）写入
[约定块](convention-block.md)。只支持本地文件式工作流，不访问远端。

- 先 `--dry-run` 预览，确认后再正式运行。
- `--replace` 升级已有约定块。块内本地段（`<!-- BEGIN:spec-guard-local -->` … `<!-- END:spec-guard-local -->`）
  原样保留；预览逐行列出 `will remove:`／`will add:`，不在现行模板里的删除行标 `[needs --accept-removals]`，
  不加这个参数时拒绝替换且不改文件。
- `--dispatch`／`--no-dispatch`：开关可选的子代理派活规则（实验性，默认关闭）。
- 已有 `.agent/state.json.disabled` 时拒绝新建空状态，先人工核对后改回原名。

### `/spec-guard:teardown-convention`

参数：`[--dry-run] [--keep-state] [--accept-removals]`

移除约定块，并把 `.agent/state.json` 改名为 `state.json.disabled`，阶段提示随之停止；`spec/`、`tasks/` 保留。

- 每次先 `--dry-run` 预览。
- 本地段的行留在块原来的位置；本地段以外、不在现行模板里的行要加 `--accept-removals` 才删，否则退出 1、不改任何文件。
- `--keep-state` 保留 `state.json` 原名，hook 会继续激活（零足迹模式）。
- 退出码 2：这个项目没启用过约定。

### `/spec-guard:phase`

查看当前阶段、当前模块、全局计数与建议的下一步（与每轮自动注入的内容相同）。没有输出表示这个项目没装约定。

| 阶段 | 含义 |
|---|---|
| `IDLE` | 还没有能力图 |
| `MAP_ONLY` | 有能力图，还没有任何模块 Spec |
| `NEEDS_SPEC` | 当前模块缺 `spec/<id>.md` |
| `NEEDS_PLAN` | 当前模块有 Spec，缺 `tasks/<id>/plan.md` |
| `BUILDING` | 当前模块的 `todo.md` 还有未勾选项 |
| `MODULE_DONE` | `activeModule` 指向的模块已完成，但能力图里还有别的模块没完成 |
| `DONE` | 每个模块都有 Plan 且没有未勾选项 |
| `MAP_INVALID` | 能力图无法按严格规则解析 |
| `UNKNOWN` | 阶段无法计算（例如任务文件读不了） |

当前模块取 `.agent/state.json` 的 `activeModule`，否则取 Build order 里第一个未完成的模块。其他可能出现的行：
`Location:`（分支与 worktree）、`Paused:`（插队时被暂停的模块）、`Suspended:`（挂起的模块）、上下文接近窗口上限时的
`/compact`／`/clear` 提醒。

### `/spec-guard:verify-artifacts`

校验已落地的产物：能力图存在并通过严格解析（唯一模块表、Build order、依赖）；`spec/` 下每个模块 Spec 都在能力图
里；项目根目录没有 `SPEC*.md`。

- ❌ 是问题，逐条说明原因和改法，确认后再改；⚠️ 只是提醒（例如有 Plan 没 todo、`state.json` 里残留已退役的
  `tracker` 字段）。
- 某部分写着“未验证”时不等于通过（例如 python3 不可用）。
- 退出码 2：项目目录无法进入。没有能力图只给 ⚠️。

### `/spec-guard:config`

查看或设置项目配置 `.agent/config.json`（入库，Claude 与 Codex 共用）：

| 键 | 取值 | 默认 |
|---|---|---|
| `artifactLanguage` | 语言标签，如 `zh-CN`、`en` | 未设置 |
| `reviewCadence` | `separate`／`combined` | `separate` |

不带参数时 `show`；`set`／`unset` 先预览差异，`--confirm` 才写。取值不合法时退出 2、不写文件。文件无效时所有项按
默认处理，阶段提示只多一行 `Project config: invalid`。同时只读汇总派活开关与默认事项后端的当前值和来源。

### `/spec-guard:module-suspend`

挂起一个已开工、只剩等待外部条件的模块：选当前模块时跳过它，它留在 Build order 原位，阶段提示列出 `Suspended:`。
`--suspend <id>`／`--resume <id>`，先预览、`--confirm` 才改 `tasks/<id>/todo.md` 的一行标记。永不自动恢复。
拒绝时退出 2、不写文件。挂起后可以按你说的时间和内容设一个提醒，插件不保存提醒。

## 加需求

### `/spec-guard:add-module`

参数：`[需求上下文]`

在模块检查点（当前模块还没开始或已完成）把新需求作为模块插进能力图。agent 根据能力图提出 id、职责、依赖、插入
位置，各带一句理由；预览新行、新 Build order 与 diff，确认后加 `--confirm` 写入。只改 `spec/CAPABILITY-MAP.md`。

- 当前模块做到一半时拒绝；确需先做新模块时加 `--interrupt` 显式插队，预览会列出被暂停的模块。
- `--proposal <id> --platform <github|gitlab> --target <目标>`：从已接受的 Proposal 晋级，四项字段全部取自远端。

### Proposal 流程（需要留痕的需求）

| 命令 | 参数 | 做什么 |
|---|---|---|
| `/spec-guard:proposal-submit` | `<proposal-id> <github\|gitlab>` | 按远端默认分支补全本地草稿的基线与 revision 并校验；预览后确认才回写草稿，不做远端写操作 |
| `/spec-guard:proposal-review` | | 只读：报告一个已发布 Proposal 的新鲜度与 Issue 阶段（`awaiting-review`、`in-review`、`stale`、`in-map`、`absent` 等） |
| `/spec-guard:proposal-promotion-preflight` | | 只读：人工接受后检查能否开晋级分支，`ready` 时给出 `baseCommit`（`add-module --proposal` 已内置同一检查，通常不必单独跑） |
| `/spec-guard:proposal-promotion-proof` | | 只读：晋级合并后证明模块已按声明进入远端能力图，`proved` 时带 `closeoutPending` |
| `/spec-guard:proposal-closeout` | | `proved` 后预览并经授权把事项标为 promoted、关闭并读回；`scan` 只读列出还欠收尾的 Proposal |

完整的四步流程见[使用流程](workflow.md)。

## 事项

| 命令 | 做什么 |
|---|---|
| `/spec-guard:ticket` | 用自然语言记 bug、需求、排查记录；不带内容时列出未关闭事项。明确选 GitHub/GitLab 时走托管流程，逐项查重、逐次授权 |
| `/spec-guard:local-ticket-ledger` | 只读查看本地事项账本状态；明确要求时安装运行时、初始化仓库、接入 Claude／Codex（需要 macOS 与 Node.js） |
| `/spec-guard:local-ticket-portability` | 只读核验或离线归档 Local 事项；明确指定目标后恢复，或逐项交接到 GitHub/GitLab |
| `/spec-guard:tracker-default` | 查看或设置项目默认的事项后端与精确目标（`.agent/tracker.json`），只用于预填预览，不代替逐次授权 |

## 文档治理与历史

| 命令 | 做什么 |
|---|---|
| `/spec-guard:documentation-baseline` | 预览或建立项目级文档基线 `docs/DOCUMENTATION-BASELINE.md`，不生成业务文档 |
| `/spec-guard:documentation-impact` | 预览一个模块对文档基线的影响和计划交付物 |
| `/spec-guard:documentation-verification` | 只读核验模块声明的文档交付状态；`ready` 只表示已声明交付，不代表内容已验证 |
| `/spec-guard:history-integrity` | `audit` 只读输出历史证据的 JSON 报告；`correct --confirm <audit-report.json> <correction.json>` 在确认后追加补正记录 |

## 报告

### `/spec-guard:cost-report`

参数：`<module-id> [更多模块] [--prices <价格文件>] [--json]`

只读：离线读取本机 Claude Code 与 Codex 的会话记录，按 todo 的勾选提交切出每个 task 的时间窗，统计主代理与子代理
的 token、主会话轮次、派活与返工信号。只有给了 `--prices` 才折算金额。退出码 2：todo 没有提交历史，时间窗切不出来
（不是用量为 0）。

## 命令对照

Codex 不加载插件的斜杠命令，对应功能通过 skill 调用，用自然语言描述要做的事即可。

| 功能 | Claude Code | Codex |
|---|---|---|
| 安装或移除约定 | `/spec-guard:setup-convention`、`/spec-guard:teardown-convention` | `spec-guard-ops` skill 的 setup、teardown 一节 |
| 查看阶段、校验产物 | `/spec-guard:phase`、`/spec-guard:verify-artifacts` | `spec-guard-ops` skill |
| 查看或设置项目默认事项后端 | `/spec-guard:tracker-default` | `spec-guard-ops` skill 的 tracker default 一节 |
| 查看或设置项目配置（产物语言、评审节奏） | `/spec-guard:config` | `spec-guard-ops` skill 的 config 一节 |
| 挂起或恢复在等外部条件的模块 | `/spec-guard:module-suspend` | `spec-guard-ops` skill 的 module-suspend 一节 |
| 快速插入新模块 | `/spec-guard:add-module` | `spec-guard-ops` skill 的 add-module 一节 |
| Proposal 提交、评审、预检、证明、收尾（晋级用 `add-module --proposal`） | `/spec-guard:proposal-submit`、`proposal-review`、`proposal-promotion-preflight`、`proposal-promotion-proof`、`proposal-closeout` | `spec-guard-ops` skill 的 proposal 一节 |
| 文档治理 | `/spec-guard:documentation-*` 三条命令 | `spec-guard-ops` skill |
| 能力历史（含审计与 `correct` 补正） | `/spec-guard:history-integrity` | `spec-guard-ops` skill 的 history 一节 |
| 会话协作（已移到 agent-relay） | 安装 agent-relay 后用 `/agent-relay:collaboration` | agent-relay 的 skill |
| 本地事项 | `/spec-guard:local-ticket-ledger`、`/spec-guard:ticket` | `local-ticket-ledger-ops`、`ticket` skill |
| 本地事项核验、归档、恢复与交接 | `/spec-guard:local-ticket-portability` | `local-ticket-portability` skill |
| 模块成本与返工报告 | `/spec-guard:cost-report` | `spec-guard-ops` skill 的 cost report 一节 |
