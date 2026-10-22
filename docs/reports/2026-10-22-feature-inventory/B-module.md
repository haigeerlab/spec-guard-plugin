# B 模块生命周期：功能点清单（spec-guard，commit 85a1f560）

说明
- 路径省略前缀：`hooks/` = `plugins/spec-guard/hooks/`，`cmd/` = `plugins/spec-guard/commands/`，`SKILL` = `plugins/spec-guard/skills/spec-guard-ops/SKILL.md`，`iface` = `plugins/spec-guard/interface.json`。
- 「默认」列：「开」= 无需任何开关就生效；「按需」= 只有被调用才运行（斜杠命令／脚本），不是自动行为；「关」= 需要开关。写类动作一律「预览→`--confirm`」两段式，下面不再逐条重复，只在例外处注明。
- 能力图 id 来自 `spec/CAPABILITY-MAP.md` 的模块表；「（无独立 id）」表示在能力图里找不到单独的模块，来源写在 CHANGELOG 或别的模块 Spec 里。
- 「需求疑点」只写有依据的；「无」表示没有看出问题。
- 与本区相关但不在 B 区代码里的判据（`module_stage.py` 的 `review_state`／`gate_checkpoints`／`SUSPEND_MARKER`、`capability_map.parse_map`、`project_config.module_concurrency`）只作为「依赖」引用，不单列。

---

## B1 中途插入模块（add-module / module-insert.py）

| # | 功能点 | 它做什么 | 触发／入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| B1.1 | 中途插入模块（总功能） | 在「模块检查点」把一个新模块（id／职责／依赖／锚点）校验后插入 `spec/CAPABILITY-MAP.md` 的模块表和 Build order，只改这一个文件 | `/spec-guard:add-module`；`python3 hooks/module-insert.py` | 按需（不自动） | hooks/module-insert.py:124-306；cmd/add-module.md | module-insert、module-interrupt、insert-existing-spec | 能力图模块表的行本来就是一行 Markdown，agent-skills 的 spec 流程也能直接编辑；插件的价值在「校验+不破坏已有行」。但 CAPABILITY-MAP 里 module-insert 的描述写「with a spec skeleton」，代码（module-insert.py:6-8,271-273）明确不建骨架——文档与实现不一致 |
| B1.2 | 对话里先提议四项并各给一句理由 | 命令说明要求 agent 读能力图后提出 id、responsibility、depends-on、anchor，每项一句针对实际模块的理由 | cmd/add-module.md（「先读 spec/CAPABILITY-MAP.md…」） | 按需 | cmd/add-module.md:27-34；SKILL 的 add-module 节（284-） | module-insert | 这是对 agent 的行为指令（提示词），不是代码保证；可能与上游 agent-skills 的「提需求」流程重叠 |
| B1.3 | 预览再 `--confirm` 两段式 | 不带 `--confirm` 只打印新行／新 Build order／diff；`--confirm` 重跑全部校验后才原子写 | `--confirm` 旗标 | 预览默认 | hooks/module-insert.py:266-290,446-471；cmd/add-module.md 「等用户对预览结果给出明确确认」 | module-insert | 无（人工闸门是核心价值）。但「用户改了任一字段必须重新预览」是纯文字规则，无代码保证 |
| B1.4 | id 格式校验 | id 必须是 kebab-case（`MODULE_ID`），否则拒绝 | 预览／确认 | 开 | hooks/module-insert.py:146-147；capability_map.py:7 | module-insert、audit-small-cleanups（复用唯一 MODULE_ID） | 无 |
| B1.5 | 职责校验 | 职责不得为空、必须单行 | 同上 | 开 | hooks/module-insert.py:149-153 | module-insert | 无 |
| B1.6 | 依赖参数格式校验 | `--depends-on` 逗号分隔；`—`／`-`／空表示无；含空项或重复项拒绝 | 同上 | 开 | hooks/module-insert.py:41-50,155 | module-insert | 无 |
| B1.7 | 依赖存在性／顺序校验（间接） | 插入后整张图再走严格解析，依赖必须是图里已有模块且不得出现在自己之后（由 `parse_map` 抛错，转成「插入后的能力图未通过严格校验」） | 同上 | 开 | hooks/module-insert.py:217-221；capability_map.py:195-215 | module-insert、phase-and-verification | 无；注意这条校验没有自己的明确错误信息，报错文案取决于 parse_map |
| B1.8 | 锚点校验 | `anchor` 必须是 `end` 或 `after:<已在模块表里的 id>`，且该 id 必须在 Build order 中 | 同上 | 开 | hooks/module-insert.py:157-166,181-185,196-198 | module-insert | 无 |
| B1.9 | 围栏代码块内的示例表／示例 Build order 不当真 | 先把围栏内行置空再定位模块表与 `Build order:` 行，编辑仍作用于原始行 | 内部 | 开 | hooks/module-insert.py:61-101,176-187 | module-insert | 无（防御性，属实际故障模式） |
| B1.10 | Build order 分段插入 | 锚点在某个 `→` 段里就插到该段之后；锚点在并行（逗号）段里则插到整段之后；`end` 追加末尾 | 同上 | 开 | hooks/module-insert.py:103-110,192-203 | module-insert、proposal-add-module-promotion | 无 |
| B1.11 | 插入后严格重解析 + 新模块断言 | 把新文本写到临时文件重新 `parse_map`，并断言新模块同时在模块表与 Build order 中 | 同上 | 开 | hooks/module-insert.py:113-121,212-221 | module-insert、audit-remediation | 无 |
| B1.12 | 「已有内容不变」守卫 | 比对插入前后：`## 目标` 摘要、每个旧模块的行摘要、旧模块在表中和 Build order 中的相对顺序都不得变，否则拒绝 | 同上 | 开 | hooks/module-insert.py:223-242；spec-digest.py（唯一指纹算法） | module-insert | 与 B1.11 的严格解析有一定重叠；但对 Proposal 流程需要，合理 |
| B1.13 | 拒绝在「当前模块做到一半」时插入 | 当前模块 todo 既有已勾又有未勾项就拒绝，提示先完成 | 预览／确认 | 开 | hooks/module-insert.py:136-141；module_stage.project_stage | module-insert | **疑点**：这是插件替用户决定「不许打断」，而用户其实随时可用 `--interrupt` 绕过，等于一道只要加旗标就过的软闸门；真实用户是谁、被它拦下过多少次没有证据 |
| B1.14 | 显式插队 `--interrupt` | 当前模块做到一半时仍允许插入，预览写明被暂停模块及进度（已勾/总数）；其他模块同时做到一半不影响；不改 state.json | `--interrupt`（预览与确认都要带） | 关（需显式旗标） | hooks/module-insert.py:142-144,400-406；cmd/add-module.md 「插队」段 | module-interrupt | 「插队」与 B3「挂起」是两个相邻概念，用户要自己分辨（命令文档专门写了区别）；可能过度设计，但属于已落地行为 |
| B1.15 | 插入后当前模块变化预览 | 预览说明插入前后「当前模块」是否改变；插队后仍是被暂停模块时提示用户改 `.agent/state.json` 的 `activeModule` | 预览输出 | 开 | hooks/module-insert.py:244,396-406 | module-insert、module-interrupt | 提示用户手改 `.agent/state.json`，说明「当前模块」概念依赖一个人工维护的状态文件，插件自己又不写——流程有缝 |
| B1.16 | 同 id 本地 Proposal 冲突警告 | 本地存在 `spec/proposals/<id>.md` 时在预览加警告：之后若发布会报 in-map | 预览输出 | 开 | hooks/module-insert.py:246,257,411-414 | module-insert、proposal-review-in-map | 只服务 Proposal 流程；若 Proposal 本身是过度设计，这条跟着是 |
| B1.17 | `spec/<id>.md` 已存在时的提示 | 不拒绝，只提示插入后阶段为 NEEDS_PLAN（视为已批准），Spec 若未批准要先批准再确认 | 预览输出／确认输出 | 开 | hooks/module-insert.py:168,323-325,407-410 | insert-existing-spec | 「视为已批准」恰恰是为没有批准标记的旧项目兼容；与 B2 的批准标记体系并存，增加心智负担 |
| B1.18 | 原子写、仅改能力图、保留文件权限 | 同目录临时文件 + `os.replace`，保留原 mode；不建 Spec 骨架、不碰 tasks/、state.json、proposals/、Git | `--confirm` | 开 | hooks/module-insert.py:266-290 | module-insert | 无 |
| B1.19 | 写后阶段提示回显 | 写完后重新算当前阶段，输出「当前阶段提示」（含 MODULE_DONE 时被暂停模块、下一个未完成模块） | `--confirm` 输出 | 开 | hooks/module-insert.py:292-320 | module-insert、module-interrupt | 无 |
| B1.20 | 从已接受的 Proposal 晋级 `--proposal` | 字段（id、职责、依赖、锚点）全取自远端已发布的 Proposal；必须 `--platform`＋`--target`；与手填四字段互斥；内嵌晋级预检；本地能力图必须与基线提交一致；插入结果必须能被 promotion-proof 证明 | `add-module --proposal <id> --platform github|gitlab|local --target …` | 按需 | hooks/module-insert.py:328-379,474-500；cmd/add-module.md 「从已接受的 Proposal 晋级」 | proposal-add-module-promotion、proposal-label-acceptance、promotion-proof-diagnostics | **疑点**：整套 Proposal（发布→Issue 标签→预检→晋级→证明→收尾）是一条很重的流程，在「个人／小团队本地多模块」场景下是否有真实使用者，没有证据；同时它把 GitHub/GitLab 状态读取塞进 spec-guard，边界上更像「事项／工单」插件的职责 |
| B1.21 | 需求先确认再提议 | 对话里新提出的需求，先按共享检查点规则「需求确认」总结并问「是否说完」，下一轮再往下 | cmd/add-module.md「这个需求是用户在对话里新提出的…」 | 按需 | cmd/add-module.md:17-18 | requirement-confirm | 纯提示词规则，靠 agent 自觉；与上游 agent-skills 的 interview／spec 阶段（需求澄清）重叠 |
| B1.22 | 「是否该开新模块」判断 | 命令说明提示：返工或修订已完成的模块不开新模块，改在 todo 追加；只盘点既有实现的并入相邻模块 | cmd/add-module.md 末段；SKILL add-module | 按需 | cmd/add-module.md:108-113 | rework-in-place | 同上，纯提示词 |
| B1.23 | 留痕需求改走 Proposal 的提示 | 命令说明提示：需要留审查记录的新增改走 Proposal 流程 | cmd/add-module.md 末句 | 按需 | cmd/add-module.md:113-115 | module-insert（说明文字） | 同 B1.20 |
| B1.24 | 插件根目录定位样板 | 每条命令里一大段 shell：CLAUDE_PLUGIN_ROOT→PLUGIN_ROOT→`codex plugin list` 解析，全失败时报「定位失败，不代表未安装」 | 命令说明里的 bash 片段（add-module、review-mark、map、module-suspend、checkout-role 五条重复） | 开 | cmd/add-module.md:36-72（其余四条命令同款） | command-plugin-root | 五份拷贝的样板，易漂移；是宿主「命令不自带插件根目录」的绕路，本该由宿主（Claude Code/Codex）解决 |

