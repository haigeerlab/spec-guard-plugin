# 技术方案: sg-gate-flow

<!-- spec-guard: review pending -->

需求文档：`spec/sg-gate-flow.md`（用户 2026-11-27「确认需求」，指纹 `6229ba37`）。照已批总体技术方案第 6、7、8 节与 4.8，不重新选型。

## 现状调研

- **流程标记**：`module_stage.FLOW_MARKER` 用 `fullmatch` 认 `<!-- spec-guard: flow v2 tier=<档位> -->` 一整行。行里多写一个字段，旧版 spec-guard 就认不出，会把模块当老流程处理。
  module-crew 和 hub 都不自己解析这一行，只读 `/map --json`（module-crew `module_crew/flow.py`，hub `orchestrator/flow.py`）。
- **批准指纹**：`review_body` 只去掉批准标记行，需求文档里别的标记行都在指纹范围内。所以新加的标记行改了，批准自动失效，不用另写判定。
- **需求确认**：`requirement_wait`、`requirement_hint`（`module_stage.py:535`、`:604`）。新流程模块的需求没确认之前，阶段提示要求复述需求、拷问，用户确认后用 review-mark 记批准。
- **档位**：`project_config.py`：
  - `ITEMS`：三项 design、merge、release，各自的取值从严到宽排；
  - `PRESETS`：只有 none、design、merge 三个预设；
  - `expand`：自定义对象里没写的项按 `human` 读；
  - `PRESET_LADDER`：收窄时逐格往下走，目前只有 none → design → merge；
  - `module_takeovers`：按「模块 > 项目 > 默认」取值，只返回各项的取值，不带预设名。
- **`/map --json`**：`map_view.py:519` 的 `takeover` 给出 design、merge、release、spec、plan、source、widerThanProject、narrowed。`_milestone_stop`（`:405`）只给出 file、milestone、modules、usages。
- **里程碑停点**：`module_stage.milestone_stop`（`:2172`）一旦停住，就把下一步换成「先不开下一个模块」。module-crew 的 `start.py:33` 只要 `milestoneStop` 不为空就不开新模块。
- **规则文件**：`references/workflow-checkpoints.md` 的第 162～163、165、180、331、520～522、542 行是这次要换的六处；第 154 行写着「agent 自己能修的失败不算，照旧自己修」。
  `hooks/test_workflow_checkpoints.py` 有八处钉着旧原文（133、211、715、851～867、881～882）。两份约定块模板里都没有「合并永远由用户」这句。
- **接口**：`interface.json` 当前是 `1.25`。
- **本仓库**：第一次有带流程标记的模块；本仓库没有 `.github/autopr/risk-paths.json`。

## 影响面

| 文件 | 改什么 |
|---|---|
| `hooks/module_stage.py` | 新标记 `release-preauth`、`overall-design` 的解析；需求确认提示里的发版一问；总体技术方案一关；里程碑停点按预设决定阻不阻塞；连着做之前先说一句 |
| `hooks/project_config.py` | 预设 `autopilot`；带 `preset` 键的对象；收窄阶梯；新函数 `module_preset` |
| `hooks/map_view.py` | `takeover.releasePreauth`、`takeover.preset`、`milestoneStop.blocking`、`flow.overallDesign` |
| `hooks/verify-artifacts.py`（及它调用的检查） | 新标记的格式；总体技术方案文件存在、批准标记格式与新鲜度（指纹失效判失败）；同一份用法草案里的模块指向不同总体技术方案时提醒 |
| `hooks/review_mark.py` | `--target overall`：给总体技术方案记批准，只认用户 |
| `references/workflow-checkpoints.md` | 六处逐字替换；新增「出事处理」「总体技术方案」两节；需求确认一节加发版一问与总体技术方案的提出；第 154 行加指向；里程碑停点一节加 autopilot 不阻塞 |
| `references/doc-skeletons.md` | 总体技术方案的骨架、两行新标记 |
| `commands/config.md` 与 Codex 侧 config 说明 | 新预设与带 `preset` 的写法 |
| `interface.json` | 升 `1.26`，只加字段 |
| 测试 | `test_workflow_checkpoints.py` 改八处并加新断言；`test_flow_v2.py`、`test_project_config.py`、`test_map_view.py`、`test_review_marker.py`、`test-phase-guard.sh` 加正反例 |
| `CHANGELOG.md`、两份 `plugin.json`、两份 README 的 `--ref` | 版本号（次版本） |

