# Plan: proposal-closeout

依据 [`spec/proposal-closeout.md`](../../spec/proposal-closeout.md)。七个 task 串行，每个 task 一条提交；
先写能在当前代码上失败的测试并记录失败输出，再实现到通过。

本分支叠在 `codex/tracker-backend-default` 上（本模块依赖 `tracker-backend-default`，它还在 PR #160
里未合并）。PR #160 合并后本分支的 diff 自动收缩为只有本模块的改动。

顺序原则：**纯核心 → 适配器 → 编排 → 写入 → 链路补齐 → 文档**。前两个 task 不含任何写入路径，
所以任何中间提交都不可能写出一次未经复核的远端变更。

每个 task 完成时都运行三条最小验证，并用 `PATH=/usr/bin:/bin` 下的 `python3`（3.9）再跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

**沿用 `tracker-backend-default` 审查换来的教训，不要再被审查发现一次**：任何读取仓库内文件的新代码
一上手就按 Spec C11 写——`O_NOFOLLOW`、拒绝非普通文件、读取上限、`UnicodeDecodeError` 归入 `invalid`、
不回显读到的原文；任何写入走独占临时文件 + `os.replace`。每个涉及读写的 task 的验收都包含这一条。

## Task 1：纯状态机与 tracker 读取扩展（C1、C2）

- 新增 `hooks/proposal_closeout.py` 的 `closeout_decision(stage, closed, proof_state)`，零 I/O。
  **签名不含 `project`／`root`／`provider`**，使它结构上不可能读到模块 stage。
- `hooks/proposal_tracker_read.py`：平台集合加 `local`（target 为 `[A-Za-z0-9_-]{1,64}` 的 projectId
  字符串，正则与 `local_ledger_runtime` 逐字相同）；`_issue_fields` 加 `local` 分支；
  `TrackerRead.issue_id` 放宽为 `int | str`；新增 `closed: bool`，缺该字段即 `unknown`。
  GitHub 的 `gh issue list --json` 增补 `state`。
- 新增 `hooks/test_proposal_closeout.py` 覆盖 Spec T1 全部用例，含**锁死签名**的那条断言。
  `test_proposal_tracker_read.py` 补 `local` 平台与 `closed` 的正反例；现有断言逐字保留。
- `scripts/validate.sh` 登记 `test_proposal_closeout.py`（显式清单，不登记 CI 永远跑不到——
  这是 `tracker-backend-default` Task 1 的实测教训）。
- **验收：** T1 与新增 tracker 断言先红后绿；`closed` 缺失时为 `unknown` 而非默认 open；
  现有 Proposal 全部回归逐字通过。
- **文件：** `proposal_closeout.py`、`test_proposal_closeout.py`、`proposal_tracker_read.py`、
  `test_proposal_tracker_read.py`、`scripts/validate.sh`。

## Task 2：github 与 gitlab 适配器（C3）

- 新增 `hooks/proposal_closeout_github.py`、`hooks/proposal_closeout_gitlab.py`，各自实现 C3 的七个方法。
  传输沿用 `hosted_ticket_provider` 的形态（`gh api --hostname` / `glab api`，分页到短页、
  `DEFINITE_REJECTIONS` 归为 `rejected`+`statusCode`），**不复制** Proposal 的身份判定逻辑。
- gitlab 的 target 是正整数 project id（与既有 Proposal 命令一致，全仓库只此一种形态）；
  note 读取须区分系统 note，系统 note 不算讨论证据。
- 测试用假 runner／writer，不联网：读回字段校验、分页不完整 → `unknown`、4xx → `rejected`、
  URL 主机与路径不符 → `unknown`。
- **验收：** 两个 adapter 的正反例先红后绿；**没有任何写入路径被真实调用**（断言 writer 未被触发）。
- **文件：** 两个 adapter 与它们在 `test_proposal_closeout.py` 中的用例。

## Task 3：local 适配器（C3）

- 新增 `hooks/proposal_closeout_local.py`，经 `local_ledger_runtime.mcp_tool_call` 调
  `epiq_issue_list` / `epiq_issue_get` / `epiq_issue_comment_add` / `epiq_issue_tag_add` /
  `epiq_issue_tag_remove` / `epiq_issue_close`。
- **`epiq_issue_tag_remove` 收的是 `tagId`**：阶段迁移先读回该 issue 的 tags 找到旧阶段 tag 的 id，
  读不到就 `unknown`，不盲猜。
- 调用前要求 Epiq runtime 与 Node `ready`、状态 worktree `owned`，否则 `unknown`。
  `tagName` 上限 60 字符（已实测 `epiq@1.11.0` 的 schema），`proposal-stage:*` 取值与托管侧逐字相同。
- 预览数据里带「该账本是否会 sync 到公开远端」这一事实；**本模块不调用 `epiq_sync`**，加断言锁死。
- 测试：patch `mcp_tool_call` 的单元用例覆盖 Spec T3；另加一个**隔离临时账本**的可选验收
  （临时仓库 + 独立 `EPIQ_GLOBAL_DIR` + 固定 runtime），缺运行时时退出 2 表示「未运行」，
  绝不把跳过报成通过。
- **验收：** T3 先红后绿；`tagId` 路径有正反例；runtime 不可用时为 `unknown`；
  断言全程未调用 `epiq_sync` 与任何受 gate 的 Epiq 工具；**不触碰真实账本与 E7V48RY**。
- **文件：** `proposal_closeout_local.py` 及其用例。

## Task 4：预览（C4）