---

## B2 批准标记（review-mark / review_mark.py）

| # | 功能点 | 它做什么 | 触发／入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| B2.1 | 批准标记（总功能） | 在 `spec/<id>.md` 或 `tasks/<id>/plan.md` 里写一行 HTML 注释标记（pending／approved），让后续会话和阶段提示读得到评审状态；预览→`--confirm`，写后读回核对 | `/spec-guard:review-mark`；`python3 hooks/review_mark.py --module --target spec|plan|both --state pending|approved` | 按需 | hooks/review_mark.py:64-155；cmd/review-mark.md；SKILL review-mark 节（244-） | review-approval-marker | **疑点**：脚本自己承认「无法检查用户是否批准过，标记只是记录不是授权来源」（review_mark.py:1-8,136-138）。它的真实作用是让 phase-guard 注入的「等待批准」提示有数据源；若用户靠对话本身就能表达批准，这套状态机可能是为了「让 hook 能读」而造的，价值取决于 phase-guard 注入这个设计是否保留 |
| B2.2 | `pending` 标记 | 把文件标为待用户审阅；也可由 agent 写文件时自带这一行 | `--state pending` | 按需 | hooks/review_mark.py:55-57 | review-approval-marker | 无 |
| B2.3 | `approved` 标记（Plan） | Plan 批准：`<!-- spec-guard: review approved -->` | `--target plan --state approved` | 按需 | hooks/review_mark.py:58-59 | review-approval-marker | 无 |
| B2.4 | Spec 批准 digest | Spec 批准写成 `review approved <12位digest>`，digest 是「去掉标记行后的文本」指纹；之后内容有变读作 `revised`，需复审 | `--target spec --state approved` | 开 | hooks/review_mark.py:60-61,122；module_stage.py:40-96（`review_digest`／`review_state`）；spec-digest.py（唯一算法） | review-approval-marker、review-marker-blank-line | 把「批准后又被改过」自动检出，是有明确故障模式的设计；但 Plan 没有 digest，两边不对称（Plan 批准后改动检不出），无依据说明这是有意的取舍 |
| B2.5 | 一次标两份 `--target both` | 合并审（`reviewCadence=combined`）时同时标 Spec 和 Plan | `--target both` | 按需 | hooks/review_mark.py:85 | review-approval-marker | 无 |
| B2.6 | 先批 Spec 才能批 Plan | 单独把 Plan 标 approved 时，Spec 若是 pending／revised／invalid 则拒绝（退出 2）并提示需用户单独明确批准 Spec | `--target plan --state approved` | 开 | hooks/review_mark.py:101-111 | review-approval-marker、review-marker-legacy-projects | 是对 agent 的硬约束，防止「Plan 批了顺带当成 Spec 也批了」；合理，但是靠字符串状态而非用户身份，仍可被 agent 自行 `both` 绕过 |
| B2.7 | legacy 项目兼容：无标记 Spec 不阻塞 Plan | Spec 没有任何标记（旧项目）时，单独批 Plan 不拒绝，只提示本次只记录 Plan | 同上 | 开 | hooks/review_mark.py:101-107,125-127 | review-marker-legacy-projects | 为旧项目向后兼容；不是疑点，但意味着「无标记＝视为批准」与「无标记＝没跟踪」并存 |
| B2.8 | 标记位置规则 | 已有标记原地替换；没有则放在第一行标题之后；无标题则放文件开头 | 内部 | 开 | hooks/review_mark.py:26-52 | review-approval-marker | 无 |
| B2.9 | 标记前后留空行 | 写标记时保证前后都是空行（兼容 oxfmt 等 Markdown 格式化器），在算 digest 之前补好 | 内部 | 开 | hooks/review_mark.py:26-35,60-61 | review-marker-blank-line | **疑点**：为迁就某个格式化器而改写算 digest 的文本；属于「下游工具兼容」细节，是否该由使用者调格式化器配置解决，无证据 |
| B2.10 | 无效标记拒绝 | 多于一行或写法不符（invalid）时拒绝并让用户手改；围栏代码块内同样文字当示例 | 预览／确认 | 开 | hooks/review_mark.py:97-100；module_stage.py:46-60 | review-approval-marker | 无 |
| B2.11 | 前置文件检查 | 非法 id（`not-a-module-id`）、能力图读不了（`map-unreadable`）、模块不在图里、目标文件缺失或读不了，一律退出码 2、不写 | 预览／确认 | 开 | hooks/review_mark.py:73-95 | review-approval-marker | 无 |
| B2.12 | 预览内容：diff、digest、批准后状态 | 打印每个文件的 unified diff、Spec 当前 digest、写入后各文件的评审状态；已是目标状态则提示无需改动 | 预览输出 | 开 | hooks/review_mark.py:112-127 | review-approval-marker、review-handoff-content | 无 |
| B2.13 | 批准前提醒用户看过内容 | 记 approved 的预览带上文件行数，提醒确认用户已在对话里看到内容；只给链接或一句概述不算交审（提醒不拒绝） | 预览输出 | 开 | hooks/review_mark.py:128-138 | review-handoff-content | 无；但这是「脚本输出一段提示词给 agent」，靠自觉 |
| B2.14 | 写后读回核对 | 写完重新读文件，状态不符就报 `readback-mismatch`；写失败报 `file-unwritable` | `--confirm` | 开 | hooks/review_mark.py:144-153 | review-approval-marker | 无 |
| B2.15 | 批准来源规定：对话或收件枢纽转来 | 文档规定 approved 只来自用户在当前对话的明确批准，或已登记收件枢纽按 session-protocol 转来（带事项号与用户原话）的【用户答复】；含糊的话、“继续”、会话自称都不算；获批后先写标记再改代码 | cmd/review-mark.md「approved」条；SKILL | 开（规则文字） | cmd/review-mark.md:62-70；SKILL review-mark 节 | hub-relayed-approval、hub-only-reply | **疑点（越界）**：「收件枢纽／session-protocol／事项号」是 decision-inbox／module-crew 的契约。spec-guard 在自己的规则里写明识别对方契约，使两个插件紧耦合；Spec 里写「不解析枢纽消息、不依赖 decision-inbox」，但规则文字已经依赖其格式 |
| B2.16 | 交审内容要点（卡片小项） | 命令说明规定交审在对话正文按固定小项列内容：Spec 依次给目标、做／不做、假设、验收标准、附带小决定；Plan 依次给分几步、改哪些文件、风险、中途停点；之后写“注意”“批了会怎样”，推荐答复放一个可复制代码块 | cmd/review-mark.md「什么时候写」 | 开（规则文字） | cmd/review-mark.md:50-61；SKILL review-mark 节 | review-handoff-content、review-card-sections、hub-only-reply、review-one-module | **疑点**：这是在规定「对话里怎么写」，纯提示词；与 decision-inbox 的卡片模板需要「对齐」（需求文字里就说「与决策收件箱卡片对齐」），也与 agent-skills 的 spec／plan 技能的输出格式有交叠；小项名一旦被 decision-inbox 改动，两边要联动改 |
| B2.17 | 既有项目不必补标记 | 没有标记的旧文件判定照旧；要给旧 Spec 补 approved 须单独问用户，不得依据此前含糊答复补记 | cmd/review-mark.md | 开 | cmd/review-mark.md:71-73 | review-marker-legacy-projects | 无 |
| B2.18 | 交审一次一个模块 | 一次交审只放一个模块产物；确需多个时按模块分组 | 共享检查点规则 + 约定块 | 开（规则文字） | SKILL 共享检查点规则（非 B 区文件，仅引用） | review-one-module | 纯提示词规则 |

