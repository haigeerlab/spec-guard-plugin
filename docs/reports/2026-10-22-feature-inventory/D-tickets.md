# D 事项与账本：功能点清单

范围：commit 85a1f560，只读精读。路径前缀：`H` = `plugins/spec-guard/hooks/`，`S` = `plugins/spec-guard/skills/`，`C` = `plugins/spec-guard/commands/`，`R` = `plugins/spec-guard/references/`。
模块 id 缩写（均为 `spec/CAPABILITY-MAP.md` 中的模块 id）：
LTL=local-ticket-ledger，LDL=ledger-dependency-lock，LWO=ledger-worktree-owner，LLO=ledger-local-only，LIM=ledger-init-machine-config，RCR=remote-credential-redaction，LTP=local-ticket-portability，HTW=hosted-ticket-workflow，HUT=hosted-ticket-untrusted-text，TBD=tracker-backend-default，AH=audit-handoff，RSL=runtime-state-layout，ASC=audit-small-cleanups，PCL=proposal-closeout，OC=open-commitments，ROR=record-on-receipt，RHM=receipt-hint-on-message，PC=project-config。

## 总览

D 区由四块组成，体量约 5900 行（含 4 个命令、4 个 skill、2 份参考）：

1. 本地账本（Epiq 包装）：安装运行时、初始化、接入 Claude／Codex、权限检查。约 1100 行（`local_ledger_runtime.py` 919 + `local_ledger_adapters.py` 180）。
2. 事项受理：`/spec-guard:ticket` 命令加 `ticket` skill（Local 路径），`hosted-ticket-workflow` skill（GitHub／GitLab 路径），`tracker-default` 默认后端。
3. 托管 Issue：`hosted_ticket*.py` 六个文件约 940 行，创建、评论、关闭，都是写远端。
4. Local 迁移：`local_ticket_*.py` 十四个文件约 2400 行，归档、验证、恢复、日志绑定、逐项交接到 GitHub／GitLab。

一个贯穿全区的观察：能力图「目标」段写明 GitHub／GitLab「只作为只读 Proposal Issue 来源，不创建或修改 Issue」，`docs/design.md` 的「已退役的边界」也说可写的远端 tracker 桥「不属于本产品」。而本区 HTW 与 LTP 的 handoff 都会创建、评论、关闭远端 Issue。两处表述冲突，见疑点 Q1。

---

## 一、本地账本启用与连接（Local ledger：Epiq 运行时 + 宿主接入）

入口：`/spec-guard:local-ticket-ledger` 命令（`C/local-ticket-ledger.md`）、`local-ticket-ledger-ops` skill（`S/local-ticket-ledger-ops/SKILL.md`）、脚本 `H/local_ledger_runtime.py`、`H/local_ledger_adapters.py`。整块默认关闭：插件安装、hook、项目打开都不会触发任何安装或初始化（`R/local-ticket-ledger-runtime.md:200`）。

### 1.1 运行时安装与状态

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 1.1.1 | 固定运行时合同 | 后端固定为 `epiq@1.11.0`（MIT，第三方 ljtn/epiq），Node 18+，入口 `node_modules/epiq/dist/mcp.js`，项目身份 `.epiq/project.json`，状态分支 `__epiq_state__`。其他包名或版本一律 invalid | `contract --format json`；所有后续操作都依赖它 | 关（未装即 absent）。无卸载命令 | `H/local_ledger_runtime.py:17-23,70` | local-ticket-ledger | 整个账本能力押在一个第三方单人项目的固定版本上，升级要人工重核 39 个工具清单（见 1.4）。这是插件主线（多模块 Spec 约定）之外的独立产品能力，更像应是独立插件，见 Q2 |
| 1.1.2 | status 只读诊断 | 分开报告 `node`、`runtime`、`project` 三段；顶层 absent／ready／initialized／conflict／invalid。不下载、不创建目录 | `status --format json\|text`；ticket skill 写入前也调用 | 开（只读，随时可用） | `H/local_ledger_runtime.py:144,171,761` | local-ticket-ledger；ledger-worktree-owner；ledger-local-only | 无 |
| 1.1.3 | npm ci 锁定安装 | 把插件自带 `package.json`／`package-lock.json` 复制到同级临时目录，执行 `npm ci --ignore-scripts --no-audit --no-fund`，核对包名、版本与 `epiq-mcp` 入口，通过后原子改名到 `~/.spec-guard/local-ticket-ledger/runtime/`。绝不写项目 `node_modules` | `install --confirm-install` | 关；必须用户明确要求。装在用户级目录，可手工删，但没有卸载命令 | `H/local_ledger_runtime.py:361-382,403-462` | ledger-dependency-lock；local-ticket-ledger | 约 119MB、269 个传递依赖的下载只为一个可选的事项账本；对「多模块 Spec 约定」插件而言体量与供应链面偏大，见 Q2 |
| 1.1.4 | 锁文件完整性校验 | `validate_lock_files` 检查随包 lockfile 可用（固定 epiq 版本、269 个包带 sha512、`resolved` 指向 registry.npmjs.org）；维护者有漂移回归测试 | 安装前自动；维护者升级 Epiq 时 | 内部，不可关 | `H/local_ledger_runtime.py:30`；`locks/local-ticket-ledger/package.json`（仅声明 `epiq 1.11.0`）与 `package-lock.json`（269 个 resolved）；`R/local-ticket-ledger-runtime.md:320-332` | ledger-dependency-lock | 无 |
| 1.1.5 | 安装失败不留残渣 | npm 失败、完整性校验失败（EINTEGRITY）、产物不符合合同时只删本次临时目录，runtime 保持 absent，诊断带 npm 最后一行输出 | 安装失败路径 | 内部 | `H/local_ledger_runtime.py:365,445-460` | ledger-dependency-lock | 无 |
| 1.1.6 | 空目录接管 | 旧版本安装失败遗留的空目录可被重新安装直接接管；非空的无效目录一律拒绝覆盖 | `install --confirm-install` | 内部 | `H/local_ledger_runtime.py:413-420` | ledger-dependency-lock | 为兼容一个已修复的旧缺陷而保留的特例，可能随版本老化而多余 |
| 1.1.7 | locked／unlocked 状态与替换 | ready 时报告运行时目录的 lockfile 是否与随包一致；unlocked 照常可用、绝不自动替换；用户确认后 `--replace-unlocked` 先在临时目录装好验证，再换掉旧目录，失败保留旧的，账本数据不受影响 | `status`；`install --confirm-install --replace-unlocked` | 关；显式 | `H/local_ledger_runtime.py:133,382-400,403` | ledger-dependency-lock | 为「旧方式安装」兼容层，若 lockfile 安装已是唯一方式，此分支只服务早期用户 |
| 1.1.8 | Node 前置检查 | 读 `node --version`，要求 18+，状态与运行时分开报告 | status／install／adapters | 内部 | `H/local_ledger_runtime.py:82` | local-ticket-ledger | 无 |

