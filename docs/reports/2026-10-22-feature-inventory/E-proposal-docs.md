# 功能区 E：Proposal、文档治理、历史、成本，以及维护者工具（功能点清单）

基线：commit 85a1f560，只读精读，未改任何文件。

## 缩写与读法

- `H/` = `plugins/spec-guard/hooks/`；`C/` = `plugins/spec-guard/commands/`；`R/` = `plugins/spec-guard/references/`；`S/` = `plugins/spec-guard/skills/spec-guard-ops/SKILL.md`。
- 「默认」列：本区的 Proposal、文档、历史、成本全是**用户手动调用的命令或脚本**，没有任何 hook 自动运行（`phase-guard.sh` 与 `verify-artifacts.sh` 里没有 documentation、history 的引用，已 grep 核对）。所以「默认」写成「手动，无 hook」或「文件存在才有效」。
- 模块 id 来自 `spec/CAPABILITY-MAP.md`（140 个模块）与各 `spec/<id>.md` 的登记说明；「引入」指模块 Spec 的 Objective，「改」指 grep 到该源码文件被模块 Spec 提及。
- 需求疑点只写有依据的；没有写「无」。
- 总体事实（供判断疑点用）：本区 Proposal 相关源码 9 个文件约 2900 行，加测试之外还有 `R/proposal-*.md` 5 份参考；本仓库 `spec/proposals/` 目录只有 6 份已发布 Proposal，而能力图有 140 个模块，绝大多数模块是经 `add-module` 快速插入或一次性登记进图的。本仓库自己没有 `docs/DOCUMENTATION-BASELINE.md`（文档治理未被本仓库自用），但有 `spec/CAPABILITY-HISTORY.json`（归档了 12 个旧 initiative）。

---

## 一、Proposal 生命周期（提交 → 审查 → 晋级预检 → 晋级证明 → 收尾）

流程总览（`R/proposal-closeout.md`、`docs/design.md`「Proposal 边界」）：四步 = 提交、接受（人在 Issue 上贴 `proposal-stage:accepted` 标签 + 一次新鲜审查）、晋级（`add-module --proposal`，属 module-insert，不在本区）、收尾（证明 + 关 Issue）。共享事实只来自远端默认分支固定快照；GitHub/GitLab/Local 只作 Proposal Issue 载体。

### 1.1 Proposal 文档契约（`H/proposal_contract.py`，335 行）

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 1 | Proposal 文件位置与 id 规则 | 已发布 Proposal 固定在 `spec/proposals/<id>.md`，id 匹配 `^[a-z][a-z0-9-]{2,62}$` | 所有 proposal_* 读取与提交 | 手动，无 hook | `proposal_contract.py:17`；`proposal_submit.py:24` | proposal-contract | 无 |
| 2 | v1/v2 身份标记 | HTML 注释单行标记 `spec-guard-proposal:v1 id=…` 或 `v2 id=… revision=sha256:…`，全文恰好一条 | 解析、Issue 正文校验 | 手动 | `proposal_contract.py:18-24,184-200` | proposal-contract | v1 仍被解析，但下游 `accepted()`、`build_preview` 对 v1 一律返回 `legacy-revision-required`（`proposal_promotion_proof.py:88-96`；`proposal_closeout.py:191-192`）。v1 解析只剩「识别出来再拒绝」，疑似历史包袱 |
| 3 | v2 内容绑定 revision | 把标记里的 64 位哈希置零后对整篇算 SHA-256，必须等于标记里的值，任何内容改动都使 revision 改变 | 解析 v2；`proposal_submit` 回算 | 手动 | `proposal_contract.py:202-213,263-264` | proposal-contract；proposal-label-acceptance（改成「新写必须 v2」） | 解决「评审后文档被悄悄改」问题。但对一个 solo 维护者流程，revision+Issue marker 双绑定是否必要，缺使用数据；`spec/proposals/` 仅 6 份 |
| 4 | Integration intent 段（v2 独有） | 6 字段表：Problem、In scope、Out of scope、Safety boundaries、Initial dependency assumptions、Acceptance intent，必须全填 | v2 解析 | 手动 | `proposal_contract.py:236-243` | proposal-contract | 强制六字段全填是文档仪式，与 Spec 的 Objective/Assumptions 重叠；与上游 `spec-driven-development` 的 spec 内容重复 |
| 5 | 严格文法：固定章节顺序、字段表、忽略围栏代码块 | 四（v2 为五）个顶级段必须按序且仅此几个；字段表重复/缺失/多余字段都拒绝；围栏内的标题、marker、表格不参与解析 | 解析 | 手动 | `proposal_contract.py:95-170` | proposal-contract | 极严格的文法让手写草稿很容易 invalid，所以后来才加 `proposal-submit` 命令去补全。是「过度严格→再加工具补洞」的链条 |
| 6 | 能力图基线段 | 记录 Remote、Default branch、Commit(40-64 hex)、Capability map 路径、Goal digest(12 hex)、Build order，外加「Module digests」表（每模块一行 12 位摘要） | 解析；`proposal_submit` 自动填 | 手动 | `proposal_contract.py:245-262,164-173` | proposal-contract；proposal-submit | 摘要全是机器值，人手算不了；整条机制是为了判「基线漂移」。每个模块一行摘要使文档随模块数线性变长（140 行） |
| 7 | Change 段（仅 `new-module`） | Type 只能 `new-module`；Module id、Responsibility、Depends on（逗号表或 `—`）、Build-order anchor（`after:<id>` 或 `end`） | 解析、晋级 | 手动 | `proposal_contract.py:264-282` | proposal-contract | 只支持「新增模块」一种变更；修改/删除模块不能走 Proposal，只能手改能力图。能力范围很窄却配了完整四步流程 |
| 8 | Tracker contract 段 | 声明 Proposal id、Identity label=`proposal`、Stage label namespace=`proposal-stage:`，必须与标记一致 | 解析 | 手动 | `proposal_contract.py:284-290` | proposal-contract | 三个值全是固定常量，写进文档只为校验「写对了」，信息量为零 |
| 9 | 对基线地图的校验 | 对调用方给定的地图字节核对 Goal digest、全部 Module digests、Build order；Change 的 module id 不得已存在；依赖必须在基线；锚点不得排在依赖之前 | 发布读取、提交 | 手动 | `proposal_contract.py:292-322` | proposal-contract | 无 |
| 10 | Issue 侧契约校验 | Issue 正文含且仅含一次完整标记；恰好一个 `proposal` 标签；恰好一个合法 `proposal-stage:*` 标签 | 读 tracker 时 | 手动 | `proposal_contract.py:324-335` | proposal-contract；proposal-tracker-read | 无 |
| 11 | 八个阶段标签 | draft、published、in-review、accepted、needs-revision、deferred、rejected、promoted | 标签校验、阶段映射 | 手动 | `proposal_contract.py:26-35` | proposal-contract | 八个阶段里只有 accepted 与 promoted 被代码用于判定，其余六个只是被映射为展示用的状态字符串（`proposal_review.py:11-20`），属于展示而非机制 |
| 12 | 与能力图解析/指纹共用实现 | 复用 `capability_map.py` 解析器与 `spec-digest.py` 指纹 | 全部 | — | `proposal_contract.py:7-14` | proposal-contract；phase-and-verification | 无（是不变量要求） |