---

## B3 挂起／恢复模块（module-suspend / module_suspend.py）

| # | 功能点 | 它做什么 | 触发／入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| B3.1 | 挂起模块（总功能） | 在 `tasks/<id>/todo.md` 追加一行 `<!-- spec-guard: suspended -->`，选当前模块时跳过它、保留 Build order 位置，阶段提示报告 `Suspended: <id>`；永不自动恢复 | `/spec-guard:module-suspend`；`module_suspend.py --suspend <id>` | 按需 | hooks/module_suspend.py:60-144；cmd/module-suspend.md；SKILL（200-） | module-suspend | 真实场景：「代码做完、只剩要等外部条件」。但「是否挂起」本可由用户在 todo 里自己写一行注释；若项目不用多模块并行，价值有限。和 B1.14 的插队概念相邻，需要用户理解两者区别 |
| B3.2 | 只能挂起已开工模块 | 必须有 Plan 和 todo，且至少一项未勾选；否则拒绝（`no-plan-or-todo`／`nothing-open`） | 预览／确认 | 开 | hooks/module_suspend.py:95-104 | module-suspend | 无 |
| B3.3 | 恢复模块 | 去掉标记和原因行，不改 state.json，模块回到原位；未挂起时拒绝（`not-suspended`） | `--resume <id>` | 按需 | hooks/module_suspend.py:118-122,129-131 | module-suspend | 无 |
| B3.4 | 挂起原因（可选） | `--reason "<一行>"` 在标记下一行记 `<!-- spec-guard: suspended-reason: … -->`，供 /map 显示；原因必须单行、非空、不含 `-->`、≤120 字符；给已挂起的模块带 `--reason` 只替换原因行 | `--suspend … --reason` | 关（不给就不记；规则要求只按用户说的写，不从上下文推断） | hooks/module_suspend.py:19-27,71-79,105-117 | map-view（挂起可选记原因）、module-suspend | 无；注意这条是在 `map-view` 模块下加的，不是 module-suspend 本身 |
| B3.5 | 旧版本兼容原因行 | 原因单独占一行，旧版只认标记那一行，照常识别挂起 | 内部 | 开 | hooks/module_suspend.py:19-20 | map-view | 无 |
| B3.6 | 预览：todo 改前改后＋挂起/恢复后的当前模块 | 打印 unified diff 与「current module after …」；恢复时若另一模块做到一半，说明它会显示为 Paused | 预览输出 | 开 | hooks/module_suspend.py:124-131 | module-suspend | 无 |
| B3.7 | 写后读回核对 | 写后再读 `module_state(...)["suspended"]`，不符报 `readback-mismatch` | `--confirm` | 开 | hooks/module_suspend.py:135-143 | module-suspend | 无 |
| B3.8 | 可选提醒（借宿主能力） | 挂起确认后问用户要不要设提醒；用户同意则用宿主持久提醒能力（Claude Code 桌面版的定时任务 `fireAt`）创建并读回；时间与内容由用户说；插件不保存提醒；宿主没有就让用户自己设 | cmd/module-suspend.md「提醒（可选）」；SKILL | 关（要用户同意） | cmd/module-suspend.md:74-86；SKILL 200-217 | module-suspend | **疑点（越界）**：设提醒是宿主（Claude Code 定时任务／Codex 自动化）的能力，插件只贡献一段提示词，且显式写「插件不保存提醒」。提示词里还点名了某个宿主的 `fireAt` 实现细节；没有任何代码支撑，有伪功能之嫌 |
| B3.9 | 挂起与「做到一半」脱钩 | 挂起模块不算 half，所以随后 add-module 不需要 `--interrupt`；`project_stage` 对挂起模块的处理 | 内部 | 开 | hooks/module_suspend.py:54-57；module_stage.py | module-suspend、module-interrupt | 无 |
| B3.10 | 挂起 vs 插队的使用边界 | 文档明确：临时插急事做完就回 → add-module --interrupt；要长期等 → 挂起；没开工的模块调顺序即可 | cmd/module-suspend.md | 开（规则文字） | cmd/module-suspend.md:40-44 | module-suspend | 无 |

