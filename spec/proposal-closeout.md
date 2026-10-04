# Spec: proposal-closeout

## Objective

Proposal 四步流程（提交、接受、晋级、收尾）的第四步目前只走了一半：
`proposal-promotion-proof` 能证明晋级已进入远端默认分支，但证明之后**没有任何东西收尾**。
文档只要求人把 Issue 标签改成 `proposal-stage:promoted`，而关闭事项既没有命令也没有判据。

后果已经发生：本仓库三个真实 Proposal Issue 全部保持 open（2026-10-04 读回核实）。
其中 #125 的标签**已经**是 `promoted`、只读证明也是 `proved`，它仍然 open —— 这说明
「改标签」和「关闭」是两件独立的事，而当前流程只做了前者，缺口只能靠事后审查发现。

本模块补上第四步的后半段：在**同一次运行内**重新取得 `proved` 之后，预览、经授权写入一条带
稳定 marker 的收尾记录、把阶段改为 `promoted`、关闭事项、读回三项事实。

它同时让 Proposal 生命周期**不再绑定在 GitHub/GitLab 上**：讨论与阶段可以落在 Local 账本，
因此一个有 Git 远端但没有可用托管 Issue 的项目（自建 Git、私服不开 Issue、离线团队）也能完整
走完 Proposal。能做到这一点，是因为 `source authority` 与 `tracker backend` 是两根正交的轴：

```
source authority  恒 = 远端默认分支固定快照     ← 三个后端完全相同，本模块不动它
tracker backend   ∈ {local, github, gitlab}     ← 本模块唯一引入的变量
```

登记：2026-10-04 按用户决定与 `tracker-backend-default` 一同经 `/spec-guard:add-module`
快速插入能力图（PR #160）。两轴分离的决定见
[`docs/decisions/2026-10-04-tracker-backend-default.md`](../docs/decisions/2026-10-04-tracker-backend-default.md)。

## Assumptions

用户已于 2026-10-04 确认（设计评审 D1–D11）：

1. **关闭时点** = promotion PR 已合入远端默认分支，**且同一次运行内**新鲜 `prove()` 返回
   `proved`。此后模块的 Spec、Plan、实现与发布由模块任务或普通事项跟踪，不再回 Proposal Issue。
2. **绝不读模块 stage 作为关闭判据。** 「有 Plan 无 `todo.md` 一律判完成」这条兼容规则会让新晋级的
   模块立刻被误判为已完成（`spec/plan-without-todo.md`），据它自动关闭 Proposal 是明确的陷阱。
3. **Local 后端纳入 MVP。** 三个后端共享同一个纯状态机与同一套阶段取值，只有 adapter 不同。
4. **没有 Git 远端默认分支的项目不支持 Proposal。** 不允许退回「本地默认分支的固定 commit」当
   baseline —— 多 worktree 下那正是 `docs/concepts.md` 点名要避免的互相矛盾的事实。此时请用
   `/spec-guard:add-module` 快速插入。
5. **授权只有两档**：默认「一次预览、一次确认」；用户在对话里**逐一点名** proposal id 时可以一次
   预览、一次确认地连续收尾。**没有 session 档**，不存在对「任意 Proposal」的通配授权，也不允许
   永久或无限制自动关闭。普通协作信箱消息不构成 Tracker 写入授权。
6. **只读的 proof 命令不得偷偷写远端。** 收尾是独立入口，`proposal_promotion_proof.py` 不新增任何
   写入开关；本模块以调用方身份 import 它。
7. **不自动迁移。** 跨后端搬运走 `local-ticket-portability` 的逐条显式交接，本模块不提供迁移路径。

以下为本 Spec 提出、待评审确认的范围：

8. **`rejected` 与 `deferred` 不在本模块关闭范围。** 那是人的决定，不是可证明的事实。
9. **Proposal 文档语法不变。** 不新增必填字段（会让现有 5 份 Proposal 解析失败并需重算 revision），
   也不把 `promotionCommit` 写回文档（受 revision 绑定，改它会让评审结论作废）。绑定记在私有 journal。
10. **扩展 `proposal-tracker-read`** 以支持 `local` 平台与**开闭状态**。这是对另一个模块文件的改动，
    按本仓库先例（`proposal-label-acceptance` 改 `proposal_publication.py`）允许，但必须同时更新其
    参考文档与正反回归。