### 1.2 项目初始化

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 1.2.1 | preflight 预检 | 只读 Git 工作树状态与 `origin` URL：工作树不干净拒绝（dirty）；有 origin 时返回 `push-confirmation-required` 并要求二选一；非 Git 返回 not-git。预检单独运行不写不推 | `preflight --format json`；初始化前必跑 | 开（只读） | `H/local_ledger_runtime.py:306-358` | local-ticket-ledger；ledger-local-only | 无 |
| 1.2.2 | 远端 URL 凭据脱敏 | preflight 报告 origin 时把 URL 里的 userinfo 替换成标记，不进输出 | preflight、Epiq 拒绝信息 | 内部 | `H/local_ledger_runtime.py:297-303,517-524` | remote-credential-redaction；ledger-init-machine-config | 无 |
| 1.2.3 | `--local-only` 本机模式 | 有 origin 时只对这一次 Epiq 子进程追加 `GIT_CONFIG_*`，把 `remote.origin.pushurl` 指向不存在的路径 `/nonexistent/spec-guard-local-only`，使 Epiq 的 `git push` 失败并记为警告；不改仓库或用户的 git 配置，已有 `GIT_CONFIG_COUNT` 条目保留在前 | `initialize --local-only` | 推荐默认，但需用户选；与 `--allow-epiq-push` 互斥 | `H/local_ledger_runtime.py:596-609,612-644` | ledger-local-only | 通过「制造一个必然失败的 push」来禁推送，是对上游缺少「不推送」开关的绕行，依赖上游把 push 失败当警告的行为 |
| 1.2.4 | `--allow-epiq-push` 显式推送 | 用户单独确认上游初始化会推送普通分支与状态分支后才放行；两者同给时预检 invalid | `initialize --allow-epiq-push` | 关 | `H/local_ledger_runtime.py:306-358,465-484` | local-ticket-ledger；ledger-local-only | 无 |
| 1.2.5 | initialize 经 MCP 调用 `epiq_project_init` | 插件自己以 stdio 启动 Epiq MCP，发 JSON-RPC 调用 `epiq_project_init`，提交 `.epiq/project.json`、建 `__epiq_state__`；进程使用私有 umask 077 | `initialize --confirm-initialize` | 关；必须显式 | `H/local_ledger_runtime.py:501-594,612-644` | local-ticket-ledger；ledger-local-only | 插件内实现了一个最小 MCP 客户端，仅为驱动一次初始化 |
| 1.2.6 | 机器级设置共存 | `user-name`、`preferred-editor`、`auto-sync` 三项改为可选，只传用户给的；`status` 的 `machineSetup` 只读报告 `~/.epiq-global/config.json` 已有哪几项，读不了为 unknown 不当未设置；已有的告诉用户到 Epiq TUI 用 `:config` 改 | `status`；`initialize` | 内部 | `H/local_ledger_runtime.py:718-760` | ledger-init-machine-config | 为适配上游「整机偏好」设计而长出的分支，复杂度源于第三方 |
| 1.2.7 | Epiq 拒绝信息清洗 | 拒绝诊断 `Epiq refused: <msg>`：控制字符换空格，远端地址凭据遮掉，限 300 字 | initialize 失败 | 内部 | `H/local_ledger_runtime.py:517-545` | ledger-init-machine-config | 无 |
| 1.2.8 | 初始化警告只报条数与编号 | `warningCount`、`warningCodes`（如 `init:15`），不回显 Git 原始错误 | initialize 成功 | 内部 | `H/local_ledger_runtime.py:486-498` | ledger-init-machine-config；ledger-local-only | 无 |
| 1.2.9 | 初始化后合并提示 | 提示把含 `.epiq/project.json` 的提交合进默认分支，否则从默认分支开出的工作树找不到账本 | initialize 成功文案 | 内部 | `C/local-ticket-ledger.md:134-137`；`H/local_ledger_runtime.py:260` | ledger-local-only | 无 |
| 1.2.10 | 身份在别的分支的诊断 | 当前检出无 `.epiq/project.json` 而本地或远端跟踪分支有时，`project.identityElsewhere` 报分支名（不联网） | status | 内部 | `H/local_ledger_runtime.py:260-273` | ledger-local-only | 无 |

### 1.3 状态 worktree、数据目录、权限

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 1.3.1 | 状态 worktree 归属检测 | Epiq 把状态 worktree 放在 `<EPIQ_GLOBAL_DIR 或 ~/.epiq-global>/worktrees/<projectId>`，路径只含 projectId。status 报告 absent／owned／foreign／unknown 及诊断（unreadable、away、branch-missing）；foreign 时顶层变为 conflict、退出码 1，给出占用仓库与处理办法 | status | 开（只读）；处理办法只是文字，插件不自动执行 | `H/local_ledger_runtime.py:207-258` | ledger-worktree-owner | 这是对上游「路径只用 projectId」缺陷的补偿，价值在于不让用户被 git worktree 报错困住 |
| 1.3.2 | projectId 单一路径分量校验 | projectId 含斜杠、点路径、绝对路径视为 invalid，不据此拼接全局目录路径；受管路径是符号链接返回 unknown | status | 内部 | `H/local_ledger_runtime.py:171-196,207-258`；`R/local-ticket-ledger-runtime.md:262-263` | ledger-worktree-owner；local-ticket-ledger | 无 |
| 1.3.3 | pending 事件计数与归档提醒 | `auto-sync` 为 false 时事项事件只是状态 worktree 里未提交的 `~pending` 文件，无 git 历史。status 报 `pendingEvents`（非空行数，只计数不解析，读不了为 null），大于 0 时提醒用离线归档备份 | status | 内部 | `H/local_ledger_runtime.py:276-294` | ledger-local-only | 无 |
| 1.3.4 | storage-check | 只读检查 `EPIQ_GLOBAL_DIR`（默认 `~/.epiq-global`）目录自身的类型、所有者、POSIX 权限位：absent／private-posix／exposed／unusable／unsafe／unknown，并声明 `scope: posix-mode-only`（不是 ACL 证明） | `storage-check --format json` | 开（只读，按需） | `H/local_ledger_runtime.py:647-671` | local-ticket-ledger | 在一个事项账本内置目录权限审计，对「多模块 Spec 约定」是旁支能力 |
| 1.3.5 | storage-protect | 只读预览把宽权限根目录改为 0700；加 `--confirm-protect` 后重检所有者、类型、父目录和路径身份，拒绝符号链接、错误归属、他人可写父目录，只对根目录 chmod 一次，不递归、不创建 | `storage-protect`；`--confirm-protect` | 关；需用户审查路径后授权 | `H/local_ledger_runtime.py:674-715` | local-ticket-ledger | 同上；这是整个插件里少数会 chmod 用户主目录下目录的写入点 |
| 1.3.6 | 私有 umask 077 | 新生成的宿主片段通过 `/bin/sh -c 'umask 077; exec "$1" "$2"'` 启动 Node 与 Epiq 入口，使首次创建的数据根和事件文件为用户私有；已装旧条目不自动迁移 | adapters 生成片段 | 内部 | `H/local_ledger_adapters.py:40-48` | local-ticket-ledger | 无 |