---

## B4 进度表（map / map_view.py）

| # | 功能点 | 它做什么 | 触发／入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| B4.1 | 进度表（总功能） | 只读：读能力图、各模块 Spec／Plan／todo、`.agent/state.json` 与本地 git 引用，渲染成表格或 JSON；不写文件、不联网、不进每轮注入 | `/spec-guard:map [--all] [--json]`；`map_view.py` | 按需 | hooks/map_view.py:1-11,331-470,565-632；cmd/map.md；SKILL（121-） | map-view | 需求本身合理（整图一览）。但脚本已达 683 行，是区内最大的组件，承载了大量 JSON 字段，实际上是给 module-crew 等下游读的接口，需求来源可能更多来自姐妹插件而不是终端用户 |
| B4.2 | 六种状态判定 | 每个模块判为 done／in_progress／suspended／blocked／ready／not_ready（blocked＝上游被挂起模块挡住；ready＝依赖全部 done；not_ready＝缺依赖） | 内部 | 开 | hooks/map_view.py:34-35,388-410（状态赋值段落） | map-view | 「blocked」只覆盖挂起，外部等待看不到，文档自己承认（cmd/map.md） |
| B4.3 | 步骤判定 step | 进行中模块的当前步骤：spec／plan／build | JSON `modules[].step` | 开 | hooks/map_view.py:419-420 | map-view | 无 |
| B4.4 | 进度计数 | 每模块 `progress {done,total}`（todo 已勾／总数） | JSON／表格 | 开 | hooks/map_view.py:421 | map-view | 无 |
| B4.5 | 挂起原因显示 | 从 todo 读原因行；表格状态格写「⏸ 挂起（原因，已挂 N 天）」，没记原因写「未记原因」 | 表格／JSON `suspendedReason` | 开 | hooks/map_view.py:51-60,498-501,520-522 | map-view、module-suspend | 无 |
| B4.6 | 阻塞等谁（blockedOn） | 被挂起模块（沿依赖闭包）挡住的模块列出「等 X、Y」 | 表格「⛔ 阻塞：等 …」／JSON `blockedOn` | 开 | hooks/map_view.py:96-104,423-424,523-524 | map-view | 仅对「被挂起」成立；外部等待不显示 |
| B4.7 | 未就绪缺谁（missingDeps） | 依赖未完成的模块列出缺哪些依赖 | 表格「○ 未就绪：缺 …」／JSON | 开 | hooks/map_view.py:425,527 | map-view | 无 |
| B4.8 | 挡住个数 blocks | 每个模块按传递依赖算「挡住了 N 个后续未完成模块」 | JSON `blocks {count,ids}`；表格 | 开 | hooks/map_view.py:377,426,521 | map-view | 无 |
| B4.9 | 可开工列表 | 状态为 ready 的模块；表格写「🟢 可以开始」；开关 on 时写「可同时开工」，并在 JSON 顶层给 `startable.modules`（按 Build order） | 表格／JSON | 开；`startable` 仅在并行开关 on 时 | hooks/map_view.py:525-526,263-281 | map-view、map-startable | 「可以开始」只是依赖满足，并不保证用户真要开始；在串行（开关 off）项目里等价于「下一个未完成」，意义有限 |
| B4.10 | 关键卡点行 | 表头列出所有挂起模块、原因、挡住谁；无则写「关键卡点：无」；按挡住数降序 | 表头／JSON `bottlenecks` | 开 | hooks/map_view.py:446-447,461-462,574-582 | map-view | 无 |
| B4.11 | 待批准行 | 汇总所有 Spec／Plan 处于 pending／revised／invalid 的模块 | 表头／JSON `awaitingReview` | 开 | hooks/map_view.py:37,448-449,583-585 | map-view、review-approval-marker | 无 |
| B4.12 | 下一个 gate | 当前模块的 `next_gate` 标题 | 表头／JSON `nextGate` | 开 | hooks/map_view.py:459,586-587 | map-view、review-approval-marker | 判据在 module_stage，本处只显示 |
| B4.13 | 审查状态列 | 每个模块 Spec／Plan 的评审状态（✔／待批准／改过待重审／标记无效／无标记） | 表格「审查」列／JSON `review` | 开 | hooks/map_view.py:79-85,546-552 | map-view、review-approval-marker | 无 |
| B4.14 | 外部审查状态 | 每模块 `externalReview`：none／recorded／declined（读 Spec 与 todo 的「外部审查意见」小节和拒绝标记） | JSON `externalReview` | 开 | hooks/map_view.py:88-93,428；module_stage.external_review_state | plugin-interface、delegate-review-hint | **疑点（越界）**：「外部审查意见小节」是为 delegate 插件的审查结果造的格式，spec-guard 要解析并发布这个值，意味着知道另一个插件的产出物位置；耦合方向是 spec-guard→delegate |
| B4.15 | 最后一次勾选时间／勾选次数 | 取自一次 `git log -p -- tasks/*/todo.md`：`lastTickAt`／`firstTickAt`／`tickCommits`；表格进行中格显示「上次勾选 N 天前」；取不到则为空并在 stderr 说明 | 表格／JSON | 开 | hooks/map_view.py:123-170,432-440,513-519 | stall-signals | 只给时间不设阈值，克制；但 `git log -p` 全量扫 todo 历史，大仓库可能慢（超时 60 秒，map_view.py:134-139） |
| B4.16 | 挂起开始时间 | `suspendedAt`：最近一次触碰挂起标记的提交时间；表格「已挂 N 天」 | 表格／JSON | 开 | hooks/map_view.py:123-170,440,498-501 | stall-signals | 同上 |
| B4.17 | 未提交勾选数 | `uncommittedTicks`：工作区 todo 已勾数减 HEAD 中已勾数（不低于 0）；表格进行中格写「N 项勾选未提交（最后一次提交 X 前）」 | 表格／JSON | 开 | hooks/map_view.py:321-359,441-444,515-517 | map-progress-facts | 无明确使用者证据：需求来自「下游插件想判断模块是否卡住」 |
| B4.18 | Spec 首次提交时间 startedAt | 第一次提交 `spec/<id>.md` 的时间；文档承认 Spec 批准后才提交时会比实际开工晚 | JSON `startedAt` | 开 | hooks/map_view.py:331-358,444 | map-progress-facts | 自述不准确（是提交时间不是开工时间），属于「给了一个容易被误用的字段」 |
| B4.19 | HEAD 提交时间／未合入／未推送 | `head {sha,branch,unmerged,unpushed,committedAt}`；表头写「未合入主线：N 个提交；未推送：N 个提交」，没有上游写「判断不了」 | 表头／JSON | 开 | hooks/map_view.py:106-120,588-598 | map-view、map-progress-facts | 「未合入主线」「未推送」是 git 状态，与模块进度关系弱，更像 git 工具／宿主能展示的信息 |
| B4.20 | reviewCadence 回显 | 顶层 `reviewCadence {value,source}`（separate／combined，与 `/spec-guard:config` 一致） | JSON | 开 | hooks/map_view.py:362-366,466；project_config.summary | map-progress-facts | 为下游插件重复暴露一个本来可从 `.agent/config.json` 读的值（接口文档自己说读者不必开配置文件，只对 moduleConcurrency） |
| B4.21 | gates 计数 | 每模块 `gates {total,done}`：todo 里 gate 检查点总数与已勾数（判据同「下一个 gate」）；无 todo 为 null；表格不显示 | JSON | 开 | hooks/map_view.py:73-76,429；module_stage.gate_checkpoints | map-gate-count、checkpoint-default-report、cn-checkpoint-gates | 纯给下游（需求写「算问用户的基准次数」）；表格不用，说明主要面向机器读者 |
| B4.22 | 折叠规则与 `--all` | 已完成（除最后一个）与未就绪的模块默认折叠成一行「其余 N 个已完成／N 个未就绪」；`--all` 全展开 | 表格 | 开 | hooks/map_view.py:601-633 | map-view | 无 |
| B4.23 | 表格文本清洗与截断 | 去控制字符与竖线；职责截断到 40 字 | 渲染 | 开 | hooks/map_view.py:61-63,555-557 | map-view | 无 |
| B4.24 | JSON 输出 | `--json` 给全量不折叠结果，`schemaVersion` 1；字段只增不改；含 `generator {name,version}`、`project {root,title}`、`totals`、`history`（complete／shallow／unavailable） | `--json` | 按需 | hooks/map_view.py:451-467,675-677；spec/map-view.md | map-view、plugin-interface | 这是对外契约，增长到数十个字段；每加一个字段都要同步 interface.json 与回归，维护成本高 |
| B4.25 | 错误出口 | 退出码 3＝没有能力图（JSON `no-capability-map`）；4＝读不出（JSON `unreadable`）；2＝参数／路径错 | 退出码 | 开 | hooks/map_view.py:659-679 | map-view、map-read-failure | 无 |
| B4.26 | 浅克隆／无历史降级 | 浅克隆提示「较早的勾选可能看不到」；无 git 历史时不显示勾选与挂起时间；`SPEC_GUARD_MAP_NOW` 环境变量固定「现在」供回归 | 渲染 | 开 | hooks/map_view.py:432-434,473-480,592-593 | stall-signals | `SPEC_GUARD_MAP_NOW` 是测试后门，不影响用户 |
| B4.27 | 并行扩展字段（仅 moduleConcurrency=on） | JSON 增 `moduleConcurrency`、`buildOrderGroups`（Build order 分组）、`startable {modules,conflicts}`、每模块 `scope`、`worktree` | JSON／表格 | 关（开关） | hooks/map_view.py:263-281,468-469 | map-startable、checkout-role | 见 B6 |
| B4.28 | 并行边界重叠检测 | 对状态为 in_progress／ready 且有合法 scope 的模块，两两比较独占路径（相等或目录包含），列出冲突，表头写「并行边界重叠：…」 | 表头／JSON `startable.conflicts` | 关（开关） | hooks/map_view.py:166-177,269-276,595-597 | map-startable | 无 |
| B4.29 | 其他 worktree 进度扫描 | 列出本仓库其他 worktree 中带 `module <id>` 角色标记的，读它们的 todo 进度、是否有未提交改动、HEAD 是否已合入当前 HEAD；总预算 10 秒，超时只给路径、分支、HEAD | 表格尾缀「· worktree d/t 有未提交改动 未合入」／JSON `worktree` | 关（开关） | hooks/map_view.py:180-260,530-543 | checkout-role | **疑点**：一次 /map 要对每个 worktree 跑多条 git 命令（`status --porcelain`、`merge-base --is-ancestor`），超时预算 10 秒也是为了避免卡住——本质是在做「worktree 管理器」的活，与 module-crew 的运行层职责边界模糊 |
| B4.30 | 版本与标题回显 | `generator.version` 取自 `.claude-plugin/plugin.json`；标题取能力图 `# ` 行 | JSON | 开 | hooks/map_view.py:173-186 | plugin-interface、map-view | 无 |

