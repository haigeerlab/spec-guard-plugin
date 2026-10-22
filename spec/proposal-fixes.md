# Spec: proposal-fixes

<!-- spec-guard: review approved 198b4376b3e0 -->

## Objective

决定 D13 保留整条 Proposal 流程，只修它的正确性问题。本模块修两条审查发现（2026-10-22 多维审查）：

| 编号 | 位置 | 现在的问题 |
| --- | --- | --- |
| F6 | `hooks/proposal_closeout.py` `close_preview` | 收尾在 `finally` 里 `os.unlink` 锁文件。进程 A 持锁时，进程 B 已打开同一路径（旧 inode）在等锁；A 释放并删掉文件后，进程 C 打开同一路径会新建一个 inode 并立即拿到锁，B 也拿到旧 inode 的锁，B、C 同时进入 `_close_locked`，对同一个 Proposal 并发写远端（评论、标签、关闭），journal 的串行化承诺失效 |
| F18（前半） | `hooks/proposal_publication.py` `read_published_pool` | `ls-tree` 列出的 Proposal 文件在 `git show` 时读取失败，`_show` 返回 `None`，接着 `write_text(None)` 抛 `TypeError`；调用方（`proposal_submit`、`proposal_promotion_proof`、`proposal_closeout`）拿不到 `PublicationPool`，只看到一个 Python 栈 |

修完后：同一个 Proposal 的收尾在多进程下严格串行；候选池遇到单个文件读不出时，返回 `unknown` 和一个稳定诊断码，三个调用方按已有的 `unknown` 路径报告「可以重试」。

## Assumptions

1. **锁文件留在磁盘上是可以接受的。** 它在 journal 同一个 0700 私有目录里，每个 `proposalId + revision` 一个、空文件、0600；journal 条目在收尾成功或平台明确拒绝时会删掉，锁文件则留下。修法就是不删，不另做清理（清理本身会重新引入同一个竞争）。仓库里其他用 `fcntl` 的地方（`hosted_ticket_actions.py`、`hosted_ticket_write.py`）也是不删锁文件，本修法与之一致。
2. **`ls-tree` 列出却 `git show` 不出，是读取故障而不是数据无效。** 同一个快照里刚列出的路径读不出来，原因是 git 进程失败或超时（`_run` 返回 `None`），不能据此说 Proposal 不合规，所以结果是 `unknown`（可重试），不是 `invalid`，也不能静默跳过（跳过会让晋级证明在缺一份 Proposal 的池上下结论）。
3. **诊断码走 `PROBE_CODES` 那一套。** 新增一个快照读取类事实及其稳定码 `snapshot-proposal-unreadable`，调用方已有的 `probe_code(...)` 映射会把它原样带出；不带出的调用方落回各自的 `proposal-pool-unknown`，行为不变。
4. **F18 的后半（`capability-history.py` 不校验 `event.at`、迁移写入 `imported` 后无法补正）不在本模块。** 本模块的能力图条目只写了「候选池枚举在 git show 失败时给出稳定诊断」；后半若要修，由模块协调另行安排（或交给相关模块）。
5. **单个 Proposal 读取（`read_published`）不改。** 它的 `_show` 返回 `None` 时报 `absent`，那条路径没有先列出再读，语义另说，不在本次范围。

## Contract

### C1 收尾锁不再删除（F6）

- `close_preview` 打开 `<journal>.lock`（`O_CREAT | O_RDWR | O_NOFOLLOW`，0600）后取 `fcntl.LOCK_EX`；释放只靠关闭文件描述符，**任何路径都不 `unlink` 锁文件**。
- 同一个 `proposalId + revision` 的锁文件在多次收尾之间是同一个 inode。
- 其他行为不变：`OSError` 仍报 `unknown: journal-unavailable`，结果状态与 journal 内容不变。
- `references/proposal-closeout.md` 写明锁文件会留在 journal 目录、为什么不删。

### C2 候选池读取失败给稳定诊断（F18 前半）

