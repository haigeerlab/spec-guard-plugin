# A 核心约定与阶段注入：功能点清单

基线：commit 85a1f560（插件 0.83.1）。只读精读，未改任何文件。
路径缩写：`hooks/` = `plugins/spec-guard/hooks/`；`cmds/` = `plugins/spec-guard/commands/`；`tpl/` = `plugins/spec-guard/templates/`。
"模块"列是能力图 `spec/CAPABILITY-MAP.md` 里引入或修改该点的模块 id（按 Spec 登记与模块职责栏核对；个别修复没有独立模块，已写明）。
"默认/可关"：除特别写明，下列点都"随项目激活自动开、没有单独的关闭开关"；整体只能靠 teardown 去掉激活信号，或在宿主里不信任 hook。

编号规则：A-xx 为功能点；同一大功能下的行按"大 → 小"排列。

---

## 一、钩子入口与激活判定

| 编号 | 名称 | 做什么 | 触发条件/入口 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-01 | 每轮阶段注入（UserPromptSubmit） | 每次用户发言时输出 `hookSpecificOutput.additionalContext`：标题、位置行、阶段、事实、建议下一步 | 宿主 UserPromptSubmit；`hooks.json` 调 `phase-guard.sh` | 开（有激活信号才出）；无独立开关 | `hooks/hooks.json:3-13`；`hooks/phase-guard.sh` 全文 | phase-and-verification | 解决"agent 不知道当前做到哪一步"；但每轮全量重复注入（几十行），无按需/静默档，用户不能关掉其中任何一类提示 |
| A-02 | 压缩后注入（SessionStart/compact） | 上下文压缩后重发一次同样的阶段摘要，末尾加"较早请求可能已做完，先核对 todo 与状态记录，核对后接着做建议的下一步"（有账本时再加 waiting-on-* 与 repoRoot） | 宿主 SessionStart，matcher `compact`；脚本参数 `SessionStart` | 开；无开关 | `hooks.json:14-22`；`phase-guard.sh:5-12,107,120-122,182-192` | compact-phase-injection、compact-next-step、open-commitments、record-on-receipt、hint-language-follow | 解决压缩后 agent 忘记任务；但是在对 agent 下指令"不要就此结束这一轮"，是行为约束而非事实报告，与 hook"只报告事实和建议"不变量有张力 |
| A-03 | 会话开始/清空后的账本读回提醒（SessionStart fresh） | 项目有 `.epiq/project.json` 时只输出一句固定提醒：先列 waiting-on-me/them/user 的未关闭事项再继续；不出阶段摘要 | SessionStart，matcher `startup|clear`，参数 `SessionStart fresh` | 开（仅有账本才出）；无开关 | `hooks.json:23-31`；`phase-guard.sh:68-97` | open-commitments、record-on-receipt、hint-language-follow | 把"本地事项账本"的使用习惯塞进阶段钩子；账本是姐妹能力（local-ticket-ledger / agent-relay 协作），阶段钩子本不该知道账本；每次开会话固定要求 agent 先查账本 |
| A-04 | 激活信号判定 | 两种信号之一即激活：CLAUDE.md 里独占一行的 `BEGIN:agent-skills-convention`，或 AGENTS.md 里 `BEGIN:spec-guard-codex-convention`，或 `.agent/state.json` 含 `activeModule` 键 | 每次 hook 启动 | 恒开 | `phase-guard.sh:35-58` | local-convention、phase-and-verification、tracker-backend-default（删掉 tracker 字段信号）、audit-small-cleanups（改 bash 内建） | 纯文本匹配，别的工具的 state.json 含同名键也会激活（脚本自己承认）；第三个信号"指向文件"另见 A-23 |
| A-05 | 无信号静默退出 | 无激活信号且无指向文件时 `exit 0`，不输出任何东西，且不启动 python | 同上 | 恒开 | `phase-guard.sh:62-66` | phase-and-verification、linked-project-root | 无。但见 A-08：在此之前已经为解析根目录跑过一次 python |
| A-06 | 逐行匹配只用 bash 内建 | 激活判定不依赖 grep，满足"只依赖 bash、git、python3" | 内部 | 恒开 | `phase-guard.sh:42-49` | audit-small-cleanups | 无 |
| A-07 | 项目根解析 | `CLAUDE_PROJECT_DIR`，否则 git toplevel，否则 pwd（Codex 不提供前者） | 内部 | 恒开 | `phase-guard.sh:17-24` | phase-and-verification、codex 相关多模块 | 无 |
| A-08 | worktree 根修正（--resolve-root） | 读 hook 输入里的 `cwd`，以它所在 git 仓库为项目根（桌面版 worktree 会话里宿主给的目录可能是主检出）；stdin 最多等 1 秒、上限 1MB，读不到则不变 | 每次 hook，stdin 非 TTY 且有 python3 | 恒开 | `phase-guard.sh:25-33`；`hooks/session_context.py:178-247` | 无独立模块（0.47 前后的 CHANGELOG 修复，commit 8e5ab85a）；stdin-timing-test 修回归 | **该步在激活判定之前运行**（行 29-32 早于行 63），所以没启用 spec-guard 的项目每轮也要启动一次 python；CHANGELOG 自认"含未启用约定的项目"；与不变量"无关项目静默退出"的轻量精神不符 |
| A-09 | python3 缺失诊断 | 已启用但无 python3 时，手写 JSON 报"python3 不可用，本轮没有阶段注入，这不是未启用" | 已激活且 `command -v python3` 失败 | 恒开 | `phase-guard.sh:99-103` | map-read-failure、audit-small-cleanups | 无（防"环境故障被当未启用"，有真实风险依据） |
| A-10 | python3 可见但无法运行的兜底诊断 | emit 失败时退回手写 JSON："python3 无法运行" | JSON 序列化失败 | 恒开 | `phase-guard.sh:105-134` | map-read-failure | 无 |
| A-11 | hooks.json：插件根缺失诊断 | `PLUGIN_ROOT`/`CLAUDE_PLUGIN_ROOT` 都空或缺 `phase-guard.sh` 时，输出"这是插件安装或宿主问题，不是项目未启用" | 三个 hook 条目各有一份 | 恒开 | `hooks.json:10,19,28` | command-plugin-root、compact-phase-injection | 三份几乎相同的长命令行（含中文兜底文案）复制粘贴三遍，改一处要改三处 |
| A-12 | hooks.json：脚本非零退出诊断 | `phase-guard.sh` 非零退出时输出"执行失败…不是未启用…排查命令" | 同上 | 恒开 | 同上 | 同上 | 同上 |
| A-13 | 事件名按实际事件给出 | `hookEventName` 随 UserPromptSubmit/SessionStart 变化，错误兜底同样 | 内部 | 恒开 | `phase-guard.sh:5-12,125` | compact-phase-injection | 无 |
| A-14 | 宿主判定（Claude/Codex） | 优先级：`SPEC_GUARD_HOST`，hook 输入含 `turn_id` 或会话记录首条为 `session_meta`（Codex），再看环境变量；判不出时空 | 内部 | 恒开；可用 `SPEC_GUARD_HOST` 覆盖 | `phase-guard.sh:235-249`；`session_context.py:142-158` | codex-command-wording | 靠宿主内部实现细节（`turn_id`、`session_meta`）推断宿主，宿主改版即失效；为的是命令提示写法两套 |

---

## 二、会话事实（session_context.py）