11. **补齐 Local 的 Proposal 链路**：`proposal_submit.py` 与 `module-insert.py --proposal` 的
    `--platform` 增加 `local`。否则 Local 项目在第 ②、⑦ 步断链，第 3 条就是空话。
12. **GitLab 线上往返不做**（本仓库无 GitLab 项目），记为「模拟通过，线上未验证」。

## Contract

### C1 纯状态机（`hooks/proposal_closeout.py`，零 I/O）

```python
closeout_decision(stage, closed, proof_state) -> Decision
```

| 条件（按此顺序判断） | state | diagnostic |
| --- | --- | --- |
| `closed is True` | `already-closed` | — |
| `proof_state != "proved"` | `not-eligible` | 透传 proof 的诊断 |
| `stage not in {accepted, promoted}` | `not-eligible` | `stage-not-closeable` |
| 否则 | `eligible` | — |

`eligible` 带 `targetStage="proposal-stage:promoted"` 与
`needsStageChange = (stage != "proposal-stage:promoted")`。

这个函数三个后端共用，**不接受任何 project/root/provider 参数**，因此不可能偷看模块 stage
（Assumption 2 的结构性保证）。

### C2 tracker 读取扩展（`hooks/proposal_tracker_read.py`）

- `recover_tracker_issue` 的平台集合增加 `local`；`local` 的 target 是非空 `projectId` 字符串
  （`[A-Za-z0-9_-]{1,64}`，与 `local_ledger_runtime` 逐字相同的正则）。
- `_issue_fields` 增加 `local` 分支：`issueId` 为 Epiq 完整 id 字符串，`container` 为 `projectId`，
  `body` 取 description，`labels` 取 tag 名列表。`TrackerRead.issue_id` 类型放宽为 `int | str`。
- `TrackerRead` 增加 `closed: bool`。GitHub 的 `gh issue list --json` 增补 `state`；GitLab 的
  `state` 已在响应中；Local 取 `isClosed`。缺这个字段即 `unknown`，**不默认当作 open**。
- `absent` / `invalid` / `unknown` / `verified` 四态、marker 唯一性、容器一致、legacy marker 拒绝、
  完整分页要求**全部不变**，三个平台共用同一个纯函数。
- `invalid` 覆盖三类不同的问题，而调用方对它们的反应应当不同，因此各给一个稳定短码：
  `tracker-marker-ambiguous`（多条事项含完整 marker，需人工选择）、
  `tracker-marker-foreign-container`（marker 出现在目标容器之外，参数给错了）、
  `tracker-legacy-marker`（正文含旧 bridge marker，属于迁移问题）；
  `validate_tracker` 的契约违规沿用 `tracker-contract-invalid`，未带短码的结果也回落到它。
  散文诊断只留给人看，调用方只允许依据短码分支——靠匹配句子来区分是假精度。
- 安全 JSON 增加 `closed`，其余不变：仍不含正文、评论、marker、URL、token、原始错误。

### C3 provider 适配器协议

三个 adapter 实现同一组方法；状态机与判据不依赖任何平台特性：

| 方法 | 作用 |
| --- | --- |
| `target_facts()` | 返回并校验精确目标；与预览中记录的不一致即 `unknown: target-changed` |
| `list_issues()` | 完整候选集 `{complete: bool, issues: [...]}`，不完整即 `unknown` |
| `get_issue(id)` | 单条读回，含 `closed`、`stage`、正文 digest |
| `list_comments(id)` | 完整评论集，用于 marker 查重 |
| `create_comment(id, body)` | 写收尾记录 |
| `set_stage(id, from_stage, to_stage)` | 阶段迁移 |
| `set_closed(id)` | 关闭 |

平台差异只落在 adapter 内：

- **github**：`gh api --hostname <host>` 读写；阶段是 label；关闭 `PATCH {"state":"closed"}`。
- **gitlab**：`glab api`；target 是正整数 project id（与既有 Proposal 命令一致，全仓库只此一种形态）；
  评论是 note，**系统 note 不算讨论证据**；关闭 `PUT {"state_event":"close"}`。
