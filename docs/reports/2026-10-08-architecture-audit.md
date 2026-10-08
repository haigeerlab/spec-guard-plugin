# 多维度架构审查（2026-10-08）

按 [审查计划](2026-10-08-architecture-audit-plan.md) 执行。只读：审查本身未修改仓库文件、未提交、未写远端或真实账本。

## 范围与基线

- 基线：`origin/main` `7ea9130`（v0.52.0 发布并完成证据之后）。
- 范围：`plugins/spec-guard/`、`scripts/`、`evals/`、`.github/workflows/`，以及文档与代码的一致性。
- 不在范围：agent-relay 仓库本身；远端与真实账本写入；2026-10-05 审计已收口的 12 项（未发现回归）。

## 方法

- 六个维度（D1 架构边界与耦合、D2 不变量、D3 双宿主一致性、D4 测试与判据有效性、D5 安全与本机数据、D6 冗余与过度设计）
  各派一次 Codex 只读任务：delegate 插件 `codex-exec.sh`，`gpt-5.6-sol`，推理档 high（每份输出末尾回报的实际模型一致）。
  `/delegate:doctor` 事先报告通过。
- 第一次派出的五个任务全部在启动前失败（退出 127「找不到 codex」）：宿主重启后本会话 `PATH` 首位是 node v12，且不含
  `~/Library/pnpm/bin`。调用时前置 node v24 与该目录后重派，六个维度均正常完成，未产生无效发现。
- 主会话逐条核验：能重跑的重跑（复现命令只用临时目录、内存桩和伪造凭据），其余读代码确认；做不到的标「采信」。
- 严重程度口径：**high** 破坏不变量、可能泄露或误删数据、把环境故障报成事实；**medium** 宿主不一致、判据可绕过、
  测试守不住；**low** 冗余、文档漂移、可读性。Codex 的原始定级按此口径重评，调整处注明。

## 结论

共 20 条发现：high 1、medium 10、low 9，均已核验（含 5 条采信）。没有发现破坏数据或绕过确认门禁的问题；
最需要优先处理的是**凭据会被原样打印或放进进程参数**（F1、F2），其次是一组**守门测试/检查器可被绕过**的问题
（F7–F10），它们本身不造成错误行为，但会让下一次回归在全绿中合入。

## 问题清单

核验列：**重跑** = 主会话重新执行复现；**读码** = 主会话读代码确认；**采信** = 未独立重跑，依据 Codex 的复现记录。

| # | 原 ID | 级别 | 问题 | 位置 | 核验 |
|---|---|---|---|---|---|
| F1 | D5-1 | high | 本地账本 `preflight --format json` 原样输出 Git origin；含 `user:token@` 的 HTTPS remote 会把凭据打进终端与 agent 上下文 | `hooks/local_ledger_runtime.py:272-287,657-658,692-693` | 重跑（伪造凭据，内存桩） |
| F2 | D5-2 | medium（原 high） | Proposal 远端快照把 `remote get-url` 得到的完整 URL 放进 `git ls-remote` / `git fetch` 的 argv，本机其他进程可见内嵌凭据 | `hooks/proposal_publication.py:97-103,149-165,183-185` | 重跑 |
| F3 | D5-3 | medium | hosted-ticket 命令把远端 Issue 标题与正文不限长、不标注「非指令」地放进 agent 读取的 JSON（hook 注入有净化，命令输出没有） | `hooks/hosted_ticket_read.py:29-49,72` 等 | 采信 |
| F4 | D2-1 | medium（原 high） | 能力图不可读（权限拒绝）时 `verify-artifacts` 报「能力图无效」并失败，`phase-guard` 报 `MAP_ONLY`；两者都把读取故障说成了能力图本身的状态。Codex 原记录写 phase 报 `UNKNOWN`，重跑实为 `MAP_ONLY` | `hooks/capability-map.py:23`、`hooks/verify-artifacts.sh:38,54`、`phase-guard.sh` | 重跑（更正） |
| F5 | D3-1 | medium | Codex 侧 `spec-guard-ops` 的插件根解析对结构异常的合法 JSON（如 `[]`）抛 traceback；Claude 命令的规范引导段已能降级为可诊断的定位失败（0.50.1），skill 未同步 | `skills/spec-guard-ops/SKILL.md:16-28` | 读码 |
| F6 | D6-1 | medium | 已迁到 agent-relay 的四个协作实现模块（`collaboration-messaging`、`collaboration-safe-defaults`、`authorized-session-delegation`、`host-native-session-routing`）仍登记在当前能力图，与 AGENTS.md「退役 Spec 不加入当前能力图」和 `retired-module-separation` 的做法相冲突 | `spec/CAPABILITY-MAP.md:23,24,51,52` | 读码 |
| F7 | D3-2 | medium | 命令插件根回归只要求「至少 15 个」使用 `$ROOT` 的命令，实际 16 个，任一命令丢掉整段引导仍全绿 | `evals/test-codex-command-roots.sh:84` | 重跑（计数） |
| F8 | D3-3 | medium | 双宿主 parity 检查器只核对 hook 文件名出现，不核对参数；删掉 skill 里的 `--prove` 仍通过 | `scripts/check-command-parity.py:10,55` | 采信 |
| F9 | D4-1 | medium | 严格能力图解析的表头分隔行规则没有反向断言：关掉该规则后 `| x | y | z |` 被当作分隔行接受，verify 与 module-insert 套件仍全绿 | `hooks/capability_map.py:104-106` | 重跑（临时副本变异） |
| F10 | D4-2 | medium | `evals/dispatch-cost/grade.sh` 用 `… \| tail -3` 跑隐藏测试且未开 pipefail，隐藏测试失败时整体仍退出 0 | `evals/dispatch-cost/grade.sh:4,11,13` | 读码 |
| F11 | D2-2 | low（原 high） | 已激活项目在 IDLE/MAP_ONLY 时若 `python3` 能找到但执行失败，`emit` 的失败被后续 `exit 0` 吞掉，宿主收到零输出；`python3` 是声明的必需依赖，场景罕见 | `hooks/phase-guard.sh:51,85-106` | 重跑 |
| F12 | D2-3 | low（原 high） | `phase-guard.sh` 实际依赖 `grep`，与不变量「只依赖 bash、git、python3」字面不符；无 `grep` 时已激活项目静默退出 | `hooks/phase-guard.sh:33,36,40`、`CLAUDE.md:51` | 重跑 |
| F13 | D2-4 | low（原 medium） | 「`spec-digest.py` 是唯一指纹算法」只靠约定与自检，没有检查器阻止新增复制实现（当前无复制实现） | `scripts/validate.sh:76-78` | 采信（源码推导） |
| F14 | D6-2 | low（原 medium） | 能力图 `context-hint-no-paste` 一行仍写「the user runs /spec-guard:handoff」，与同一能力图后面的退役说明矛盾；退役静态检查未覆盖能力图 | `spec/CAPABILITY-MAP.md:67` | 读码 |
| F15 | D1-1 | low | Local ticket 顶层 CLI 同时承载共享异常与库存函数，底层模块反向依赖它，形成导入环（Codex 统计 12 个） | `hooks/local_ticket_portability.py:21,251-306` 等 | 采信（环数未重算） |
| F16 | D1-2 | low | module id 正则与「当前模块」选择各有两份实现 | `hooks/capability_map.py:7`、`documentation_impact.py:11`、`module_stage.py:128-144`、`module-insert.py:53-59` | 读码 |
| F17 | D1-3 | low | `remove_codex_table`、`remove_claude_server` 协作迁出后只剩测试调用（同文件的 `add_claude_server` 仍被账本使用） | `hooks/host_config_removal.py:25,77` | 读码 |
| F18 | D3-4 | low | `docs/workflow.md` 的命令对照表缺 `cost-report` 与 `local-ticket-portability` | `docs/workflow.md:220-235` | 读码 |
| F19 | D4-3 | low | CI 的 ShellCheck 用非递归 `evals/*.sh`，漏掉 `evals/dispatch-cost/` 下三个脚本 | `.github/workflows/ci.yml:41-42` | 重跑（glob 展开） |
| F20 | D6-3 | low | `/spec-guard:collaboration` 约定只保留一到两个版本，已随 7 个发布标签交付；本机另有 2 个项目仍引用它，移除前要先迁移这些引用 | `commands/collaboration.md:6`、`spec/collaboration-dependency.md` | 采信（跨项目只计数，不记项目名） |

