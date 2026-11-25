# 命令参考

spec-guard 在 Claude Code 里以斜杠命令提供下列功能。Codex 不加载斜杠命令，同样的功能通过 skill 用自然语言调用，
对照见文末的[命令对照](#命令对照)。这一页面向使用者，写的是参数、效果和你会看到什么；agent 执行命令时另有更细的步骤，
你不需要去读。

几条共同规则：

- **先预览，确认后才写。** 会写文件或远端的命令默认只预览；看过预览、明确确认后才带 `--confirm` 或去掉
  `--dry-run` 再跑一次。改了参数要重新预览。
- **原样转述。** 命令输出由 agent 原样转述给你，被拒绝时说明是哪条校验失败，不自行改参数重试。
- **定位失败不等于没安装。** 找不到插件根目录时，命令会说明是哪一步查询失败并退出 2。

## 约定与阶段

### `/spec-guard:setup-convention`

参数：`[local] [--host=codex] [--dry-run] [--replace [--accept-removals]]`

在当前项目安装多模块约定：建 `spec/`、`tasks/`、`.agent/state.json`，在 `CLAUDE.md`（Codex 是 `AGENTS.md`）写入
[约定块](convention-block.md)。只支持本地文件式工作流，不访问远端。

- 先 `--dry-run` 预览，确认后再正式运行。
- `--host=codex`：在 Claude Code 里装 Codex 一侧，约定块写进 `AGENTS.md`；不加时写 `CLAUDE.md`。
- `--replace` 升级已有约定块。块内本地段（`<!-- BEGIN:spec-guard-local -->` … `<!-- END:spec-guard-local -->`）
  原样保留；预览逐行列出 `will remove:`／`will add:`，不在现行模板里的删除行标 `[needs --accept-removals]`，
  不加这个参数时拒绝替换且不改文件。只差空白或折行的段不算删减，预览汇总成一行
  `will adjust whitespace or line wrapping: N paragraph(s)`。
- `--replace` 只替换已有块、从不新建：目标文件（Claude 侧 `CLAUDE.md`、Codex 侧 `AGENTS.md`）里没有块时退出 1、不改任何文件和目录，
  另一侧有块就提示改用那一侧（加或去掉 `--host=codex`），两侧都没有就提示去掉 `--replace` 新建；`--dry-run` 结论相同。
- 派活规则段已退役：`--dispatch`／`--no-dispatch` 会被拒绝；旧块里带着它时 `--replace` 移除整段，不需要 `--accept-removals`。
- 已有 `.agent/state.json.disabled` 时拒绝新建空状态，先人工核对后改回原名。

### `/spec-guard:teardown-convention`

参数：`[--host=claude|--host=codex] [--dry-run] [--keep-state] [--accept-removals]`

移除约定块，并把 `.agent/state.json` 改名为 `state.json.disabled`，阶段提示随之停止；`spec/`、`tasks/` 保留。

- 每次先 `--dry-run` 预览。
- `--host=codex`：移除 `AGENTS.md` 里的约定块；不加（或 `--host=claude`）时移除 `CLAUDE.md` 里的。另一侧的块还在时 `state.json` 保留原名，hook 继续激活。
- 本地段的行留在块原来的位置；本地段以外、不在现行模板里的行要加 `--accept-removals` 才删，否则退出 1、不改任何文件。
- `--keep-state` 保留 `state.json` 原名，hook 会继续激活（零足迹模式）。
- 退出码 2：这个项目没启用过约定。

### `/spec-guard:phase`

查看当前阶段、当前模块、全局计数与建议的下一步，总是给完整内容。没有输出表示这个项目没装约定。

每轮自动注入的阶段提示平时只有一行：`spec-guard: <阶段> · <模块> · <未勾选数> · <分支>`，表示状态和上一次完整提示时相同。
新会话、压缩之后、读不到会话记录、状态变了、进入停点（交审、gate、最终验收）那一轮，以及出诊断时，给完整内容。

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
`Location:`（分支与 worktree）、`Paused:`（插队时被暂停的模块）、`Suspended:`（挂起的模块）、`Linked project`（项目指向）、
`Project config`（配置无效或有键被忽略）、模块边界提醒。模块边界提醒只在模块之间（`MODULE_DONE`、`DONE`）、会话上下文达到
窗口 70% 时出现，建议 `/compact` 或 `/clear`；模块进行中不提醒。Claude 的会话记录不带窗口大小，只有读数超过 200k 时按 1M 窗口估算，
否则不出这一行；读不到用量（例如新会话第一轮）也不出。

### `/spec-guard:verify-artifacts`

校验已落地的产物，逐项给出 ✅／⚠️／❌：

| 检查 | 不通过时 |
|---|---|
| 能力图存在并通过严格解析（唯一模块表、Build order、依赖） | ❌（没有能力图只给 ⚠️） |
| `spec/` 下每个模块 Spec 都在能力图里 | ❌ |
| 项目根目录没有 `SPEC*.md` | ❌ |
| `.agent/config.json` 有效 | 文件无效 ❌；只有不认识的键 ⚠️（已忽略）；有已退役的 `autonomyTier`／`moduleAutonomy` ⚠️；`moduleTakeover` 里有能力图上没有的模块 ⚠️（每个一条） |
| 有 Plan 没 todo 的模块 | ⚠️（按已完成计） |
| 挂起标记 | 重复 ❌；已没有未勾选项 ⚠️ |
| 批准标记 | 写法无效 ❌；批准后已修订、待批准却已有勾选 ⚠️ |
| 并行边界格式（只在 `moduleConcurrency` 为 `on` 时） | 格式错 ❌；未完成模块的 Spec 缺这一节 ⚠️ |
| Plan 的「预先声明」格式（有这一节时，不看并行开关） | ❌ |
| 多模块批次：同一次提交插入、还没完成的模块有 2 个及以上，是否有用法草案覆盖 | 缺草案 ⚠️（每批一条，写明模块与提交）；读不到 git 未判定 ⚠️ |
| 用法草案 `spec/usage/*.md`（有这个目录时）：三节与表格、用法与里程碑对得上、模块在能力图上且只归一个里程碑、入口的模块在里程碑里、Build order 顺序、里程碑确认记录的写法 | ❌；里程碑里的模块没有入口、确认后里程碑的模块变了 ⚠️ |
| 新流程模块的回归用例（`tasks/<id>/regression.md`，bug／small 为需求文档的「回归用例」一节）：字段、执行方式、命令、编号、成功标准对照、受影响的老功能 | ❌（bug 构建中还没有用例 ⚠️，todo 全勾后 ❌） |
| `projectSections` 声明的章节只有标题、没有内容 | ❌（写「不涉及」即可） |
| 多模块需求的联调回归 `spec/usage/<需求>.regression.md`：用例格式、涉及的模块在能力图上、对照表里的 `S<n>` 在用法草案里有 | ❌ |
| 任务目录里 `plan.md`、`todo.md` 以外文件的未勾选项 | ⚠️（不计入阶段） |
| `state.json` 里残留已退役的 `tracker` 字段 | ⚠️ |

- ❌ 是问题，逐条说明原因和改法，确认后再改；⚠️ 只是提醒，不影响退出码。
- 某部分写着“未验证”时不等于通过（例如 python3 不可用）。
- 退出码 2：项目目录无法进入。没有能力图只给 ⚠️。

### `/spec-guard:config`

查看或设置项目配置 `.agent/config.json`（入库，Claude 与 Codex 共用）：

| 键 | 取值 | 默认 |
|---|---|---|
| `artifactLanguage` | 语言标签，如 `zh-CN`、`en` | 未设置 |
| `reviewCadence` | `separate`／`combined` | `separate` |
| `moduleConcurrency` | `off`／`on` | `off` |
| `takeover` | 预设 `none`／`design`／`merge`，或自定义三项 | `none` |
| `moduleTakeover` | 模块 id → 同 `takeover` 的值 | 未设置 |
| `projectSections` | 文档 → 追加章节名列表，如 `{"design": ["浏览器兼容"]}` | 未设置 |

`takeover`（接管档位）定技术方案、合并、发布三项各由你做还是交给 AI；需求永远由你确认，新流程 Plan 永远自动批准，两者不可配。
`none` 全由你做（每份技术方案都由你批，不需要审的也一样），`design` 让第二审查者审过即放行技术方案（重要需求仍由你批），`merge` 再加审查通过后自动合并；
发布只能用自定义打开（`human`／`prepare`／`auto-confirm`／`auto`）。spec-guard 只存、读、报告来源，自动接管由 autopilot 与 module-crew 读它去做。
用说话的方式设置，先预览三项、你确认后才写：

```text
技术方案让第二审查者审过就行
```

旧值照旧能读、不再写入（`set` 拒绝，`takeover-legacy`）：预设 `plan` 读作 `none`，旧 `merge` 读作新 `merge`，自定义里的 `spec`、`plan`
对新流程模块不生效；老流程模块仍按旧含义读谁批 Spec、Plan（`plan`、`design` 都是 Codex 批 Plan）。`show` 列出生效值，存的是旧值时加提示。
0.84.0～0.94.0 的 spec-guard 读到 `design` 只忽略这个键，团队都升级后再设。

`moduleTakeover` 给单个模块另设档位，用 `set --key moduleTakeover --module <模块 id> --value <值>` 一次改一个，没设的模块随项目；
比项目宽时只提醒、不截断。能力图上没有的模块 id 由 verify-artifacts 警告。设置时要你在对话里的原话。原来的 `autonomyTier`、
`moduleAutonomy` 已退役，不映射到接管档位；文件里还有时不生效，可以 `unset` 删掉。团队都升级到 0.91.0 后再设。

出事时 autopilot 或 module-crew 会用 `narrow` 自动把档位往严里收一格（先收发布，再收合并、技术方案；预设按 `merge` → `design` → `none`），不用问你，并在
`.agent/config.json` 里记下原因；这个文件改了之后要提交。想恢复时照常说一句，比如「恢复成接管到合并」；收窄过的档位一次只能升一格，
差两格就分两次说。`/map --json` 里每个模块的 `takeover.narrowed` 写着从哪一档收下来、谁收的、什么时候。

不带参数时 `show`；`set`／`unset` 先预览差异，`--confirm` 才写。取值不合法时退出 2、不写文件。文件本身坏了时所有项按
默认处理，阶段提示只多一行 `Project config: invalid`；个别键有问题时只有那个键失效、其余照常，阶段提示多一行
`Project config: ignored`。同时只读汇总默认事项后端的当前值和来源。

### `/spec-guard:module-suspend`

挂起一个已开工、只剩等待外部条件的模块：选当前模块时跳过它，它留在 Build order 原位，阶段提示列出 `Suspended:`。
`--suspend <id>`／`--resume <id>`，先预览、`--confirm` 才改 `tasks/<id>/todo.md` 的一行标记。永不自动恢复。
你说了原因时加 `--reason "<一行>"`，原因记在标记的下一行，`/spec-guard:map` 里显示；恢复时一起去掉。
拒绝时退出 2、不写文件。挂起后可以按你说的时间和内容设一个提醒，插件不保存提醒。

### `/spec-guard:link-project`

会话开在一个不是项目的目录里（比如需求文档目录），实际开发在别处的仓库时用：`set --project <路径>` 在会话目录写
`.agent/spec-guard-link.json`，之后阶段钩子改读被指向的项目，注入多一行 `Linked project`。`show` 查看，`unset` 解除；
`set`／`unset` 先预览、`--confirm` 才写，只动这一个文件。多个会话共用一个目录、各做不同项目时，三个动作都加
`--session <会话标识>`（Claude Code 传 `"$CLAUDE_CODE_SESSION_ID"`，Codex 传 `"$CODEX_THREAD_ID"`），登记只对那一个会话生效；
钩子先用本会话的登记，其次目录级指向，都没有则静默。会话目录自己已启用 spec-guard 时不需要指向；没有指向文件的
无关目录照旧静默。其他命令与阶段注入用同一套解析自动跟随指向（`project_link.py follow`），输出写明「本次操作的是被指向的项目
`<路径>`」；指向失效时命令退出 2 并给出诊断，不会改去操作会话目录。拒绝时退出 2、不写文件。

### `/spec-guard:review-mark`

记录模块 Spec 或 Plan 的批准状态：`--module <id> --target <spec|plan|both> --state <pending|approved>`，先预览、
`--confirm` 才改文件里的一行标记。当前模块待批准时阶段提示报告等待批准、不建议写 Plan 或继续 build；Spec 的批准标记
带内容指纹，批准后被改会报告“批准后已修订”。记为已批准时命令会提醒 agent 先确认你已在对话里看到内容。`approved` 只在你明确批准之后写（交审时推荐答复放在一个可复制代码块里，回复“批准”即可；所装协作插件对在哪里答复另有规定时以它为准；“继续”不会被记为批准）；批准来源以所装协作插件的规定为准；没装只认当前对话里的明确批准。没有标记的
文件判定照旧；Spec 没有标记时可以单独记录 Plan 的批准，Spec 标着待批准或已修订时不行。拒绝时退出 2、不写文件。

接管档位里 Spec 或 Plan 交给 Codex 时，agent 用 /delegate:review 请 Codex 审，再用 `--state codex-approved --review <报告文件>` 记下
（有阻断时用 `codex-reviewed` 记一轮、改完再审，两轮仍有阻断就交给你）。spec-guard 核对报告确实是 Codex 对这份文件的完成审查；
`/map --json` 的 `reviewApprovedBy` 写明每份文件实际是你批的还是 Codex 批的；`important` 写明哪些模块按规则是重要需求、理由是什么
（同批多模块、跨模块、碰高风险路径），这些模块的 Spec 不论档位都由你批。

合并交给自动化的模块，最终验收也可以由 Codex 做：agent 请 Codex 审最终补丁，等 autopilot 在同一个提交上跑完检查（由非作者跑、全部通过），
再用 `--target acceptance --state codex-approved --review <报告文件>` 记下。记录写在 git 目录里、不进提交，autopilot 据此合并；
`/map --json` 每个模块的 `acceptance` 报出它（`null` 或 `{marker, sha}`）。缺一样证据或有越界改动就拒绝，停下等你；拟回告不会自动发出。

新流程（`normal`／`important`）模块的技术方案用 `--target design` 记录。重要需求由你批（`--state approved`），第二审查者的意见一并附上；
影响面列了开工前已有的文件（或写不出路径）、或项目开关 `designReview` 为 `on` 时，agent 用 `/delegate:review --profile design --backend auto --author-host <宿主>` 请第二审查者审一轮，
没有阻断就用 `--state reviewer-approved --review <报告文件>` 记下、不用你批，有阻断用 `reviewer-reviewed` 记一轮、改完带 `--previous-report` 复审，两轮仍有阻断就交给你；
阻断数算上复审里仍未解决的旧条目。没有可用的审查者时记为「未审」，交给你批。都不是时不审，技术方案写完直接往下。
`/map --json` 每个模块的 `designApproval` 报出状态、谁放行的、审查者厂商、是否同厂商、最后一轮报告的 sha256 与每一轮（interface 1.20 起；老模块与 bug、small 为 null）。

新流程模块的 Plan 写完即自动批准，不交你、也不交 Codex：`--target plan`／`both` 对新流程模块一律拒绝（`plan-auto`，退出 2，什么都不写）；
`/map --json` 里它的 `reviewApprovedBy.plan` 为 `auto`、`codexRoute.plan` 为 `auto`，不出现在 `awaitingReview` 里（interface 1.21 起）。越界、碰 T4 路径、不可逆操作照旧停下问你。

接管档位里有任一项不是「人」的模块，构建中还会做越界检查：改到 Spec 并行边界与（已批准的）Plan 预先声明之外的文件，阶段提示就停下来，
让 agent 逐个说明为什么要改、由你决定；没写并行边界也会停。只读结果用
`module_scope.py check --module <id> --format json`（`--base` 可省，默认是这个模块 Spec 第一次提交之前的状态），合并前看 `outside` 是不是 0。

### `/spec-guard:milestone-mark`

记录用法草案的一个里程碑已确认：`--draft spec/usage/<需求>.md --milestone M<n>`，先预览、`--confirm` 才在草案的 Milestones 表之后写一行
`<!-- spec-guard: milestone M<n> confirmed <模块, …> -->`。阶段提示报「里程碑停点」时，agent 先按本里程碑的典型用法实际跑一遍、把证据给你看，
你明确说通过后才用它记下，阶段提示随后转到下一个模块；你说不通过就在本里程碑补任务或改草案。确认后里程碑又加了模块，记录失效，
新模块做完后会再停一次。拒绝（退出 2、不写文件）：里程碑不存在、有模块没完成、前面还有没确认的里程碑。

### `/spec-guard:checkout-role`

多模块并行开关为 on 时，给当前 checkout 标角色：`set --module <id>` 或 `set --coordinator`，`clear` 清除，`show` 查看；先预览、`--confirm` 才写。
标记在本 checkout 的 git 目录里，不进版本库。模块 checkout 的阶段提示只指向自己的模块，协调 checkout 不建议构建；`/map` 据此给出各模块 worktree 的进度。
开关不是 on 时拒绝写入（退出 3），阶段提示也不读标记。

## 加需求

### `/spec-guard:add-module`

参数：`[需求上下文]`

在模块检查点（当前模块还没开始或已完成）把新需求作为模块插进能力图。agent 根据能力图提出 id、职责、依赖、插入
位置，各带一句理由；预览新行、新 Build order 与 diff，确认后加 `--confirm` 写入。只改 `spec/CAPABILITY-MAP.md`。

- 当前模块做到一半时拒绝；确需先做新模块时加 `--interrupt` 显式插队，预览会列出被暂停的模块。
- `--proposal <id> --platform <github|gitlab> --target <目标>`：从已接受的 Proposal 晋级，四项字段全部取自远端。
- 项目有用法草案时，预览多一段「用法草案」：列出草案文件、锚点所在的里程碑，并提醒把新模块加进对应草案的里程碑表（本命令不改草案）。
- 同一个需求写入第 2 个模块后，如果还没有草案覆盖这批模块，结果末尾提醒写 Spec 前先出用法草案。

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
| `/spec-guard:history-integrity` | 只读：`verify`（默认）核对旧布局项目归档文件的 SHA-256；`migration-preview` 预览旧证据的迁移 |

## 报告

### `/spec-guard:map`

参数：`[--all] [--json]`

只读的模块进度表：按开发顺序列出每个模块的作用、状态（✅ 已完成、🔨 进行中、⏸ 挂起（原因）、⛔ 阻塞：等被挂起的
模块、🟢 可以开始（只表示依赖都已完成，不代表本轮要做）、○ 未就绪：缺哪个依赖）与 Spec、Plan 的审查状态；表头给合计、关键卡点（挂起的模块按依赖链挡住了
谁；只算挂起造成的阻塞，等人交付、等审查结论看不到）、待批准、下一个 gate、里程碑停点（有用法草案、某个里程碑做完还没确认时）、未合入主线与未推送的提交数。进行中与挂起两格带距今多久（上次勾选、已挂多久），取自已提交的
git 历史，不设阈值；工作区比 HEAD 多勾了几项时，进行中一格再写"N 项勾选未提交（最后一次提交多久前）"，JSON 另给开工
时间、最后一次提交时间、批准节奏的生效值和来源，以及每个模块 gate 检查点的总数与已勾数（见 `interface.json` 的 `progressFacts`）。已完成与未就绪默认折叠，`--all` 全部展开。`--json` 给全量
结果（`schemaVersion` 1，字段与稳定性承诺见插件根目录 `interface.json` 的 `mapView`；里程碑停点在顶层 `milestoneStop`，interface 1.13 起；按它派活的调用方在停点期间不开任何新模块，不论属于哪个里程碑或草案；每个模块的接管档位与来源在 `takeover`，interface 1.15 起；Spec、Plan 能否由 Codex 批及原因在 `codexRoute`，interface 1.16 起；Spec、Plan 每轮 Codex 审查的轮次、阻断数与被审文件 sha256 前 12 位在 `reviewRounds`，interface 1.17 起；新流程模块的档位在 `tier`（老模块为 null），`step` 多了 `design`、`regression` 两个取值，interface 1.18 起；新流程模块的需求确认在 `requirementConfirm`（状态、确认人只能是 user、确认提交时间、需求文档指纹；老模块为 null），`codexRoute` 多了取值 `requirement`，interface 1.19 起；新流程模块技术方案的审查与批准在 `designApproval`（状态、放行人、审查者厂商与是否同厂商、报告 sha256、每一轮；老模块与 bug、small 为 null），interface 1.20 起；新流程模块的 Plan 自动批准，`reviewApprovedBy`、`codexRoute` 的 plan 一项多了取值 `auto`，interface 1.21 起；`takeover` 改为 `design`、`merge`、`release` 三项的生效值，加 `designForcedBy`，`spec`、`plan` 两项只剩老流程含义、标为 deprecated，interface 1.22 起；旧的 `autonomy` 本版仍在、标为 deprecated），供其他插件读取，可用
`--project <路径>` 从项目外调用。退出码：3 没有能力图，4 能力图或模块文件读不出，2 参数或路径错误。

### `regression_view.py`（给其他插件读）

```bash
python3 -B hooks/regression_view.py --json --project <路径> --module <id> [--ref <git ref>]
python3 -B hooks/regression_view.py --json --project <路径> --usage <需求>
```

只读：把新流程模块的回归用例读成 JSON（编号、标题、步骤、预期、执行方式、命令、证据、覆盖的成功标准、是否受影响的老功能、每条用例内容的 sha256），
连同整份文档的 sha256 与问题列表；`--ref` 读那个提交上的版本（在临时目录里做本地克隆，文档按原始 blob 读）；`--usage` 读多模块需求的联调回归。
回归 Markdown 只在这里解析，autopilot、module-crew 读它的输出；字段与退出码见 `interface.json` 的 `regressionView`（interface 1.23 起）。
退出码：3 不是新流程模块、文档还没写或那个提交上没有，4 读不了，2 参数错误或模块不在能力图上。

### `/spec-guard:cost-report`

参数：`<module-id> [更多模块] [--prices <价格文件>] [--json]`

只读：离线读取本机 Claude Code 与 Codex 的会话记录，按 todo 的勾选提交切出每个 task 的时间窗，统计主代理与子代理
的 token 与主会话轮次。只有给了 `--prices` 才折算金额。退出码 2：todo 没有提交历史，时间窗切不出来
（不是用量为 0）。

## 命令对照

Codex 不加载插件的斜杠命令，对它说下面这些话即可；说法里点出 skill 名（多数是 `spec-guard-ops`），agent 会照那个 skill 里对应的一节去做。
会写文件或远端的操作同样先给你看预览，你确认后才执行。

| 功能 | Claude Code | Codex（直接对 agent 说） |
|---|---|---|
| 安装或移除约定 | `/spec-guard:setup-convention`、`/spec-guard:teardown-convention` | 「用 spec-guard-ops 在这个项目里安装约定」／「用 spec-guard-ops 移除这个项目的约定」 |
| 查看阶段、校验产物 | `/spec-guard:phase`、`/spec-guard:verify-artifacts` | 「用 spec-guard-ops 查看阶段」／「用 spec-guard-ops 校验产物」 |
| 查看或设置项目默认事项后端 | `/spec-guard:tracker-default` | 「用 spec-guard-ops 查看默认事项后端」 |
| 查看或设置项目配置 | `/spec-guard:config` | 「用 spec-guard-ops 查看项目配置」／「用 spec-guard-ops 把批准节奏设为 combined」 |
| 挂起或恢复在等外部条件的模块 | `/spec-guard:module-suspend` | 「用 spec-guard-ops 挂起模块 <id>，原因是……」／「用 spec-guard-ops 恢复模块 <id>」 |
| 会话目录不是项目目录时指向项目 | `/spec-guard:link-project` | 「用 spec-guard-ops 把这个会话指向项目 <路径>」 |
| 记录 Spec 或 Plan 的批准状态 | `/spec-guard:review-mark` | 不用你说：你回复批准后，agent 自己用 spec-guard-ops 的 review-mark 记下 |
| 记录用法草案的里程碑已确认 | `/spec-guard:milestone-mark` | 不用你说：你判定里程碑通过后，agent 自己用 spec-guard-ops 的 milestone-mark 记下 |
| 多模块并行时给 checkout 标角色 | `/spec-guard:checkout-role` | 「用 spec-guard-ops 把这个 checkout 标为模块 <id>」／「……标为协调」 |
| 快速插入新模块 | `/spec-guard:add-module` | 「用 spec-guard-ops 插入一个新模块」，再说清需求 |
| Proposal 提交、审查、预检、证明、收尾（晋级用 `add-module --proposal`） | `/spec-guard:proposal-submit`、`proposal-review`、`proposal-promotion-preflight`、`proposal-promotion-proof`、`proposal-closeout` | 「用 spec-guard-ops 提交 Proposal <id>」／「审查 Proposal <id>」／「证明 Proposal <id> 已晋级」／「收尾 Proposal <id>」 |
| 文档治理 | `/spec-guard:documentation-*` 三条命令 | 「用 spec-guard-ops 预览文档基线」／「预览模块 <id> 的文档影响」／「核验模块 <id> 的文档交付」 |
| 能力历史（verify 核对与迁移预览） | `/spec-guard:history-integrity` | 「用 spec-guard-ops 核对能力历史」 |
| 会话协作（已移到 agent-relay） | 安装 agent-relay 后用 `/agent-relay:collaboration` | 安装 agent-relay 后说「加入本机联调」 |
| 本地事项 | `/spec-guard:local-ticket-ledger`、`/spec-guard:ticket` | 「查看本地事项账本状态」／「看看本地事项」／「记一个 bug：……」 |
| 本地事项核验、归档、恢复与交接 | `/spec-guard:local-ticket-portability` | 「核验本地事项账本」／「把本地事项归档到 <目录>」 |
| 模块进度表（含关键卡点） | `/spec-guard:map` | 「用 spec-guard-ops 看模块进度表」 |
| 模块成本报告 | `/spec-guard:cost-report` | 「用 spec-guard-ops 出模块 <id> 的成本报告」 |