- **local**：经 `local_ledger_runtime.mcp_tool_call` 调 Epiq stdio MCP
  （`command = [node_path, runtime_dir/MCP_RELATIVE_PATH]`，参数带 `repoRoot`，取 `response["value"]`）。
  `epiq_issue_list` / `epiq_issue_get` / `epiq_issue_comment_add` / `epiq_issue_tag_add` /
  `epiq_issue_tag_remove` / `epiq_issue_close`。
  **注意 `epiq_issue_tag_remove` 收的是 `tagId` 不是 `tagName`**，所以阶段迁移必须先读回该 issue 的
  tags 找到旧阶段 tag 的 id；读不到就报 `unknown`，不盲猜。`tagName` 的约束是 1–60 字符、无字符限制
  （实测已安装 `epiq@1.11.0` 的 schema），因此 `proposal-stage:*` 取值与托管侧**逐字相同**。
  调用前要求 Epiq runtime 与 Node `ready`、状态 worktree `owned`，否则 `unknown`。

### C4 预览

`preview` 子命令只读。它依次：重取远端默认分支快照读 Proposal（必须 `published` 且为 v2）→ 在给定
精确目标内完整分页按 marker 定位**恰好一条**事项 → 读阶段与开闭 → **在同一次运行内**调
`proposal_promotion_proof.prove_from_remote()` → 只有 `proved` 才生成预览。

预览必须显示：

`backend`、`exactTarget`、`proposalId`、`revision`、`issueId` 与短编号（Local 为 7 位 ref）、
`currentStage`、`targetStage`、`promotionCommit`、`reviewCommit`、**将写入的收尾记录全文**（含 marker）、
动作清单（评论 → 改阶段 → 关闭）、目标来源（`explicit` / `project-default` / `project-default-target`）、
以及 `digest`。

Local 的预览**额外显示该账本是否会 sync 到公开远端**：本仓库 origin 是公开的，`__epiq_state__`
也是公开分支（`spec/local-ticket-ledger.md` 已记载该决定），用户必须知道收尾记录的可见范围。
本模块自己**不调用** `epiq_sync`（它是受 gate 的工具）。

### C5 写入前复核（`--confirm` 之后、第一次写之前，全部重做）

| 复核项 | 不通过 |
| --- | --- |
| 预览 `digest` 与重算一致 | `preview-invalid` |
| Proposal 仍 `published`，marker 与 revision 未变 | `preview-stale: proposal-revision-changed` |
| 精确目标未变（`target_facts()` 比对） | `unknown: target-changed` |
| 事项身份未变（`issueId` + 正文 digest） | `conflict: issue-content-changed` |
| 仍 open | `already-closed` |
| 阶段仍可关闭 | `not-eligible` |
| **重跑 `prove()` 仍为 `proved` 且 `promotionCommit` 相同** | `not-eligible: proof-changed` |
| journal 中已记录的绑定与本次一致 | `conflict: binding-target-changed` |

### C6 写入顺序、marker 与幂等

稳定 marker（新命名空间，与 hosted/local ticket 都不冲突）：

```
<!-- spec-guard-proposal-closeout:v1 <proposalId>/<revision 前 12 位> -->
```

置于收尾记录**最后一行**；只在最后一行认定有效。带 marker 但正文不是本次记录的评论判为
`conflict: closeout-marker-not-ours`：marker 由公开信息推得出来，任何能评论的人都伪造得出来，
因此只有逐字相同的那条记录才算已写过。

收尾记录正文固定包含一句边界声明：本事项记录的是**设计决定**，已随 `<promotionCommit>` 进入能力图；
模块的 Spec、Plan、实现与验收由后续模块任务或普通事项跟踪，**不由本事项代表**。
（防止「关闭」被误读成「模块已交付」。）

每步写入前先按 marker / 阶段 / 开闭查重，命中则跳过：

```
1. 评论（带 marker）  → list_comments 已有 marker 则跳过
2. 阶段 → promoted    → 已是 promoted 则跳过；否则先 tag_add 新阶段，再 remove 旧阶段
3. 关闭               → 已 closed 则跳过
4. 读回               → 阶段 == promoted ∧ closed == true ∧ **本次记录恰好一条**
```

### C7 私有 journal

`~/.local/state/spec-guard/proposal-closeout/<sha256(proposalId + revision)>.json`，
0600、父目录 0700、`O_NOFOLLOW`、`fcntl` 独占锁，按 proposal 串行化。
记录 `{version, backend, exactTarget, proposalId, revision, digest, attempted, remoteId, lastStep}`。

**诚实的局限（写进文档）**：插件无法扫描所有容器，因此**不能证明**同一个 Proposal 没有在另一个
Tracker 里也存在一条。journal 丢失后仍须靠 marker 重新对账。与 `local-ticket-portability` 对同一
问题的表述一致。