| 编号 | 名称 | 做什么 | 触发条件/入口 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-15 | 位置行 | 标题下第一行：`Location: branch <分支> · worktree <根>. State this location to the user whenever you ask them to review or confirm.`（分离 HEAD 时 `detached at <sha>`；非 git 目录无此行；zh-CN 时中文） | 每次注入（所有阶段；能力图无效/读不了的诊断也带） | 开；无开关 | `session_context.py:194-214`；`phase-guard.sh:250-254` | fresh-session-hint、hint-language-follow | 解决"多 worktree 下用户不知道代码在哪"；但每轮都重复一遍，且命令 agent 每次交审时向用户复述位置，已是固定话术；可疑为过度提示 |
| A-16 | 上下文大小读取 | 从会话记录末尾 4MB 里找最近一轮主会话（非 sidechain）usage：Claude 取 input+cache_read+cache_creation，Codex 取 `last_token_usage.input_tokens`；零值当作无读数 | hook 输入含 `transcript_path` | 开；读不到则无上下文提示 | `session_context.py:24-106` | fresh-session-hint、context-hint-thresholds | 解析宿主私有的会话记录格式；宿主有自己的上下文用量显示与自动压缩，此功能是否值得 |
| A-17 | 压缩后的大小处理 | 记录里有较新的压缩记录时，按压缩后大小（Claude `compact_boundary.postTokens`；Codex `compacted` 视为 0）判断 | 同上 | 开 | `session_context.py:49-63,103-105`；`phase-guard.sh:221-223`（压缩后那次注入直接按 0） | context-after-compact、phase-hint-gaps | 同 A-16 |
| A-18 | Codex 上下文窗口 | 读 `model_context_window`；Claude 记录无窗口，按 1M 折算 | 同上 | 开 | `session_context.py:66-71`；`module_stage.py:358-377` | context-hint-thresholds、boundary-hint-70 | Claude 按 1M 写死；用户若用其他窗口则阈值失真 |
| A-19 | 无人值守判定 | `CLAUDE_CODE_SESSION_ATTENDED=0`（`claude -p`，注释自称"实测、未文档化"）或 Codex rollout 首条 `session_meta.source=="exec"` 视为无人在场；读不到按有人 | 每次读取会话事实 | 开 | `session_context.py:109-139`；`phase-guard.sh:229-232` | unattended-run-hint、unattended-long-first-record | 依赖未文档化的环境变量与首条记录格式（首条记录甚至要读至 1MB）；为一两行可选提示而深挖宿主内部 |
| A-20 | 别的会话转来的消息识别 | 提示词以 `<cross-session-message from-session=… from-name=…>` 开头时取两个属性（名清洗，会话 id 校验 `local_…`） | UserPromptSubmit | 开 | `session_context.py:250-269,276-283` | receipt-hint-on-message | 依赖 Claude 桌面版跨会话消息的包装格式；该格式属于宿主与 agent-relay/decision-inbox，不属于本插件 |
| A-21 | hook 输入读取保护 | 标准输入最多等 1 秒、1MB 上限，调用方未关闭 stdin 时不挂住 | 每次 | 恒开 | `session_context.py:19-21,217-231` | stdin-timing-test、audit-remediation | 无 |
| A-22 | 位置/会话事实的多行协议 | 输出五行：token、位置行、窗口、`unattended`、host，给 shell 分段读 | 内部 | 恒开 | `session_context.py:272-311`；`phase-guard.sh:216-234` | fresh-session-hint 等 | 用换行拼接的隐式协议，两侧各自解析，脆弱（可见 `phase-guard.sh` 里大量 case 截断）；属实现债 |

---

## 三、关联项目（link-project，会话目录 ≠ 项目目录）

| 编号 | 名称 | 做什么 | 触发条件/入口 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-23 | 指向文件作为第三种激活信号 | 会话目录没有激活信号、但有 `.agent/spec-guard-link.json` 时，改读被指向项目并输出其阶段 | hook 启动时 | 开（仅有该文件才触发）；删文件即关 | `phase-guard.sh:60-66,136-175` | linked-project-root | 解决"会话开在需求目录、代码在别处"；宿主多已支持 additional directories/换 cwd，且命令都不自动跟随（用户需手动传路径），收益存疑 |
| A-24 | 指向文件 v1 格式 | `{version:1, project}`，目录级，对该目录所有会话生效 | link-project set 写入 | 开 | `project_link.py:29-60,175-186` | linked-project-root | 无 |
| A-25 | 指向文件 v2：按会话登记 | `{version:2, sessions:{id:path}, project?}`；hook 用 `session_id`、会话记录文件名及尾部 UUID 作候选 id 查表；本会话登记优先，其次目录级，都没有静默 | `--session <id>`；hook 输入 | 开 | `project_link.py:68-116` | link-per-session | 需要调用方手工传会话 id（`$CLAUDE_CODE_SESSION_ID`/`$CODEX_THREAD_ID`），登记不会自动清理；为"多会话共用一目录各做不同项目"的小众场景叠了第二层格式 |
| A-26 | 关联项目提示行（4 种） | 标题后加一行 `Linked project`/`关联项目`：区分来源 session/directory × 语言 zh/en；写明路径、来自哪个目录、"运行 spec-guard 命令时把此路径作为项目传入"；directory 来源再提醒"若本会话做的是别的项目，忽略这里的阶段" | 跟随指向成功时 | 开 | `phase-guard.sh:255-272` | linked-project-root、link-shared-directory-note、link-per-session、hint-language-follow | 要求 agent 手工带 `--project`，说明命令不自动跟随；该行 4 份几乎重复的文案 |
| A-27 | 指向失效诊断（4 种） | 目标进不去 / 目标未启用 / 目标不存在或非目录 / 格式无效 / 读取失败 → 一行诊断"这是指向失效，不是未启用"，并给 `/spec-guard:link-project` 引导 | 指向文件在但无效 | 开 | `phase-guard.sh:153-174` | linked-project-root | 无（用户已声明过，不静默有依据） |
| A-28 | 只有别会话的登记时静默 | 文件里只有他人会话的登记、本会话无登记且无目录级指向时视同无指向 | resolve 返回 none | 开 | `phase-guard.sh:163-164`；`project_link.py:83-84` | link-per-session | 无 |
| A-29 | 不连环跟随 | 只看目标自身的激活信号，不读目标里的指向文件 | 内部 | 恒开 | `phase-guard.sh:136-137` | linked-project-root | 无 |
| A-30 | 跟随指向时 fresh 事件 | 会话开始/清空：指向有效才出账本提醒；失效或缺 python3 静默 | SessionStart fresh | 开 | `phase-guard.sh:93-97,169` | open-commitments、linked-project-root | 无 |
| A-31 | `/spec-guard:link-project show` | 报告指向文件状态：valid/invalid/missing/not-enabled，目录级与会话登记各自判定，目标当前阶段行，共享目录提醒 | 命令 | 手动 | `project_link.py:197-233,354-392`；`cmds/link-project.md` | linked-project-root、link-per-session、link-shared-directory-note | 无 |
| A-32 | `link-project set`（预览/--confirm） | 预览将写入的文件、内容、解析后项目路径、目标当前阶段；确认后原子写 `.agent/spec-guard-link.json` 并读回核对；提示别入库（含本机路径）但不改 .gitignore | 命令 | 手动，先预览 | `project_link.py:252-310` | linked-project-root、link-per-session | 无 |
| A-33 | `link-project set` 拒绝条件 | 会话 id 非法 / 会话目录自己已启用 / 已有文件格式无效 / 路径非法 / 目标不存在 / 目标即会话目录 / 目标未启用，均退出 2 不写 | 命令 | 恒开 | `project_link.py:252-282` | linked-project-root | 无 |
| A-34 | `link-project unset`（预览/--confirm） | 删目录级或某会话登记；无会话登记则删文件；无效文件只能整个删；`.agent/` 目录保留 | 命令 | 手动 | `project_link.py:313-351` | linked-project-root、link-per-session | 无 |
| A-35 | 共享目录提醒文案 | 预览/show/提示行都带"指向对该目录所有会话生效；多会话各做不同项目时别建目录级指向" | 命令输出 | 开 | `project_link.py:159-172` | link-shared-directory-note | 文案补丁性质；本身说明目录级指向设计有坑 |
| A-36 | `project_link.py resolve`（hook 专用） | 输出状态、目标、两条清洗后的路径、来源（路径限长 1024），供 shell 分行读取 | hook 调用 | 内部 | `project_link.py:374-384` | link-per-session | 无 |

---

## 四、阶段判定核心（module_stage.py / capability_map.py）