### 1.2 Proposal 提交（`H/proposal_submit.py`，282 行；`C/proposal-submit.md`）

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 13 | 草稿补全 | 读本地草稿 `spec/proposals/<id>.md`，从远端默认分支快照算出基线段和 Module digests 整段替换，其余字节原样保留 | `/spec-guard:proposal-submit <id> <github\|gitlab>`；Codex 走 ops skill 的 proposal 节 | 手动；默认只预览 | `proposal_submit.py:75-112,197-262` | proposal-submit | 这是为了弥补功能点 5/6 的手算难度而加的。Spec 记录首版「13 键 JSON 生成整篇」被用户评审判为过度设计，改为本版（`spec/proposal-submit.md`），说明用户自己警惕过 |
| 14 | revision 回填 | 先置零算哈希，再写回标记并重新校验 | 提交 | 手动 | `proposal_submit.py:225-236` | proposal-submit | 无 |
| 15 | 路径=id 校验 | 草稿路径必须是 `spec/proposals/<id>.md` 且 id 与标记一致 | 提交 | 手动 | `proposal_submit.py:201-203` | proposal-submit | 无 |
| 16 | id 唯一与修订识别 | 扫描远端已有 Proposal 文件；另一文件已声明同 id 则拒绝；同路径已发布则视为「修订」 | 提交 | 手动 | `proposal_submit.py:114-131,242-249` | proposal-submit | 无 |
| 17 | 预览 diff 与 `--confirm` 原子回写 | 无 `--confirm` 只打印 unified diff、revision、基线提交；加 `--confirm` 才原子重写草稿文件，不动别的 | 提交 | 默认只读预览 | `proposal_submit.py:184-195,251-262` | proposal-submit | 无 |
| 18 | 「下一步」清单（只打印不执行） | 打印合并 PR、开 Issue 的 `gh issue create`/`glab issue create` 命令、建标签命令、去审查、改标签接受 | 提交输出 | 手动 | `proposal_submit.py:133-165` | proposal-submit | 流程里「开 Issue、贴标签」全靠人手工做，插件只打印命令；而收尾那步却由插件自动写评论/改标签/关 Issue。两端的自动化边界不一致 |
| 19 | Local 后端的下一步 | `platform=local` 时不给 CLI，改为指引经 `/spec-guard:ticket` 建事项，标明首行 marker 和两个 tag | 提交 | 手动 | `proposal_submit.py:135-143` | proposal-closeout（第三后端加入时） | Proposal 为「无 GitHub/GitLab Issue 的项目」专门接了本地账本后端。需确认是否真有此类用户；对「有 Git 远端、没有 Issue」这种组合较窄 |
| 20 | 摘要提取为 Issue 正文 | 取草稿 Summary 作为 Issue 正文，首行放 marker | 提交 | 手动 | `proposal_submit.py:168-182` | proposal-submit | 无 |

### 1.3 发布读取（`H/proposal_publication.py`，336 行；`R/proposal-publication.md`）

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 21 | 远端默认分支固定快照 | 在临时 bare 仓库里只抓远端默认分支一次，钉住观察到的 tip；绝不读本地 worktree 的 Proposal 或能力图 | review、预检、证明、提交、收尾都经它 | 手动 | `proposal_publication.py:135-216` | proposal-publication | 解决「多 worktree 下本地文件互相矛盾」，与主线一致。代价是没有远端 Git 默认分支的项目完全不能用 Proposal（`R/proposal-closeout.md` 明说） |
| 22 | 探测重试 3 次 + 退避 | `ls-remote` 读不到或 fetch 失败最多重试 3 次，间隔 0.2 秒 | 快照 | 内置 | `proposal_publication.py:14-16,135-216` | proposal-publication；proposal-closeout（加重试） | 来自一次收尾中偶发网络失败（`R/proposal-closeout.md`）；合理，但重试逻辑只是网络健壮性，不是需求 |
| 23 | tip 移动不重试 | 观察与抓取之间 tip 变了，报 `snapshot-tip-moved`，不在原地重试（钉 tip 是保证） | 快照 | 内置 | `proposal_publication.py:21,26-31` | proposal-publication | 无 |
| 24 | 稳定的探测诊断码 | `snapshot-head-unavailable`、`snapshot-fetch-failed`、`snapshot-tip-moved`、`snapshot-temp-repo-failed` | 所有读取的输出 | 内置 | `proposal_publication.py:26-47` | proposal-publication；promotion-proof-diagnostics | 无 |
| 25 | 单个 Proposal 读取 `read_published` | 返回 `published/absent/invalid/unknown` 四态；校验远端名、默认分支名与基线一致，基线提交必须是默认分支祖先，且基线地图可读 | `/proposal-review`、收尾预览 | 手动 | `proposal_publication.py:222-258` | proposal-publication | 无 |
| 26 | Proposal 池读取 `read_published_pool` | 读 `spec/proposals/*.md` 全部，重复 id 报 invalid | 预检、证明 | 手动 | `proposal_publication.py:260-322` | proposal-publication | 无 |
| 27 | 池大小上限 100 | 超过 100 份返回 unknown | 池读取 | 内置 | `proposal_publication.py:14,289-292` | proposal-publication | 上限没有来由说明；对一个只有 6 份的仓库是预防性限制 |
| 28 | 已晋级且过期的 Proposal 排除出池 | 模块已在远端地图里、却基线校验失败的 Proposal 记入 `skipped` 而不让整池失效 | 池读取 | 内置 | `proposal_publication.py:34-38,303-313` | proposal-pool-isolation | 起因是仓库迁移后历史 Proposal 基线提交不存在导致全池 invalid。这是「基线必须在默认分支祖先」设计的次生复杂度；若 Proposal 晋级后即视为归档，则无需此例外 |
| 29 | 发布结果 JSON 脱敏 | 不含远端 URL、临时路径、文档/地图内容 | 输出 | 内置 | `proposal_publication.py:49-86` | proposal-publication；remote-credential-redaction | 无 |

### 1.4 Tracker 只读核验（`H/proposal_tracker_read.py`，280 行；`R/proposal-tracker-read.md`）

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 30 | GitHub 读取 | `gh issue list --state all --limit 1000` 读候选，本地逐行匹配 marker | review、预检、证明 | 手动 | `proposal_tracker_read.py:228-250` | proposal-tracker-read | 无 |
| 31 | GitLab 读取 | `glab api projects/<id>/issues?state=all&per_page=100&page=n`，最多 10 页 | 同上 | 手动 | `proposal_tracker_read.py:11-12,251-267` | proposal-tracker-read；tracker-backend-default | 无 |
| 32 | 不依赖服务端搜索 | 全量拉取后本地逐行匹配 marker（GitLab 的 `search=` 匹配不到 HTML 注释，2026-09-28 实测） | 读取 | 内置 | `proposal_tracker_read.py:150-157`；`R/proposal-tracker-read.md` | proposal-tracker-read | 每次要拉全量 Issue（至多 1000 条）才能找到一条 Proposal，随仓库 Issue 数增长而变慢；设计上用 marker 当身份，导致放弃了索引能力 |
| 33 | Local 账本作为第三后端 | 不在本模块传输，由 `proposal_closeout_local` 给候选集再交纯函数核验，必须带 `includeClosed` | 收尾 | 手动 | `proposal_tracker_read.py:15,159-210`；`R/proposal-tracker-read.md` | proposal-closeout | 无 |
| 34 | 已关闭事项与 closed 事实 | 返回 `closed`；响应不带开闭信息则 unknown，不默认当 open | 读取 | 内置 | `proposal_tracker_read.py:18-22,66-87` | proposal-tracker-read；proposal-closeout | 无 |
| 35 | 稳定诊断码 | `tracker-marker-ambiguous`、`tracker-marker-foreign-container`、`tracker-legacy-marker`、`tracker-contract-invalid`、`tracker-read-unavailable` | 读取 | 内置 | `proposal_tracker_read.py:24-27` | proposal-tracker-read | 无 |
| 36 | 旧 bridge marker 检测 | 正文含 `spec-guard-sync:v2` 旧标记时报 `tracker-legacy-marker` | 读取 | 内置 | `proposal_tracker_read.py:154-157` | proposal-tracker-read | 为已退役的 spec-github-bridge 留的检测，退役说明已保留历史；检测本身是退役残余，可再评估是否还有人持有旧 marker 的 Issue |
| 37 | 读取结果脱敏 | 不含 Issue 正文、评论、marker、URL、token、原始 CLI 错误 | 输出 | 内置 | `proposal_tracker_read.py:44-56` | proposal-tracker-read | 无 |