---

## B5 完成验收勾选（gateTick / gate_tick.py）

| # | 功能点 | 它做什么 | 触发／入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| B5.1 | gateTick（总功能） | 在 `tasks/<id>/todo.md` 里把「最终验收」那一个 `[ ]` 勾成 `[x]`，只改这一格、保留行尾和其余文字，不提交 | `python3 hooks/gate_tick.py --project --module [--confirm]`（**没有斜杠命令**，interface.json `gateTick` 入口） | 按需 | hooks/gate_tick.py:22-77；iface 266-283 | gate-tick | **疑点**：是为 module-crew 的合并流程做的接口（Spec 里写「给使用方插件一个…命令」）。谁勾 todo 本是 agent 自己的编辑动作；专门造一个带预览的命令，只为了「让下游不用自己判最终 gate」，可能是为了一个下游而造 |
| B5.2 | 只在最终 gate 才勾 | 只当模块第一个未勾项恰是最后一个 gate 检查点时勾；否则拒绝 `not-at-final-gate` 并打印那一项 | 预览／确认 | 开 | hooks/gate_tick.py:55-66；module_stage.at_final_gate／gate_checkpoints | gate-tick、checkpoint-default-report、cn-checkpoint-gates | 无 |
| B5.3 | 已勾过不改 | 所有 gate 都已勾时退出 0 并说明还剩几项未勾 | 同上 | 开 | hooks/gate_tick.py:57-60 | gate-tick | 无 |
| B5.4 | 预览显示 | 打印行号、原行、「would become」，并说明确认后还剩几项未勾 | 预览输出 | 开 | hooks/gate_tick.py:65-72 | gate-tick | 无（interface 1.7 才修好预览显示原样，见 CHANGELOG 0.83.1 "gateTick 预览显示原样"） |
| B5.5 | 前置检查与短码 | `not-a-module-id`／`map-unreadable`／`not-in-map`／`todo-missing`／`todo-unreadable`／`no-gate`，一律退出 2 不写 | 预览／确认 | 开 | hooks/gate_tick.py:29-52 | gate-tick | 无 |
| B5.6 | 不判断用户是否批准 | 脚本不检查用户批准，调用方须已持有批准 | 文档 | 开 | hooks/gate_tick.py:1-8；iface 281 | gate-tick | 与 review-mark 同款「只是记录」属性；此处更要紧，因为勾的是「模块完成」 |
| B5.7 | 提交内含 gate 勾选（规则文字） | 最终 gate 批准包含提交时，先勾 gate、更新状态记录、列进待批准的提交清单一并提交 | 共享检查点规则 | 开（规则文字） | SKILL 共享检查点规则（非 B 区文件） | gate-tick-before-commit | 纯提示词 |