## 建议修复顺序（按模块归组，每组一个 add-module）

1. **凭据不外露**（F1、F2）：输出前去掉 URL 的 userinfo；git 命令改用 remote 名或从配置读取，不把 URL 放进 argv。
   收口：带伪造凭据的 remote 下，preflight 输出与 argv 均不含凭据，正反回归。
2. **不可信远端文本**（F3）：hosted-ticket 输出对标题/正文限长并标注为数据，延续 phase-context 净化决策的做法。
3. **读取故障不报成状态**（F4、F11）：能力图读取失败在 phase 与 verify 两侧都报可诊断的读取失败；`emit` 失败时仍输出
   最小合法 JSON 或可诊断错误。收口：不可读能力图、损坏解释器两组夹具。
4. **守门测试补强**（F7、F8、F9、F10、F13、F19）：命令引导回归改为精确集合；parity 检查核对关键参数；分隔行反向断言；
   grade.sh 传递隐藏测试失败；指纹唯一实现检查器；CI ShellCheck 覆盖子目录。收口：每项附一次手工变异变红的记录。
5. **Codex 根解析降级**（F5）：skill 复用与命令一致的解析与诊断。
6. **能力图与退役一致**（F6、F14）：按 `retired-module-separation` 把四个协作实现模块移出当前能力图并归档；修正第 67 行；
   退役静态检查覆盖能力图。
7. **小清理**（F12、F15、F16、F17、F18）：不变量文字改为写明 POSIX 工具或去掉 `grep`；拆出共享异常模块破环；
   module id 与当前模块选择单源；删除孤儿函数；补对照表。
8. **待决定**（F20）：先迁移本机仍引用 `/spec-guard:collaboration` 的项目，再决定移除时间。

## 误报与更正

- 无整条剔除的误报。
- 更正：D2-1 中 phase 的结果实为 `MAP_ONLY` 而非 `UNKNOWN`；D2-1/D2-2/D2-3 从 high 下调（环境罕见或输出仍带错误原文），
  D5-2 从 high 下调（凭据本已在 git 配置中，暴露面是本机进程参数），D2-4、D6-2 从 medium 下调。

## 未验证边界

- F3、F8、F13、F15、F20 未在主会话独立重跑，依据 Codex 记录的复现步骤（均为只读或临时目录）。
- 真实 Epiq、真实宿主会话读取模式、Windows 与 Linux 上的 `/bin/bash` 行为未运行。
- 审查外观察（不计入本报告问题）：delegate 插件的 `/delegate:doctor` 在派活实际失败的 `PATH` 下仍报告通过，属于
  delegate 插件仓库。
