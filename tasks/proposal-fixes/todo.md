# Todo: proposal-fixes

- [x] Task 0：提交已批准的 Spec 标记、Plan 与 todo — Spec（C27）与 Plan（C33）由模块协调带批准标记提交到集成分支 aab3133，`module-crew sync` 合入（745166e）。按 D6 A 把并行边界一节补进 Spec，并把 Assumptions 1「journal 本身也不删」改为事实（86d09fd）；`module_scope.py check --module proposal-fixes --base crew/fix-batch` 越界 0。Spec 指纹因此改变，最终验收附差异复审。
- [x] Task 1：F6 回归（先红） — `test_proposal_closeout.py` 新增「锁文件在成功、`preview-stale`、`OSError` 三种返回后都在且 inode 不变」与三方交错用例（线程 A 停在 `_close_locked`，B 停在 `flock`，A 返回后起 C）；`test_a_finished_closeout_leaves_no_journal_entry_or_lock` 改写为 `..._but_keeps_the_lock`（只剩一个 0600 的 `.lock`）。现有代码上 3 处红：锁文件数 0、目录多出 `.lock` 断言不符、最大并发 2。
- [x] Task 2：F6 修复 — 删 `close_preview` 的 `finally: os.unlink(<journal>.lock)`，加一行注释说明为什么不删；`references/proposal-closeout.md` 写明锁文件留在 journal 目录及原因，「journal 里还有东西」改为「还有 `.json` 条目」。`test_proposal_closeout.py` 连跑 3 遍、并发用例单独连跑 10 遍全绿；`test_proposal_closeout_local.py`、`test_proposal_closeout_providers.py` 全过。
- [x] Task 3：F18 回归（先红） — `test_proposal_publication.py` 新增「列出却读不出即 `unknown`」（打桩 `_show` 只对 `spec/proposals/gamma.md` 返回 `None`）；`test_proposal_promotion_proof.py` 新增同一失败下 `prove_from_remote` 与 `preflight` 都报 `unknown: snapshot-proposal-unreadable`。现有代码上两例都是 `TypeError: data must be str, not NoneType`。
- [x] Task 4：F18 修复 — `proposal_publication.py` 加 `PROPOSAL_UNREADABLE` 与 `PROBE_CODES` 项 `snapshot-proposal-unreadable`，`read_published_pool` 在 `write_text` 前遇 `None` 返回 `unknown`；`references/proposal-publication.md` 候选池一节补一句。`test_proposal_publication.py`、`test_proposal_promotion_proof.py`、`test_proposal_submit.py`、`test_proposal_closeout.py` 全过；调用方未改代码。
- [x] Checkpoint 1（report）：变异核对 — 在 scratchpad 里 `tempfile.mkdtemp` 建的副本上各改一处：把 `unlink` 加回 → `test_proposal_closeout.py` 3 处红；去掉 `None` 检查 → `test_proposal_publication.py` 1 处错误；去掉 `PROBE_CODES` 新项 → `test_proposal_promotion_proof.py` 1 处红。
- [ ] Task 5：合入集成分支并跑完整检查
- [ ] Checkpoint 2（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **修复**：Proposal 收尾不再在释放时删除锁文件，同一个 Proposal 的多次收尾在多进程下严格串行，不会再同时写远端；锁文件留在私有 journal 目录。Proposal 候选池遇到列出却读不出的文件时，结果为 `unknown`（诊断 `snapshot-proposal-unreadable`，可重试），不再抛 `TypeError`。
