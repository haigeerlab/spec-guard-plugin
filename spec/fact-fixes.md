# Spec: fact-fixes

<!-- spec-guard: review approved 074199b6641c -->

## Objective

2026-10-22 多维度审查与功能清单核出了几处「文档说的和实现做的不一致」，以及一处违背「无关项目静默退出」轻量精神的启动顺序。
本模块把它们一次修正，不改任何功能的行为（第 7 项除外：它只改未启用项目里的启动顺序，输出不变）：

1. 能力图「目标」段说 GitHub/GitLab「只作为只读 Proposal Issue 来源，不创建或修改 Issue」，还说插件有「需显式启用的本机协作邮箱」。
   实际上 Proposal 收尾、托管事项、本地事项交接都会在用户授权后写远端 Issue（决定 D12：改为如实描述）；协作邮箱已拆成独立插件
   agent-relay，本插件只经 `agent_relay_probe.py` 只读检测。
2. 能力图仍把 `dependency-check` 列为现行模块，但它的代码已在 `install-by-scope`（提交 `a42a7f1b`）删除（功能清单 A-138）。
3. 能力图 `module-insert` 一行写「with a spec skeleton」，实现明确不建骨架（`hooks/module-insert.py:6-8,269-273`，`spec/module-insert.md:40`）。
4. README 说「agent-skills 默认一个项目只有一份 Spec 和一份 plan」，已过时：上游 `/spec` 的 Phase 0 已有能力图与每模块
   `SPEC-<模块>.md`，真缺口是 `/plan` 只写一份 `tasks/plan.md`／`todo.md`、没有跨轮的阶段续接（审查 F13，`docs/upstream-analysis.md`）。
5. `interface.json` 的 `reviewKinds.field` 写「contract v2.3」，session-protocol 现已到 v2.5（决定记录「核实依据」）。
6. README 说 `cost-report`「只统计 token 与轮次」，实现还读工具结果文本、编辑的文件路径、用户提问时间与子代理派生关系（审查 F12，
   `hooks/module_cost_report.py:149-174,327-337`）。
7. `phase-guard.sh` 在激活判定之前就启动 `python3 session_context.py --resolve-root`（`hooks/phase-guard.sh:27-31` 早于 `:63`），
   于是装了 spec-guard 的机器上，每个**未启用**的项目每轮对话都要起一次 python3（功能清单 A-08）。

登记：2026-10-22 修复批次 12 个模块之一，经用户批准事项 C24 开模块会话；能力图依赖 `phase-and-verification`。
依据：`docs/reports/2026-10-22-feature-inventory/decisions.md`（D12 等）与 `docs/reports/2026-10-22-multidimension-audit.md`（F12、F13）。

## Assumptions

以下是写 Spec 时定下的前提，请在批准时一并确认：

1. **只改说法，不改功能。** 第 1～6 项只改文字；第 7 项只改 `phase-guard.sh` 里启动 python3 之前的判定顺序，
   已启用项目与有指向文件的项目的输出逐字节不变。
2. **`dependency-check` 按已有的退役做法处理（推荐，见「待定」第 1 条）。** 照 `retired-module-separation` 的先例：从模块表与
   Build order 同时移除，原 Spec、Plan、todo 用 `git mv` 原样归档到 `docs/retirements/dependency-check/`，加一份退役说明；
   依赖它的 `install-by-scope` 去掉这条依赖。`spec/install-by-scope.md` 第 5 条当时写「能力图里 `dependency-check` 那一行作为
   历史保留，不改」——本模块取代这一句，按 `config-per-key` 的做法只在那句后面加一句指向本 Spec 的说明，正文不重写。
3. **能力图只改目标段、两行职责／依赖、Build order 与变更记录。** 其他模块行不动；`capability-history` 一行里的 audit／correct
   归 `history-slim`，`proposal-tracker-read` 一行的「只读」本来就对（它只读），都不改。
4. **cost-report 的说明按当前实现写。** 同批的 `cost-slim-link-follow` 会去掉返工信号识别，届时读取范围可能变窄；README
   那句由它跟着改。本模块在 todo 末尾的交接说明里写明这一点，不预先替它写。
5. **interface.json 只改那一处版本说法，不升接口版本。** 那是描述文字，不是字段或取值；`reviewKinds` 按 D9 冻结，
   取值本身不动。描述里收件枢纽复制块那半句归 `sibling-rules-out`（D9），本模块不碰。
6. **第 7 项的预检在 bash 里完成，不引入新依赖。** 只用 bash 内建与 git（不变量：`phase-guard.sh` 只能依赖 bash、git、python3）。
   拿不准时（输入读不全、`cwd` 含转义字符等）退回现在的做法，照旧启动 python3 解析——宁可多起一次 python3，也不把已启用的
   worktree 会话判成未启用。
7. **`references/local-ticket-ledger-runtime.md` 里的「协作邮箱」不改。** 那三处说的是「装了邮箱插件时」的通用情形，不声称
   spec-guard 自带邮箱，与事实不冲突。

## Contract

### C1 能力图目标段（`spec/CAPABILITY-MAP.md` 第 10～12 行那一段）