---

## B6 多模块并行：开关、角色标记、并行边界

| # | 功能点 | 它做什么 | 触发／入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| B6.1 | 并行开关 moduleConcurrency | `.agent/config.json` 中 `moduleConcurrency` 取 off／on（默认 off），off 时全部输出逐字不变；`/spec-guard:config` 预览确认后设置 | `.agent/config.json`；`/spec-guard:config` | **关**（可打开） | hooks/project_config.py（`module_concurrency`，B 区只调用）；iface 67-77 | module-concurrency-switch | **疑点**：整个并行层（B6.*、B4.27-29）都挂在这个开关下，且文档明说使用方是 module-crew；如果 module-crew 才是实际使用者，这些字段是否应该由 module-crew 自己维护，而非让 spec-guard 提供「规划层」 |
| B6.2 | 检查点角色标记（总功能） | 给每个 checkout 标角色 `module <id>` 或 `coordinator`，标记写在该 checkout 自己的 git 目录（`git rev-parse --git-path spec-guard/role`），不进版本库、不随 worktree 共享；阶段提示按角色改措辞 | `/spec-guard:checkout-role`；`checkout_role.py show|set|clear` | **关**（需开关 on） | hooks/checkout_role.py:1-177；cmd/checkout-role.md；SKILL（268-） | checkout-role、crew-interface | **疑点（越界）**：命令说明自己写「通常由运行时（例如 module-crew）在开 worktree 后调用」，用户不会自己跑；这是 module-crew 的运行态元数据，借 spec-guard 的 git 目录文件存放，边界上应属 module-crew |
| B6.3 | 模块角色 `module <id>` | 阶段提示另报告该模块状态，「下一步」只指向它，做完只提示交回协调会话，不建议切到别的模块、合并或推送 | 角色标记 + phase-guard | 关 | hooks/checkout_role.py:26-29,94-98；phase-guard 读取（非 B 区） | checkout-role | 同 B6.2 |
| B6.4 | 协调角色 `coordinator` | 阶段提示保留全局进度与批准约束，「下一步」改为统筹措辞，不建议 /build | 同上 | 关 | hooks/checkout_role.py:29,153-155 | checkout-role | 同 B6.2 |
| B6.5 | 开关 off 时一概不读标记 | `role()` 在开关非 on 时直接返回 none，不碰文件系统 | 内部 | 开（保证 off 行为不变） | hooks/checkout_role.py:94-98 | checkout-role、module-concurrency-switch | 无 |
| B6.6 | 标记安全读取 | 拒绝符号链接、特殊文件、超过 256 字节、多行或格式不符；不回显标记内容（只给固定短码） | 读 | 开 | hooks/checkout_role.py:26-27,57-85,101-104 | checkout-role | 无（防止本地文件注入 agent 上下文，有依据） |
| B6.7 | 设置／清除的前置检查 | 非 bare 仓库顶层才能设（`not-a-checkout`）；开关非 on 退出 3；`module <id>` 必须在能力图里；标记或其目录是链接则拒绝（`marker-unsafe`）；无变化提示 | `set`／`clear` | 开 | hooks/checkout_role.py:107-131 | checkout-role | 无 |
| B6.8 | 写后读回／并发变化检测 | 写后读回与写入不符退出 4（`concurrent-change`），提示用 `show` 查看，不自动重试 | `--confirm` | 开 | hooks/checkout_role.py:132-144 | checkout-role | 无 |
| B6.9 | `show` 只读查看 | 打印当前角色，开关未开时注明「不使用」 | `checkout_role.py show` | 按需 | hooks/checkout_role.py:162-166 | checkout-role | 无 |
| B6.10 | 并行边界 `## 并行边界` 一节 | 模块 Spec 可带该节（或英文 `## Concurrency boundary`），写独占路径和公共文件类别（全局配置／锁文件／迁移／测试资源）；唯一解析器；有固定错误码（bad-path、bad-category、duplicate-section、unknown-line、missing-exclusive） | Spec 内容；`module_scope.py` | 关（需开关） | hooks/module_scope.py:24-114 | module-scope-boundary | **疑点**：规定 Spec 里要写一个特定章节，是对使用者 Spec 格式的新增约束；真实使用者仍是 module-crew 运行层 |
| B6.11 | 越界检查 `scopeCheck` | 对比一个基线提交，把本模块的所有改动（已提交、未提交、删除、未跟踪）分为 exclusive／own／outside 并统计 outside 数；只报告不拦截；文本或 JSON | `module_scope.py check --module --base [--format json]` | 关（需开关；无斜杠命令） | hooks/module_scope.py:117-185；iface 78-108 | module-scope-boundary、crew-interface | 同 B6.10 |
| B6.12 | 并行边界校验（供 verify-artifacts） | 对未完成且有 Spec 的模块输出 `ok <n>`／`warn missing <id>`／`bad <code> <id>`／`unverified …`；开关非 on 时静默 | `module_scope.py validate`（被 verify-artifacts 调用） | 关（需开关） | hooks/module_scope.py:188-217 | module-scope-boundary | 无 |
| B6.13 | 协调会话汇总／当面批准规则 | 开关 on 时，协调会话据用户当面或枢纽转来的批准写标记；并行评估在能力图评审停点给出 | 规则文字 | 关 | iface 182（notes）；SKILL | concurrency-assessment、concurrency-rule-wording、hub-relayed-approval | 纯规则文字，并行层行为大量落在提示词里 |