### 1.5 审查（`H/proposal_review.py`，191 行；`C/proposal-review.md`）

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 38 | 新鲜度/阶段汇总 | 合并发布结果、tracker 结果、当前远端地图，给出 `awaiting-review/in-review/accepted/needs-revision/deferred/rejected/promoted-claim/stale/in-map/absent/invalid/unknown` | `/spec-guard:proposal-review`；CLI `proposal_review.py` | 手动，只读 | `proposal_review.py:85-166` | proposal-review | 无 |
| 39 | stale 三种判据 | 目标指纹或既有模块行变了（`proposal-baseline-drifted`）、依赖不在图里（`proposal-dependency-missing`）、锚点失效或排在依赖前（`proposal-anchor-drifted`）；追加不相关模块不算 stale | 审查 | 内置 | `proposal_review.py:126-157` | proposal-review；`docs/decisions/2026-09-28-single-capability-map.md` | 无 |
| 40 | `in-map` 状态 | 模块已在远端地图中报 `in-map` 而非 stale，不区分是自己晋级还是重名，交给证明 | 审查 | 内置 | `proposal_review.py:136-143` | proposal-review-in-map | 无 |
| 41 | 展示 `moduleId` | 所有读到 Proposal 的结果带要加入的模块 id（与 proposal id 可不同） | 审查、预检、证明输出 | 内置 | `proposal_review.py:23-36` | review-module-id | 无 |
| 42 | 阶段标签映射为状态 | 把 8 个标签映射为 7 个展示状态；`accepted` 只是被观察到的标签，不是授权 | 审查 | 内置 | `proposal_review.py:11-20` | proposal-review；proposal-label-acceptance | 无 |
| 43 | 分层 blocked 诊断 | 发布/tracker 层非成功时返回 `publication-<state>`/`tracker-<state>`，不吞掉原因 | 审查 | 内置 | `proposal_review.py:59-66,101-112` | proposal-review | 无 |
| 44 | 「接受」只看标签+新鲜审查 | 2026-09-29 起删除主链策略文件、验收记录、`integration/mainline` 分支、两个 mainline 命令和边界提示 | 接受判定 | 内置 | `proposal_promotion_proof.py:88-96`；`spec/proposal-label-acceptance.md` | proposal-label-acceptance；retired-module-separation | 这条本身是「做减法」。要核对的是：Proposal 的「接受」现在等于任何有权给 Issue 贴标签的人贴一个标签，不再有授权/身份校验，评审的「人」属性靠约定而非机制。（目的是灵活，属取舍，不算疑点，但值得用户确认接受） |

### 1.6 晋级预检与晋级证明（`H/proposal_promotion_proof.py`，355 行；`C/proposal-promotion-preflight.md`、`C/proposal-promotion-proof.md`）

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 45 | 晋级预检 `preflight` | 重读池和 Issue 阶段，新鲜审查；阶段为 accepted 且新鲜时返回 `ready` + `baseCommit`，供人建晋级分支 | `/spec-guard:proposal-promotion-preflight` | 手动，只读 | `proposal_promotion_proof.py:177-217` | proposal-promotion-proof；proposal-label-acceptance | `C/proposal-promotion-preflight.md` 与 `docs/commands.md` 自己说明 `add-module --proposal` 已内置同一预检，「通常不必」单独跑，命令是冗余入口 |
| 46 | `promotion_base` | 供 `add-module --proposal` 内部调用的同一预检函数 | add-module | 内部 | `proposal_promotion_proof.py:182-193` | proposal-add-module-promotion | 无 |
| 47 | 接受门禁 `accepted()` | 只接受 v2；v1 返回 `legacy-revision-required` | 预检、收尾 | 内置 | `proposal_promotion_proof.py:88-96` | proposal-label-acceptance | 同功能点 2 |
| 48 | 晋级证明 `prove` | 从 Proposal 基线提交沿远端默认分支 first-parent 走，找到第一个把模块加入地图的提交 C，P 为 C 的第一父；通过则 `proved` 带 `reviewCommit=P`、`promotionCommit=C` | `/spec-guard:proposal-promotion-proof`；`--prove` | 手动，只读 | `proposal_promotion_proof.py:219-300` | proposal-promotion-proof；proposal-label-acceptance | 证明的是「模块行出现在地图里」，而不证明模块 Spec/Plan 存在或模块交付（`R/proposal-closeout.md` 自己强调）。证明价值主要是防止「错行/夹带」 |
| 49 | 证明 invalid 条件 | P 已含该模块；C 的行/依赖/位置与 Proposal 不符；P→C 之间改了其他模块行或顺序 | 证明 | 内置 | `proposal_promotion_proof.py:124-171` | proposal-promotion-proof；promotion-proof-diagnostics | 把「PR 不得夹带别的能力图修改」固化为机器判据，限制较死：晋级 PR 若顺手改了另一个模块的职责描述就被拒。与「保持灵活」方向有张力 |
| 50 | 在 P 上判新鲜度 | 新鲜度（基线未漂移、模块未存在、依赖在、锚点有效）在 P 的地图上判，非当前地图 | 证明 | 内置 | `proposal_promotion_proof.py:219-300` | proposal-promotion-proof | 无 |
| 51 | `not-promoted` | 尚无提交含该模块时返回，提示合并后重跑 | 证明 | 内置 | `proposal_promotion_proof.py:219-300` | proposal-promotion-proof | 无 |
| 52 | `prove_from_remote`/`--prove` | 先从同一次新快照重建池和 Issue 阶段，再运行 `prove` | `--prove` | 手动 | `proposal_promotion_proof.py:307-328,339` | proposal-promotion-proof | 无 |
| 53 | 晋级提交可改其他路径 | 允许 PR 合并提交带别的文件，不要求同时含模块 Spec/Plan | 证明 | 内置 | `R/proposal-promotion-proof.md` | proposal-label-acceptance | 无 |
| 54 | `closeoutPending` | 证明通过后输出事项是否仍开着，提示去收尾 | 证明输出 | 内置 | `proposal_promotion_proof.py:81-82,326` | proposal-closeout-reminder | 无 |
| 55 | `skippedProposals` 输出 | 池里被排除的 Proposal 列出原因码；被排除者查询 id 视同缺失 | 预检、证明 | 内置 | `proposal_promotion_proof.py:64-86` | proposal-pool-isolation | 无 |
| 56 | 诊断透传表 | 底层给了稳定码就透传，没有才折叠成 `promotion-<state>` | 预检、证明输出 | 内置 | `R/proposal-promotion-proof.md` 表；`proposal_promotion_proof.py:17,49-86` | promotion-proof-diagnostics | 无 |
| 57 | 仅在 add-module 之后作一次预览 | 预检不创建分支/提交/PR/标签/任务 | 全部 | 内置 | `C/proposal-promotion-preflight.md` | proposal-promotion-proof | 无 |