整段替换为下面这段（保留前后两段不动）：

> 插件的能力分五类：Proposal 生命周期（共享事实只来自远端默认分支快照；GitHub/GitLab 上的 Proposal Issue 只读核验，唯一的远端
> 写入是晋级证明通过后、经用户授权把它标为 promoted 并关闭）；防止多模块产物互相覆盖的本地约定，以及只报告事实的阶段注入与
> 产物校验；在检查点把新模块校验后插进能力图的快速插入；可核验的能力历史与显式的文档治理；以及需显式启用的本地事项账本，
> 和按明确选定的目标处理 GitHub/GitLab 普通 Issue（托管事项、本地事项逐项交接），每次远端写入都先预览、经用户确认再读回。
> 会话协作邮箱已拆为独立插件 agent-relay，本插件只做只读检测。

（原文写「分四类」却列了五组，一并改正。）

### C2 退役 `dependency-check`

- 模块表删去 `dependency-check` 一行；Build order 删去 `dependency-check →`；`install-by-scope` 的 Depends on 由
  `scope-authorization, dependency-check` 改为 `scope-authorization`。
- `git mv spec/dependency-check.md docs/retirements/dependency-check/spec.md`，`tasks/dependency-check/plan.md`、`todo.md`
  同样移到该目录，内容逐字节不变。
- 新增 `docs/retirements/dependency-check.md`：退役原因（`install-by-scope` 按决定 62 删除了 `dependency_check.py` 与
  verify-artifacts 的对应段落，提交 `a42a7f1b`）、归档路径、「只作历史证据」。
- `spec/install-by-scope.md` 第 5 条末尾加一句：「（2026-10-22 起由 `spec/fact-fixes.md` 取代：该行已移出能力图，归档见
  `docs/retirements/dependency-check.md`。）」
- 能力图变更记录加一条（日期、原因、来源）。CHANGELOG、`docs/releases/` 里的历史提及不改。

### C3 `module-insert` 一行

职责里的 `with a spec skeleton` 删去（行改为 `…validate and insert one new module into the capability map, after previewing and
explicit confirmation.`），其余不变。

### C4 README 上游描述（中英两份同步）

- 中文第 5～7 行改为：「agent-skills 的 `/spec` 已能把需求拆成能力图和每个模块的 Spec，但 `/plan` 每次都写同一份
  `tasks/plan.md`／`todo.md`，模块之间会互相覆盖，下一轮也不知道做到了哪。spec-guard 让每个模块各有自己的 Spec、Plan 和
  todo，并在每轮对话开头告诉 agent 现在该做哪个模块、做到了哪一步。」
- 英文同义改写，`scripts/check-readme-sync.py` 照旧通过。

### C5 `interface.json`

`reviewKinds.field` 里的 `(contract v2.3)` 改为 `(values defined in contract v2.3 and unchanged through v2.5)`。接口版本、
其他字段不变。

### C6 README 的 cost-report 读取说明（中英两份同步）

改为如实描述：离线读本机 Claude Code 与 Codex 的会话记录，用到其中的 token 计数、用户提问时间、工具调用结果（判断被拒与交回
时间）、编辑过的文件路径与子代理派生关系；这些只在本次运行的内存里用来归到 task，输出只有计数，不打印会话内容，结果只在终端。
「插件没有遥测」那句保留。

### C7 未启用项目不启动 python3（`hooks/phase-guard.sh`）

- 现在的顺序：确定 `ROOT` → **python3 读 hook 输入、按 `cwd` 修正根目录** → 判断激活信号 → 未启用则退出。
- 改后：确定 `ROOT` → 在 bash 里读 hook 输入的前 64KB（最多等 1 秒）→ 在 `ROOT` 与输入 `cwd` 所在 git 仓库根两处查激活信号
  与指向文件（判据与现在的 `has_block`／`has_state`／指向文件相同）→ **两处都没有、且拿得准时直接 `exit 0`，不启动任何 python3**
  → 否则把已读到的前缀与其余输入按原字节交给 `session_context.py --resolve-root`（其余部分由一个同样最多等 1 秒的拷贝进程转过去；
  1 秒、1MB 的上限仍由 `session_context` 判），后续一切照旧。
- 「拿不准」包括：输入超过 64KB（没读完）、`cwd` 不是不含转义的普通 JSON 字符串、`"cwd"` 出现不止一次。这些情况保持现在的行为；
  `cwd` 不是目录或不在 git 仓库里时与 `session_context` 一样只看 `ROOT`。
- 已启用项目、有指向文件的项目、桌面版 worktree 会话（宿主给主检出、`cwd` 在 linked worktree）的输出与现在逐字节相同。

## Acceptance criteria

- **AC1** 能力图目标段与 C1 的文字一致；`capability_map.parse_map` 严格解析通过，依赖全在图中、拓扑序正确；
  verify-artifacts 不报图外 Spec。
- **AC2** 模块表、Build order 都不再含 `dependency-check`；`docs/retirements/dependency-check/` 下三份文件与改前 `HEAD` 对应
  文件 blob 相同；退役说明存在；阶段注入的模块总数比改前少 1，DONE／当前模块判定不变。