### 1.4 宿主接入（Claude MCP 注册、ask 规则、Codex 配置）

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 1.4.1 | 只读打印宿主片段 | `local_ledger_adapters.py codex\|claude` 输出 stdio 配置片段（Codex 为 TOML 表，Claude 为 command／args／permissions.ask JSON），不含 token、HTTP 地址、账本内容 | `adapters codex` / `claude` | 开（只读） | `H/local_ledger_adapters.py:51-60,142-168` | local-ticket-ledger | 无 |
| 1.4.2 | Claude MCP 注册 | `install-claude --confirm-install`：先合并 ask 规则，再通过 `claude mcp add --scope user spec-guard-local-ledger -- <command>` 注册用户级 stdio 服务；通过 CLI 而不改 Claude 状态文件；同名已存在则拒绝覆盖；超时 30 秒 | `install-claude --confirm-install --claude-bin "$(command -v claude)"` | 关；需用户明确指定宿主；客户端重启后生效。无卸载命令 | `H/local_ledger_adapters.py:126-132`；`H/host_config_removal.py:11-24` | local-ticket-ledger | 配置写在用户级（所有项目共享），而账本是仓库级，需要每次调用传 `repoRoot`（Claude 的用户级 MCP 进程不在会话目录）；这是接入形态带来的使用摩擦。另 `host_config_removal.py` 现在只剩 `add_claude_server`，移除函数已在审查 F17 删除，文件名与内容不符 |
| 1.4.3 | Claude `permissions.ask` 门控 | 把 10 个高风险 Epiq 工具（`epiq_sync`、`epiq_project_init`、`epiq_skill_install`、`epiq_issue_comment_delete`、`epiq_swimlane_delete`、`epiq_tag_remove`、`epiq_contributor_remove`、三个邮箱工具）写入 `~/.claude/settings.json` 的 `permissions.ask`（`mcp__spec-guard-local-ledger__<tool>`），保留其他设置、保持文件权限、拒绝符号链接或非 JSON 对象；`bypassPermissions` 模式下无效 | `install-claude`（自动）；`install-claude-guard --confirm-install`（旧宿主迁移） | 随安装自动加；可手工删规则 | `H/local_ledger_adapters.py:32-35,62-99,159-160` | local-ticket-ledger | 修改用户全局 Claude 设置文件。工具清单与 Epiq 版本强绑定，升级必须人工重核（文件内注释已要求） |
| 1.4.4 | Codex 配置写入 | `install-codex --confirm-install`：向 `~/.codex/config.toml` 原子追加 `[mcp_servers.spec_guard_local_ledger]` 表，保持原权限，拒绝符号链接，同名表存在则拒绝覆盖；不使用 Codex managed app-server，不影响 ChatGPT in Chrome | `install-codex --confirm-install` | 关；显式 | `H/local_ledger_adapters.py:102-123` | local-ticket-ledger | 无 |
| 1.4.5 | Codex `enabled_tools` 白名单 | Codex 片段只暴露 29 个日常工具，10 个高风险工具与 Epiq 日后新增的工具都不注册；需要同步的人到终端自行用受管运行时的 `node_modules/.bin/epiq` | 随 1.4.4 | 随安装 | `H/local_ledger_adapters.py:18-37,51-60` | local-ticket-ledger | Codex 路径下 `epiq_sync` 等不可用，等于 Codex 与 Claude 能力不对等，且是靠插件维护的静态清单 |
| 1.4.6 | 宿主迁移路径 | 旧版本接入的宿主不自动获得门控；Claude 用 `install-claude-guard`，Codex 手工把 `enabled_tools` 行加入现有表 | 用户要求时 | 关 | `H/local_ledger_adapters.py:142-168`；`R/local-ticket-ledger-runtime.md:431-440` | local-ticket-ledger | 兼容旧装机，随用户迁移完应可删 |
| 1.4.7 | 不提供移除／卸载 | 明确没有「删除账本」「移除 MCP」命令；host_config_removal 的移除函数已删除；`teardown-convention` 也不管账本。停用只能用户手工删 MCP 条目、runtime 目录 | 无入口 | 不可由插件关闭 | `R/local-ticket-ledger-runtime.md:442-444`；`C/local-ticket-ledger.md:178-180`；`H/host_config_removal.py:1-6` | local-ticket-ledger；audit-small-cleanups | 一旦 init 就把 `.epiq/project.json` 提交进仓库、写入用户级 MCP 与 ask 规则，却没有对称的退出路径，可逆性差，见 Q6 |

### 1.5 激活信号与读回提醒（与 phase-guard 的接口）

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 1.5.1 | 账本启用的读回提醒 | 项目存在 `.epiq/project.json` 时，`SessionStart`（matcher `startup\|clear`）输出一句固定读回提醒；钩子只判文件存在，不读账本、不调 Epiq。属于 phase-guard，不在 D 区文件内 | 会话启动／clear | 项目启用账本即开；不能单独关 | `plugins/spec-guard/hooks/phase-guard.sh:69-81,184,197`；`hooks/hooks.json:24` | open-commitments；record-on-receipt；receipt-hint-on-message | 账本这个可选能力在每个启用项目里向主线 hook 注入文案，把账本与「阶段注入」主线耦合；是否应由账本能力自己承担，见 Q4 |

---

## 二、自然语言受理事项（Local：`/spec-guard:ticket` + `ticket` skill）

