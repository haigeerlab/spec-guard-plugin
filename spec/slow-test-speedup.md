# Spec: slow-test-speedup

## Objective

`validate.sh` 本机约 4–5 分钟，其中三个测试占了大头：`test_module_cost_report.py`、
`test_proposal_promotion_proof.py`、`test_local_ticket_portability.py`（第二轮联调在 main 4ca0098 上测得 68、35、34 秒，
合计约 137 秒，占 validate 的 63%）。每次全套提交都要等它们。本模块在覆盖范围不缩小的前提下给它们提速。来源：第二轮联调
按用户意见整理的需求，用户 2026-10-09 确认写入能力图并选做法 A（改夹具 + 测试类分进程并行）。

读者：本仓库维护者。

## 测出来的原因（2026-10-09，本机 8 核，负载 20–27，秒数偏高）

| 测试 | 用时 | 用例 | 时间花在哪 |
|---|---|---|---|
| `test_module_cost_report` | 67–92 秒 | 149 | 几乎每个用例新建仓库：`git init` + 2 次 `git config`，每写一次 todo 就 `git add` + `git commit`；测试自己约 1300 次 git 调用，被测代码另有约 600 次（`git show`、`rev-parse`、`log`） |
| `test_proposal_promotion_proof` | 50 秒 | 59 | 用例本身约 30 秒，其余在类级准备：建本地与远端仓库、推送、拉取 |
| `test_local_ticket_portability` | 45 秒 | 52 | 每个用例建仓库加一个 worktree（约 9 次 git 调用）；被测代码 658 次 `git rev-parse`，另有打包与拉取 |

被测代码自己的 git 调用按约束不能动，所以只改夹具估计省 30%–40%，到不了目标；需要并行。

## Assumptions

用户于 2026-10-09 确认（做法 A）：

1. **夹具瘦身**（只改测试文件里的夹具）：
   - 每个测试类建一次模板仓库（`setUpClass`），每个用例复制一份，代替每个用例 `git init`；带 worktree 的夹具复制后用
     `git worktree repair` 修正路径；
   - 提交者身份用环境变量（`GIT_AUTHOR_NAME` 等）代替每个仓库两次 `git config`；
   - 能合并的提交步骤合并（例如一次 `git commit` 带上要提交的路径，省掉单独的 `git add`）。
2. **测试类分进程并行**：新建 `scripts/run_tests_parallel.py`，把一个 unittest 文件按 `TestCase` 类分到若干个进程
   （默认取 CPU 核数与类数的较小值）跑，汇总每个进程的结果；任一进程失败即整体失败。它核对实际运行的用例总数等于
   发现的用例数，少跑一个就算失败。`validate.sh` 用它来跑这三个测试。测试彼此不共享状态（都只用各自的临时目录），
   并行前逐个核对这一点。
3. **覆盖范围不缩小**：用例数和断言不减少（改前改后对比用例总数，并逐个看夹具改动没有删断言）；每个测试文件各改坏一个
   被测判据，用并行运行器跑，相应测试必须变红（实测证明）；只改测试与夹具，不改被测代码的行为；系统自带的 Python 3.9
   （`/usr/bin/python3`，3.9.6）也要通过。
4. **发布包会变**：这三个测试文件位于 `plugins/spec-guard/hooks/`，发版打包会带上（发布包里共 39 个测试文件）。所以
   发布包内容会变，但只是测试文件，插件行为不变、版本号不改，随下次发版。`scripts/run_tests_parallel.py` 不在包里。
5. **验收**：三个测试改前改后各计时一次（尽量在相近的负载下，记下当时的负载），`validate.sh` 整体改前改后也各计时一次，
   写进 todo。目标：三个测试合计 40 秒以内。某个测试做不到时，在 todo 和 PR 里说明原因，由用户决定。

## Requirements

1. 三个测试文件的夹具按假设 1 改；用例总数分别仍为 149、59、52。
2. 新建 `scripts/run_tests_parallel.py`（只依赖 Python 标准库，3.9 可用），输出每个进程的用例数与耗时、总用例数和结论；
   它自己的回归 `scripts/test_run_tests_parallel.py`：全部通过时退出 0；任一类失败时退出非零并报出类名；用例总数对不上时
   失败；进程数可用参数指定。登记进 `validate.sh`。
3. `validate.sh` 用并行运行器跑这三个测试，其余不变。
4. 变异证明（每个文件一处，改坏被测代码的一个判据，跑完立即还原）与 3.9 结果写进 todo。

## Commands

```bash
python3 -B scripts/run_tests_parallel.py plugins/spec-guard/hooks/test_module_cost_report.py
/usr/bin/python3 -B scripts/run_tests_parallel.py plugins/spec-guard/hooks/test_local_ticket_portability.py
/bin/bash scripts/validate.sh
```

## Boundaries

- Always：只改测试、夹具与运行方式；改坏被测代码只用于变异证明，立即还原。
- Ask first：推送、PR；改任何被测代码。
- Never：删用例或断言；为提速跳过用例；改插件行为或版本号。

## Success criteria

1. 三个测试合计 40 秒以内（或说明哪个做不到、为什么）。
2. 用例数与断言不减少，改坏判据时仍会变红。
3. `validate.sh` 整体明显变快。

## Open questions

无。