### 1.7 收尾（`H/proposal_closeout.py` 708 行 + `_github.py` 108 + `_gitlab.py` 102 + `_local.py` 181；`C/proposal-closeout.md`；`R/proposal-closeout.md` 190 行）

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 58 | 纯状态机 `closeout_decision` | 顺序固定：已关闭 → proof 读不到 → proof 不成立 → 阶段不合；签名刻意不含 project/root/provider，禁止读模块 stage | 预览 | 内置 | `proposal_closeout.py:53-80` | proposal-closeout | 无 |
| 59 | unknown 与 not-eligible 分开报 | 探测读不到是 `unknown`（重试），读到不成立才 `not-eligible` | 预览与复核 | 内置 | `proposal_closeout.py:53-80`；`R/proposal-closeout.md` | proposal-closeout | 无（落实了「探测失败≠结论」不变量） |
| 60 | 三后端共用同一七方法适配器协议 | `target_facts/list_issues/get_issue/list_comments/create_comment/set_stage/set_closed` | 收尾 | 内置 | `proposal_closeout.py:549-560`；各 adapter | proposal-closeout | 为三个后端各写一份传输（见 61–63），而插件另有 `hosted_ticket_provider`/`local_ticket_*` 做类似读写，存在传输层重复风险。`proposal_closeout_github.py` 复用了 `hosted_ticket_provider`，所以重复被部分控制 |
| 61 | GitHub 适配器 | `gh api --hostname`，POST 标签再 DELETE 旧标签，PATCH 关闭 | `--backend github` | 手动 | `proposal_closeout_github.py:23-108` | proposal-closeout | 无 |
| 62 | GitLab 适配器 | `glab api`，单次 PUT 带 add_labels/remove_labels，`state_event=close` | `--backend gitlab` | 手动 | `proposal_closeout_gitlab.py:23-102` | proposal-closeout；gitlab-tracker-support（归档 initiative） | 无 |
| 63 | Local（Epiq）适配器 | 只调日常 Epiq 工具（含 `includeClosed`、`tagId`），绝不调用 `epiq_sync`；报告 `origin` 是否会公开该账本 | `--backend local` | 手动 | `proposal_closeout_local.py:36-181,124-137` | proposal-closeout；runtime-state-layout | 与 local-ticket-ledger 深耦合；账本本身默认关闭。「无 Issue 的项目走 Proposal」这一用户群需确认存在 |
| 64 | 后端与目标解析 | 显式 `--backend/--target` 或按项目默认值（`/spec-guard:tracker-default`）解析，预览标注 source；解析不出报 `target-unselected` | 预览、扫描 | 手动 | `proposal_closeout.py:561-591`；`C/proposal-closeout.md` | tracker-backend-default；proposal-closeout | 无 |
| 65 | 预览（只读） | 现取远端 Proposal → 按 marker 在精确目标定位恰好一条事项 → 读阶段/开闭 → 同次重跑 proof；只有 `proved` 才出预览，含完整 record 与动作清单；写到仓库之外的 `--output` 路径 | `proposal_closeout.py preview` | 手动 | `proposal_closeout.py:169-236,602-608` | proposal-closeout | 无 |
| 66 | proof 在预览内现取 | 不接受调用方传入的旧 proof；tracker reader 与 proof 共用同一份候选集 | 预览 | 内置 | `proposal_closeout.py:128-146,169-236` | proposal-closeout | 无 |
| 67 | 事项内容 digest | 对正文+标签集算 digest，预览后被人改过则拒绝 | 预览、复核 | 内置 | `proposal_closeout.py:279-290` | proposal-closeout | 无 |
| 68 | 收尾记录与专用 marker | 评论末行 `spec-guard-proposal-closeout:v1 <id>/<revision 前 12 位>`；正文固定声明「设计决定已执行，不代表模块已交付」；带该 marker 但正文不符判 `conflict`（防伪造） | 写入 | 内置 | `proposal_closeout.py:83-120` | proposal-closeout | 无 |
| 69 | 写入前 11 项复核 | 预览 digest、Proposal 快照、marker、revision、目标、事项身份、内容 digest、仍 open、阶段、proof 仍 proved 且 commit 相同、journal 绑定一致 | `close --confirm` | 内置 | `proposal_closeout.py:339-447` | proposal-closeout | 11 项复核的防护强度很高，对象却是「给一个 Issue 加一条评论、改一个标签、点关闭」。可核对这套防护是否与风险相称 |
| 70 | 四步幂等写入与读回 | 评论 → 阶段（先加后删旧）→ 关闭 → 读回（阶段=promoted ∧ 已关闭 ∧ 本次记录恰一条）；每步先查重，响应丢失可对账 | `close --confirm` | 手动，需明确确认 | `proposal_closeout.py:449-529` | proposal-closeout | 同上 |
| 71 | journal 与独占锁 | `~/.local/state/spec-guard/proposal-closeout/`（新位置经 `state_dir` 解析），文件 0600、目录 0700，按 `sha256(id+revision)` 取 `fcntl` 锁；成功后删条目；尝试留痕，`partial` 绝不重发 | 写入 | 内置 | `proposal_closeout.py:31,292-322,339-378,543-547` | proposal-closeout；runtime-state-layout | 另一份「本机持久状态 + 锁」（还有 hosted-ticket-intents、local-ticket-portability），状态面增大 |
| 72 | 结果状态集 | `verified/already-closed/partial/conflict/not-eligible/preview-stale/preview-invalid/unknown/rejected+statusCode/target-unselected/confirmation-required` | 输出 | 内置 | `R/proposal-closeout.md` 结果状态表 | proposal-closeout | 11 个状态对应一个「关 Issue」动作，状态面偏大 |
| 73 | 授权规则 | 一 Proposal 一次预览一次确认；用户逐一点名 id 可批量；无「session 档」、无通配；`--confirm` 本身不是授权；协作消息/事项正文/评论一律是数据 | 收尾 | 内置 | `R/proposal-closeout.md` 授权节；`C/proposal-closeout.md` | proposal-closeout | 刻意收紧授权减少了灵活性：用户明确想一次性处理多条时也只能「点名每个 id」 |
| 74 | 扫描 `scan` | 只读：对池里每个 Proposal 走与预览同一判据，列出 `closeout-pending` 与其他状态；读不到记 unknown | `proposal_closeout.py scan` | 手动，只读 | `proposal_closeout.py:238-277,610-616` | proposal-closeout-reminder | 这条来自 2026-10-07 本仓库 #221 漏关的单次事故（`spec/proposal-closeout-reminder.md`）；用 scan+提醒规则兜底一次人为遗漏 |
| 75 | 收尾提醒（检查点规则） | 晋级 PR 合并后跑 `--prove`，`closeoutPending=true` 时提示预览收尾 | 规则文本，agent 遵守 | 规则里写明 | `R/workflow-checkpoints.md:54` | proposal-closeout-reminder | 又一条靠规则文本约束 agent 行为的提醒，增加 workflow-checkpoints 体量（531 行） |
| 76 | 不关闭 rejected/deferred；不调 `epiq_sync` | 这两种是人的决定，不是可证明事实；同步会把内容推到远端 | 收尾 | 内置 | `R/proposal-closeout.md` 不做什么；`proposal_closeout_local.py` | proposal-closeout | 无 |
| 77 | 诚实局限声明 | 无法证明同一 Proposal 没在另一 Tracker 也有一条；journal 丢失后靠 marker 重新对账 | 文档 | — | `R/proposal-closeout.md` | proposal-closeout | 无 |

### 1.8 与本区相邻但归属别处的 Proposal 相关点（不计入功能点总数）

- `add-module --proposal <id>`：晋级写入，在 `module-insert.py`，归 module-insert / proposal-add-module-promotion。
- `retired-module-separation`：把已退役的 `proposal-mainline-review`、`proposal-boundary-guidance` 从图里移出并留历史 Spec，属整理性模块。
- `git-fixture-template`：Proposal 测试的 git 夹具复用，属测试加速。

---