只读调用方：module-crew 要读 `milestoneStop.blocking` 才会在 autopilot 档下不停；不读的话照旧停，只会更严，不会更松。hub 模块 3 要读 `releasePreauth`。

## 实现方案

### 1. 提前授权

- 新标记行：`<!-- spec-guard: release-preauth yes -->`，单独一行，写在流程标记行下面。正则 `RELEASE_PREAUTH = <!-- spec-guard: release-preauth (\S+) -->`，只认 `yes`；别的值算格式错，verify-artifacts 判失败，`releasePreauth` 按没有这一行算。
- `release_preauth(root, module) -> True | False | None`：
  - 老流程模块：`None`；
  - 生效档位的 `release` 不是 `auto-confirm`、`auto`：`None`；
  - 有 `yes` 行、需求批准有效（`requirement_wait` 为 `None`，且批准标记不是 invalid）：`True`；
  - 其余：`False`。
- 需求确认提示（`requirement_hint`）：档位允许时，复述要求里加一句「并问用户『做完自动发版吗？』：答是，在流程标记行下面写 `release-preauth yes`，再记确认；答否不写」。档位不允许时不加，文字和现在逐字相同。
- `/map --json`：`takeover.releasePreauth`。

### 2. 总体技术方案关卡

- 新标记行：`<!-- spec-guard: overall-design spec/overall/<名字>.md -->`，单独一行，写在流程标记行下面。不改流程标记行的格式，旧版 spec-guard 照样能认出流程标记。
  路径只认 `spec/overall/` 下、以 `.md` 结尾、kebab-case 文件名，防止指向仓库外。
- 总体技术方案文件：`spec/overall/<名字>.md`。章节照总体技术方案的大纲：现状调研、影响面、技术选型、架构、目录结构、数据模型、实现方案、接口和数据改动、风险与回滚、方案取舍。骨架写进 `doc-skeletons.md`，内容要求细化归模块 6。
  批准标记和需求文档一样，是一行 `review pending|approved <指纹>`。
- `review-mark --target overall --module <id>`：给这个模块指向的那份文件记批准，只接受 `pending`、`approved`。Codex 的几种状态一律拒绝，拒绝码 `overall-user-only`。
- `overall_wait(root, module)`：模块需求已确认、有 `overall-design` 行，而文件缺失、标记缺失、`pending` 或指纹失效时，返回原因（`missing`、`pending`、`revised`、`invalid`）；否则返回 `None`。
- 阶段提示：`overall_wait` 有值时，排在需求确认之后、模块技术方案审查之前，下一步写「写总体技术方案 `spec/overall/<名字>.md` 并交用户批；批准前先不要写技术方案」。用 `_hold` 的现有文字，不新加阶段名，阶段仍是 `NEEDS_DESIGN`。
- 需求确认一节加一句：复述时提出这次要不要总体技术方案；项目还没有任何代码时默认提出「要」；用户确认后写 `overall-design` 行。
- `/map --json`：每个模块的 `flow` 对象（现有，放着 `tier`、`requirementConfirm`）加 `overallDesign`：老流程模块或没有这一行时为 `null`；否则 `{"path", "status"}`，`status` 取 `approved`、`missing`（文件不在）、`pending`（没有标记或标记是 pending）、`revised`（批准后改过）、`invalid`（标记写坏或路径不合规）之一，与 `overall_wait` 同一判据。
- verify-artifacts：`overall-design` 行格式错、路径不合规、文件缺失判失败；文件在但批准失效时，模块已过需求确认就判失败，没过只提醒。同一份用法草案（`spec/usage/<需求>.md`）里写了 `overall-design` 的模块指向不同文件时提醒（需求文档规则 7「同一需求的模块指向同一个文件」；单模块需求没有草案，不查）。

### 3. 里程碑