| 编号 | 名称 | 做什么 | 触发条件/入口 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-37 | 模块阶段判据 | 单模块：无 `spec/<id>.md`→NEEDS_SPEC；有 Spec 无 `tasks/<id>/plan.md`→NEEDS_PLAN；有 Plan 且 todo 有 `- [ ]`→BUILDING；否则→DONE | 每次注入 | 恒开 | `module_stage.py:99-120` | phase-and-verification | 核心；只看文件与勾选，不读 Git/远端，合理 |
| A-38 | 项目级阶段 | `DONE`（全部模块完成）；`MODULE_DONE`（当前模块完成但 Build order 里还有未完成的）；否则取当前模块自身阶段 | 同上 | 恒开 | `module_stage.py:204-220` | done-stage-split | 无 |
| A-39 | 当前模块选取 | `.agent/state.json` 的 `activeModule`（须在图中且未挂起），否则 Build order 第一个未完成且未挂起的模块 | 同上 | 恒开 | `module_stage.py:179-220` | phase-and-verification、module-suspend | 无 |
| A-40 | activeModule 校验 | 必须完整匹配 kebab-case；无效则报"不是有效的 module id"但**不回显值**，按 Build order 取 | 同上 | 恒开 | `module_stage.py:179-195,769-773` | phase-context-sanitization | 无 |
| A-41 | 提示注入净化（safe_fragment） | 仓库来的值折叠空白、去反引号与反斜杠、去 Cc/Cf 字符、限长 200，防伪造标题或代码围栏 | 所有写进注入的仓库值 | 恒开 | `module_stage.py:128-168` | phase-context-sanitization、audit-remediation | 无（正当的 prompt-injection 防护） |
| A-42 | 能力图严格解析器 | 唯一一张 `Module id | Responsibility | Depends on` 表；围栏代码块内不算；id 须 kebab-case、不重复、依赖已知无环、恰好一条 `Build order:`、顺序须满足依赖；逗号分组展开成串行 | 阶段注入、verify-artifacts、spec-digest、其他模块共用 | 恒开 | `hooks/capability_map.py:1-261` | phase-and-verification、map-table-count-diagnostic、audit-remediation | 严格度很高（任何能力图格式偏差即 MAP_INVALID）；为上游 agent-skills 格式留了逗号并行兼容、却又不支持并行（注释自述） |
| A-43 | 能力图 CLI | `capability-map.py <path>` 输出单个 JSON：ok/modules/orderGroups/order；读不了退出 2、内容无效退出 1 | verify-artifacts 调用 | 内部 | `hooks/capability-map.py:1-34` | map-read-failure、phase-and-verification | 无 |
| A-44 | 多张模块表报错带行号 | 报"必须恰好有一个模块表，找到 N 张：第 a、b 行" | 解析失败 | 恒开 | `capability_map.py:97-106` | map-table-count-diagnostic | 无 |
| A-45 | 文本指纹算法（spec-digest） | 唯一指纹：sha256 前 12 位；`compute <map>` 给行摘要/目标摘要/顺序/是否含 `example-` 占位，`text <file>` 给文本摘要；`--selftest` | Proposal 校验、评审标记 | 内部 | `hooks/spec-digest.py:1-111` | proposal-contract（引入）、review-approval-marker（复用）、phase-and-verification | 能力图指纹原为 Proposal 服务；评审标记复用它，耦合 Proposal 子系统 |
| A-46 | 挂起标记 | todo.md 里独占一行 `<!-- spec-guard: suspended -->`（且有未勾选项）才算挂起；无未勾选项的挂起标记视为过期、模块按完成计 | 阶段判定 | 开 | `module_stage.py:27,108,118` | module-suspend | 无 |
| A-47 | no-todo 声明标记 | plan.md 里独占一行 `<!-- spec-guard: no-todo -->` 声明"有意不建 todo"，之后不再提醒缺 todo | 阶段判定、verify-artifacts | 开 | `module_stage.py:25,119-125` | plan-without-todo | 为"有 Plan 无 todo 判完成"这一历史包袱补的逃生口；判据本身（缺 todo=完成）需要标记与警告多处兜底 |
| A-48 | "暂停"判定（半做模块） | 当前模块之外 todo 既有已勾又有未勾项、且未挂起的模块 | 阶段判定 | 恒开 | `module_stage.py:223-225` | module-interrupt | "暂停"（隐式推断）与"挂起"（显式标记）两套概念并存，易混淆 |
| A-49 | 完成判据的未合并提交探测 | DONE/MODULE_DONE 时比较 HEAD 与本地已知 `origin/HEAD`（回退 origin/main、master）的提交数，只读、不联网 | 阶段为 DONE/MODULE_DONE | 恒开 | `module_stage.py:236-251` | done-unmerged-hint | 见 A-71 |
| A-50 | 检查点（gate/report）判据 | todo 里以 `Checkpoint`/`检查点` 开头，或冒号前带（gate）/（report）的勾选项为检查点；未标级别的中间检查点按 report，最后一个按 gate；单点实现供"下一个 gate"、"最终 gate"、/map 的 gates 共用 | 阶段注入（BUILDING） | 恒开 | `module_stage.py:439-502` | checkpoint-tiers、checkpoint-default-report、cn-checkpoint-gates、map-gate-count | gate/report 是对 agent-skills `/build` 之外自创的任务检查点语法，靠 todo 文案约定；上游无此概念，插件在自建一套审批流程语言 |

---

## 五、阶段注入的每一种提示行（逐条）

### 5.1 标题与固定头部

| 编号 | 名称 | 做什么 | 出现条件 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-51 | 标题行 | `## spec-guard local workflow`（所有输出共有，文本不随语言变） | 任何输出 | 恒开 | `phase-guard.sh:251` | phase-and-verification | 无 |
| A-52 | `当前阶段: **X**` | 阶段代码行（IDLE/MAP_ONLY/NEEDS_SPEC/NEEDS_PLAN/BUILDING/MODULE_DONE/DONE/MAP_INVALID/UNKNOWN），英文也用这个中文标签 | 任何阶段 | 恒开 | `module_stage.py:949,952`；`phase-guard.sh` 各 emit | done-stage-split、phase-and-verification | 英文输出中混着中文标签（"检测用的标题行保持原样"） |
| A-53 | `- 能力图: …`/`- Capability map: …` | 有/没有/已有但无效/已有但读不了 | 各阶段 | 恒开 | 同上 | phase-and-verification、map-read-failure | 无 |
| A-54 | `- 模块 Spec: N` | 仅 IDLE/MAP_ONLY/UNKNOWN 路径显示 Spec 文件数 | IDLE、MAP_ONLY、UNKNOWN | 恒开 | `phase-guard.sh:321,345,373` | phase-and-verification | 无 |
| A-55 | `- 当前模块: \`id\`（来源）` | 来源为 `activeModule` 或 "Build order 中下一个" | NEEDS_SPEC/PLAN、BUILDING、MODULE_DONE | 恒开 | `module_stage.py:949-950,952-953` | phase-and-verification | 无 |
| A-56 | 计数行 | `Modules N · Specs N · Plans N · In progress N · Done N`，有挂起时尾加 `· Suspended N` | 除 IDLE/MAP_ONLY/UNKNOWN 外 | 恒开 | `module_stage.py:795-802` | phase-and-verification、module-suspend | 无 |

### 5.2 各阶段与"建议下一步"