## 二、文档治理（`H/documentation_baseline.py` 158 行、`documentation_impact.py` 188 行、`documentation_verification.py` 126 行；`C/documentation-*.md`；`R/documentation-*.md`）

整体事实：三个脚本只在 `C/documentation-*.md` 与 `S/` 的 documentation 节被引用，没有任何 hook 或 verify-artifacts 调用它们；本仓库自己没有启用基线文件。

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 78 | 文档基线文件 | 项目根 `docs/DOCUMENTATION-BASELINE.md` 内恰好一张四列表（Concern/Authority/Status/Rationale），是索引不是内容副本 | `/spec-guard:documentation-baseline` | 文件不存在=未启用，静默 | `documentation_baseline.py:65-125`；`R/documentation-baseline.md` | documentation-baseline | 解决「写 Spec 前不知哪些文档是上游约束」。但上游 agent-skills 已有 `documentation-and-adrs` skill，且本插件检查点规则的「文档建议」本身也在做同类提示（见 #98）；三处并存 |
| 79 | 三项通用关注点 | `product-direction`、`architecture`、`developer-entry` 必须各声明一次 | 基线解析 | 内置 | `documentation_baseline.py:7-9,116-119` | documentation-baseline | 对已有文档的项目要求「必答三项」，没有文档的项目只能标 pending，仍有填表负担 |
| 80 | 条件性关注点 | `consumer-guide`、`integration-contract`、`adr`、`operations`、`compliance` 可选声明 | 基线 | 内置 | `R/documentation-baseline.md` | documentation-baseline | 无 |
| 81 | 五种状态 | target / in-progress / verified / pending / not-applicable | 基线 | 内置 | `documentation_baseline.py:10-12` | documentation-baseline | 状态是人填的断言，插件明确不核验（不看 diff/时间戳），所以 `verified` 的含义完全依赖人 |
| 82 | Authority 规则 | 路径或外部 URL；`not-applicable` 必须为空/`-`/`—`，其余必须有来源；Rationale 必填 | 基线解析 | 内置 | `documentation_baseline.py:60-63,97-122` | documentation-baseline | 无 |
| 83 | 基线解析器严格化 | 唯一表、分隔行、行完整、符号链接拒绝、围栏忽略 | 解析 | 内置 | `documentation_baseline.py:33-93` | documentation-baseline | 无 |
| 84 | 基线创建/更新流程 | 命令检测 absent 时询问并给最小草稿，用户确认后才创建；引用既有文档路径，不迁移不覆盖 | `/spec-guard:documentation-baseline` | 手动，确认才写 | `C/documentation-baseline.md` | documentation-baseline | 无 |
| 85 | 模块文档影响表（Spec） | 在 `spec/<id>.md` 恰好一张 `Documentation impact` 表：Concern/Decision/Rationale；基线里非 not-applicable 的关注点都必须有决定 | `/spec-guard:documentation-impact <模块>` | 仅基线有效时 | `documentation_impact.py:87-110` | documentation-impact | 每个模块 Spec 都要为每个关注点（至少 3 项）写决定，按 140 模块计成本不小；而本仓库未启用，没有自用证据 |
| 86 | 五种影响决定 | follow / update / create / pending / not-applicable | 影响表 | 内置 | `documentation_impact.py:10` | documentation-impact | 无 |
| 87 | 项目级 vs 模块级 n/a | 项目 n/a 的关注点不得出现在模块表；模块 n/a 表示有此关注点但本模块不涉及 | 影响解析 | 内置 | `documentation_impact.py:93-96` | documentation-impact | 无 |
| 88 | 计划交付表（Plan） | 决定为 update/create 时，Plan 必须有 `Documentation delivery` 表；update 的目标必须等于基线 Authority | 影响解析 | 内置 | `documentation_impact.py:111-137` | documentation-impact | 无 |
| 89 | Spec 阶段预期报错 | Spec 写完、Plan 未写时影响检查报 `module plan must be a regular file`，被视为预期（不是故障） | 影响检查 | 文档说明 | `R/documentation-impact.md` 末段 | doc-suggestion-at-handoff（第 2 点起因） | 「预期的报错」被写进文档来防止误读为故障，说明工具的错误语义不直观，使用者曾误判 |
| 90 | 影响解析只读基线/Spec/Plan | 不读代码、diff、时间戳、权威文档正文 | 影响 | 内置 | `documentation_impact.py:140-155` | documentation-impact | 无 |
| 91 | 交付 outcome 表 | Plan 可写 `Documentation outcome` 表（Concern/Outcome/Evidence/Rationale），outcome 为 delivered/deferred/pending，delivered 需用户给证据指针 | `/spec-guard:documentation-verification <模块>` | 仅基线+影响有效时 | `documentation_verification.py:37-71` | documentation-verification | 无 |
| 92 | 四种核验状态 | absent / invalid / attention / ready | 核验输出 | 内置 | `documentation_verification.py:72-97` | documentation-verification | `ready` 只表示「声明层没有未收口项」，文档里反复强调「不得解释为文档正确/已发布/代码符合」。一个只核对「自己写的表格填完了没」的状态，价值有限 |
| 93 | attention 只提醒不阻断 | pending 决定、缺 outcome、deferred/pending 都归 attention；不阻断开发/Issue/PR | 核验 | 内置 | `documentation_verification.py:85-96` | documentation-verification | 提醒无处触发（没有 hook/检查点自动调用），实际要靠人想起来跑命令 |
| 94 | 命令与 Codex 路由 | 三个 Claude 命令；Codex 走 ops skill 的 documentation 节，三条 python 命令 | 命令/skill | 手动 | `C/documentation-*.md`；`S/:335-345` | documentation-baseline；-impact；-verification | 无 |
| 95 | 文档建议的「基线类别」引用 | 检查点规则的文档建议第 2 步说「项目建了文档基线就以基线为准」 | 规则文本 | 规则里 | `R/workflow-checkpoints.md:241-243` | doc-suggestion-at-handoff | 文档建议规则才是主流程里真正会触发的文档提示，且不依赖基线；文档治理三件套与它是两套并行体系 |
| 96 | 验收表里单列文档改动 | 验收清单把文档类改动单列一张表（含基线登记的文档） | 规则文本 | 规则里 | `R/workflow-checkpoints.md:76` | changed-files-at-acceptance | 无 |

文档治理的整体疑点（供用户核对）：整套「基线 → 影响 → 核验」的目标用户是「文档本身也要交付、要审查的项目」（`docs/optional-features.md`）。本仓库自己没启用；三个脚本不被任何自动路径调用；`documentation_baseline.py` 在 `grep` 中没有任何 spec 文件引用（只有模块 Spec）。需求侧缺使用证据。

---

## 三、能力历史（`H/capability-history.py` 514 行、`history-migration.py` 106 行、`verify-history.sh`；`C/history-integrity.md`；`S/` history 节）