### C8 结果状态

| state | 含义 |
| --- | --- |
| `verified` | 三步成功并读回；带 `promotionCommit`、`issueId` |
| `already-closed` | 事项已关闭，**不写任何内容**，只读回报告 |
| `partial` | 部分成功（如评论成功、关闭结果不明）；journal 保留，**不自动重试** |
| `conflict` | marker 多条 / 正文被改 / 绑定目标不同 |
| `not-eligible` | proof 非 proved、阶段不可关闭、proof 变化 |
| `preview-stale` / `preview-invalid` | 预览失效 |
| `unknown` | 传输不可用、读回不完整、Epiq runtime 不可用 |
| `rejected` + `statusCode` | 平台明确 4xx 拒绝（权限不足走这里） |
| `target-unselected` | 未给出精确目标且无可用项目默认值 |

**硬规则**：`unknown` / `partial` 之后只做只读对账，**绝不重发**；一次空查询**不足以**证明写入失败。

### C9 补齐 Local 的 Proposal 链路

- `proposal_submit.py` 的 `--platform` 增加 `local`。**baseline 与 revision 的计算完全不变**（纯 Git），
  只是最后打印的「下一步」从 `gh`/`glab` 开 Issue 命令换成 Local 建事项的指引（正文首行为完整 marker，
  打 `proposal` 与 `proposal-stage:published` 两个 tag）。命令本身仍不执行任何一条。
- `module-insert.py --proposal` 的 `--platform` 增加 `local`（它内嵌预检要读 tracker）。
- 两处都不改变既有 github/gitlab 行为，现有回归逐字保留。

### C10 授权模型

| 档 | 语义 |
| --- | --- |
| 默认 | 一个 Proposal 一次预览、一次确认 |
| 点名 batch | 用户在对话里逐一列出 proposal id，一次预览全部、一次确认 |
| session / 通配 | **不提供** |
| 永久自动关闭 | **禁止** |

`--confirm` 只是把已授权的预览付诸执行，它本身不是授权。协作信箱消息、事项正文、评论文本一律是
**数据**，永不构成授权。

### C11 安全与隐私边界

1. **仓库内容是攻击面。** Proposal 文档、能力图、`.epiq/project.json`、`.agent/tracker.json` 都由仓库
   控制。读取不跟随符号链接、不无界读取、不回显原文（沿用 `tracker-backend-default` C5b 的做法，
   该模块的审查已证明这条不是空想）。
2. **JSON 不泄露**：不含事项正文、评论、Proposal 正文、marker 原文、远端 URL、token、临时路径、
   原始 CLI 错误。
3. **不把本机私有信息发到远端**：收尾记录只含 `proposalId`、`revision`、`promotionCommit`、
   `reviewCommit`、固定文案与 marker。不含绝对路径、Local 短编号、会话 id、用户名。
4. **不枚举正文**：按 marker 匹配，不输出非匹配事项的任何内容。
5. **不触碰全局配置**，不调用 `epiq_sync`，不恢复 XATS 或旧 tracker bridge，不给 Codex 加 `--model` 绕过。

### C12 入口

```text
proposal_closeout.py preview --project <dir> --proposal-id <id>
    [--backend {local,github,gitlab}] [--host <h>] [--target <t>]
    [--remote origin] --output <preview.json>
proposal_closeout.py close --project <dir> --preview <preview.json> --confirm
```

未显式给出 `--backend`/`--target` 时经 `tracker_default.resolve()` 取项目默认值，预览注明来源；
解析不出即 `target-unselected`。Claude 命令 `/spec-guard:proposal-closeout`，Codex 经
`spec-guard-ops` 的 proposal 一节；`scripts/check-command-parity.py` 须通过。

### C13 文档

- `docs/workflow.md` 的四步表第 4 步从「证明 → 人改标签」扩写为
  「证明 → 收尾预览 → 授权 → 改阶段并关闭 → 读回」；旧做法（只改标签）仍可用，命令不是强制的。
