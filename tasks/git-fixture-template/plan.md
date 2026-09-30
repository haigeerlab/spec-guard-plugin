# Plan: git-fixture-template

依据 [`spec/git-fixture-template.md`](../../spec/git-fixture-template.md)。两个 task 串行，每个一条提交；只改测试。

每个 task 的验收：两种 Python 下相关测试与三条最小验证全绿；测试数不变；等价性对比——把改造前后的测试文件分别放到
v0.34.0 的 hook 上跑，失败的测试名集合相同；计时与 cProfile 数值写入提交说明。

## Task 1：晋级证明测试的夹具模板

- `test_proposal_promotion_proof.py`：`PromotionFixture` 改为类级模板 + 每测试复制 + 修正 origin；`test_module_insert.py`
  中继承它的类随之受益（不改其断言）。
- **验收：** `setUp` 总耗时降低 ≥70%；等价性成立；全绿。

## Task 2：其余三个测试文件

- `test_proposal_submit.py`、`test_proposal_publication.py`、`test_module_insert.py` 自有的 git 夹具，用同一办法。
- **验收：** 等价性成立；全绿；`validate.sh` 总耗时记录（改造前约 135 秒）。

## Checkpoint：完成

- 两种 Python 下全部检查；逐条核对 Spec 成功标准；勾选随模块 PR 一起提交。