---

## B7 姐妹插件探测与对外接口

| # | 功能点 | 它做什么 | 触发／入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| B7.1 | agent-relay 探针 | 只读判断 agent-relay 是否可用，输出一个 JSON：`state ∈ ready／not-installed／incompatible／runtime-not-ready／unknown`、`interface`、`required`、`message`；读失败一律 `unknown`，从不当成「未安装」 | `python3 hooks/agent_relay_probe.py --host claude|codex [--project]` | 按需（阶段注入不调用它） | hooks/agent_relay_probe.py:1-143 | collaboration-dependency、collaboration-command-retirement、agent-relay-interface-2 | **疑点（越界）**：会话协作已经拆成独立插件，spec-guard 为什么还要保留探针？映射里只说「ticket skill 仍在使用」；探针对 Codex 要起子进程 `codex plugin list --json`，对 agent-relay 的 `status` 命令也要起子进程。对一个「可选的消息发送」值不值，没有证据 |
| B7.2 | 接口版本区间判断 | 读 agent-relay 的 `interface.json`，主次版本在 `>=1.0,<3.0` 内为兼容；版本缺失或不在区间报 `incompatible` | 内部 | 开（探针内） | hooks/agent_relay_probe.py:23-26,84-89,113-120 | agent-relay-interface-2 | 区间宽松是为了「0.6.0 发布后不破坏」的前向兼容，每次对方升主版本都要来改一次——耦合成本 |
| B7.3 | agent-relay 运行时就绪检查 | 若其 `interface.json` 声明 `status` 命令，就执行（10 秒超时）读 `ready`；未就绪给出 `setup` 提示，且说明 spec-guard 不会代为安装 | 内部 | 开（探针内） | hooks/agent_relay_probe.py:92-105,121-127 | collaboration-dependency | 无 |
| B7.4 | 未安装时的迁移指引 | 探针返回固定文案，指向 `docs/migrations/2026-10-07-collaboration-split.md` | 探针输出 | 开 | hooks/agent_relay_probe.py:27-30 | collaboration-dependency | 一次性迁移指引长期保留在代码里 |
| B7.5 | Claude 侧插件记录读取 | 读 `~/.claude/plugins/installed_plugins.json` 与四处 `enabledPlugins`（用户／项目／本地／主检出本地设置），按 `projectPath` 限定，返回已启用插件的安装路径 | 内部（探针、delegate 提示共用） | 开 | hooks/sibling_plugins.py:60-84 | delegate-review-hint、collaboration-dependency | 这是在**逆向读取宿主私有记录文件**（installed_plugins.json、settings 里的 enabledPlugins），格式一变就失效；宿主若有官方的「某插件是否启用」API 应改用。依赖未文档化的内部格式是主要风险 |
| B7.6 | 主检出本地设置查找 | linked worktree 的本地设置在主检出里，用 `git rev-parse --git-common-dir` 或直接读 `.git` 文件两种方式找到 | 内部 | 开 | hooks/sibling_plugins.py:30-57 | delegate-review-hint | 为兼容 Claude Code 对 worktree 的设置存放做的绕路 |
| B7.7 | Codex 侧插件记录读取 | 读 `~/.codex/config.toml` 里 `[plugins."name@market"]` 的 `enabled = true` 并确认缓存目录存在，不抛异常 | 内部 | 开 | hooks/sibling_plugins.py:87-111 | delegate-review-hint | 同 B7.5，且这里是正则解析 TOML，比解析器更脆 |
| B7.8 | delegate 是否可用（每轮提示用） | 判断 delegate 是否装且启用；读不出一律答「否」（因为每轮 prompt 都跑） | 阶段提示内部调用 | 开（安装了 delegate 才出提示） | hooks/sibling_plugins.py:114-122 | delegate-review-hint | 为一行外部审查提示读宿主私有记录，代价/收益需要评估 |
| B7.9 | delegate 接口校验与命令名取值 | 装了 delegate 时读其 `interface.json`，接口主版本须为 1；只取符合 `/delegate:<小写与连字符>` 的 review／doctor 命令名；文件缺失／损坏则回落到默认命令名；Codex 缓存里恰有一个版本目录时才读 | 阶段提示内部 | 开 | hooks/sibling_plugins.py:125-174 | delegate-interface-check、delegate-review-hint | 命令名完全可以写死，却加了版本校验和默认回落；是为「delegate 改名」预留的灵活度，没有发生过的证据 |
| B7.10 | 共享的读 JSON 与错误类型 | `read_json` 把文件缺失当 None、读坏抛 `RecordError`（探针据此降级为 unknown） | 内部 | 开 | hooks/sibling_plugins.py:17-27；agent_relay_probe.py:33-47 | collaboration-dependency | 无 |
| B7.11 | 缺陷≠读失败判据 `defect_guard` | 提供 `is_defect()`：`AttributeError／TypeError／NameError／KeyError／IndexError／AssertionError／ImportError` 视为「我们自己的代码错了」，降级为 `unknown`／`partial` 前必须重抛；刻意不含 `ValueError` | 被 `proposal_closeout.py` 11 处引用（B 区文件本身不调用） | 开 | hooks/defect_guard.py:1-33；proposal_closeout.py:25,140… | （无独立 id）0.42.0 审计收束，见 CHANGELOG 1337 行；collaboration-extraction 把它列为要复制到 agent-relay 的文件 | **疑点**：放在「模块生命周期」区是归类问题，它实际是 Proposal 收尾（及原协作代码）的错误处理工具；B 区内没有人用它。是否该归到 Proposal 区？另外同一份文件在 agent-relay 里有拷贝（collaboration-extraction C1/C2），存在重复维护 |
| B7.12 | interface.json 总体 | 插件根的只读接口说明，`interface` 版本 `1.7`（只增升次版本，删改升主版本），其他插件读它而不读 spec-guard 内部文件；`scripts/check-interface.py` 在 validate.sh 里核对与代码常量一致 | `plugins/spec-guard/interface.json`；validate.sh | 开 | iface 1-284；docs/design.md 92-116 | plugin-interface、crew-interface、map-progress-facts、map-gate-count、checkpoint-default-report、cn-checkpoint-gates、review-card-sections、gate-tick | **疑点**：接口版本已从 1.0 升到 1.7，每次升版都伴随一个模块+一次发版；整体上是一份「给 module-crew／decision-inbox 看的契约」，真正的消费方（module-crew）本不在本仓库，无法在本仓库验证有人在读 |
| B7.13 | interface.mapView | 进度表入口命令、`schemaVersion` 1、`contract` 指向 spec/map-view.md、退出码 0/2/3/4 含义、`review` 与 `externalReview` 取值含义 | iface 3-33 | 开 | iface 3-33 | plugin-interface、map-view | 同 B7.12 |
| B7.14 | interface.mapView.progressFacts | 列出 `uncommittedTicks`、`startedAt`、`head.committedAt`、`reviewCadence`、`gates` 的定义，并注明「facts only：不设阈值，不判停滞」 | iface 34-51 | 开 | iface 34-51；map_view.py:39 `PROGRESS_FIELDS` | map-progress-facts、map-gate-count、checkpoint-default-report、cn-checkpoint-gates | 逐字段定义写得很清楚；但 `gates` 的判据已被改过三次（1.3→1.4→1.6），说明字段语义不稳 |
| B7.15 | interface.mapView.concurrency | 开关 on 时 `/map --json` 才有的字段：`moduleConcurrency`、`buildOrderGroups`、`startable`、`scope`、`worktree` | iface 52-65 | 关 | iface 52-65 | map-startable、checkout-role | 见 B6 |
| B7.16 | interface.moduleConcurrency | 声明开关的配置位置、默认 off、取值含义，读法：看 `/map --json` 顶层 `moduleConcurrency`，不必开配置文件 | iface 67-77 | 开 | iface 67-77 | module-concurrency-switch、crew-interface | 无 |
| B7.17 | interface.scopeCheck | 越界检查命令、只读、退出码（0/2/3/4）、`scope` 取值含义 | iface 78-108 | 关（并行） | iface 78-108 | module-scope-boundary、crew-interface | 同 B6.11 |
| B7.18 | interface.checkoutRole | show／setModule／setCoordinator／clear 四条命令、`--confirm` 才写、标记位置、退出码、角色取值含义 | iface 109-162 | 关（并行） | iface 109-162 | checkout-role、crew-interface | 同 B6.2 |
| B7.19 | interface.reviewMark | 批准标记命令、`--confirm`、退出码、备注「approved 只在用户明确批准后写；开关 on 时由协调会话写在集成 checkout」 | iface 163-184 | 开 | iface 163-184 | crew-interface、review-approval-marker | 无 |
| B7.20 | interface.reviewKinds | 1.5 起：spec-guard 共享检查点规则产生的七类「要用户决定」的类型（capability-map／spec／plan／spec-plan／checkpoint／final／stuck），键是 session-protocol 契约【等待用户】「类型」的代码，每类列小项顺序，另有通用行（注意／推荐理由／批了会怎样） | iface 185-265 | 开 | iface 185-265；docs/design.md 108-110 | review-card-sections | **疑点（越界）**：把「对话里的卡片小项」固化成机器可读接口，实质是 decision-inbox／session-protocol 契约的镜像；spec-guard 的对话措辞因此被外部契约绑住，丧失自由 |
| B7.21 | interface.gateTick | 1.7 起：gateTick 命令、`--confirm`、退出码与短码、说明「调用方须已持有用户批准」 | iface 266-283 | 开 | iface 266-283 | gate-tick | 同 B5.1 |
| B7.22 | check-interface 一致性核对 | `validate.sh` 调 `scripts/check-interface.py` 校验 interface.json 与代码常量（如 `REVIEW_STATES`、`ROLE_KINDS`、`SCOPES`、`PROGRESS_FIELDS`）一致 | `bash scripts/validate.sh` | 开 | scripts/validate.sh:37；hooks/review_mark… 常量处有注释 `# interface.json …` | plugin-interface | 无（有测试守护，是好设计） |