- `project_config.module_preset(root, module) -> str | None`：生效值是预设字符串时返回预设名；是带 `preset` 键的对象时返回那个键；不带 `preset` 的对象返回 `None`。`module_takeovers` 的返回不变，避免波及其他调用方。
- `milestone_blocking(root, modules) -> bool`：里程碑里的模块全都是 `autopilot`（`module_preset` 为 `autopilot`）才返回 `False`，其余返回 `True`。
- 阶段提示：不阻塞时，事实行照旧，最后加「（autopilot 档，不阻塞，写进汇报）」；下一步不替换成「先不开下一个模块」，补一句「用户事后要确认时用 milestone-mark」。阻塞时逐字照旧。
- `/map --json`：`milestoneStop` 加 `blocking`。出错对象（`error`）不加这个字段。

### 4. 合并写法与出事处理

- 六处照附录 A 逐字替换。
- 新增一节「出事处理」，放在「Plan 检查点分级」之后，正文见附录 B，待你批。
- 第 154 行的「agent 自己能修的失败（测试没过、写错了）不算，照旧自己修」后面加「（开 PR 以后出的事见「出事处理」）」。
- 测试：八处断言改成钉新原文，并新增几条断言：六处全文逐字一致；「合并永远由用户在对话里决定」不再出现；「出事处理」一节存在，且第 154 行指向它。

### 5. 关卡预设

- `PRESETS["autopilot"] = {"design": "reviewer", "merge": "auto", "release": "auto-confirm"}`。`DEFAULTS["takeover"]` 仍是 `"none"`。
- `valid_takeover`：对象可以带 `"preset"` 键，值必须是 `PRESETS` 里的名字（旧的 `plan` 不行）。`expand`：带 `preset` 的对象，先取该预设的三项，再用对象里写的项覆盖；不带 `preset` 的照旧，没写的项按 `human` 读。
- `legacy`：带 `preset` 的对象，对象里写了的 `spec`／`plan` 照写的读（和现在一样「as written」）；没写的取 `LEGACY_OF_PRESET[预设]`（`autopilot` 当 `merge` 处理），对象里另写了 `design` 时仍按现有规则从 `design=reviewer` 推 `plan`。
- `PRESET_LADDER = ("none", "design", "merge", "autopilot")`，收窄 `autopilot` 得到 `merge`。带 `preset` 的对象收窄时，先展开成三项，再按现有 `NARROW_ORDER` 一项一项收回，结果是不带 `preset` 的对象。
- `/spec-guard:config`：`set takeover autopilot`、`set takeover '{"preset":"autopilot","release":"human"}'`。写入仍要用户原话，预览和确认的流程不变。
- `/map --json`：`takeover.preset`，取 `module_preset` 的值。

### 6. 连着做之前先说一句

- 新流程模块处在 `NEEDS_DESIGN`、`NEEDS_REGRESSION`、`NEEDS_PLAN`、`BUILDING`，并且下一步不停（没有待批的文档）时，阶段提示的下一步后面加一句「接着要连着做几步时，先用一句话告诉用户接下来做什么，再开始；这不是停点，不等回答。」
- 有关卡在等（需求、总体技术方案、技术方案交用户）时不加，老流程模块也不加。

### 7. 接口

`interface.json` 升 `1.26`，新增以下内容，都写明说明和出现条件：
- `reviewMark` 的 `--target` 加 `overall`（只接受 `pending`、`approved`，拒绝码 `overall-user-only`）；
- `mapView.takeover.releasePreauth`、`mapView.takeover.preset`；
- `mapView.milestoneStop.blocking`；
- `mapView.flow.overallDesign` 与它的 `status` 取值表；
- 需求文档的两行标记；
- 预设 `autopilot` 与带 `preset` 的对象。

不删 `takeover.spec`／`takeover.plan`。

## 接口和数据改动