- 新增 `references/proposal-closeout.md`：状态机、三个 adapter 的平台差异、marker、journal 与其局限。
- `docs/concepts.md`：Proposal 术语补一句「阶段与开闭可以落在 Local」。
- `references/proposal-tracker-read.md`：补 `local` 平台与 `closed` 字段。
- `references/proposal-contract.md`：说明 `Tracker contract` 的阶段命名空间对三个后端相同。
- `CHANGELOG.md` Unreleased。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_proposal_closeout.py
python3 -B plugins/spec-guard/hooks/test_proposal_tracker_read.py
python3 -B plugins/spec-guard/hooks/test_proposal_submit.py
python3 -B plugins/spec-guard/hooks/test_module_insert.py
python3 -B plugins/spec-guard/hooks/test_tracker_default.py
python3 scripts/check-command-parity.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash evals/codex-plugin-smoke.sh --selftest
```

## Project structure

```text
plugins/spec-guard/hooks/proposal_closeout.py        -> C1 状态机、C4 预览、C5 复核、C6 写入、C7 journal、C12 CLI
plugins/spec-guard/hooks/proposal_closeout_github.py -> C3 github adapter
plugins/spec-guard/hooks/proposal_closeout_gitlab.py -> C3 gitlab adapter
plugins/spec-guard/hooks/proposal_closeout_local.py  -> C3 local adapter（经 mcp_tool_call）
plugins/spec-guard/hooks/test_proposal_closeout.py   -> 全部正反测试
plugins/spec-guard/hooks/proposal_tracker_read.py    -> C2
plugins/spec-guard/hooks/proposal_submit.py          -> C9
plugins/spec-guard/hooks/module-insert.py            -> C9
plugins/spec-guard/commands/proposal-closeout.md     -> C12
plugins/spec-guard/skills/spec-guard-ops/SKILL.md    -> C12
docs/, plugins/spec-guard/references/, CHANGELOG.md  -> C13
```

## Testing strategy

先红后绿，每项先确认在当前代码上失败并记录输出。聚焦测试用假 provider 与临时 Git 仓库，不联网；
Local 用**隔离临时账本**（临时仓库 + 独立 `EPIQ_GLOBAL_DIR` + 固定 runtime），
**不扫描真实账本，不读取、评论或关闭真实 Local 事项 E7V48RY**。

### T1 纯状态机

`closed=True` → `already-closed`；`accepted`+`proved` → `eligible` 且 `needsStageChange`；
`promoted`+`proved` → `eligible` 且不需改阶段；`proved` 以外的每个 proof 状态
（`not-promoted`/`stale`/`invalid`/`unknown`/`not-accepted`）→ `not-eligible` 并透传诊断；
`draft`/`published`/`in-review`/`needs-revision`/`deferred`/`rejected` + `proved` →
`not-eligible: stage-not-closeable`。
**另加一条断言锁死函数签名不含 project/root/provider 参数**，使它结构上不可能读到模块 stage。

### T2 每个后端的正反矩阵（local / github / gitlab 各一遍）

预览侧：目标未给出 → `target-unselected`；marker 0 条 → `absent`；≥2 条 → `conflict`；
marker 在容器外 → `invalid`；legacy bridge marker → `invalid`；分页截断 → `unknown`（**不得报 absent**）；
provider 不可用 → `unknown`；403 → `rejected`+`statusCode`；v1 Proposal → `legacy-revision-required`；
缺开闭字段 → `unknown`（**不默认当 open**）。

确认侧：digest 不符 → `preview-invalid`；revision 变 → `preview-stale`；正文被改 → `conflict`；
`target_facts()` 变 → `unknown: target-changed`；重跑 proof 不再 proved → `not-eligible: proof-changed`；
journal 绑定不同 → `conflict: binding-target-changed`。

写入侧：全成功 → `verified` 并读回三项；评论已存在 → 跳过不重复；阶段已 promoted → 跳过；
关闭响应丢失但实际已关闭 → 对账后 `verified`；关闭响应丢失且确实未关 → `partial` 且**重跑不产生
第二条评论**；连续两次 confirm → 第二次 `already-closed`。

### T3 Local 专属

`epiq_issue_tag_remove` 需要 `tagId`：读不到旧阶段 tag 的 id → `unknown`，不盲猜；
Epiq runtime / Node 未 ready → `unknown`；状态 worktree 非 `owned` → `unknown`；
7 位 ref 与完整 id 都能定位同一条，但**写入一律用完整 id**；
预览必须出现「该账本是否会 sync 到公开远端」一行；**断言全程未调用 `epiq_sync`**。

### T4 设计点名的场景

| 场景 | 落点 |
| --- | --- |
| 三个后端各自完整生命周期 | T2 + 端到端串联 |
| 无 remote 的 Local 项目 | publication 读不到远端默认分支 → `unknown`，**不退回本地** |
| Tracker 未配置 | `target-unselected` |
| 切换默认后旧 Proposal 保持原绑定 | journal 冲突用例 |
| marker/revision 预览后变化 | `preview-stale` |
| proof 不是 proved | T1 + 确认侧各一 |
| 关闭响应丢失但已关闭 | 对账 → `verified` |
| 重试不重复评论或关闭 | 幂等跳过用例 |
| 多候选拒绝猜测 | `conflict` |
| 已关闭幂等读回 | `already-closed` |
| 缺权限 / provider 不可用 | `rejected` / `unknown` |
| **新模块没有 todo 时不得判定为可自动关闭** | T1 的签名断言 + 一条端到端：晋级后模块只有 Plan 无 todo，收尾仍只依据 proof |

### T5 C9 的回归

`proposal_submit --platform local` 输出 Local 建事项指引且 baseline/revision 与 github 路径**逐字相同**；
`add-module --proposal --platform local` 预检读 Local tracker；两者的 github/gitlab 既有断言全部保留。

### T6 真实往返（需单独授权）

每个平台至少一次经精确目标与内容授权的受控真实往返。GitHub 的候选是 #149 / #104
（两条都是 `accepted` + `proved` + open，最干净的样本）；**执行前必须先展示逐字的评论正文、
将加/删的 tag 或 label、关闭动作，并取得针对那两个具体 Issue 的明确授权**。
未获授权则记「真实远端未验证」，不以模拟顶替。GitLab 按 Assumption 12 记为线上未验证。

## Boundaries

- **Always**：先红后绿；`prove()` 在同一次运行内重取；预览与写入之间全部复核重做；
  只依赖 bash/git/python3（Local 另需 Node 与固定 Epiq runtime），不引入 `jq`；
  保留 `from __future__ import annotations`；Python 3.9 与默认 python3 均通过；
  marker 只在最后一行认定；`unknown`/`partial` 只对账不重发。
- **Ask first**：对 #149/#104/#125 的任何真实写入；新增 Issue 阶段取值；放宽 Proposal 的事实源规则；
  让本模块调用 `epiq_sync` 或任何受 gate 的 Epiq 工具；修改 Proposal 文档语法。
- **Never**：读模块 stage、todo 或能力图完成度作为关闭判据；给 `proposal_promotion_proof` 加写入开关；
  自动在另一个 Tracker 重建同一个 Proposal；自动迁移已有事项；关闭 `rejected`/`deferred`；
  在 Spec、代码、测试、提交信息或 PR 中写入其他项目的名称、模块或编号；
  恢复 XATS 或旧 tracker bridge；修改全局 Claude/Codex 配置。

## Success criteria

- 三个后端在隔离环境下各自走完「发布 → 接受 → 晋级 → 收尾」，收尾返回 `verified` 并读回
  阶段 `promoted`、已关闭、marker 恰好一条。
- 同一条 Proposal 连续两次 `close --confirm`：第二次 `already-closed`，且评论数不变。
- proof 不是 `proved` 时任何后端都写不出去；`proposal_promotion_proof.py` 的 CLI 与返回状态逐字不变。
- 晋级后模块只有 Plan、没有 `todo.md` 时，收尾结果与有 todo 时**完全相同**（判据不看模块 stage）。
- 关闭响应丢失的场景下重跑不产生第二条评论、不重复关闭、不在别处重建事项。
- 没有 Git 远端的项目得到 `unknown` 并给出「用快速插入」的下一步，而不是退回本地 commit。
- `validate.sh`、`check-command-parity.py`、两条 hook 回归、`codex-plugin-smoke --selftest` 全部通过；
  两种 Python 下一致。
- 真实往返：GitHub 在获授权后完成一次并读回；GitLab 明确记为「模拟通过，线上未验证」。

## Open questions

- **Local 事项的 `proposal` 与 `proposal-stage:*` tag 是否需要预先创建**：`epiq_issue_tag_add` 的描述
  说「creating the tag if it does not exist」，因此预期不需要；实施时以隔离账本实测确认，
  若需预创建则在 C3 的 local adapter 中补一步并加正反测试。
- **Epiq 的 7 位 ref 是否全局唯一**：预览展示它、写入用完整 id，因此不影响正确性；若实测发现 ref
  可能碰撞，预览需要额外标注这一点。