- `proposal_publication.py` 新增一个快照读取类事实（与 `FETCH_FAILED` 等并列）和它在 `PROBE_CODES` 里的码 `snapshot-proposal-unreadable`。
- `read_published_pool` 在逐个读取 Proposal 时，`_show` 返回 `None` 即返回 `PublicationPool("unknown", review_commit=<快照提交>, diagnostic=<该事实>)`，不再写文件、不抛异常。
- 调用方不改代码就能拿到结果：`proposal_promotion_proof` 经 `probe_code` 报 `snapshot-proposal-unreadable`；`proposal_submit` 与 `proposal_closeout` 按已有的 `unknown` 路径报告。
- `references/proposal-publication.md` 的候选池一节补一句：列出却读不出的文件让整个池为 `unknown`。

## Commands

```bash
python3 plugins/spec-guard/hooks/test_proposal_closeout.py
python3 plugins/spec-guard/hooks/test_proposal_publication.py
python3 plugins/spec-guard/hooks/test_proposal_promotion_proof.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- **F6 回归**（`test_proposal_closeout.py`）：一次收尾后锁文件仍存在；两次收尾前后锁文件 inode 相同；以及一个三方交错用例——A 在 `_close_locked` 内被挡住，B 已打开锁文件在等，A 返回后再起 C，断言任一时刻进入 `_close_locked` 的最多一个。先在现有代码上跑出红（删锁时三方用例出现两个并发），再改。
- **F18 回归**（`test_proposal_publication.py`）：构造 `ls-tree` 列出、`git show` 失败的快照（打桩 `_show` 对某个 Proposal 路径返回 `None`），断言 `read_published_pool` 返回 `unknown`、诊断为新事实、`probe_code` 得 `snapshot-proposal-unreadable`，不抛异常；现有代码上应抛 `TypeError`（红）。
- **调用方**（`test_proposal_promotion_proof.py`）：同一失败下晋级证明报 `unknown` 和 `snapshot-proposal-unreadable`。
- 变异验证：手工把 `unlink` 加回、把 `None` 检查去掉，确认对应断言变红。

## Boundaries

- 只改 `hooks/proposal_closeout.py`、`hooks/proposal_publication.py`、对应测试和两份 references 文档。
- 不改 `hosted_ticket_provider.py` 与 tracker-provider-unify 定下的读写接口；不改 `spec/proposal-closeout.md` 的契约（C7「`fcntl` 独占锁，按 proposal 串行化」本次正是把它落实）。
- 不改 `read_published` 单个读取、`capability-history.py`、journal 格式、结果状态集合。
- 不改 CHANGELOG 与版本号（由模块协调整批统一改，更新说明记在 todo 末尾）。

## 并行边界

- 独占：`plugins/spec-guard/hooks/proposal_closeout.py`、`plugins/spec-guard/hooks/proposal_publication.py`、`plugins/spec-guard/hooks/test_proposal_closeout.py`、`plugins/spec-guard/hooks/test_proposal_publication.py`、`plugins/spec-guard/hooks/test_proposal_promotion_proof.py`、`plugins/spec-guard/references/proposal-closeout.md`、`plugins/spec-guard/references/proposal-publication.md`

## Success criteria

- AC1：`close_preview` 的任何返回路径（成功、blocked、`OSError`）之后，锁文件仍在，inode 不变。
- AC2：三方交错用例中同一 Proposal 同时进入 `_close_locked` 的进程（线程）最多一个；改前该用例为红。
- AC3：`read_published_pool` 在某个列出的 Proposal `git show` 失败时返回 `unknown`，诊断经 `probe_code` 得 `snapshot-proposal-unreadable`，不抛异常；改前为 `TypeError`。
- AC4：晋级证明在同一失败下报 `unknown: snapshot-proposal-unreadable`。
- AC5：两份 references 文档按 C1、C2 补写；最小验证三条全绿。

## Open questions

- F18 后半（history 的 `event.at` 校验与 `imported` 补正）由谁做、做不做？本 Spec 按不做写，请模块协调确认。
