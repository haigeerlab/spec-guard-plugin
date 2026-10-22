# Plan: proposal-fixes

<!-- spec-guard: review approved -->

依据 [`spec/proposal-fixes.md`](../../spec/proposal-fixes.md)（2026-10-22 批准，事项 C27）。
Spec 的待定问题按用户答复定为：**F18 后半（`capability-history.py` 的 `event.at` 校验与 `imported` 补正）不在本模块，交给 history-slim**。

分支 `proposal-fixes`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/proposal-fixes`，从集成分支 `crew/fix-batch` 开出。
module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调整批合完后统一改，
本模块把拟写的更新说明记在 todo 末尾。

所需工具：无 UI 改动，不需要浏览器或电脑操作；不访问真实 GitHub/GitLab，不新增依赖。

## 并行边界

- 独占：`plugins/spec-guard/hooks/proposal_closeout.py`、`plugins/spec-guard/hooks/proposal_publication.py`、`plugins/spec-guard/hooks/test_proposal_closeout.py`、`plugins/spec-guard/hooks/test_proposal_publication.py`、`plugins/spec-guard/hooks/test_proposal_promotion_proof.py`、`plugins/spec-guard/references/proposal-closeout.md`、`plugins/spec-guard/references/proposal-publication.md`

说明：
- 越界检查（`module_scope.py`）只从 Spec 读这一节，已批准的 Spec 没有这一节。按 tracker-provider-unify 的先例，本次交审请用户定**是否把同样一节补进 Spec**（Spec 指纹会变，最终验收附差异一并复审）。
- 写 Plan 时核对代码发现 Spec「Assumptions 1」有一句不准：「journal 本身也不删」——实际上收尾成功（`verified`）或平台明确拒绝时 journal 条目会被删掉（`proposal_closeout.py:525`、`:478` 调 `_clear`），只有未完成的尝试才留 journal。修法不受影响（锁文件仍按 Spec 不删；成功后目录里只剩一个空锁文件），若补并行边界一节，同时把这句改成事实。
- `test_proposal_promotion_proof.py` 曾是 tracker-provider-unify 的独占文件；该模块已合入集成分支，本模块只在文件末尾加一例。

## 实现要点

- **F6**：删掉 `close_preview` 的 `finally` 分支（`os.unlink(<journal>.lock)`），其余不动：仍是 `os.open(O_CREAT | O_RDWR | O_NOFOLLOW, 0o600)` → `fdopen` → `flock(LOCK_EX)`，`with` 结束关闭描述符即释放；`OSError` 仍报 `unknown: journal-unavailable`。
- **F6 现有测试**：`test_a_finished_closeout_leaves_no_journal_entry_or_lock` 断言成功后 journal 目录为空，正是被修的行为。改为：没有 `.json` 条目，只剩一个 `.lock`（0600）。这是 Spec AC1 要求的行为变化，不是放宽断言。
- **F6 三方交错用例**：线程内各自 `os.open` 拿到独立的打开文件描述，`flock` 在同进程线程间同样互斥，所以用线程即可复现。打桩 `_close_locked`：进入时计数加一、记录最大并发，A 停在一个 `Event` 上，B、C 各停 0.3 秒，退出时计数减一。顺序：起 A，等 A 进入；起 B，等 0.2 秒让 B 停在 `flock` 上；放行 A，等 A 返回；起 C。断言最大并发为 1。现有代码上 C 打开的是新 inode，与持旧 inode 锁的 B 重叠，最大并发为 2（红）。
- **F18**：`proposal_publication.py` 新增 `PROPOSAL_UNREADABLE = "proposal listed in the snapshot could not be read"`，`PROBE_CODES` 加 `PROPOSAL_UNREADABLE: "snapshot-proposal-unreadable"`。`read_published_pool` 的循环里 `_show` 返回 `None` 时 `return PublicationPool("unknown", review_commit=observed_commit, diagnostic=PROPOSAL_UNREADABLE)`，放在 `write_text` 之前。
- **调用方不改**：`proposal_promotion_proof._preflight` 与证明路径已经 `probe_code(pool.diagnostic)`；`proposal_submit` 与 `proposal_closeout` 按已有 `unknown` 路径报告。

## Task List

### Task 0：提交已批准的 Spec 标记、Plan 与 todo

Plan 获批后由模块协调带批准标记提交到集成分支，`module-crew sync` 合入。用户若选补并行边界一节，同步把它与 Assumptions 1 的事实更正补进 Spec。

- 验收：sync 退出码 0；`verify-and-commit.sh` 快档通过；补了并行边界时 `module_scope.py check --base crew/fix-batch` 越界 0。

### Task 1：F6 回归（先红）

`test_proposal_closeout.py` 加：锁文件在成功、blocked、`OSError` 三种返回之后都在且 inode 不变；三方交错用例。改写 `test_a_finished_closeout_leaves_no_journal_entry_or_lock`（见实现要点）。

- 验收：在现有代码上新增用例与改写的用例为红，红的原因恰是锁被删、出现并发 2；其他用例不变。
- 验证：`python3 -B plugins/spec-guard/hooks/test_proposal_closeout.py`（预期失败）。

### Task 2：F6 修复

删 `finally` 里的 `unlink`；`references/proposal-closeout.md` 写明锁文件留在 journal 目录、为什么不删（删了会让等旧 inode 的进程与新建锁文件的进程同时进入写入）。

- 验收：`test_proposal_closeout.py`、`test_proposal_closeout_local.py`、`test_proposal_closeout_providers.py` 全过（AC1、AC2）。

### Task 3：F18 回归（先红）

`test_proposal_publication.py` 加：打桩 `proposal_publication._show`，对 `spec/proposals/` 下某一路径返回 `None`、其余照常，断言 `read_published_pool` 返回 `unknown`、`diagnostic` 为新事实、`probe_code` 得 `snapshot-proposal-unreadable`。`test_proposal_promotion_proof.py` 加：同一失败下晋级证明报 `unknown: snapshot-proposal-unreadable`。

- 验收：现有代码上两例报 `TypeError`（红）。

### Task 4：F18 修复

按实现要点加常量、`PROBE_CODES` 项与 `None` 检查；`references/proposal-publication.md` 候选池一节补一句：列出却读不出的文件让整个池为 `unknown`（可重试），诊断码 `snapshot-proposal-unreadable`。

- 验收：`test_proposal_publication.py`、`test_proposal_promotion_proof.py`、`test_proposal_submit.py` 全过（AC3、AC4）。

### Checkpoint 1（report）：变异核对

在 `mktemp -d` 建的副本上分别：把 `unlink` 加回；去掉 `None` 检查；去掉 `PROBE_CODES` 新项。每种都应让对应断言变红，结果记进 todo。

### Task 5：合入集成分支并跑完整检查

单独执行 `module-crew sync`，再走 `verify-and-commit.sh` 全套（validate、phase-guard、verify-artifacts）提交实现。

- 验收：sync 退出码 0（冲突按 sync 规则处理）；全套通过（AC5）。

### Checkpoint 2（gate）：模块最终验收

发最终验收【交审】：按 AC1～AC5 逐条给证据、变异核对结果、改动统计与越界检查（`module_scope.py check --base crew/fix-batch` 的结果，Spec 没有并行边界一节时如实说明）、
新增依赖（无）、提交表、拟写的更新说明。不推送、不开 PR，合并由模块协调按用户原话做。

## 风险

- 三方交错用例靠 0.2 秒等待让 B 先停在 `flock` 上；机器很忙时 B 可能还没打开文件，那样改前也可能不红。以 Task 1 先红为准，红不稳定就把等待改为轮询「B 已调用 `os.open`」（打桩记录）再继续。
- 锁文件留在 `~/.local/state/spec-guard/proposal-closeout/`，每个 `proposalId + revision` 一个空文件；数量随收尾过的 Proposal 增长，不清理（清理会重新引入竞争），文档写明。

## 中途会停下的地方

- Checkpoint 1：`report`，记录后继续。
- Checkpoint 2：`gate`，最终验收；不含推送与开 PR。
- 无其他中途 `gate`。