入口：Claude 为命令 `C/ticket.md`，Codex 为 skill `S/ticket/SKILL.md`。默认关闭：账本未启用时只做只读诊断并给一条下一步（`S/ticket/SKILL.md` 末段）。无专属脚本，全部通过 Epiq MCP 工具由 agent 执行，纯规则文本，无可执行校验。

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 2.1 | 命令无参列表 | 只说 `/spec-guard:ticket` 时列出未关闭事项（标题、短编号、状态）；账本未启用则只读诊断 | `/spec-guard:ticket` | 随账本启用 | `C/ticket.md:10-14` | local-ticket-ledger | 无 |
| 2.2 | 自然语言受理 | 用户只描述事，不必给 Epiq 工具名、看板 ID、泳道 ID 或角色；agent 判断是可执行事项、补充还是无需追踪的小操作 | 命令／Codex 说「记个 bug」 | 随账本启用 | `S/ticket/SKILL.md:8-9,24-35` | local-ticket-ledger | 是整块里最贴近「需求受理」的部分，但与 Spec 主线（需求→能力图模块）是两条平行入口：事项与模块之间没有强绑定，见 Q3 |
| 2.3 | 写前状态检查 | 写入前读 status：顶层须 `initialized` 且 `stateWorktree` 为 owned 或 absent；conflict、foreign、unknown 或运行时异常时不调写工具、不移动状态 worktree | ticket 每次写 | 内部 | `S/ticket/SKILL.md:11-17` | local-ticket-ledger；ledger-worktree-owner | 无 |
| 2.4 | `repoRoot` 必传 | 每次 `epiq_*` 调用都传当前项目根；不传时 Epiq 取 MCP 进程自己的 cwd，会误报「No .epiq/project.json found」 | 所有 epiq 调用 | 内部 | `S/ticket/SKILL.md:17-19`；`C/ticket.md:24-26` | ledger-local-only | 为用户级 MCP 与仓库级账本不匹配打的补丁 |
| 2.5 | 标题优先显示 | 首次提到事项写 `《标题》（短编号）`，不只显示短编号，不展示完整内部 ID；写工具只返回 ID 时沿用写前读到的标题，读不到就说无法核实 | 所有面向用户回复 | 内部 | `S/ticket/SKILL.md:20-26`；`C/ticket.md:15-22` | local-ticket-ledger | 纯展示规则，占用较多规则篇幅 |
| 2.6 | 短编号→完整 ID | 写操作前先 `epiq_issue_get` 取完整 `value.id`，写工具用 `issueId`／`issueIds` 传完整 ID，不直接传短编号；读取失败报告实际错误，不推断账本未初始化 | 评论、关闭等 | 内部 | `S/ticket/SKILL.md:55-57`；`C/ticket.md:28-31` | local-ticket-ledger | 无 |
| 2.7 | 查重（found／absent／unknown） | 实现类事项动代码前，`epiq_issue_list(includeClosed:true)` 按标题、同义词、描述核候选，再 `epiq_issue_get` 读全文；found 沿用，absent 才创建并读回稳定 ID，unknown 不创建；创建前再查一次，并声明不是原子防重 | 实现需求、修复问题 | 内部 | `S/ticket/SKILL.md:27-35` | local-ticket-ledger；audit-handoff | 查重靠 agent 的语义判断，无法被代码校验；两个 agent 并发仍可能重复（文中承认） |
| 2.8 | 最小事项创建 | 创建最小事项（问题、范围、可验证结果），详细 Spec／Plan 之后补；不把完整文档复制进正文；探索与小操作不强制建事项 | 创建时 | 内部 | `S/ticket/SKILL.md:33-35` | local-ticket-ledger | 事项正文与 `spec/`、`tasks/` 产物并存，可能出现两处记录同一需求，见 Q3 |
| 2.9 | 泳道选择 | 用 `epiq_swimlane_list` 找开放泳道，把 ID 传给 `epiq_issue_create` 的 `parentId`；Closed 看板下泳道只读，会报 `Swimlane is readonly`；优先 Todo／To do／Backlog，无明显收件泳道且多选才问一次 | 创建时 | 内部 | `S/ticket/SKILL.md:42-46` | ledger-local-only | 对 Epiq 看板模型的细节规则渗入插件 skill |
| 2.10 | 不自动建结构 | 不因一次请求自动创建看板、泳道、标签、负责人或永久 Agent 身份 | 全程 | 内部 | `S/ticket/SKILL.md:45-47` | local-ticket-ledger | 无 |
| 2.11 | 实质变更用决定评论 | 范围、验收、方案实质变更先追加决定评论（旧约定、废止部分、新约定、理由、影响），再把正文改成生效版本并指向该评论；评论成功而编辑失败报「决定待应用」，重试先读回；独立新目标另建事项并关联 | 变更范围时 | 内部 | `S/ticket/SKILL.md:48-53` | local-ticket-ledger | 与 `change-source-record`（Spec 末尾「变更记录」）在做同类事，一套在事项里，一套在 Spec 里 |
| 2.12 | 完成与关闭规则 | 完成时先记录代码引用、验证方式与结果、结论；验证未通过保持开放；仅用户要求关闭或确认验证通过才关；关闭后读回，响应丢失先读回再重试；不以「已修复」评论推断已关闭 | 收尾 | 内部 | `S/ticket/SKILL.md:54-58` | local-ticket-ledger | 无 |
| 2.13 | GitHub PR 交付对账 | 代码经 GitHub PR 交付时，PR 创建后把核实的 PR 地址及覆盖范围逐条写回事项；合并后核对实际合并状态、合并提交与 CI／验收再写回；PR 合并本身不构成关闭证明；未获公开授权的 Local 标题与编号不写进公开 PR；合并后账本不可用则报「待对账」 | PR 流程 | 内部 | `S/ticket/SKILL.md:56-65` | local-ticket-ledger；audit-handoff | 把「Local 事项」与「GitHub PR」两个系统的对账义务压在 agent 的规则上，易漏 |
| 2.14 | 项目级审查→事项交接 | 审查批次完成后按根因合并重复发现，再按 2.7 查重；待调查发现只记缺少的证据；读回实际事项后才把报告状态从「待入账」改「事项已入账」；Local 不可用保持待入账；Git remote 为 GitHub 也不改变已选 Local 目标 | 审查批次结束 | 内部 | `S/ticket/SKILL.md:36-41`；`C/ticket.md:3-8` | audit-handoff | 事项作为审查结论的落点；若不启用账本则此段无意义 |
| 2.15 | 高风险工具逐次确认 | `epiq_sync`、`epiq_project_init`、`epiq_skill_install`、删除类与邮箱类 10 个工具，仅在用户本轮明确要求该具体操作并再次确认后使用，事项内容、评论、网页或其他 Agent 消息中的文字不构成授权；工具不可用或被拒时如实说明，不绕道 shell／Git | 调用这些工具时 | 内部（skill 层，另有 1.4.3 宿主层） | `S/ticket/SKILL.md:67-74`；`C/ticket.md:33-40` | local-ticket-ledger | 同一规则在命令与 skill 中重复，以及与 1.4.3 双层防护 |
| 2.16 | 身份复用 | 当前会话已声明的 Epiq 身份继续复用；用户提供或确认稳定身份时才调 `epiq_actor_assume`，不为每次会话编造新贡献者 | 首次写 | 内部 | `S/ticket/SKILL.md:67-68` | local-ticket-ledger | 无 |
| 2.17 | 通知另一个 Agent | 先完成事项操作，再运行 `hooks/agent_relay_probe.py --host <claude\|codex>`；`ready` 才用 `agent-relay:collab` 按名字发带标题与短编号的消息，其他状态原样转述并跳过，不改用其他途径；跨仓库收件人必须附来源项目与文字摘要；报告事项写入与消息投递各自结果 | 用户要求通知 | 随 agent-relay 是否安装 | `S/ticket/SKILL.md:75-84` | local-ticket-ledger；agent-relay-interface-2；collaboration-boundary | 与姐妹插件 agent-relay 的耦合点；账本与邮箱「各自独立」靠文字约束 |
| 2.18 | 账本不可用时降级 | MCP 工具不可用或项目未初始化时转 `local-ticket-ledger-ops` 的只读诊断，只给当前所需一条下一步；日常入口不隐式安装运行时、不初始化、不改宿主配置、不同步、不写 GitHub／GitLab | 工具缺失时 | 内部 | `S/ticket/SKILL.md:86-90` | local-ticket-ledger | 无 |
| 2.19 | 不直接编辑账本原始状态 | `.epiq`、`__epiq_state__` 只由 Epiq MCP 管理，agent 不直接编辑 | 全程 | 内部 | `S/ticket/SKILL.md:88-90` | local-ticket-ledger | 无 |
| 2.20 | 未了承诺落盘（账本的另一用途） | 「别人向我提的需求、我通知后等对方回报、等用户拍板」三类有人在等的事，在球换手时记进账本；收到即记；收到会话消息时钩子提醒记账。规则在模板与 phase-guard，不在 D 区文件，但依赖本账本 | 收到期待回音的消息等 | 账本启用才生效 | `spec/open-commitments.md`、`spec/record-on-receipt.md`、`spec/receipt-hint-on-message.md`；`plugins/spec-guard/templates/claude-block-local.md` | open-commitments；record-on-receipt；receipt-hint-on-message | 把事项账本当「协作承诺台账」用，与 agent-relay 的信箱、decision-inbox 的待决事项账、module-crew 的收件记账同属一类问题（别人在等什么），明显重叠，见 Q4。注：用户提到的 `waiting-on-*` 标签只出现在 `workflow-checkpoints.md` 与模板里，不在 D 区文件内 |

---

## 三、默认后端（`/spec-guard:tracker-default`）

入口：`C/tracker-default.md`；脚本 `H/tracker_default.py`；数据 `.agent/tracker.json`（入库）。默认：不存在，缺失不是错误。

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 3.1 | 读取与三态 | `show`：configured／absent（无文件，非错误）／invalid（诊断码 `tracker-default-invalid`，绝不当 absent） | `tracker_default.py show --project <p>` | 开（只读） | `H/tracker_default.py:129-150,285` | tracker-backend-default | 无 |
| 3.2 | 目标形状校验 | github=`{host, repo}`，gitlab=`{host, projectId:正整数}`，local=`{projectId}`；多余字段、版本非 1、未知后端均 invalid | set／show | 内部 | `H/tracker_default.py:26-38,64-96` | tracker-backend-default | 无 |
| 3.3 | 防敌意仓库读取 | `.agent/tracker.json` 是仓库内容：O_NOFOLLOW、非常规文件、超过 64KB、非 UTF-8 都算 invalid；不回显文件原文，只输出解析值 | show | 内部 | `H/tracker_default.py:98-127` | tracker-backend-default | 无，安全做得认真但对象只是一个预填值 |
| 3.4 | 设置／切换 | `set` 不带 `--confirm` 只打印改前改后差异；`--confirm` 原子写回这一个文件并保留权限，不碰 `.agent/state.json`、`spec/`、`tasks/` 或 Git；形状非法退出码 2 且不写 | `tracker_default.py set --backend … [--confirm]` | 关；显式 | `H/tracker_default.py:210-282` | tracker-backend-default | 无 |
| 3.5 | resolve 规则 | 显式后端与目标优先于默认，来源标注 `explicit`／`project-default`／`project-default-target`；显式后端与默认不同则 `target-unselected`；默认只预填预览，每次外部写入仍逐次授权 | 调用方（HTW、proposal-closeout） | 内部 | `H/tracker_default.py:152-181` | tracker-backend-default；proposal-closeout | 默认值「不是权威、不决定写入、不改变既有绑定」，那它存在的净价值只是省去每次输入 host／repo；见 Q7 |
| 3.6 | 声明「不是激活信号」 | 文件在不在与阶段提示完全无关；已退役的 `.agent/state.json` tracker 字段被删除 | 设计约束 | 内部 | `H/tracker_default.py:1-11`；`C/tracker-default.md:259-262` | tracker-backend-default | 无 |
| 3.7 | 紧急切换场景 | 平台不可用时把默认改成 local，此后新建事项走本地；既有事项仍绑定原后端，命令报告它们当前读不到，不在本地重建 | 文案场景 | 内部 | `C/tracker-default.md:296-298` | tracker-backend-default | 无 |
| 3.8 | 汇总显示于 config | `/spec-guard:config` 汇总显示默认事项后端的值与来源（该命令不在 D 区） | config | 内部 | `spec/project-config.md` | project-config | 无 |