| 编号 | 名称 | 做什么（建议下一步文案要点） | 出现条件 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-57 | 阶段 IDLE | 能力图没有；"先跟用户确认需求已说完，再写能力图并交审，然后做规划" | 无 `spec/CAPABILITY-MAP.md`（含非激活导致的纯声明块状态） | 恒开 | `phase-guard.sh:315-337` | phase-and-verification、requirement-confirm | 无 |
| A-58 | 阶段 MAP_ONLY | 有能力图、`spec/` 下无模块 Spec；"先确认第一个模块需求说完，再写第一份模块 Spec 并交审" | 能力图在、Spec 数为 0 | 恒开 | `phase-guard.sh:339-361` | phase-and-verification、requirement-confirm | 无 |
| A-59 | 阶段 NEEDS_SPEC | 当前模块缺 `spec/<id>.md`：建议"写 Spec 并交审"；若有读数，上一模块验收后常在此处出现模块边界行 | 当前模块无 Spec | 恒开 | `module_stage.py:908-923,894-898` | phase-and-verification、phase-hint-gaps | 无 |
| A-60 | 阶段 NEEDS_PLAN | 有 Spec 缺 Plan：建议"写 plan.md 和 todo.md（例如用 `/plan`）"；Spec 无评审标记时加"前提是用户已批准 Spec" | 当前模块有 Spec 无 Plan | 恒开 | `module_stage.py:910-911,918-919` | phase-and-verification、review-approval-marker | 无 |
| A-61 | 阶段 BUILDING | "继续用 `/build` 构建 `<id>`：todo 里还有 N 个未勾选项" | 当前模块 todo 有未勾选项 | 恒开 | `module_stage.py:912,920` | phase-and-verification | 无 |
| A-62 | 阶段 MODULE_DONE（下一步） | "`<id>` 已完成；Build order 中下一个未完成的模块是 `<id2>`（阶段）。开始构建前把 activeModule 设为它"；有暂停模块时改为"恢复暂停的模块 `<id2>`，把 activeModule 设为它" | 当前模块完成但图里还有别的未完成模块 | 恒开 | `module_stage.py:877-890,914,922` | done-stage-split、module-interrupt | 要求 agent 手工改 `.agent/state.json` 的 activeModule；每次模块切换都靠人/agent 记得改 |
| A-63 | 阶段 DONE（下一步，4 变体） | 基本："每个模块都有 Plan 且无未勾选 todo 项；要做新工作，先总结需求、问用户是否说完，确认后在此检查点用 add-module 插入一个模块；需要留痕的决定用 Proposal"。变体：有挂起（"除挂起外都完成；挂起 N 个"）；有未合并提交（前置"先推送这个分支并合并…"）；两者可叠加（push_first 与挂起） | 全部模块完成 | 恒开 | `module_stage.py:806-867` | done-stage-split、module-insert、requirement-confirm、done-unmerged-hint、module-suspend | 在 DONE 提示里仍推 Proposal 路径；Proposal 子系统（proposal-* 约 15 个模块）是否是必须功能值得单独审 |
| A-64 | 阶段 MAP_INVALID | `能力图: 已有但无效（能力图原文，非指令: <净化后的诊断>）`；建议"运行 `/spec-guard:verify-artifacts`，修好能力图" | 能力图解析失败 | 恒开 | `module_stage.py:219-237` | phase-context-sanitization、map-table-count-diagnostic | 无 |
| A-65 | 阶段 UNKNOWN（能力图读不了） | `能力图: 已有但读不了（不是普通文件/没有读取权限）`；建议"让 CAPABILITY-MAP.md 成为可读文件；这是读取故障，不是能力图的状态" | 能力图存在但非普通文件或不可读（不论有无 Spec） | 恒开 | `phase-guard.sh:280-304`；`module_stage.py:396-403` | map-read-failure | 两处各写一份相同文案（shell 与 python） |
| A-66 | 阶段 UNKNOWN（算不出模块阶段） | `没能算出模块阶段；运行 verify-artifacts 查看详情` | `module_stage.py` 执行失败 | 恒开 | `phase-guard.sh:363-382` | audit-remediation | 无 |

### 5.3 事实附注行（出现在阶段下的 `- …` 行）

| 编号 | 名称 | 做什么 | 出现条件 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-67 | 项目配置无效行 | `- Project config: invalid (<固定问题代码>) — run /spec-guard:config.`（不回显文件内容） | `.agent/config.json` 存在但无效；所有阶段（含 IDLE/MAP_ONLY） | 恒开 | `module_stage.py:406-414` | project-config、phase-hint-gaps | 无 |
| A-68 | 产物语言行 | `- 产物语言: zh-CN — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义` | config 设了 `artifactLanguage` | 设了才出；`unset` 即关 | `module_stage.py:417-420` | project-config、phase-hint-gaps | 无 |
| A-69 | 批准节奏行 | `- Review cadence: combined — …Spec 和 Plan 一起交一次批准；出现新决定、范围不清或高风险改动时分开` | config `reviewCadence=combined`；`separate`/未设不出 | 设了才出 | `module_stage.py:421-426` | project-config、checkpoint-tiers | 一份"单人快速 vs 多决策"的节奏开关，每次注入占一行 |
| A-70 | activeModule 提示行 3 种 | ①无效 id；②已挂起（"using Build order"）；③不在能力图里 | state.json 的 activeModule 无效/挂起/不在图 | 恒开 | `module_stage.py:769-780` | phase-context-sanitization、module-suspend | 无 |
| A-71 | 未合并提交提示行 | `- 这个分支有 N 个提交还不在 origin/main 里（按上次 fetch 的结果）`；同时在下一步前置"先推送这个分支并合并" | DONE/MODULE_DONE 且 `rev-list --count origin/HEAD..HEAD>0` | 恒开；离线只读 | `module_stage.py:813-822,830-831,871-872` | done-unmerged-hint | 属于 git 工作流提醒，不是 spec 阶段信息；插件替用户规定"完成后先推送合并"，对不用 PR 流程或本地分支协作的项目是噪音 |
| A-72 | 挂起列表行 | `- Suspended: \`id\`（N 个未勾选项）；用 /spec-guard:module-suspend --resume id 恢复。` | 存在挂起模块 | 恒开 | `module_stage.py:800-805,824,873` | module-suspend | 无 |
| A-73 | 暂停列表行 | `- Paused: \`id\`（N 个未勾选项）；\`当前\` 之后恢复它。` | 非当前、todo 半勾且未挂起的模块（DONE 阶段不出） | 恒开 | `module_stage.py:812,874-876` | module-interrupt | 见 A-48 |
| A-74 | 有 Plan 没 todo 的单模块行 | `- activeModule \`id\` 有 Plan 但没有 tasks/id/todo.md，所以按已完成计；还有工作要做就补上 todo。` | activeModule 为该类模块且阶段 DONE | 恒开；plan.md 里 no-todo 声明可关 | `module_stage.py:790-794,826-827,869-870` | plan-without-todo | 见 A-47 |
| A-75 | 有 Plan 没 todo 的汇总行 | `- Plan without todo: N module(s) counted as done; run /spec-guard:verify-artifacts to review.` | 阶段 DONE 且存在此类模块 | 恒开 | `module_stage.py:806-811` | plan-without-todo | 无 |
| A-76 | activeModule 已完成可清除行 | `- activeModule \`id\` is already done and can be cleared.` | DONE 且 current 不为空 | 恒开 | `module_stage.py:827-829` | done-stage-split | 无 |
| A-77 | 下一个 gate 行（3 种语气） | 有 gate 检查点时："Next gate: X — 一直做到它；report 检查点记进 todo 后不停下"（Plan 已批准）/"Plan 没有批准标记：用户没批准就先等"（Plan 无标记）/ 协调会话："由它的模块会话推进；到了在这里审" | BUILDING 且无评审步骤挂起；有 gate；非 module 角色 | 恒开 | `module_stage.py:924-943` | review-approval-marker、review-marker-legacy-projects、checkpoint-tiers | 把 gate/report 约定变成每轮提示；"report 检查点直接通过不停下"是在授权 agent 越过检查，行为约束强 |

### 5.4 上下文提示行