整体事实：账本的生命周期事件（暂停、恢复、完成等）命令已退役，插件内没有任何路径自动写账本（grep 确认：只有 `create`、`correct`、`history-migration import` 会写）。`docs/design.md` 文件布局写「谁写：只有一次性的历史迁移」。账本现在只用来保存「全插件一张能力图」改制之前归档的 initiative（本仓库 12 个）。

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 97 | 账本格式 | `spec/CAPABILITY-HISTORY.json`，schemaVersion 1；事件 created/paused/resumed/completed/abandoned/superseded，状态转移受限；每个 checkpoint 带地图/Spec/Plan/state 快照与 sha256 | 数据结构 | 文件存在才有效 | `capability-history.py:12-24,59-127` | capability-history | 生命周期事件（pause/resume…）的命令已退役，但格式与校验仍保留这套状态机，是遗留设计 |
| 98 | `validate`/`status` | 校验账本结构；`status` 取某 initiative 当前状态 | CLI | 手动 | `capability-history.py:191-210,462-514` | capability-history | 无 |
| 99 | `verify`（`verify-history.sh`） | 核对每个登记文件的 sha256，并拒绝 `spec/history`、`tasks/history`、`.agent/history` 下未登记的孤儿目录；无账本报「未验证」退 0 | Codex ops skill history 节 | 手动 | `capability-history.py:250-277`；`verify-history.sh:1-31` | capability-history（history-verification 整合） | 无 |
| 100 | `audit` | 独立于 verify，报告无法由证据确立的字段；输出 JSON，`readOnly:true` | `/spec-guard:history-integrity audit`；ops skill | 手动，只读 | `capability-history.py:313-415` | capability-history；audit-remediation | 审计规则会对**每一个**带 `at` 的事件报 `timestamp-unverified`、对每个 status 不为 unknown 的模块报 `status-unsupported`（`:337-339,408-411`），即几乎所有历史记录天然产生「未解决发现」，需要 `correct` 逐条补正；噪声占比高，用户收益不明显 |
| 101 | 审计发现代码 | `timestamp-unverified`、`map-missing`、`map-digest-differs`、`map-unparseable`、`module-missing-from-map`、`responsibility-mismatch`、`dependency-mismatch`、`status-unsupported` | audit 输出 | 内置 | `capability-history.py:337-411` | capability-history | 同上 |
| 102 | resolution 标记 | 每条发现带 `resolution: corrected\|unresolved`，summary 给 `unresolvedFindings/unresolvedByCode` | audit 输出 | 内置 | `capability-history.py:395-414` | capability-history | 无 |
| 103 | `correct --confirm` | 向账本追加 `history-correction`，不改写原事件；需审计报告哈希、原值/修正值、initiativeId/eventIndex/checkpointId 完全匹配；拒绝把 unknown 升级成 completed | `/spec-guard:history-integrity correct`；ops skill | 手动，需明确确认 | `capability-history.py:128-190,426-460` | capability-history | 一整套「追加式补正」机制，只为让旧归档的 audit 不再报未解决。很可能没有人会真去补 |
| 104 | `create` | 追加新 initiative 到账本 | 迁移导入内部使用 | 内部 | `capability-history.py:236-244` | capability-history | 无 |
| 105 | `artifact-dirs` | 列出账本引用的所有历史目录 | verify-history.sh 内部使用 | 内部 | `capability-history.py:278-304` | capability-history | 无 |
| 106 | 原子写入 | 账本写入走临时文件+原子替换 | create/correct | 内置 | `capability-history.py:216-234` | capability-history | 无 |
| 107 | 迁移预览 `history-migration preview` | 只读列出旧项目（`.agent/state.json`、旧地图、`SPEC-*.md`）可导入的证据与冲突 | ops skill history 节 | 手动，只读 | `history-migration.py:38-53` | capability-history | 无 |
| 108 | 迁移导入 `import --confirm` | 把旧地图快照进 `spec/history/<id>/19700101T000000Z-0001/`，建账本条目；任何冲突拒绝，失败回滚自己写的文件 | `history-migration.py import --confirm` | 手动，确认才写 | `history-migration.py:56-101` | capability-history | 用固定的伪时间戳 `19700101…`、`at: "imported"`，导入出的记录天然被 audit 判为 `timestamp-unverified`。服务对象是「从旧版 spec-guard 升级的项目」，v0.14 之前的用户群规模未知 |
| 109 | 命令与 Codex 路由 | Claude 只暴露 audit 与 correct；Codex ops skill 暴露 verify、audit、迁移 preview | 命令/skill | 手动 | `C/history-integrity.md`；`S/:416-441` | capability-history | Claude 命令不含 verify 与迁移，两宿主入口不对称（`evals/test-codex-skill-teardown-history.sh` 专门防止 Codex 缺 correct） |
| 110 | teardown 保留历史 | 卸载约定时保留 spec/history 等 | teardown | 内置 | `docs/design.md` 文件布局「永不删除」 | local-convention | 无 |

---

## 四、成本与返工报告（`H/module_cost_report.py` 677 行；`C/cost-report.md`；`S/` cost report 节）

| # | 功能点 | 做什么 | 触发/入口 | 默认 | 关键位置 | 能力图模块 | 需求疑点 |
|---|---|---|---|---|---|---|---|
| 111 | 命令入口 | `module_cost_report.py --project … <模块…> [--prices f] [--json]`；只读，不是 hook | `/spec-guard:cost-report <模块>`；Codex ops skill | 手动，只读 | `module_cost_report.py:635-677` | module-cost-report | 目的是回答「`/build` 派活给子代理是否更省」（`spec/module-cost-report.md`），而 `build-task-dispatch` 是默认关闭的实验性规则，全局记录显示实测并未证明派活更省（2026-10-06）。报告这块「有没有人用」依赖一个默认关闭的特性 |
| 112 | task 时间窗切分 | 用 `tasks/<模块>/todo.md` 的 git 历史，按各项被勾上的作者时间切窗；起点=上一项完成时间或 todo 首次提交 | 报告 | 内置 | `module_cost_report.py:67-130` | module-cost-report | 无 |
| 113 | 同窗不重复计数 | 同一时刻完成的项与未勾项共享一个窗，归第一项，其余标 `shared_with` | 报告 | 内置 | `module_cost_report.py:119-129` | module-cost-report | 无 |
| 114 | 勾选后改名的位置兜底 | 按行位置推断完成时间并标注 | 报告 | 内置 | `module_cost_report.py:107-112` | module-cost-report | 无 |
| 115 | 无法归属（退出码 2） | todo 不存在/无提交历史/不是 git 仓库时报「无法归属」，不当作用量 0 | 报告 | 内置 | `module_cost_report.py:23-26,50-56` | module-cost-report | 无 |
| 116 | 读 Claude 会话记录 | 离线读 `~/.claude/projects/<编码目录>` 下 transcript，含子代理文件（以 toolUseId 关联），只取 token 用量、时间、工具名，不取内容 | 报告 | 内置 | `module_cost_report.py:133-280` | module-cost-report | 依赖宿主私有 transcript 格式；宿主格式变化即失效，维护成本不确定（有 `self_report.py` 同样读 transcript，见维护者工具） |
| 117 | 读 Codex rollout | 读 `~/.codex` 的 rollout，主线程与子线程关联，guardian 线程单列 | 报告 | 内置 | `module_cost_report.py:282-385` | module-cost-report | 同上，且依赖 Codex 私有格式 |
| 118 | token 类别 | Claude：input、cache_write_5m/1h、cache_read、output；Codex：input、cache_read、cache_write、output（reasoning 仅提示） | 报告 | 内置 | `module_cost_report.py:133,201-212,282-297` | module-cost-report | 无 |
| 119 | 按模型/类别汇总 | 每 task 主代理、子代理、guardian 三类 | 报告 | 内置 | `module_cost_report.py:387-448` | module-cost-report | 无 |
| 120 | 派活次数 | 统计主代理 `Agent`/`Task` 工具调用 | 报告 | 内置 | `module_cost_report.py:134,413-423` | module-cost-report；build-task-dispatch | 无 |
| 121 | 重派（redispatches） | `max(派活-1, 0)` | 报告 | 内置 | `module_cost_report.py:443` | module-cost-report | 把「同一 task 内第二次及以后的派活」都算重派，粗略推断返工 |
| 122 | 收回（reclaims） | 被 hook 拒绝的派活不算派活；拒绝文本含 `第二次失败后的收回` 时记一次收回 | 报告 | 内置 | `module_cost_report.py:136-137,414-419` | module-cost-report | 靠匹配 tier-guard 拒绝文案的中文字符串识别，两插件之间的隐式文本契约，一边改字另一边静默失效；也只覆盖 Claude |
| 123 | 交回后改（edits_after_handback） | 最后一次交回之后、task 结束之前，主代理用编辑工具/apply_patch 改的不同文件数（排除 todo.md） | 报告 | 内置 | `module_cost_report.py:135,138,435-442` | module-cost-report | shell 命令改文件不计入，文档已声明；是一个粗信号 |
| 124 | 覆盖率 | `已记录子代理数/派活数`，宿主没留下记录的派活单列 | 报告 | 内置 | `module_cost_report.py:444-446` | module-cost-report | 无 |
| 125 | 主会话轮次与缓存读 | 统计时间窗内主会话产生用量的消息数，以及缓存读 token | 报告 | 内置 | `module_cost_report.py:398-412` | module-cost-report | 无 |
| 126 | 模块完成后的收尾 | 最后一次勾选到该会话下一次用户发言之间的用量，另算「合计（含收尾）」 | 报告 | 内置 | `module_cost_report.py:450-478` | module-cost-report | 无 |
| 127 | 价格文件折算 | `--prices` JSON；不给只输出 token；缺价标「未定价」；插件不内置价格 | 报告 | 默认只出 token | `module_cost_report.py:491-526` | module-cost-report | 无 |
| 128 | 多模块对照 | 多个模块时给「有派活/没派活」的 task 平均 token（和金额），声明不得下因果结论 | 报告 | 内置 | `module_cost_report.py:531-549,625-632` | module-cost-report | 报告里自带「不要据此下结论」的免责，说明数据口径不足以支撑原始目的 |
| 129 | 贡献会话清单 | 时间窗内本项目所有会话都计入（含并行会话），并列出 | 报告 | 内置 | `module_cost_report.py:596-603` | module-cost-report | 会计入同一时间窗内其他无关会话，归属不精确（文档承认） |
| 130 | 「无法统计的部分」声明 | 每份报告列出 shell 改动、续派用量、Codex 无收回信号、未定价、跳过的坏时间戳 | 输出 | 内置 | `module_cost_report.py:604-620` | module-cost-report | 无 |
| 131 | `--json` 输出 | 同一份数据的 JSON | 输出 | 手动 | `module_cost_report.py:481-489,639` | module-cost-report | 无 |
| 132 | 评测脚手架 `evals/dispatch-cost` | 在 ledgerlite 种子项目上跑完整 `/build auto`，用本报告计价并配隐藏测试判分；已有 18 次运行的原始数据 | 维护者手动，不进 validate | 手动 | `evals/dispatch-cost/*`（README 73 行） | build-task-dispatch；module-cost-report | 为研究派活成本建的实验平台；结论已定（派活不稳定省钱），脚手架继续留在仓库需要决定是否归档 |