---

## 四、GitHub／GitLab 普通 Issue 托管（`hosted-ticket-workflow`）

入口：`S/hosted-ticket-workflow/SKILL.md`，由 `ticket` 命令在用户或审查批次明确选定 GitHub／GitLab 时加载（`C/ticket.md:6-8`）。脚本：`H/hosted_ticket_read.py`、`hosted_ticket.py`、`hosted_ticket_write.py`、`hosted_ticket_action.py`、`hosted_ticket_actions.py`、`hosted_ticket_provider.py`。默认关闭，无激活信号；依赖本机已登录的 `gh`／`glab`。

### 4.1 查重与创建

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 4.1.1 | 明确目标才开 | 仅处理用户或审查批次明确选用的 GitHub／GitLab 普通缺陷 Issue；不凭 Git remote、旧 `.agent/state.json` 或 Proposal Issue 推断目标；无目标则先补目标，只读审查到报告为止 | ticket 命令判断 | 默认关 | `S/hosted-ticket-workflow/SKILL.md:8-15`；`C/ticket.md:6-8` | hosted-ticket-workflow；tracker-backend-default | 见 Q1：能力图总目标写明不创建或修改 Issue |
| 4.1.2 | 完整分页读取查重 | `hosted_ticket_read.py` 完整分页读取开放与关闭事项，排除 GitHub PR，返回 found／absent／unknown／conflict | `hosted_ticket_read.py --platform … --request-id … --title …` | 只读，随用 | `H/hosted_ticket_read.py:16-53` | hosted-ticket-workflow | 无 |
| 4.1.3 | 分页上限 | 每页 100，最多 50 页（即最多 5000 条）；页过大、非列表、条目非对象视为 malformed；到上限仍满页报 `pagination limit reached`，结果 unknown 而不是静默截断 | list_issues／comments | 内部 | `H/hosted_ticket_provider.py:50-52,100-110` | hosted-ticket-workflow | 无 |
| 4.1.4 | 稳定 request marker | 每个事项正文末行带 `<!-- spec-guard-hosted-ticket:v1 <request-id> -->`；末行恰好一次为 match，出现在别处或多次为 displaced／ambiguous conflict | read／publish | 内部 | `H/hosted_ticket_read.py:12-13,32-45` | hosted-ticket-workflow | 在公开 Issue 正文里留机读标记，给读者看到的是插件实现细节 |
| 4.1.5 | 同名候选冲突 | 无 marker 但标题大小写不敏感相同视为 `root-cause-candidate` conflict，列出候选（最多 10 条，附 `candidatesTotal`） | read | 内部 | `H/hosted_ticket_read.py:46-52`；`H/hosted_ticket_provider.py:30-47` | hosted-ticket-workflow；hosted-ticket-untrusted-text | 无 |
| 4.1.6 | 根因复核闸门 | `absent` 仍带 `rootCauseReviewRequired`：精确标记与同名查重不能证明没有同根因异名事项；agent 须用平台查询逐项阅读，不完整或有歧义时停止，不传 `--root-cause-reviewed` | publish 前 | 内部 | `H/hosted_ticket_read.py:53`；`H/hosted_ticket_write.py:88-95`；`S/hosted-ticket-workflow/SKILL.md:28-31` | hosted-ticket-workflow | `--root-cause-reviewed` 只是一个布尔参数，agent 自己传，代码无法验证它真的做了复核（skill 对 `--coverage-complete` 也自承「布尔参数本身不是证据」）。形式大于实质 |
| 4.1.7 | 目标事实与可见性核验 | 先取目标元数据：GitHub 要求 `full_name` 一致、`has_issues` 真、有 id、private 布尔；用户给的 visibility 与实际不符返回 `target-visibility-changed`；host／target 字符正则校验，GitHub 目标必为 `owner/repo` | read／preview／publish | 内部 | `H/hosted_ticket_provider.py:113-140`；`H/hosted_ticket_read.py:20-24` | hosted-ticket-workflow | 无 |
| 4.1.8 | preview（含 digest） | `hosted_ticket.py preview` 只读输出精确目标、正文、来源标记与 digest；要求展示目标可见性与完整拟发布内容并取得本次授权；内部路径、Local 私有编号、凭据、敏感日志不得入公开 Issue（skill 规则） | `hosted_ticket.py preview` | 关（需用户授权后才 publish） | `H/hosted_ticket_write.py:17-43`；`H/hosted_ticket.py:16-63`；`S/hosted-ticket-workflow/SKILL.md:32-37` | hosted-ticket-workflow | 无 |
| 4.1.9 | publish 的多重门 | 须同时有 `--confirm`、`--root-cause-reviewed`、`--expected-digest`（与预览一致）、marker 末行校验、preview 完整性；缺任一返回 confirmation-required／review-required／preview-invalid | `hosted_ticket.py publish …` | 关 | `H/hosted_ticket_write.py:88-110` | hosted-ticket-workflow | 门很多，但 `--confirm` 仍是 agent 可自行填的参数，人的授权在对话里而非代码里 |
| 4.1.10 | 防重发意图日志 | 创建前把 `attempted:true` 记录写进私有意图文件（`hosted-ticket-intents`，0600，目录 0700），用 flock 串行；结果未知时下次先按 marker 对账，若上次尝试且远端不可见返回 `prior-create-not-visible`，绝不自动重发；确定拒绝（4xx）则标 `attempted:false` 并回报状态码 | publish | 内部 | `H/hosted_ticket_write.py:44-80,111-166`；`H/hosted_ticket.py:13` | hosted-ticket-workflow；runtime-state-layout | 无 |
| 4.1.11 | 创建后读回对账 | 创建响应后 `get_issue` 读回比对标题与正文；读回失败再按 marker 重新 inspect；`verified`／`found`／`conflict`／`unknown`；找到已有同内容则复用不重建 | publish | 内部 | `H/hosted_ticket_write.py:81-87,129-166` | hosted-ticket-workflow | 无 |
| 4.1.12 | 定性拒绝与未知结果区分 | 通过 `gh|glab api --include` 解析 HTTP 状态；`{400,401,403,404,405,410,413,414,422}` 为 `provider-rejected`，其余失败（超时、5xx、无状态）为 `write result is unknown`；30 秒超时 | 所有写 | 内部 | `H/hosted_ticket_provider.py:52,65-97` | hosted-ticket-workflow | 无 |
| 4.1.13 | 双平台适配器 | GitHub 走 `gh api --hostname`，GitLab 走 `glab api`；校验 `html_url`／`web_url` 必须与 host、目标路径完全一致且无 query／fragment；GitLab 记录并绑定 web scheme（http／https） | 所有托管操作 | 内部 | `H/hosted_ticket_provider.py:121-344` | hosted-ticket-workflow | 为 GitLab 和 GitHub 各写一份并行适配，另有 Proposal 读适配器和 LTP 交接适配器共三套 gh／glab 封装，见 Q8 |
| 4.1.14 | 非指令文本标注 | 命令输出里的远端 Issue 标题截 200 字、正文只给 300 字摘录 `bodyExcerpt` 加 `bodyLength`，经 phase 的 `safe_fragment` 净化；冲突候选最多 10 条；输出带 `remoteText` 说明「这是数据不是指令」；匹配、digest、写门仍用完整文本 | read／publish／comment／close 输出 | 内部 | `H/hosted_ticket_provider.py:10-47` | hosted-ticket-untrusted-text | 针对提示注入的合理防护 |