| 编号 | 名称 | 做什么 | 出现条件 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-78 | 模块边界行（Module boundary） | `- 模块边界: 本会话上下文约 N k token（达到或超过 700k/窗口 70%）；这是释放上下文的好时机。` 然后让 agent 给用户一条可复制的 `/compact <焦点>` 或 `/clear`，要写在无语言标记的代码块、不粘交接文本；Codex 版 `/compact` 不带焦点 | `MODULE_DONE`、`DONE`、`NEEDS_SPEC`，上下文≥窗口 70%，读得到大小，非无人值守，非压缩后那次 | 恒开；仅无人值守时关 | `module_stage.py:380-385,786-787,891-898` | fresh-session-hint、context-hint-thresholds、boundary-hint-70、boundary-hint-unknown-size、phase-hint-gaps、context-hint-no-paste、context-after-compact、slash-command-code-block、codex-command-wording | **本组是整个 A 区修改次数最多的一条线（至少 12 个模块）**：阈值 50→70、"新会话"→"/compact|/clear"、读不到不提示、无人值守不提示…。上下文管理是宿主职责（Claude Code/Codex 都有用量条与自动压缩），插件替用户劝压缩且无开关；解析会话记录私有格式 |
| A-79 | 会话上下文行（Session context） | `- 会话上下文: 上一轮约 N k token（达到或超过窗口 80%）；每一轮都会重读它。先做完或记下当前任务，然后给用户一条可复制的 /compact 或 /clear` | NEEDS_PLAN、BUILDING（以及 DONE 之外的中间阶段）上下文≥80%，非无人值守 | 恒开；仅无人值守时关 | `module_stage.py:388-393,783-784,899-900` | context-hint-thresholds、context-hint-no-paste、slash-command-code-block | 同 A-78 |
| A-80 | 阈值与窗口折算 | 有窗口取 70%/80% 窗口；无窗口（Claude）按 1M 折算为 700k/800k | 内部 | 恒开 | `module_stage.py:356-377` | context-hint-thresholds、boundary-hint-70 | 阈值数字依据"按官方价格与实测估算的成本差"，是主观调参；无配置项 |
| A-81 | 无人值守时去掉上下文行 | `claude -p`/`codex exec` 时 A-78、A-79 都不出 | `--unattended` | 自动 | `module_stage.py:788-789` | unattended-run-hint | 见 A-19 |
| A-82 | 压缩后核对提醒（COMPACT_NOTE） | 压缩后注入末尾加 "Context was just compacted: …"；有账本时扩展为核对 waiting-on-* 并附 repoRoot；zh 版 | 仅 SessionStart(compact) | 恒开 | `phase-guard.sh:107,120-122,182-192` | compact-phase-injection、compact-next-step、open-commitments、record-on-receipt | 见 A-02 |

### 5.5 评审标记与外部审查行

| 编号 | 名称 | 做什么 | 出现条件 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-83 | 评审标记状态读取 | 读 Spec/Plan 里独占一行的 `<!-- spec-guard: review pending|approved [12位指纹] -->`；状态 none/pending/approved/revised/invalid；Spec 批准带内容指纹，批准后再改→revised；围栏代码内不算；多于一行→invalid | NEEDS_PLAN、BUILDING 阶段 | 开（没标记时输出与无此功能一致） | `module_stage.py:30-96,505-512` | review-approval-marker、review-marker-legacy-projects | 一整套"Spec/Plan 是否被用户批准"的状态机，标记是文件里的一行文字，agent 自己写、自己读，实际上无法证明"用户批准过"（设计文档自述"标记是记录，不是授权来源"）；hub-relayed-approval 又扩出"转述的批准也算" |
| A-84 | Review 行：标记无效/读不到 | `- Review: the review marker in \`path\` is invalid.`，下一步强替换为"运行 verify-artifacts 查看…批准状态未知，修好之前不要继续"；或"读不了，批准状态未知（这是读取故障）" | 标记 invalid / 文件不可读 | 开 | `module_stage.py:526-538,527-531` | review-approval-marker | "修好之前不要继续"把一行标记错误升级为阻塞 |
| A-85 | Review 行：Spec 待审 | `- Review: Spec \`spec/id.md\` is awaiting the user's review.`；下一步被替换为"等用户审阅；先不要写 Plan/不要继续构建；用户批准后用 /spec-guard:review-mark 记下" | Spec 标记 pending | 开 | `module_stage.py:543-549`；zh `570-603` | review-approval-marker | 同 A-83，行为覆盖建议下一步 |
| A-86 | Review 行：combined 节奏下 Spec 待审 | 下一步改为"写 plan.md 与 todo.md，然后把 Spec 和 Plan 一起交给用户一次批准" | NEEDS_PLAN + Spec pending + config `reviewCadence=combined` | 随 config | `module_stage.py:546-548` | project-config、review-approval-marker | 无 |
| A-87 | Review 行：Spec 批准后被改（3 种） | ①BUILDING 且在最终 gate：下一步"最终 gate，把改过的 Spec 的 diff 原样放进验收消息，批准验收也批准修订的 Spec，批准后先 review-mark 再勾选并提交"；②BUILDING 非最终 gate：范围内修正可继续，记进 Spec 变更记录，最终验收附差异一并批准；改范围/方向/新取舍则停下复审；③非 BUILDING：把改过的 Spec 再给用户审一次 | Spec 状态 revised | 开 | `module_stage.py:550-563` | review-approval-marker、acceptance-review-streamline、align-upstream-rules、rules-in-context | 三种分支文案都很长且在每轮重复；其中"范围内修正可继续"为跟上游对齐的放宽，说明早期版本过严 |
| A-88 | Review 行：Plan 待审 | `- Review: Plan \`tasks/id/plan.md\` is awaiting the user's review.`；下一步"等用户审阅；不要继续构建；批准后 review-mark" | BUILDING 且 Plan pending | 开 | `module_stage.py:564-566` | review-approval-marker | 同 A-83 |
| A-89 | 外部审查行（delegate） | 三个检查点（Spec 待审/Plan 待审/最终验收）且模块还没有"外部审查意见"小节或拒绝标记、且本机装了并启用 delegate 时，加一行提议用 `/delegate:review` 做只读复核（附判据：跨模块、取舍、不可逆、信息缺失、接口提案、任务很多）；结论记在 `## 外部审查意见`，不需要时写 `<!-- spec-guard: external-review declined -->` | 上述条件全满足；role_kind≠module | 装了 delegate 才出；写拒绝标记可关 | `module_stage.py:600-663`；`hooks/sibling_plugins.py` | delegate-review-hint、delegate-interface-check、sibling-plugin-hints | **姐妹插件越界**：阶段注入替 delegate 做广告，且读取宿主插件安装记录、delegate 发布的 interface.json 来校验版本、拼命令名；本插件对 delegate 有耦合 |
| A-90 | 命令名表（按宿主） | `COMMANDS`/`COMMANDS_ZH`：add-module、verify、config、resume、review-mark、plan、build、free-next、free-current、delegate-review、checkout-role、map 按 claude/codex/未知三套写法 | 内部 | 恒开 | `module_stage.py:268-349` | codex-command-wording、slash-command-code-block、delegate-interface-check | 每条提示要写 3 宿主 × 2 语言，维护面大 |
| A-91 | 提示语言跟随（hint-language-follow） | `artifactLanguage` 恰好为 `zh-CN` 时说明文字改中文；命令、路径、阶段代码、标记行不变；其它值或配置无效为英文，且英文与 0.67.0 逐字节相同 | 每次渲染 | 随 config | `module_stage.py:430-436`；`phase-guard.sh:178-182` | hint-language-follow | 约束"英文逐字节同 0.67.0"迫使所有新增提示双写；语言本该由 agent 随用户语言决定，而不是在插件里硬编码两份文案 |

---

## 六、多模块并行相关注入（开关 moduleConcurrency=on 才有）

| 编号 | 名称 | 做什么 | 出现条件 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-92 | checkout 角色注入（模块） | 加 `- Checkout role: module \`id\` — 这个 checkout 只做此模块；做完交回协调会话（不在这里合并或推送）`，并重写建议下一步（按模块阶段：NEEDS_SPEC/PLAN"写…交给协调会话请用户审"，BUILDING"继续构建…"，DONE"交回协调会话做最终验收与合并"，挂起，模块不在图里等 7 种） | 开关 on 且 `$(git rev-parse --git-path spec-guard)/` 下有角色标记为模块 | `moduleConcurrency=on` 且有标记；off 或无标记时输出不变 | `module_stage.py:665-731,945-947` | checkout-role、module-concurrency-switch、map-startable、crew-interface | **越界 module-crew**：运行层的"会话角色/交回/合并"规则在规划插件的每轮注入里实现；module-crew 才是并行运行的所有者 |
| A-93 | checkout 角色注入（协调） | `- Checkout role: coordinator — …不在这里开发模块`，下一步改为"统筹各模块：用 /spec-guard:map 查看…不在这里开发"；有待审时保留并追加"在这里呈现并记录" | 角色标记为协调 | 同上 | `module_stage.py:673-682,924-929` | checkout-role | 同上 |
| A-94 | 角色标记无效提示 | `- checkout 角色: 角色标记无效，已忽略；用 checkout-role 查看` | 开关 on 且标记损坏 | 同上 | `module_stage.py:764-768` | checkout-role | 无 |
| A-95 | 模块角色下隐藏评审/外部审查行 | 模块会话不显示 Review 与外部审查行，改指向"交给协调会话" | role_kind==module | 同上 | `module_stage.py:901-907` | checkout-role | 无 |