| 位置 | 新增 | 取值 | 旧调用方 |
|---|---|---|---|
| `/map --json` 每个模块 `takeover.releasePreauth` | 字段 | `true` / `false` / `null` | 不读，hub 主干现在不读 |
| `/map --json` 每个模块 `takeover.preset` | 字段 | 预设名或 `null` | 不读 |
| `/map --json` 顶层 `milestoneStop.blocking` | 字段 | `true` / `false` | module-crew 照旧按非空停，更严 |
| `/map --json` 每个模块 `flow.overallDesign` | 字段 | `{"path","status"}` 或 `null` | 不读 |
| `review_mark.py --target` | 新值 `overall` | 只接受 `pending`、`approved` | 旧版拒绝这个值（参数错误） |
| `spec/<id>.md` | 两行标记 | `release-preauth yes`；`overall-design spec/overall/<名字>.md` | 旧版 spec-guard 不认这两行：不问发版，不出这一关 |
| `.agent/config.json` `takeover`／`moduleTakeover` | 预设 `autopilot`，对象可带 `preset` | 见上 | 旧版 spec-guard 读到会判无效，退回下一层：`moduleTakeover` 无效时整张表作废、各模块取项目的值；项目 `takeover` 无效时取 `none`。下一层都不会比 `autopilot` 宽，所以只会更严 |
| `spec/overall/<名字>.md` | 新文件 | 带批准标记 | — |

## 风险与回滚

- **旧版读到新配置**：旧版 spec-guard 读到 `autopilot` 或带 `preset` 的对象会判无效，退回下一层（`moduleTakeover` 作废时各模块取项目的值，项目无效时取 `none`），都不会比 `autopilot` 宽，只会更严；但 `moduleTakeover` 里别的模块的设置也会一起作废。本仓库和消费者升级前不要写这些值。
- **规则文字变了，自动化跟不上**：六处换成新措辞后，「交给 autopilot」这条路要 hub 模块 2 做完、B 批的必需检查加上才走得通。在那之前，长期授权的条件不满足，全部走人工路，和现在一样。
- **出事处理收紧了 PR 以后的修复**：同一原因修两次就停，对所有档位生效。本仓库原来没有次数上限，这是行为变化，CHANGELOG 要写明。
- **回滚**：这是一个 PR，revert 合并提交即可恢复代码与规则。回滚不是完整撤销，有三件事要知道：
  - 回滚后旧版不认 `overall-design` 行，总体技术方案这一关随之消失，指向它的模块直接往下走；回滚前要先告诉用户这些模块的方案批没批，没批的由用户决定先停还是照旧往下。
  - 需求文档里已写的 `release-preauth` 行留在文件里不起作用（hub 读不到字段按没有提前授权处理）。
  - 配置里写了 `autopilot` 的项目按上一条退回下一层。

## 方案取舍

- **新信息放在哪**：
  - 选的做法：两条新信息各自单独写一行标记。
  - 没选的做法：把字段加进流程标记行，写成 `flow v2 tier=normal preauth=yes overall=...`。这样旧版 spec-guard 的 `fullmatch` 认不出这一行，模块会被当成老流程，后果最坏。
- **总体技术方案关卡怎么挂**：
  - 选的做法：不新增阶段名，挂在 `NEEDS_DESIGN` 上，像需求确认那样拦住。
  - 没选的做法：新增一个阶段 `NEEDS_OVERALL`。module-crew、hub 认得的阶段名单都要跟着改，总体方案也没要求新增阶段名。
- **里程碑按谁的预设算**：
  - 选的做法：里程碑里每个模块都是 `autopilot` 才不阻塞（需求文档规则 11）。
  - 没选的做法：按项目级的值算。模块可以单独设档位，按项目级算会漏掉更严的模块。
- **`autopilot` 的发版项**：
  - 选的做法：`auto-confirm`（需求文档规则 17）。
  - 没选的做法：`auto`。`auto` 表示连「要你动手」的步骤也不停，和 R5「要你动手的照样找用户」冲突。
- **出事处理放在哪**：
  - 选的做法：在规则文件里新开一节，第 154 行只加一句指向。
  - 没选的做法：改写第 154 行。那一句管的是「外部原因第二次过不去」，管的范围不一样。

## 待定问题