---

## 五、维护者工具（只列功能，不作使用者需求评价，除非越界）

### 5.1 `scripts/`（34 个文件）

| # | 功能点 | 做什么 | 入口 | 关键位置 | 能力图模块 |
|---|---|---|---|---|---|
| 133 | `validate.sh` | 仓库完整性校验总入口（清单一致、检查器、各套回归测试、退役扫描、smoke 判决器自检）；CI 与本地共用 | 手动、CI、verify-and-commit | `scripts/validate.sh`（202 行） | verify-and-commit；validate-parallel-files |
| 134 | `validate.sh --quick` | 仅结构类检查（文档类提交用） | 手动 | `scripts/validate.sh:11`；`scripts/test_validate_quick.py` | local-check-dedup |
| 135 | `verify-and-commit.sh` | 在 pipefail 下并行跑检查，全过才提交已暂存内容，并记 tree | 提交唯一入口 | `scripts/verify-and-commit.sh`（136 行） | verify-and-commit；local-check-dedup；verify-and-commit-untracked-warning |
| 136 | `verified_trees.py` | 记录已通过检查的 tree，预推送钩子对仅由这些 tree 组成的推送跳过重复检查；`tier` 判快档/全档 | 内部 | `scripts/verified_trees.py` | local-check-dedup；pre-push-ref-only-skip |
| 137 | `install-git-hooks.sh` | 安装 pre-push 钩子，与 CI 一致 | 手动 | `scripts/install-git-hooks.sh` | audit-remediation；pre-push-ref-only-skip |
| 138 | `run_steps_parallel.py` | 并行跑 validate 的回归步骤，按原顺序打印 | validate 内部 | `scripts/run_steps_parallel.py` | validate-parallel-files |
| 139 | `run_tests_parallel.py` | 把一个 unittest 文件按 TestCase 类分到多进程，任一丢失或失败即失败 | validate 内部 | `scripts/run_tests_parallel.py` | slow-test-speedup；validate-parallel-files |
| 140 | `check-tests-registered.py` | 每个测试文件必须被运行器点名 | validate | `scripts/check-tests-registered.py` | test-registration-check |
| 141 | `check-acceptance-wired.py` | 每个可选验收测试都必须有处说明何时/怎么跑 | validate | `scripts/check-acceptance-wired.py` | test-registration-check |
| 142 | `check-acceptance-immutable.py` | 基线分支上的验收记录不得被改或删（只可新增） | validate | `scripts/check-acceptance-immutable.py` | proposal-label-acceptance |
| 143 | `check-bash32.py` | 静态检查 bash 3.2 会误解析的 `$VAR<多字节字符>` | validate | `scripts/check-bash32.py` | 无直接模块（不变量） |
| 144 | `check-grep-pipe.py` | 禁止 `cmd \| grep -q` | validate | `scripts/check-grep-pipe.py` | 无直接模块（不变量） |
| 145 | `check-gh-json-fields.py` | 校验仓库里 `gh … --json <字段>` 都是真实字段 | validate | `scripts/check-gh-json-fields.py` | 无直接模块 |
| 146 | `check-digest-single-source.py` | 禁止第二份能力图指纹实现 | validate | `scripts/check-digest-single-source.py` | checker-hardening |
| 147 | `check-command-names.py` | 用户可见输出里提到的斜杠命令必须真实存在 | validate | `scripts/check-command-names.py`（195 行） | sibling-plugin-hints 等 |
| 148 | `check-command-parity.py` | 每条命令引用的脚本都要有 skill 路由到（Claude/Codex 双入口一致） | validate | `scripts/check-command-parity.py` | checker-hardening |
| 149 | `check-command-table.py` | 每个斜杠命令都在 `docs/commands.md` 命令对照里 | validate | `scripts/check-command-table.py` | docs-reorganization |
| 150 | `check-manifests.py` | marketplace 与两份 plugin.json 版本一致 | validate | `scripts/check-manifests.py` | 无直接模块 |
| 151 | `check-readme-sync.py` | `docs/convention-block.md` 内嵌声明块与 templates 逐字节一致；README 的 `--ref` 为当前版本 | validate | `scripts/check-readme-sync.py` | docs-reorganization |
| 152 | `check-interface.py` | `interface.json` 与代码一致（给其他插件读的接口说明） | validate | `scripts/check-interface.py` | plugin-interface |
| 153 | `check-state-paths.py` | hooks 里家目录路径只来自 `state_paths.py` | validate | `scripts/check-state-paths.py` | runtime-state-layout |
| 154 | `check-collaboration-boundary.py` | 会话协作拆到 agent-relay 后，禁止其重新出现在 spec-guard | validate | `scripts/check-collaboration-boundary.py`；`scripts/collaboration-owned.txt` | collaboration-boundary |
| 155 | `check-no-parallel-surface.py` | 禁止已退役的并行工作流泄漏到现行插件表面 | validate | `scripts/check-no-parallel-surface.py` | concurrency-assessment 等 |
| 156 | `check-decision-supersession.py` | 被取代的决定必须在状态行指向取代者 | validate | `scripts/check-decision-supersession.py` | 无直接模块 |
| 157 | `test-checkers.sh` | 以上检查器自身的回归测试（816 行） | validate | `scripts/test-checkers.sh` | checker-hardening |
| 158 | `release-evidence.py` | 校验发布证据文件，不把较弱观察当较强证据 | 发版 | `scripts/release-evidence.py` | local-check-dedup；发版流程文档 |
| 159 | `release-package.py` | 校验具名发布包而非源码 checkout | 发版 | `scripts/release-package.py` | 同上 |
| 160 | `self_report.py` | 维护者只读自观测：读本机 Claude transcript 与 Codex rollout 中 spec-guard 注入的阶段提示，列出可疑问题；不随插件发布 | 维护者手动 | `scripts/self_report.py`（262 行） | self-observation-report；self-report-tmpdir-independence |
| 161 | scripts 自带测试 | `test_pre_push_environment.py`、`test_run_steps_parallel.py`、`test_run_tests_parallel.py`、`test_self_report.py`、`test_validate_quick.py`、`test_verify_and_commit.py` | validate | `scripts/test_*.py` | 各对应模块 |