- `proposal_closeout.py` 加 `preview` 子命令：重取远端快照读 Proposal → 完整分页按 marker 定位恰好
  一条 → 读阶段与开闭 → **同一次运行内**调 `proposal_promotion_proof.prove_from_remote()` →
  只有 `proved` 才出预览。
- 未显式给出 `--backend`／`--target` 时经 `tracker_default.resolve()` 取项目默认值，
  预览注明来源；解析不出即 `target-unselected`。
- 预览字段按 Spec C4 全列，并带 `digest`；输出到 `--output`，内容按 C11 脱敏。
- **`proposal_promotion_proof.py` 一个字节都不改**：本模块以调用方身份 import 它。加一条断言
  锁死它的 CLI 与返回状态集合未变。
- **验收：** 预览侧正反矩阵（Spec T2 预览侧）先红后绿；proof 非 proved 时不出预览；
  `--output` 文件按 C11 不含正文、URL、token、临时路径。
- **文件：** `proposal_closeout.py`、`test_proposal_closeout.py`。

## Task 5：复核、写入、journal 与幂等（C5–C8）

- `close` 子命令：`--confirm` 之后把 Spec C5 的八项复核**全部重做**，然后按 C6 的顺序写入，
  每步先查重后写，最后读回三项。
- journal 按 C7：`~/.local/state/spec-guard/proposal-closeout/<sha256(id+revision)>.json`，
  0600、父目录 0700、`O_NOFOLLOW`、`fcntl` 独占锁，按 proposal 串行化。
- 结果状态按 C8；`unknown`／`partial` 之后只对账不重发。
- **验收：** 确认侧与写入侧正反矩阵（Spec T2）先红后绿；
  连续两次 `close --confirm` → 第二次 `already-closed` 且评论数不变；
  关闭响应丢失但实际已关闭 → 对账后 `verified`；丢失且确实未关 → `partial` 且重跑不产生第二条评论；
  **写入路径按 C11 用独占临时文件，journal 不被符号链接劫持**（正反各一）。
- **文件：** `proposal_closeout.py`、`test_proposal_closeout.py`。

## Task 6：补齐 Local 的 Proposal 链路（C9）

- `proposal_submit.py` 的 `--platform` 加 `local`：baseline 与 revision 的计算**完全不变**（纯 Git），
  只把最后打印的「下一步」换成 Local 建事项指引（正文首行为完整 marker，打 `proposal` 与
  `proposal-stage:published` 两个 tag）。命令仍不执行其中任何一条。
- `module-insert.py --proposal` 的 `--platform` 加 `local`（内嵌预检要读 tracker）。
- **验收：** `--platform local` 的 baseline/revision 输出与 github 路径**逐字相同**（同一夹具对比）；
  两个脚本的 github/gitlab 既有断言全部逐字保留。
- **文件：** `proposal_submit.py`、`module-insert.py`、`test_proposal_submit.py`、`test_module_insert.py`。

## Task 7：入口与文档（C12、C13）

- 新增 `commands/proposal-closeout.md`；`skills/spec-guard-ops/SKILL.md` 的 proposal 一节加同等入口；
  `docs/workflow.md` 命令对照加一行。
- 新增 `references/proposal-closeout.md`：状态机、三个 adapter 的平台差异、marker、journal 及其局限
  （无法证明同一 Proposal 没有在另一个容器里也存在一条）。
- `docs/workflow.md` 四步表第 4 步扩写为「证明 → 收尾预览 → 授权 → 改阶段并关闭 → 读回」，
  写明旧做法仍可用；`docs/concepts.md` 的 Proposal 术语补一句阶段可落在 Local；
  `references/proposal-tracker-read.md` 补 `local` 与 `closed`；
  `references/proposal-contract.md` 说明阶段命名空间三后端相同；`CHANGELOG.md` Unreleased。
- **验收：** `check-command-parity.py` 通过；文档不描述未实现的行为（`tracker-backend-default`
  审查抓到过决策记录声称已回归而实际未实现，本次自查一遍再提交）。
- **文件：** 一个命令、一份参考、四份既有文档、CHANGELOG。

## Checkpoint：完成

- 两种 Python 下运行：`test_proposal_closeout.py`、全部 Proposal 回归、`test_tracker_default.py`、
  `test_module_insert.py`、`test_proposal_submit.py`、三条最小验证、
  `check-command-parity.py`、`check-acceptance-immutable.py`、
  `evals/codex-plugin-smoke.sh --selftest`、`git diff --check`。
  逐项按 通过／失败／未运行／环境不可用 报告。
- 隔离临时账本上跑 Local 的端到端一遍并记录输出；**不扫描真实账本，不触碰 E7V48RY**。
- 本仓库阶段与 `verify-artifacts` 输出与改动前逐字对比（本模块不应改变它们）。
- 端到端断言：晋级后模块只有 Plan、没有 `todo.md` 时，收尾结果与有 todo 时完全相同。
- 完整代码审查与安全审查，审查发现先复现再修、修后重跑复现。
- 检查点勾选随模块 PR 提交；推送并创建 PR；等待 CI；**不自行合并 main，不自行发版**。

## 条件性任务（需单独授权，不在本计划的默认范围内）

- **GitHub 真实往返**：候选 #149 / #104（两条都是 `accepted` + `proved` + open）。
  执行前必须先展示逐字的评论正文、将加／删的 label、关闭动作，并取得针对那两个具体 Issue 的明确授权。
  未获授权则记「真实远端未验证」，不以模拟顶替。
- **GitLab 真实往返**：本仓库无 GitLab 项目，按 Spec Assumption 12 记为「模拟通过，线上未验证」。