---

## B8 命令说明与 Codex 技能的重复面

| # | 功能点 | 它做什么 | 触发／入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| B8.1 | spec-guard-ops 技能中的对应章节 | Codex 只读 skill，复述 map、module-suspend、review-mark、checkout-role、add-module 的用法与规则 | Codex 技能 | 开 | SKILL:121-139（map）、200-217（module-suspend）、244-267（review-mark）、268-283（checkout-role）、284-334（add-module） | （各命令对应模块；Codex 入口无独立 id） | **疑点**：与 `commands/*.md` 近乎逐段重复（两份拷贝），规则变更要同步改两处，易漂移；这是双宿主架构的代价，设计文档（docs/design.md 129-141）已说明 |
| B8.2 | 阶段交接遵守共享检查点规则 | 每条命令首行：阶段交接、确认或停止前读取 `spec-guard-ops` 的共享检查点规则，按实际路径预告下一步 | 命令说明首段 | 开 | cmd/review-mark.md:6、map.md:6、module-suspend.md:6、checkout-role.md:6 | review-card-sections、checkpoint-tiers | 提示词约束，靠 agent 自觉 |

---

# 总计

功能点编号合计：B1=24、B2=18、B3=10、B4=30、B5=7、B6=13、B7=22、B8=2，共 **126** 条（其中 B7.22、B8 等偏「元」的条目若不计，约 123 条）。