- **O1（要 lead 或你定）**：附录 A 的第 162～163 行和第 331 行改后写的是「建 tag、Release 和发版不由会话做：由 autopilot ……执行」。这和两处现状冲突：
  - 本仓库现在的发版流程是：你授权后，由会话跑 `scripts/release.py publish/install/smoke`（`docs/release-process.md`）；
  - spec-guard 是公开插件，没装 hub 的项目也只能由会话在用户授权后发版。

  逐字照抄的话，hub 模块 3 上线之前，本仓库和外部项目都没有人能按规则发版。
  - 我的建议：这两句的意思收窄为「装了 autopilot 的仓库由 autopilot 执行；其余照旧在用户确认后由会话执行」。
  - 已批措辞不由我改，已报 lead，等它定或转你定。O1 定下之前，附录 A 先按原文列出。

## 第二审查者意见

第 1 轮：Codex（gpt-5.6-sol，effort high，`/delegate:review --profile design`），2026-11-27，5 条阻断、2 条建议，全部采纳：

1. `overall` 没进 reviewMark 接口：采纳，接口一节加上。
2. 带 `preset` 的对象丢掉旧流程显式写的 spec／plan：采纳，`legacy` 改成写了的照写读。
3. `moduleTakeover` 无效时实际退回项目值而不是 `none`：采纳，兼容与风险两处改写。
4. revert 会让总体技术方案关卡消失：采纳，回滚一条写明不是完整撤销、回滚前要做什么。
5. verify-artifacts 漏了总体方案批准的新鲜度：采纳。
6. 同一需求多模块指向同一文件没有校验（建议）：采纳，按用法草案查，单模块需求不查。
7. `overallDesign` 的位置与状态取值没定义（建议）：采纳，放进现有的 `flow` 对象，五种状态。

## 附录 A：六处改后全文（逐字）

来源：`plugin-ecosystem` 提交 `cae816e`，`research/2026-11-26-自动驾驶目标/模块1-环境与授权-草稿.md`「③-2」一节，到 `7b2daf7` 没改过。下面是该节原文，实现时只取每处「改后」引用块里的文字。

#### 第 162～163 行（原文是一段，跨两行）

改前：
> 远端写入（推送、开 PR/MR、建 tag 或 Release）只有当 Plan 的 `gate` 检查点逐项写明授权时才免问，例如“本 Plan 获批即授权推送并开模块 PR”；没写的步骤照旧在交付前询问。合并永远由用户在对话里决定：用户明确说『合并』后 agent 才执行；先看 PR 状态，必需检查已全部通过时直接合并（GitHub：`gh pr merge`），检查还没跑完时用平台的自动合并（GitHub：`gh pr merge --auto`），由平台等必需检查通过后合并；平台不支持自动合并时，等必需检查全部通过后再合并；合并方式按本仓库习惯；合并后核实已合并、记下合并提交，再告诉用户。任何 Plan 都不能代替用户这句话。本地集成分支有唯一例外：项目打开了多模块并行开关时，见「协调会话的批准与合并」一节。

改后：
> 远端写入（推送、开 PR/MR、建 tag 或 Release）只有当 Plan 的 `gate` 检查点逐项写明授权，或者所在仓库规则文件里用户批准的长期授权逐项写明了这一种操作、而且它写的条件当时都满足时，才免问，例如“本 Plan 获批即授权推送并开模块 PR”；没写的步骤照旧在交付前询问。建 tag、Release 和发版不由会话做：由 autopilot 按需求确认时的提前授权或用户确认过的发版步骤清单执行。
>
> 远端合并分两种情况。**交给 autopilot**：同时满足——带 `flow v2` 标记的模块；生效档位里合并是 `auto`；所在仓库的长期授权写明的其余条件都满足。这时开 PR 后交给 autopilot，由它做合并前验证和风险分级，判为可以自动合并的由它打开平台自动合并；agent 不问用户合并，自己也不执行合并命令。autopilot 判为 T4 的，按下一种情况交用户；验证没通过的，停下按「出事处理」走，不问合并。**由用户决定**：其余所有情况，用户明确说『合并』后 agent 才执行；先看 PR 状态，必需检查已全部通过时直接合并（GitHub：`gh pr merge`），检查还没跑完时用平台的自动合并（GitHub：`gh pr merge --auto`），由平台等必需检查通过后合并；平台不支持自动合并时，等必需检查全部通过后再合并；合并方式按本仓库习惯；合并后核实已合并、记下合并提交，再告诉用户。任何 Plan 都不能代替用户这句话，也不能把档位从人改成 `auto`。本地集成分支有唯一例外：项目打开了多模块并行开关时，见「协调会话的批准与合并」一节。