- **AC3** `module-insert` 一行不再含 `spec skeleton`，其余字段不变。
- **AC4** 两份 README 不再说上游「一个项目只有一份 Spec」；`check-readme-sync.py` 通过。
- **AC5** `interface.json` 合法 JSON，`version` 不变，只改那一处字符串；接口相关回归全绿。
- **AC6** 两份 README 的 cost-report 说明列出 C6 的读取项，不再写「只统计 token 与轮次」。
- **AC7** 新增 `test-phase-guard.sh` 用例：在 PATH 最前放一个记录调用的 `python3` 替身，对**无激活信号**的项目以 JSON 输入
  （含 `cwd`）分别跑 UserPromptSubmit、SessionStart compact、SessionStart fresh 三种事件——退出码 0、无输出、替身**零次**调用。
  反向用例：`cwd` 指向的 linked worktree 已启用而 `ROOT` 未启用时，仍有阶段注入；`cwd` 带转义字符时退回 python3 解析，行为与改前相同。
  现有 phase-guard 回归全部不改、全绿。手工变异：把预检改成恒「拿不准」，零调用断言变红。
- **AC8** `scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿；改到 `.sh` 时 ShellCheck 通过。

## Boundaries

- **会做**：上述七项及其回归；能力图变更记录一条；todo 末尾记更新说明（供协调整批写 CHANGELOG）。
- **先问再做**：发现别的文档与实现不一致——记下交模块协调，不顺手修。
- **不做**：改版本号与 CHANGELOG（协调整批统一改）；改 `cost-report` 的实现（归 `cost-slim-link-follow`）；改收件枢纽相关话术
  （归 `sibling-rules-out`）；改能力历史功能（归 `history-slim`）；重装或更新本机 spec-guard；改 session-protocol 仓库。

## 并行边界

- 独占：`spec/fact-fixes.md`、`spec/install-by-scope.md`、`docs/retirements/dependency-check.md`、`README.md`、`README.en.md`、`plugins/spec-guard/hooks/phase-guard.sh`、`plugins/spec-guard/hooks/test-phase-guard.sh`
- 公共：无

## 待定（请在批准时选）

1. **`dependency-check` 怎么处理**
   - **A（推荐）退役归档**：如 C2。与 `retired-module-separation` 先例一致，能力图只列现行模块。代价是取代 `install-by-scope`
     当时「保留那一行」的决定。
   - **B 保留行、改职责**：行留在图里，职责改成「（已退役：0.78.1 起由 install-by-scope 删除）原职责……」，Spec、Plan 不动。
     改动最小，但图里继续有一个不存在的功能。
2. **interface.json 的版本写法**：推荐 C5 的「v2.3 定义、到 v2.5 未变」（如实且不声称整份契约的兼容性）；也可以直接写
   「contract v2.5」，但 spec-guard 并没有按 v2.4／v2.5 做过对照。

## 文档建议

只改 README（中英）与能力图、退役说明这些说明类文档；项目没有文档基线，不需要文档影响登记。

## 变更记录

- 2026-10-22（构建中，范围内修正）：
  1. 并行边界按用户批准 Spec 时的答复（事项 C30：「spec/CAPABILITY-MAP.md 与 interface.json 是公共文件，改动发【公共变更请求】由模块协调落地」）
     去掉 `spec/CAPABILITY-MAP.md`、`plugins/spec-guard/interface.json`，以及随能力图一起由模块协调移动的 `spec/dependency-check.md`、
     `tasks/dependency-check/`、`docs/retirements/dependency-check/`；这些改动经【公共变更请求】C42 在集成分支落地（`d5e9423`、`35f85bd`）。
     「公共」一行只收全局配置、锁文件、迁移、测试资源四类，能力图与接口文件不属其中，所以仍写「无」。
  2. C7 的读法：实测 macOS `/bin/bash` 3.2 的 `read` 从管道逐字节读，1MB 要约 2 秒，超过 1 秒的等待上限，并且超时会丢掉已读部分；
     照原写法读满 1MB，0.5MB～1MB 的输入会失去 `cwd` 修正和会话事实。改为 bash 只读前 64KB（约 0.04 秒），超出算拿不准，前缀与其余输入
     按原字节交给 python3。目标、判据与「拿不准照旧走 python3」不变，已启用项目输出逐字节不变；回归覆盖约 70KB、约 900KB 与超过 1MB 三种大小。
  3. 返工 1（2026-10-23，账本 M6K7H98）：C7 的「最多等 1 秒」，超时也算拿不准。0.84.0 只要 `read` 返回非零就当作读完；bash ≥ 4 超时返回 >128
     并保留已读部分，被当成完整输入，worktree 会话丢注入（CI 第 11 段时好时坏）。现在返回 0 或 >128 都设 RAW_MORE，已读部分与其余输入交给
     python3。bash 3.2 超时返回 1 并丢掉已读部分，分不出超时，与 0.83.2 相同，不在此修。目标、判据与「拿不准照旧走 python3」不变。
     来源：用户本人（「按原话修：bash≥4 上状态 >128 设 RAW_MORE=1；3.2 的限制另记账」）。