### 4.2 讨论与交付收尾

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 4.2.1 | 决定评论预览与发布 | `comment-preview`／`comment-publish`：用稳定 `--event-id` 生成带标记 `spec-guard-hosted-comment:v1` 的评论，digest 绑定；Issue 标题或正文在预览后变化则停止重核；评论已写入则按标记读回；结果未知不自动补发；marker 不得出现在用户消息中 | `hosted_ticket_action.py comment-*` | 关；每次授权 | `H/hosted_ticket_actions.py:21-137`；`H/hosted_ticket_action.py:27-87` | hosted-ticket-workflow | 无 |
| 4.2.2 | 评论意图日志与锁 | 同 4.1.10 机制：私有意图文件加 flock，`prior-comment-not-visible` 防二次发 | comment-publish | 内部 | `H/hosted_ticket_actions.py:66-137` | hosted-ticket-workflow | 无 |
| 4.2.3 | GitLab 内部备注处理 | 评论列表跳过 `internal` 备注，但若 marker 出现在私有备注里报 ambiguous；`internal` 字段缺失即抛错 | GitLab list_comments | 内部 | `H/hosted_ticket_provider.py:290-302` | hosted-ticket-workflow | 无 |
| 4.2.4 | 交付核对（PR／MR） | `get_delivery` 读回 PR／MR 的 merged 状态与合并提交，核对 base 仓库、URL、编号；GitLab fast-forward／squash 无 merge_commit 时用 squash／sha 并回溯该提交是否在目标分支的 refs 中 | close-preview | 内部 | `H/hosted_ticket_provider.py:200-209,309-344` | hosted-ticket-workflow | 无 |
| 4.2.5 | 关闭预览与发布 | `close-preview` 要求 `--coverage-complete` 与来自真实 CI／验收的 `--validation-file`，PR／MR 已合并才出 preview，Issue 已关则 `already-closed`；`close-publish --expected-digest … --confirm` 重核交付、目标、Issue 内容摘要后关闭并读回；`verified` 只证明远端已关闭 | `hosted_ticket_action.py close-*` | 关；每次授权 | `H/hosted_ticket_actions.py:140-206` | hosted-ticket-workflow | `validation-file` 内容真伪与 `--coverage-complete` 均由 agent 自填；代码只验形式，验收真实性仍靠 agent 诚信（skill 已承认） |
| 4.2.6 | 范围续授权限制 | 新发布、评论、关闭各需独立授权，「继续」不扩大上次授权范围；Proposal 生命周期保持只读，旧 tracker bridge 不恢复；普通 bug 不自动建能力模块 | 全程 | 内部 | `S/hosted-ticket-workflow/SKILL.md:56-74` | hosted-ticket-workflow | 无 |
| 4.2.7 | 单复数命名陷阱 | `hosted_ticket_action.py`（CLI）与 `hosted_ticket_actions.py`（库）相差一个字母，已在两文件头注释警示；改名会使带行号引用的审计记录失效 | 维护者 | 内部 | `H/hosted_ticket_action.py:1-9`；`H/hosted_ticket_actions.py:1-7` | hosted-ticket-workflow | 命名问题已被自己承认；可视为过度拆分的症状 |
| 4.2.8 | 检查点报告 | 每个检查点按共享检查点规则报告已处理／剩余数量、真实验证与未验证项、下一停点；修复代码复用 agent-skills 的诊断、TDD、增量实现与代码复审 | 全程 | 内部 | `S/hosted-ticket-workflow/SKILL.md:56-60` | hosted-ticket-workflow；audit-handoff | 无 |

---

## 五、Local 事项迁移、归档、恢复与交接（`local-ticket-portability`）

入口：`/spec-guard:local-ticket-portability` 命令（`C/local-ticket-portability.md`）、skill `S/local-ticket-portability/SKILL.md`、统一 CLI `H/local_ticket_portability.py`，参考 `R/local-ticket-portability.md`。默认关闭，所有写入都显式授权；归档与预览不设隐含默认输出路径。

### 5.1 只读盘点与核验

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 5.1.1 | inventory | 只读盘点：必须在 Git worktree 根，身份 initialized，状态 worktree owned；列出每个事件文件与媒体文件（sha256、大小），拒绝缺口；媒体名限 `<64hex>.(png|jpg|gif|webp)`；foreign／unknown 是「停」而不是「空账本」 | `local_ticket_portability.py inventory --project <repo>` | 开（只读） | `H/local_ticket_inventory.py:21,38,117-198`；`H/local_ticket_portability.py:15-` | local-ticket-portability；audit-small-cleanups（拆出独立模块） | 无 |
| 5.1.2 | verify | 校验归档：manifest、文件哈希、安全文件名、状态分支 bundle、project.json、映射日志；v1 与 v2 格式都有效 | `verify --archive <dir>` | 开（只读） | `H/local_ticket_archive.py:69-216` | local-ticket-portability | 无 |
| 5.1.3 | verify --prove | 在临时 Git 与临时 Epiq 状态里重放：对比全部源事件与 Epiq 物化视图，并做一次一次性写入证明；不证明异机持久性 | `verify --archive … --prove` | 开（只读，临时目录） | `H/local_ticket_restore.py:20,74-157` | local-ticket-portability | 无 |

### 5.2 离线归档

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 5.2.1 | archive | 生成单目录离线归档：`manifest.json`、仅含状态分支的 Git bundle、`.epiq/project.json`、原样的事件与媒体字节（含 `~pending`）、私有映射日志快照；要求历史只含 `.epiq/` 路径；复制前后双重比对源不变（`source-changed`）；先在临时目录构建并 verify，最后以 manifest 最后移动的顺序落盘 | `archive --project <repo> --output <new-private-dir>` | 关；用户必须给新目录。不含项目源码与其他分支 | `H/local_ticket_archive.py:219-326` | local-ticket-portability；ledger-local-only | 归档是本机文件备份，不防本机丢失；为 `auto-sync` 默认不提交状态事件而设的补偿，见 Q9 |
| 5.2.2 | 输出位置约束 | 归档目录须为全新目录、权限 0700，且不得位于源仓库任何 linked worktree 或状态 worktree 内；预览输出同理 | archive／handoff-preview | 内部 | `H/local_ticket_archive.py:49-56,225-243`；`H/local_ticket_preview.py:155-163` | local-ticket-portability | 无 |
| 5.2.3 | 归档格式 v1／v2 | 绑定过日志的项目生成 v2，并多写 `binding-provenance.json`（含绑定链）；旧 v1 仍有效 | archive／verify | 内部 | `H/local_ticket_archive.py:250-300` | local-ticket-portability | 版本分支为兼容而存在 |

### 5.3 恢复

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 5.3.1 | restore | 只恢复到用户指定的空 Git 仓库与空 Epiq 全局目录：先隔离证明归档，再在新仓库默认分支提交 `.epiq/project.json`、创建 `__epiq_state__` 与 worktree；不 push；中断时保留部分数据供检查，不得重跑到非空目标 | `restore --archive … --project <empty-repo> --epiq-global-dir <empty-dir> --confirm` | 关；需 `--confirm` 且展示路径 | `H/local_ticket_restore.py:160-238` | local-ticket-portability | 无 |
| 5.3.2 | 目标空仓库检查 | 目标只能含 `.git`，无历史、无引用，非共享 common dir 的 linked worktree，且与归档路径不重叠；需预先配置 Git author | restore | 内部 | `H/local_ticket_restore.py:160-186,207-216` | local-ticket-portability | 无 |
| 5.3.3 | 恢复锁 | 目标 `.git/spec-guard-local-restore.lock` 用 flock，防并发恢复 | restore | 内部 | `H/local_ticket_restore.py:198-202`；`H/local_ticket_lock.py:16-57` | local-ticket-portability | 无 |
| 5.3.4 | 不导入映射日志 | 映射日志随归档导出，但不自动导入新项目的用户级分区；结果带 `localIdentitySetupRequired: true`，恢复后首次写入前需用 Epiq 流程设置本地身份 | restore | 内部 | `H/local_ticket_restore.py:76-80` | local-ticket-portability | 无 |