#### 第 165 行

改前（证据 L144，逐字）：
> 合并的时机与 CI（规范 v1.7）：最终验收的交审消息里就问合并，不等 CI 跑完、不等 PR 变 CLEAN，合成一问「验收通过、合并吗？」（按钮「验收通过并合并」「只验收，先不合」；选后者之后照旧再问一次合并）；验收没过不问合并。开 PR 后，宿主有 PR 监控功能时提议打开，用户批准才开，宿主没有就跳过。会话不自己等 CI：不用后台 `--watch`、定时任务或唤醒、循环，也不反复查检查状态；要等时告诉用户「跑完叫我」并结束本轮。下次被叫醒或用户回来时，先核实已合并（PR 是 merged、主干指向合并提交）、记下合并提交再告诉用户；没合并就照实说状态。

改后：
> 合并的时机与 CI（规范 v1.8）：属于「交给 autopilot」那种情况的模块不问合并：开 PR、交给 autopilot 以后，用一句话告诉用户「已交 autopilot，合并前验证通过后由平台自动合并」，结束本轮；过最终 gate 的依据见下文「新流程模块按回归文档做合并前验证」。其余模块：最终验收的交审消息里就问合并，不等 CI 跑完、不等 PR 变 CLEAN，合成一问「验收通过、合并吗？」（按钮「验收通过并合并」「只验收，先不合」；选后者之后照旧再问一次合并），问的时候写明 PR 当前的 head 提交，用户批准的就是这个提交，之后推了新提交要重新问；验收没过不问合并。开 PR 后，宿主有 PR 监控功能时提议打开，用户批准才开，宿主没有就跳过。会话不自己等 CI：不用后台 `--watch`、定时任务或唤醒、循环，也不反复查检查状态；装了 autopilot 的仓库由它的本机巡检盯 CI，有结果时通知会话；要等时告诉用户「跑完叫我」并结束本轮。下次被叫醒或用户回来时，先核实已合并（PR 是 merged、主干指向合并提交）、记下合并提交再告诉用户；没合并就照实说状态。

#### 第 180 行

改前（逐字）：
> 两种节奏下人工闸门都在，合并永远由用户在对话里决定（见「Plan 检查点分级」）。本地集成分支有唯一例外：项目打开了多模块并行开关时，见「协调会话的批准与合并」一节。多个模块一次审完走下一节「按需求批量前置审」，与本节互不替代。

改后：
> 两种节奏下人工闸门都在；远端合并按「Plan 检查点分级」里「远端合并分两种情况」一段，交给 autopilot 或由用户在对话里决定。本地集成分支有唯一例外：项目打开了多模块并行开关时，见「协调会话的批准与合并」一节。多个模块一次审完走下一节「按需求批量前置审」，与本节互不替代。

#### 第 331 行

改前（证据 L168，逐字）：
> **不授权**合并（照 F3 由用户在对话里决定）、发布，以及 Plan 交审一节「只在这几类情况停下问用户」里的其余操作（删除工作区外的文件、改全局配置、外发凭据等），这些照旧先问。

改后：
> **不授权**会话自己合并（按「Plan 检查点分级」里「远端合并分两种情况」一段，交给 autopilot 或照 F3 由用户在对话里决定）、会话自己发布（发版由 autopilot 按需求确认时的提前授权或用户确认过的步骤清单执行），以及 Plan 交审一节「只在这几类情况停下问用户」里的其余操作（删除工作区外的文件、改全局配置、外发凭据等），这些照旧先问。

#### 第 520～522 行（原文是一段，跨三行）

