# Spec: git-fixture-template

## Objective

`scripts/validate.sh` 在本机一次约 135 秒（2026-10-01 实测）。最慢的五项都在临时 git 夹具上，合计约 131 秒：
`test_proposal_promotion_proof.py` 74s、`test_module_insert.py` 21s、`test_proposal_submit.py` 20s、
`test_proposal_publication.py` 11s、`test_local_ledger_runtime.py` 7s。剖析 `test_proposal_promotion_proof.py`：49 个测试
共 1746 次 git 子进程；约 70% 时间在 `setUp`——43 个测试各自从零 `init`／`commit`／`push`／`clone` 同一套夹具（每次约
0.73s）；约 30% 在被测代码自己的快照 fetch（应保留）。每个 task 验收要在两种 Python 下各跑一次，预推送 hook 再跑一次，
这些时间反复支付。

本模块只改测试：每个测试类只构建一次夹具模板，每个测试复制一份目录并修正远端地址。

登记：2026-10-01 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-01 确认（按推荐方案）：

1. 只改测试文件，不改任何产品代码、hook 或脚本逻辑。
2. 分两步：先改 `test_proposal_promotion_proof.py`（最大一项，`test_module_insert.py` 的晋级夹具继承它），实测有效后
   再用同一办法改 `test_proposal_submit.py`、`test_proposal_publication.py` 与 `test_module_insert.py` 自有的 git 夹具。
3. 每个测试仍拿到独立的目录与仓库（隔离不变）；所有断言逐字不变；测试数量不变。

本 Spec 提出、用户于 2026-10-01 确认的细节：

4. 模板在 `setUpClass` 中按类属性（`merge_promotion`、`drift_map` 等）构建，记录各提交 SHA 为类属性；`setUp` 用
   `shutil.copytree(..., symlinks=True)` 复制到每个测试自己的临时目录，再对复制出的仓库执行
   `git remote set-url origin <新远端路径>`；需要"刚读出的发布结果"的夹具在复制后重新读取（被测行为照常执行）。
   模板在 `tearDownClass` 删除。
5. 等价性验收（代替"先红"）：把改造前后的同一测试文件分别放到一组**较旧的 hook**（v0.34.0，缺少后来的诊断码等）上跑，
   两者失败的测试名集合必须完全相同；再在当前 hook 上都全绿。这证明改造没有让任何断言变弱。
6. 速度验收：同一台机器、同一时段，改造后 `test_proposal_promotion_proof.py` 的 `setUp` 总耗时降低至少 70%（用
   cProfile 统计）；两步完成后 `validate.sh` 总耗时明显下降（目标约 60–80 秒，受机器负载影响只作记录，不作硬门槛）。

## Contract

- 模板构建与复制的逻辑写在测试文件内（或一个测试专用 helper 模块，名字以 `test_` 开头之外的 `_fixture` 结尾时需确认
  不被 `validate.sh` 当成测试入口、不触发 `check-no-parallel-surface.py`）；不新增运行时依赖。
- 复制后的仓库不得指向模板目录：所有 `remote.origin.url` 指向本测试自己的远端副本；测试结束清理临时目录。
- `test_module_insert.py` 中继承 `PromotionFixture` 的类不需修改即可受益；其自有 `setUp` 若另建 git 夹具，在第二步处理。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py
python3 -B plugins/spec-guard/hooks/test_module_insert.py
python3 -B plugins/spec-guard/hooks/test_proposal_submit.py
python3 -B plugins/spec-guard/hooks/test_proposal_publication.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- 每步：测试数量与名称不变；两种 Python 下全绿；第 5 条的等价性对比（失败集合相同）；第 6 条的计时与剖析记录写入提交说明。
- 复制隔离：任意一个测试对其远端的 push 不影响同类其他测试（现有测试已覆盖多次 push 的场景，全绿即证明）。

## Boundaries

- Always：断言逐字不变；每个测试独立目录；不改产品代码；两种 Python 下验证。
- Ask first：删除或合并测试；改动 `validate.sh` 的测试列表或并行执行测试。
- Never：为提速跳过、弱化或删除断言；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- `test_proposal_promotion_proof.py` 的 `setUp` 总耗时降低 ≥70%，失败集合等价性成立。
- 两步完成后四个文件全绿、测试数不变、等价性成立，`validate.sh` 总耗时明显下降并记录数值。
- 两种 Python 下三条最小验证通过。

## Open questions

- 无（第 4–6 条已于 2026-10-01 经用户确认）。