---

## 七、项目配置（project_config.py / config 命令）

| 编号 | 名称 | 做什么 | 触发条件/入口 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-96 | 配置文件与唯一解析器 | `.agent/config.json`（入库）；`{version:1, artifactLanguage?, reviewCadence?, moduleConcurrency?}`；未知键/版本/取值非法→整份不生效并报固定问题代码（unreadable/not-json/not-an-object/version-invalid/unknown-key/<key>-invalid） | 所有读配置的路径 | 文件缺失=全默认；无效=全默认 | `project_config.py:28-73` | project-config | 配置项只有 3 个，却建了严格版本化 schema、固定词表、原子写、读回核对、预览差异的全套；对三个开关偏重 |
| A-97 | `artifactLanguage` | 语言标签（`zh-CN`/`en`/`pt-BR`…，正则校验）；约束新写产物正文语言，zh-CN 时同时驱动注入文案语言 | config set | 默认未设 | `project_config.py:30,35`；`module_stage.py:417-420,430-436` | project-config、hint-language-follow | 一个值同时管"产物语言"和"提示语言"两件事（后者靠 zh-CN 精确相等触发），耦合 |
| A-98 | `reviewCadence` | `separate`（默认，Spec 与 Plan 分别审）/ `combined`（一起审一次） | config set | 默认 separate | `project_config.py:31,36` | project-config、checkpoint-tiers | 无 |
| A-99 | `moduleConcurrency` | `off`（默认）/`on`：打开并行规划规则；本身不开会话、不建 worktree；`module_concurrency()` 是唯一读取入口 | config set | 默认 off | `project_config.py:32,37,76-79` | module-concurrency-switch | 开关 off 时"所有输出逐字相同"约束，使并行相关代码混入核心注入路径（A-92~95） |
| A-100 | config show | 只读汇总所有项的有效值与来源（default/`.agent/config.json`/convention block/tracker.json），含 dispatch 与 trackerDefault 两个"别处管理"的项，可 `--format json` | `/spec-guard:config` | 手动 | `project_config.py:97-155` | project-config、tracker-backend-default | "汇总别处的项"让 config 命令成了杂项出口 |
| A-101 | config 附带：被 gitignore 警告 | 配置文件被 .gitignore 命中时警告团队看不到 | show | 手动 | `project_config.py:120-123,148-150` | project-config | 无 |
| A-102 | config 附带：本机状态位置报告 | 打印状态根（`~/.spec-guard` 或 `SPEC_GUARD_STATE_DIR`）以及仍在回退读取的旧目录 | show | 手动 | `project_config.py:151-154`；`hooks/state_paths.py` | runtime-state-layout | 配置命令附带"本机状态目录"报告，职责混杂 |
| A-103 | config set / unset | 预览改前改后 diff（canonical 渲染）；`--confirm` 才原子写并读回比对；拒绝：键属别处管理（dispatch、trackerDefault）→指路、未知键、值非法、配置本身无效、`.agent` 是符号链接/非目录 | `/spec-guard:config set|unset` | 手动，先预览 | `project_config.py:158-201` | project-config | 无 |
| A-104 | config check | 配置无效退出 1，供 verify-artifacts 调用 | verify-artifacts | 内部 | `project_config.py:223-229` | project-config | 无 |
| A-105 | 运行时状态目录计算 | `state_root()`：`SPEC_GUARD_STATE_DIR` 或 `~/.spec-guard`；`state_dir(name, legacy)` 整目录回退旧位置；`legacy_in_use()` | 其他模块写本机状态时 | 恒开 | `state_paths.py:1-43` | runtime-state-layout | 本区代码仅计算路径；旧位置回退的"整目录"策略是迁移包袱 |

---

## 八、setup / teardown / 声明块

| 编号 | 名称 | 做什么 | 触发条件/入口 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-106 | setup：创建骨架 | 建 `spec/`、`tasks/`、`.agent/`；`.agent/state.json` 不存在时写 `{"activeModule":""}`；`spec/CAPABILITY-MAP.md` 不存在时从模板复制；已存在一律不动 | `/spec-guard:setup-convention` | 手动 | `setup-convention.sh:166-185` | local-convention | 无 |
| A-107 | setup：写入约定块 | Claude 写 CLAUDE.md（`agent-skills-convention` 块），Codex（`--host=codex`）写 AGENTS.md（`spec-guard-codex-convention` 块）；新建时在文件末尾追加、前加空行 | setup | 手动 | `setup-convention.sh:42-56,118-164`；`tpl/claude-block-local.md`、`tpl/codex-block-local.md` | local-convention、convention-block-blank-lines | 块内容约 30 条规则（见 A-122），全部常驻用户的 CLAUDE.md |
| A-108 | setup：--dry-run | 只预览将做的事 | 参数 | 手动 | `setup-convention.sh:19,150-153` | local-convention | 无 |
| A-109 | setup：--replace | 仅替换已有块，用新模板升级；本地段原样保留 | 参数 | 手动 | `setup-convention.sh:119-148` | convention-block-local-lines | 无 |
| A-110 | setup：--replace --dry-run 逐行预览 | 列 `will remove:` / `will add:`、`will adjust blank lines`、`block content unchanged`、`keeps the local section` | 参数 | 手动 | `managed-block.py:164-176` | convention-block-local-lines、convention-block-blank-lines | 无 |
| A-111 | setup：--accept-removals | 替换要删除模板以外的行时须显式接受，否则退出 3 不改文件 | 参数 | 手动 | `setup-convention.sh:33-36,136-146`；`managed-block.py:100-105,177-178` | convention-block-local-lines | 无 |
| A-112 | setup：块标记预检 | 已有块时先校验标记：BEGIN/END 须各恰好一个、BEGIN 在前，否则拒绝并不改任何文件 | setup 前置 | 恒开 | `setup-convention.sh:60-74`；`managed-block.py:17-29` | local-convention、audit-remediation | 无 |
| A-113 | setup：build-task-dispatch 规则段开关 | `--dispatch`/`--no-dispatch` 在块基础模板后追加一段可选规则（/build 把非 Checkpoint 的 task 派给一个子代理，带 tier-guard 档位标记；验收、提交、勾选留主代理）；开关状态存在块内一行标记；`--replace` 沿用已有状态；两者同给则拒绝 | 参数 | **默认关** | `setup-convention.sh:22-29,76-106`；`tpl/claude-dispatch-rule.md`、`tpl/codex-dispatch-rule.md` | build-task-dispatch、project-config（汇总显示） | 文档自认"实验性、省钱未经证明；实测反而贵 15%–54%"，默认让主代理自己做、只派 3 个以上文件的 task；本是 tier-guard / 派活的议题；规则内容引用 tier-guard 档位，越界；很可能是伪需求 |
| A-114 | setup：退役 tracker 模式拒绝 | 传 `github`/`gitlab` 位置参数→退出 2 并说明已退役；`local` 仅作兼容 | 参数 | 恒开 | `setup-convention.sh:13-17` | tracker-backend-default 等退役模块 | 保留已退役参数只为给出拒绝文案；可视为遗留 |
| A-115 | setup：state.json.disabled 保护 | 若 teardown 留有 `.agent/state.json.disabled`，拒绝新建空状态，要求用户先决定是否恢复 | setup 前置 | 恒开 | `setup-convention.sh:108-116` | local-convention | 无 |
| A-116 | setup：完成后提示 | 输出下一步、可设产物语言、`separate`/`combined` 节奏说明 | 非 dry-run | 开 | `setup-convention.sh:187-194` | project-config | 无 |
| A-117 | 声明块工具（managed-block.py） | `validate`（返回块行数）、`compose`（新块内部排版）、`replace`（保留本地段、对比模板、拒绝悄悄删行）、`remove`（本地段留在原位去标记）；原子写保留权限；空行规范（标记前后各留一空行，符合 Markdown 格式化器） | setup/teardown | 内部 | `managed-block.py:1-221` | local-convention、convention-block-local-lines、teardown-local-section、convention-block-blank-lines | 为"不悄悄删用户在块里手写的行"造了完整的差异与确认机制；块里本就不该放用户内容，本地段是补丁式补救 |
| A-118 | 本地段（spec-guard-local） | 块内独占一行的 `BEGIN:/END:spec-guard-local` 之间内容，替换与卸载时原样保留 | setup --replace、teardown | 恒开 | `managed-block.py:32-45` | convention-block-local-lines、teardown-local-section | 同 A-117 |
| A-119 | teardown：移除声明块 | 删 CLAUDE.md/AGENTS.md 里的块（标记外一个字节不动），本地段留在原位；块外不属于现行模板/规则段的行要 `--accept-removals` | `/spec-guard:teardown-convention` | 手动 | `teardown-convention.sh:109-130`；`managed-block.py:182-216` | local-convention、teardown-local-section | 无 |
| A-120 | teardown：停用 state.json | 默认把 `.agent/state.json` 改名为 `.agent/state.json.disabled`（让 hook 真停且不丢模块状态）；另一宿主块仍在则保留；`--keep-state` 保留原名（hook 继续激活，"零足迹模式"） | teardown | 手动 | `teardown-convention.sh:132-147` | local-convention | "零足迹模式"（只有 state.json 即激活）使"仅有 state.json 是否算启用"的语义复杂；`--keep-state` 的存在说明该模式被有意保留，需确认是否真有用户 |
| A-121 | teardown：自检与保留清单 | 实际跑一遍 phase-guard 验证无输出（"已验证：hook 不再注入任何内容"），打印保留清单（spec/、tasks/、state.json.disabled）及提示未处理远端 Issue/账本、插件仍装着 | teardown | 开 | `teardown-convention.sh:155-186` | local-convention | 无 |
| A-122 | teardown：参数与目录保护 | 重复参数拒绝、host 只能指定一次、必须从项目根执行（用 `CLAUDE_PROJECT_DIR`/git toplevel，不用 cwd）、什么都没做时退出 2 | teardown | 恒开 | `teardown-convention.sh:28-51,150-153` | local-convention | 无 |
| A-123 | 约定块模板内容（规则清单） | 模板每条规则一条 bullet，约 30 条：目录约定（spec/tasks 隔离、activeModule 切换规则）；账本查重（`spec-guard:ticket`）；项目级审查批次；托管 Issue；检查点 gate/report；批 Plan 即授权范围；新需求先确认说完；交审呈现内容；delegate 复核提议；UI 自验；最终验收列文件/提交/依赖表；文档建议；外部阻塞停点；AC 编号；评审标记与变更记录；来源回告；agent-relay 发消息；等待事项记账（waiting-on-*）；收到即记账；一次交审一个模块；最终验收附 Spec diff；下一模块直接写 Spec；产物语言与节奏以 config 为准 | setup 写入 | 开（模板固定） | `tpl/claude-block-local.md:1-62`、`tpl/codex-block-local.md:1-57` | local-convention、checkpoint-tiers、review-handoff-content、tables-at-acceptance、commits-at-acceptance、changed-files-at-acceptance、doc-suggestion-template-line、ui-verify-by-change、sibling-plugin-hints、record-on-receipt、review-one-module、rules-in-context、scope-authorization、stop-rule-and-ac 等十余个"只改规则文字"模块 | **这是最大的范围问题**：这些多是工作流/汇报风格规则（最终验收表格、UI 自验、文档建议、外部阻塞停点…），属于上游 agent-skills 的 `/build`、`/ship` 与宿主权限流程，而不是"防多模块产物互相覆盖"的核心；还把 delegate、agent-relay、账本三个姐妹能力写进每个项目的 CLAUDE.md；用户无法按条关闭，只能 --replace 整体换或手改块 |
| A-124 | 能力图模板 | 复制 `tpl/CAPABILITY-MAP.md`（目标 + 表 + Build order + 审阅记录清单，示例 id 为 `example-a/b`，指纹脚本识别占位） | setup 新建 | 手动 | `tpl/CAPABILITY-MAP.md`；`spec-digest.py:39` | local-convention | 无 |