改前（逐字）：
> 几个模块同时开发时，用户只在协调会话里批准，模块的 Spec、Plan 和代码由各自的模块会话写在各自的 worktree 里。本节说明这种分工下谁写批准标记、谁做本地合并。它是「合并永远由用户在对话里决定」（见「Plan 检查点分级」与「批准节奏」）的**唯一例外**，只在三个条件同时成立时适用：开关为 `on`；由当前的协调会话执行；合并的是用户刚批准最终验收的那一个模块。其他任何合并都不适用。合并怎么做（命令、顺序、合并后的检查、失败与冲突的处理）由运行时（例如 module-crew）规定，本节只规定授权的边界与底线。

改后：
> 几个模块同时开发时，用户只在协调会话里批准，模块的 Spec、Plan 和代码由各自的模块会话写在各自的 worktree 里。本节说明这种分工下谁写批准标记、谁做本地合并。本地合并原本由用户在对话里决定（见「Plan 检查点分级」与「批准节奏」），本节是它的**唯一例外**，只在三个条件同时成立时适用：开关为 `on`；由当前的协调会话执行；合并的是用户刚批准最终验收的那一个模块。其他任何合并都不适用，远端合并见本节末尾。合并怎么做（命令、顺序、合并后的检查、失败与冲突的处理）由运行时（例如 module-crew）规定，本节只规定授权的边界与底线。

#### 第 542 行

改前（证据 L174，逐字）：
> - **推送和远端合并（PR／MR）仍然只由用户做**，或者按「Plan 检查点分级」在 `gate` 检查点逐项写明授权后才推送。任何批准都推不出可以合并 PR。

改后：
> - **推送和远端合并（PR／MR）不因本节的例外而放宽**，逐件按下面的规矩：
>   - 推送：协调会话只在 Plan 的 `gate` 检查点逐项写明授权、或者仓库长期授权写明了这一种推送且条件都满足时才推；否则由用户做。
>   - 远端合并属于「交给 autopilot」的情况：由 autopilot 打开平台自动合并，协调会话不执行合并命令。
>   - 其余远端合并：用户在当前对话里明确说「合并」后，协调会话按 F3 人工路执行；没有这句话就不合。
>   - 本节的任何批准（包括最终验收的批准）都推不出协调会话可以自己合并 PR。


## 附录 B：「出事处理」一节正文（待你批）

```markdown
## 出事处理

本节管开 PR 以后（以及合进主干、发版以后）出的事，所有档位都适用。构建中本地写代码时测试没过、写错了，照「Plan 检查点分级」里的规矩自己修，不计次数。

- **能修的**：PR 上测试跑出来的代码问题、合并前验证没过、审查有阻断。先找根因再修；同一个原因最多修两次，还不行就停下，写明出了什么事、试过什么、可选的做法和各自的代价，交用户决定。
  同一项检查、同一条回归用例或同一条审查意见失败，算同一个原因；改了代码以后重新跑一遍失败的那项检查，算修一次。
- **不改裁判**：修的过程中不改已有的测试和回归用例；要改就停下找用户。实现新功能时新写的测试不受这条限制。
- **测试失败不自己放行**：可以分析是代码的问题还是用例的问题，写明依据，但不自己下结论放行；判断为用例的问题时，停下交用户。
- **合进去以后才出事**：合进主干后 CI 变红、已经发出去的版本有问题，不自动撤回，通知用户，由用户决定撤不撤。
- **等太久要说**：任何一步等了明显超过平常的时间还没结果，停下告诉用户，不空等，也不跳过去接着做。参考时长：PR 的 CI 或打开自动合并后 60 分钟、发布的单个步骤 30 分钟；
  其他步骤按这一步平常要多久判断，停下时写明等了多久、平常多久、依据是什么。
- **CI 变红怎么分**：装了 autopilot 的仓库，CI 变红的分类、自动重跑与收紧档位由 autopilot 做，会话只处理它交过来的「能修的」；没装的，CI 变红按「能修的」处理，修不了交用户。
```

<!-- spec-guard: design-review round=1 blocking=5 sha256=e483490f9170 vendor=openai same-vendor=false criteria=design-v1 report=8cf08531b59dff134756dbb7bf26aa4739c506caa0b2d93e32c5543f83972189 -->