### 5.4 日志（映射 journal）与绑定链

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 5.4.1 | 私有交接日志 | 每个交接目标一条 entry（键为 projectId／issueId／目标的 sha256）；状态集 planned／partial／verified／conflict；JSON 原子替换并 fsync；分区由 Git common dir 绝对路径的 sha256 决定，位于 `~/.spec-guard/local-ticket-portability/` | handoff 时自动 | 内部；日志删了会失去防重 | `H/local_ticket_journal.py:20-52,284-350` | local-ticket-portability；runtime-state-layout | 分区键依赖路径哈希，项目一搬家日志就「丢」，由此才需要 5.4.3 的绑定机制，是自己造出来的复杂度，见 Q5 |
| 5.4.2 | journal-candidates | 只读发现同 projectId 的其他路径分区（含无 mapping.json 的旧分区，计数未知），任一不安全或损坏的分区即停止发现；一个候选不证明属于当前检出 | `journal-candidates --project <repo>` | 开（只读） | `H/local_ticket_journal.py:53-117` | local-ticket-portability | 无 |
| 5.4.3 | journal-bind-preview／journal-bind | 项目路径移动后，凭旧 Git common-dir 路径（必须已不存在）或已验证归档，逐项核对旧映射键与当前 Local 事项和目的地、旧源摘要与当前历史或其可证前缀；输出 0600 预览；`journal-bind --confirm` 重检全部后只在新分区安装一个私有指针，不改旧日志、不调平台 API、不运行 `git worktree repair` | `journal-bind-preview …`；`journal-bind --project … --preview … --confirm` | 关；需针对该候选的明确确认 | `H/local_ticket_bind.py:115-257`；`H/local_ticket_journal.py:120-210` | local-ticket-portability | 极窄场景（项目目录搬家且曾交接过）的专用机制，257 行加一整套指针链加 100 步链长上限；`R/local-ticket-portability.md` 自己承认「相同复制仓库无法区分」。过度设计嫌疑，见 Q5 |
| 5.4.4 | 绑定链解析与别名 | 沿 `binding.json` 指针链解析到唯一规范日志；所有可用候选须都在链内，否则 `manual-reconciliation-required`；链上多余的 unrelated 候选阻断发布；二次搬家需再次预览 | handoff-publish／archive | 内部 | `H/local_ticket_journal.py:161-282` | local-ticket-portability | 同上 |
| 5.4.5 | 崩溃释放锁 | 锁文件先写 magic 再 `link` 发布初始化完整的私有 inode，随后 `flock`；进程崩溃由 OS 释放；遗留或损坏的锁拒绝并要求人工审查；检查 inode 未被替换 | 日志写入、发布、恢复 | 内部 | `H/local_ticket_lock.py:13-57`；`H/local_ticket_journal.py:321-362` | local-ticket-portability | 无 |

### 5.5 逐项交接到 GitHub／GitLab

| # | 功能点 | 行为 | 触发／入口 | 默认／可关 | 关键位置 | 来自模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 5.5.1 | 源快照 | 对一个 issue 用完整 ID 两次读取（原始事件文件与 Epiq MCP 视图）夹住稳定盘点；视图与原始事件不一致、无创建历史、附件与媒体不符、读取期间账本变化均失败；格式 v2 用稳定源摘要，`--legacy-format` 用 v1 摘要 | handoff-preview／publish 内部 | 内部 | `H/local_ticket_handoff.py:19-151` | local-ticket-portability | 无 |
| 5.5.2 | 目标事实核验 | 要求精确目标、已知可见性、可写权限（GitHub 须 push／maintain／admin；GitLab 任一访问级别 ≥30）、Issue 已启用、GitLab URL scheme 必须与 host 与路径一致；用户给的可见性与实际不符失败 | handoff-preview | 内部 | `H/local_ticket_preview.py:32-86` | local-ticket-portability | 无 |
| 5.5.3 | handoff-preview | 在 0600 私有文件里写完整预览：全部 Local 历史、评论、源摘要、附件状态、代码引用限制、目标与可见性；正文逐事件渲染为可读 Markdown，带 `spec-guard-local-ticket:v1` 与每事件 `spec-guard-local-event:v1` 标记；limitations 里声明代码引用未验证、写 API 范围不可证、GitLab HTTP 无传输保密、附件字节未转移 | `handoff-preview --project … --issue-id … --platform … --host … --target … --visibility … --output …` | 关；只读，写一个本机预览文件 | `H/local_ticket_preview.py:98-186` | local-ticket-portability | 公开目标会暴露 Local 完整历史（预览已警示）；把 Epiq 原始 JSON 事件整段贴进公开 Issue，可读性与隐私都存疑 |
| 5.5.4 | handoff-publish | 重核源摘要、预览正文与目标事实，在发布锁内：创建 Issue（若无）、逐条按事件标记发布历史评论、同步 closed／open 状态，并读回每个受管标记；GitHub PR 与 GitLab 系统备注排除在匹配之外 | `handoff-publish --project … --preview … --confirm` | 关；需针对精确目标与内容授权 | `H/local_ticket_publish.py:70-281`；`H/local_ticket_github.py:13-78`；`H/local_ticket_gitlab.py:13-100` | local-ticket-portability | 这是除 HTW 外第二条「写 GitHub／GitLab Issue」路径，实现与 HTW 完全分离（各自的 marker、意图日志、适配器），见 Q1、Q8 |
| 5.5.5 | 结果状态机 | verified／partial／conflict／publication-uncertain／provider-rejected／preview-incompatible；partial、conflict、uncertain 时 Local 仍是权威；不因即时搜索为空就重试创建或评论 | publish | 内部 | `H/local_ticket_publish.py:70-281` | local-ticket-portability | 无 |
| 5.5.6 | 防重复与标记歧义 | 目标已有两个匹配 Issue、标记出现在受管区之外、评论被编辑或重复、远端状态改变，一律 conflict 并保留尝试记录，不可静默重置重试保护 | publish | 内部 | `H/local_ticket_publish.py:95-215` | local-ticket-portability | 无 |
| 5.5.7 | 确定拒绝的恢复 | 创建前被定性拒绝（4xx）且远端无写入，可在内容修正后用新预览重试；若拒绝后出现匹配标记则 conflict；Issue 或评论一旦存在，源历史变化即 conflict | publish | 内部 | `H/local_ticket_publish.py:130-160`；`H/local_ticket_provider.py:14,17-50` | local-ticket-portability | 无 |
| 5.5.8 | 版本 1 兼容 | 旧 v1 交接用 `--legacy-format` 续写；默认 v2 遇到已有 v1 交接返回 `preview-incompatible`；v1 若定性拒绝可用 v2 重启 | handoff-preview／publish | 内部 | `H/local_ticket_publish.py:50-67,108-128` | local-ticket-portability | 两套摘要格式并行，仅服务早期交接 |
| 5.5.9 | 附件处理 | 附件字节不转移、不验证；有附件时结果保持 partial，原 Local 媒体留在归档里 | handoff | 内部 | `H/local_ticket_preview.py:164-170`；`H/local_ticket_handoff.py:107-116` | local-ticket-portability | 迁移不完整，附件永远 partial，这块能力实际上是半成品 |
| 5.5.10 | 代码引用限制 | 预览记录引用的提交 SHA，格式 v1 记源提交是否可达，v2 声明在预览时已检查可达；目标仓库上提交是否存在均不核实 | handoff-preview | 内部 | `H/local_ticket_handoff.py:64-76`；`H/local_ticket_preview.py:127-139` | local-ticket-portability | 无 |
| 5.5.11 | 交接边界 | 交接后不自动把日常工作切到 GitHub／GitLab，不关闭 Local 事项，不改 Proposal Issue、能力图或 `.agent/state.json`；`verified` 只说明预览快照在目标上读回成功 | 全程 | 内部 | `S/local-ticket-portability/SKILL.md:44-49`；`R/local-ticket-portability.md:150-160` | local-ticket-portability | 无 |
| 5.5.12 | 平台传输封装 | 本区内第三套 gh／glab JSON 封装：定性拒绝集合、状态码解析、分页同上（100／页、50 页上限） | 所有交接 API 调用 | 内部 | `H/local_ticket_provider.py:12-61` | local-ticket-portability | 与 `hosted_ticket_provider.py` 的 `run_json`／`pages`／`DEFINITE_REJECTIONS` 常量与逻辑几乎相同，是重复代码，见 Q8 |