---

## 九、verify-artifacts / verify-history

| 编号 | 名称 | 做什么（输出） | 触发条件/入口 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-125 | 命令入口与定根 | `/spec-guard:verify-artifacts` 先解析插件根（`CLAUDE_PLUGIN_ROOT`→`PLUGIN_ROOT`→`codex plugin list`），找不到则报"无法定位…不代表插件未安装"；项目目录无法进入退出 2 | 命令 | 手动 | `cmds/verify-artifacts.md`；`verify-artifacts.sh:5-7` | command-plugin-root、codex-skill-root | 同一大段"找插件根"shell 复制在 6 个命令文件里 |
| A-126 | 能力图存在检查 | `✅ 能力图存在` / `⚠️ spec/CAPABILITY-MAP.md 不存在；单模块项目可忽略` | 每次 | 手动 | `verify-artifacts.sh:16-20` | phase-and-verification | 无 |
| A-127 | 根目录 spec 漂移 | 项目根有 `SPEC*.md` → `❌ 根目录有不受支持的 spec 文件: …` | 每次 | 手动 | `verify-artifacts.sh:22-31` | phase-and-verification、local-convention | 无 |
| A-128 | 能力图严格解析 | 解析通过 `✅ 能力图通过严格解析`；无效 `❌ 能力图无效: …`；读不了 `⚠️ 未验证：能力图读取失败…`；解析器没跑起来 `⚠️ 未验证…`；python3 缺失 `⚠️ 未验证：python3 不可用…` | 能力图存在 | 手动 | `verify-artifacts.sh:33-71` | phase-and-verification、map-read-failure | 无 |
| A-129 | 能力图外的模块 Spec | `spec/*.md` 里不在图中的 → `❌ 能力图上没有的模块 spec: <id>` | 解析成功 | 手动 | `verify-artifacts.sh:64-71` | phase-and-verification | 无 |
| A-130 | 有 Plan 无 todo 汇总 | `⚠️ N 个模块有 Plan 但没有 todo.md，按已完成计：id1, id2…`（最多列 10 个） | 解析成功 | 手动 | `verify-artifacts.sh:72-90` | plan-without-todo | 见 A-47 |
| A-131 | 已退役 tracker 字段提醒 | `.agent/state.json` 含 `"tracker":` → `⚠️ 检测到已退役的 tracker 字段…可删除` | 每次 | 手动 | `verify-artifacts.sh:95-99` | tracker-backend-default | 为已删除功能保留的告警，属遗留 |
| A-132 | 项目配置校验 | 有 `.agent/config.json` 时：`✅ 项目配置有效` / `❌ 项目配置无效: <代码>` / `⚠️ 未验证…` | config 存在 | 手动 | `verify-artifacts.sh:101-116` | project-config | 无 |
| A-133 | 挂起标记校验 | `✅ 挂起标记有效：id` / `❌ 挂起标记重复：…（只能有一行）` / `⚠️ 挂起标记过期：id 已没有未勾选项，按完成计` | 存在含挂起标记的 todo | 手动 | `verify-artifacts.sh:118-143` | module-suspend | 无 |
| A-134 | 评审标记校验 | `✅ 批准标记有效：N 个文件` / `❌ 批准标记无效：path` / `⚠️ path 在批准后已修订，需要用户复审` / `⚠️ path 待批准，但 todo 已有勾选项；确认用户是否已批准` / `⚠️ 未验证：读取失败` | 存在评审标记 | 手动 | `verify-artifacts.sh:145-181` | review-approval-marker | 与 A-83 同源 |
| A-135 | 并行边界校验 | 开关 on 时：`✅ 并行边界格式有效（N 个未完成模块）` / `⚠️ 某 Spec 没有并行边界一节` / `❌ 某模块的并行边界格式错误` / `⚠️ 未验证…`；开关 off 时无此项 | `.agent/config.json` 存在 | 随开关 | `verify-artifacts.sh:183-199`（判据在 `module_scope.py`，不属本区） | module-scope-boundary | 并行规划规则挂进核心校验器 |
| A-136 | 旁路清单警告 | `tasks/<id>/` 下 plan.md、todo.md 之外的 `*.md` 里仍有未勾选项 → `⚠️ … 它们不计入阶段（阶段判定只数 todo.md）；返工请写进该模块的 todo.md`；读取失败 → 未验证 | 每次 | 手动 | `verify-artifacts.sh:201-228` | rework-in-place | 为"别另建清单文件"的流程偏好加了检查器；对用户自己的 tasks 目录布局有约束 |
| A-137 | 汇总行与退出码 | `结果: N 通过 · N 警告 · N 失败`；有 ❌ 退出 1 | 末尾 | 手动 | `verify-artifacts.sh:230-231` | phase-and-verification | 无 |
| A-138 | 依赖改动核对（已移除，图未同步） | 能力图仍有模块 `dependency-check`（verify-artifacts 对比新增依赖与 Plan"外部条件"，0.78.0 引入），但 `verify-artifacts.sh` 现无此代码；commit a42a7f1b（install-by-scope，决定 62）已移除 | — | — | 无（仅历史 commit eb73cf86 / b29f989b 与 `docs/releases/v0.78.*.json`） | dependency-check、install-by-scope | **能力图与现实漂移**：dependency-check 在图里仍显示为现役模块；命令文档也已不提 |
| A-139 | 历史证据校验 verify-history | 对 `spec/CAPABILITY-HISTORY.json` 校验账本与 `spec/history`、`tasks/history`、`.agent/history` 下是否存在不在账本里的孤儿证据；无账本时报"未验证" | `/spec-guard:...` 经 spec-guard-ops 技能 | 手动 | `hooks/verify-history.sh:1-27`；调用点 `skills/spec-guard-ops/SKILL.md:421` | capability-history | 属"能力历史"子系统，非阶段注入；只服务历史归档功能 |