### 5.2 `evals/`（10 个文件 + `dispatch-cost/`）

| # | 功能点 | 做什么 | 入口 | 关键位置 | 能力图模块 |
|---|---|---|---|---|---|
| 162 | `codex-plugin-smoke.sh` | Codex 真实宿主 smoke，在临时消费者项目验证阶段注入；`--selftest` 只验判决器不调 Codex；退出码 0/1/2 区分行为失败与环境未就绪 | 手动、validate 自检 | `evals/codex-plugin-smoke.sh`（342 行） | command-plugin-root；hint-language-follow；proposal-closeout 等 |
| 163 | `_preflight.sh` | evals 共用前置检查，被 source | 内部 | `evals/_preflight.sh` | 无直接模块 |
| 164 | `module-namespace.sh` | 验「多模块产物互不覆盖」承诺（主线性质的机械判定） | 手动 | `evals/module-namespace.sh`（426 行） | hint-language-follow 等 |
| 165 | `hint-english-diff.sh` | 英文阶段提示须与基线版本逐字节一致 | 手动 | `evals/hint-english-diff.sh`（默认基线 v0.67.0） | hint-language-follow |
| 166 | `test-codex-command-roots.sh` | 命令插件根目录定位的回归 | validate | `evals/test-codex-command-roots.sh` | command-plugin-root |
| 167 | `test-codex-skill-teardown-history.sh` | Codex 路由必须能预览/执行 teardown，且有 history 的 correct 路由 | validate | `evals/test-codex-skill-teardown-history.sh` | capability-history |
| 168 | `test-public-metadata.sh` | 公开元数据检查 | validate | `evals/test-public-metadata.sh` | 无直接模块 |
| 169 | `test-release-evidence.sh`、`test-release-package.sh` | 发布证据与发布包校验器的回归 | validate | `evals/test-release-*.sh` | local-check-dedup |
| 170 | `dispatch-cost/` 套件 | `run.sh`、`grade.sh`、`verify-seed.sh`、`prices.json`、种子/参考/隐藏测试、18 次运行结果 | 手动，不进 validate | `evals/dispatch-cost/` | build-task-dispatch；module-cost-report |

### 5.3 `.github/workflows/ci.yml`

| # | 功能点 | 做什么 | 入口 | 关键位置 | 能力图模块 |
|---|---|---|---|---|---|
| 171 | CI `validate` job | ubuntu-latest 单元素矩阵（保持 required check 名称）：bash 版本、`validate.sh`、phase-guard 回归、verify-artifacts 回归、ShellCheck（npm 4.1.0=二进制 v0.11.0，阻塞，范围含 hooks、scripts、evals） | push main / PR / 手动 | `.github/workflows/ci.yml` | run-ci-shellcheck-before-push（仅记忆）；checker-hardening |

维护者工具的整体疑点：scripts+evals 共约 44 个文件，其中「并行加速」「已验证 tree 跳过」「预推送」三类是仅服务本仓库提交速度的基础设施（verify-and-commit、local-check-dedup、slow-test-speedup、validate-parallel-files、verified_trees、run_*_parallel 共 6 个模块 + 4 个 scripts）。另有三个检查器（collaboration-boundary、no-parallel-surface、acceptance-immutable）守的是**已退役**功能的边界，只会随时间增多。这些都不影响使用者，但占模块数与维护面。

---

## 六、统计

- 功能点编号：1–171（其中 8.、57 等归并后连续编号），编号即总数，**171 个**（Proposal 77、文档治理 19、历史 14、成本 22、维护者工具 39）。
  - 一、Proposal：1–77（含契约 12、提交 8、发布读取 9、tracker 8、审查 7、预检/证明 13、收尾 20）。
  - 二、文档治理：78–96（19 个）。
  - 三、能力历史：97–110（14 个）。
  - 四、成本与返工：111–132（22 个）。
  - 五、维护者工具：133–171（39 个）。

## 七、最值得与用户核对的需求疑点（按重要性）

1. **Proposal 四步流程整体是否值得保留这个体量**：Proposal 源码约 2900 行加 5 份参考文档，能力范围却只支持「新增一个模块」；而本仓库 `spec/proposals/` 只有 6 份、能力图 140 个模块绝大多数走 `add-module` 或一次性登记。需要确认 Proposal 的真实用户和使用频率，以及它与 `add-module`（也能插入模块）、社区 OpenSpec 的 change 目录（`docs/reports/2026-10-22-multidimension-audit.md` 已把二者列为同类）的定位区别。
2. **收尾（closeout）把「只读」插件变成会写 tracker 的工具**：评论、改标签、关 Issue、journal+锁、11 项复核、11 个结果状态、三个后端各一份适配器，缘起是一次 #221 漏关事故；与 Proposal 流程其余部分「只读、人来贴标签」不一致，也与 hosted-ticket-workflow / local-ticket-portability 的写事项能力重叠。可考虑改为只提示、让人或日常事项流程去关。
3. **文档治理三件套（基线/影响/核验）没有任何自动入口**：不在 hook、verify-artifacts、检查点流程中被调用，本仓库自己也没启用基线文件；`ready` 仅表示声明层填完，且主流程里真正会触发的是检查点规则的「文档建议」，与上游 `documentation-and-adrs` 也有重叠。需求侧缺使用证据。
4. **能力历史（含 audit/correct/迁移导入）服务的是已退役的 initiative 生命周期**：现在没有任何路径自动写账本，audit 对几乎所有带时间或状态的记录天然报「未解决」，`correct` 需要整套审阅文件才能消除；使用者仅限从旧版升级且有归档的项目。需确认是否仍需保留，还是只留 verify 并把 audit/correct 退役。
5. **成本报告的前提和耦合**：它为回答「派活是否省钱」而建，但 `build-task-dispatch` 默认关闭、全局记录显示实测未证明派活更省，报告自身对多模块对照也声明「不要下因果结论」；实现依赖宿主私有 transcript/rollout 格式，并靠匹配 tier-guard 拒绝文案的中文字符串（`第二次失败后的收回`，`module_cost_report.py:137`）识别「收回」，属于跨插件的隐式文本契约，且「按模块算总账」是否本该归 tier-guard 的 tier-report 值得再确认。

补充次要疑点：v1 Proposal 仍被解析但全链路拒绝（功能点 2、47）；`proposal-promotion-preflight` 命令被自己的文档称为通常不必（功能点 45）；`check-*` 守护已退役边界的脚本只增不减（5.3 末）。