---

## 六、文档与参考（非功能点，供对照）

- `docs/design.md:44,163-170,182-195`：部件表末行概述 `local_ledger_*`、`local_ticket_*`、`hosted_ticket*`；文件布局表登记 `.epiq/project.json`、`.agent/tracker.json` 入库，`~/.spec-guard/local-ticket-ledger/runtime`、`local-ticket-portability`、`hosted-ticket-intents` 为本机状态；「已退役的边界」宣布可写的远端 tracker 桥不属于本产品。
- `README.md:44,156-163`：本地事项账本需 macOS 与 Node.js；联网仅在显式调用时；启用账本用 `npm ci`；钩子只判 `.epiq/project.json` 在不在。
- 锁文件目录 `plugins/spec-guard/locks/local-ticket-ledger/` 只含 `package.json`（仅声明 `{"epiq": "1.11.0"}`，包名 `spec-guard-local-ticket-ledger-runtime`）和 `package-lock.json`（269 个 resolved 条目）。

---

## 七、需求疑点汇总（按重要性）

- **Q1 与主线声明冲突（越界／自相矛盾）**：能力图「目标」段写明 GitHub／GitLab「只作为只读 Proposal Issue 来源，不创建或修改 Issue、PR、分支或任务」，`docs/design.md` 把可写远端 tracker 桥列为「已退役、不属于本产品」。但 HTW（4.1、4.2）与 LTP 的 handoff-publish（5.5）都能创建、评论、关闭远端 Issue。这是同一类能力换了名字回来，需要用户决定：要么改写总目标承认这块是产品范围，要么拆出独立插件。
- **Q2 整个事项账本是否属于「多模块 Spec 约定」插件**：账本包装一个第三方包（Epiq，约 119MB、269 依赖）、用户级 MCP、`~/.claude/settings.json` 的 ask 规则、`chmod` 数据目录，以及迁移、托管三大块，约占 D 区 5900 行；它与 Spec／Plan／能力图主线没有数据依赖（事项与模块无绑定）。能力图自己把它定位为「需显式启用的本机能力」，更像独立插件。
- **Q3 事项与 Spec／Plan 两套记录并行**：2.8、2.11、2.12 让事项里写「问题、范围、可验证结果」「决定评论」「验证记录」，而 Spec／Plan／todo 与 `change-source-record` 也在记录范围、决定与验收，且没有任何机制把事项与模块 id 关联。对一个以「Spec 是需求来源」为核心的插件，容易出现两处记录同一需求、各说各话。
- **Q4 与姐妹插件职责重叠**：2.20（open-commitments、record-on-receipt、receipt-hint-on-message）与 1.5.1 把本地账本当作「有人在等什么」的台账，并让 phase-guard 在收到会话消息时提醒记账。这与 agent-relay（信箱）、decision-inbox（待决事项与等待记录）、module-crew（收件记账）处理的是同一问题的不同载体；另 2.17 的通知依赖 agent-relay probe。归属应由用户核对。
- **Q5 日志绑定链是自造复杂度**：5.4.1 把交接日志分区键定为 Git common dir 绝对路径的 sha256，项目一搬家就找不到旧日志，于是 5.4.2–5.4.4 增加候选发现、证据预览、指针链（257＋约 240 行，链长上限 100）。参考文档自己承认「相同复制仓库无法仅凭旧日志事实区分」。如果日志键改用稳定的项目身份，这整套可能不需要。
- **Q6 启用后没有退出路径**：1.4.7 明确没有卸载、移除 MCP、删账本的命令，`teardown-convention` 也不管。init 之后 `.epiq/project.json` 入库、用户级 MCP 与 ask 规则写入、运行时留在 `~/.spec-guard`，用户想「关掉」只能手工清理，与「默认不生效、可逆」的插件不变量不对称。
- **Q7 默认后端的净价值**：tracker-default（第三章）自己声明「不是权威、不决定写入、不改变既有绑定、不是激活信号」，只在预览里预填 host／repo；而每次写入仍逐次授权并展示完整目标。它省下的只是输入几个参数，却带来一个入库文件、三种目标形状、一套敌意文件读取防护、一个独立命令，且被 project-config 与 proposal-closeout 引用，扩大了依赖面。
- **Q8 三套 gh／glab 封装与重复常量**：`hosted_ticket_provider.py`、`local_ticket_provider.py`＋`local_ticket_github.py`／`local_ticket_gitlab.py`、以及 Proposal 的只读 tracker 适配器各自封装 gh／glab，`PAGE_SIZE=100`、`MAX_PAGES=50`、`DEFINITE_REJECTIONS` 在前两处逐字重复（`H/hosted_ticket_provider.py:50-52` 与 `H/local_ticket_provider.py:12-14`），marker 与意图日志也各一套。属于可合并的重复，且 `hosted_ticket_action(s).py` 单复数命名已被自己警示。
- **Q9 `auto-sync` 默认带来的备份补偿链**：因为 Epiq 在 `auto-sync` 为 false 时事件只存为未提交文件，才长出 pendingEvents 计数（1.3.3）、归档提醒、离线归档（5.2）、`verify --prove`（5.1.3）、restore（5.3）。这些都在为「本地账本其实没有历史、没有备份」补洞，补洞规模大于账本本身的受理功能。
- **Q10 规则文本即实现，不可校验**：第二章 20 项里绝大多数（查重、泳道、决定评论、PR 对账、通知）只是写给 agent 的自然语言规则，没有对应代码或检查器；查重也被自己承认非原子。要求越多、代码越少，越难证明被遵守（对比 hosted 路径有 digest／marker／意图日志等硬校验）。
- **Q11 `--root-cause-reviewed`、`--coverage-complete`、`--confirm` 是 agent 自填的布尔**：4.1.6、4.1.9、4.2.5 的核心闸门由调用者自己传参，代码无法验证它真的做了根因复核或验收，真正的闸门仍是对话里的授权；闸门形式感强于实际约束力。
- **Q12 兼容层随早期用户老化**：1.1.6（空目录接管）、1.1.7（unlocked 替换）、1.4.6（旧宿主迁移）、5.2.3（归档 v1）、5.5.8（交接 v1／`--legacy-format`）都只服务早期安装，可考虑设日落。
- **Q13 小项**：`host_config_removal.py` 现仅含 `add_claude_server`，文件名与职责不符；Codex 白名单使 `epiq_sync` 对 Codex 不可用，两宿主能力不对等；用户级 MCP 与仓库级账本不匹配导致 `repoRoot` 必传的补丁规则（2.4）。用户提到的 `waiting-on-*` 标签在 D 区文件中未发现，只在 `references/workflow-checkpoints.md`、`phase-guard.sh`、模板与几份 spec 中，应归 phase／检查点区清单。