---

## 十、命令层（本区六条命令）

| 编号 | 名称 | 做什么 | 触发条件/入口 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-140 | `/spec-guard:phase` | 手工跑一次 phase-guard 并**格式化**报告；含阶段含义表（9 个阶段）、位置行说明、语言说明、上下文提醒说明、净化说明、无输出提示"没装约定，跑 setup-convention" | 命令 | 手动 | `cmds/phase.md:1-115`（大段说明在 40-115） | phase-and-verification、fresh-session-hint 等 | 命令文件里约 70 行是对 hook 实现细节的叙述（阈值、宿主判断顺序、净化规则、历史修复原因），属内部设计文档塞进了用户命令 |
| A-141 | `/spec-guard:verify-artifacts` | 见 A-125~137；强制"原样转述"，❌ 逐条说明并**确认后再动手**，⚠️ 提一句，"未验证≠通过" | 命令 | 手动 | `cmds/verify-artifacts.md` | phase-and-verification | 无 |
| A-142 | `/spec-guard:setup-convention` | 先 `--dry-run` 预览，转述后用户明确确认才真装；转述 `build-task-dispatch rule:` 行、`will remove:` 等 | 命令 | 手动，先预览 | `cmds/setup-convention.md` | local-convention | 命令正文里夹了大量对实验性派活规则的说明 |
| A-143 | `/spec-guard:teardown-convention` | 调脚本移除约定；`--keep-state`、`--accept-removals`；说明保留项 | 命令 | 手动 | `cmds/teardown-convention.md` | local-convention | 无 |
| A-144 | `/spec-guard:config` | 见 A-100~104 | 命令 | 手动 | `cmds/config.md` | project-config | 无 |
| A-145 | `/spec-guard:link-project` | 见 A-31~36 | 命令 | 手动 | `cmds/link-project.md` | linked-project-root | 无 |
| A-146 | 插件根定位片段 | 每条命令开头：`CLAUDE_PLUGIN_ROOT`→`PLUGIN_ROOT`→`codex plugin list --available --json`，三者失败时分别报哪个失败，"不代表插件未安装" | 每条命令 | 恒开 | 各 `cmds/*.md` 开头 | command-plugin-root、codex-skill-root | 同段 shell 在每条命令各复制一次（已有一致性检查脚本兜底），属维护债 |
| A-147 | 共享检查点规则前置语 | 每条命令第一行："阶段交接、确认或停止前，读取并遵循 spec-guard-ops 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问" | 每条命令 | 恒开 | 各 `cmds/*.md` 第 6 行 | checkpoint-tiers | 把一个跨命令的"行为规则"以复制文本注入每个命令 |

---

## 十一、账本相关的注入（open-commitments 家族）

| 编号 | 名称 | 做什么 | 出现条件 | 默认/可关 | 位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| A-148 | 收到别会话消息时的记账提醒 | 建议下一步之前多一行："这一轮是别的会话发来的消息（对方 `name`，会话 `id`）：先记进本地事项账本——对方、来路与回路、内容、球在谁手里——再决定要不要问用户；记账不是受理，要不要做仍由用户定。传 repoRoot=<路径>" | 有 `.epiq/project.json` 且本轮提示词带 `<cross-session-message …>` 包装 | 随账本启用 | `phase-guard.sh:194-214,110-119` | receipt-hint-on-message、record-on-receipt、open-commitments | 阶段钩子在按"跨会话消息"这一宿主私有包装触发；"记账"、"waiting-on-*"标签属本地账本/协作姐妹插件的话术 |
| A-149 | repoRoot 提示 | 账本工具调用要传 `repoRoot`：路径来自当前目录（跟随指向时在目标项目）；含引号/反斜杠/控制字符时不写路径 | 账本提醒出现时 | 随账本启用 | `phase-guard.sh:72-79` | record-on-receipt | 为绕开账本工具多 worktree 时选错仓库的问题而在注入里补丁 |
| A-150 | 提醒行插入位置 | 提醒行插在"建议下一步"之前（没有建议下一步则放末尾） | 同 A-148 | 恒开 | `phase-guard.sh:108-119` | receipt-hint-on-message | 无 |

---

## 合计与分布

- 功能点总数：**150**（A-01 ~ A-150）。
- 大功能分布：钩子入口 14 · 会话事实 8 · 关联项目 14 · 阶段判定核心 14 · 提示行 41（含上下文 5、评审与外部审查 9）· 并行 4 · 配置 10 · setup/teardown/声明块 19 · 校验 15 · 命令层 8 · 账本注入 3。
- 阶段/提示行全表：IDLE、MAP_ONLY、NEEDS_SPEC、NEEDS_PLAN、BUILDING、MODULE_DONE、DONE（4 种建议变体）、MAP_INVALID、UNKNOWN（2 种）；事实行 21 种（见 5.3、5.4、5.5、6）；外加 hooks.json 3 条与 phase-guard 2 条的诊断 JSON。

## 最值得和用户核对的需求疑点（摘要，详见各行）

1. **上下文阈值提示（A-16~19、A-78~82）**：为宿主已有的上下文用量条/自动压缩做提醒，解析会话记录私有格式、至少 12 个模块反复调阈值与措辞、没有关闭开关。
2. **姐妹插件内容进了阶段注入（A-89、A-92~95、A-148~149）**：delegate 复核广告、module-crew 的 checkout 角色/交回、账本 waiting-on-* 话术都在 spec-guard 的每轮注入里实现，边界该归谁。
3. **评审标记状态机强引导 agent（A-83~88）**：标记只是文件里一行文字，却驱动建议下一步被替换成"不要写 Plan/不要继续"，与"hook 只报告事实和建议、保持灵活"冲突，且无法证明用户真批准过。
4. **link-project 三层（目录级 v1、按会话 v2、失效诊断，A-23~36）**：解决"会话目录不是项目目录"的小众场景，却要手工传 id/路径、命令不自动跟随，可能被宿主多目录能力替代。
5. **约定块模板与派活规则膨胀（A-113、A-123）**：约 30 条汇报/流程风格规则常驻用户 CLAUDE.md、不能按条关闭；`--dispatch` 规则自认"实测更贵"仍保留；另有能力图残留已删除的 `dependency-check` 模块（A-138）。

另：未启用 spec-guard 的项目每轮也要启动一次 python（A-08，行 29-32 早于激活判定行 63），与"无关项目静默退出"的轻量承诺不一致。
