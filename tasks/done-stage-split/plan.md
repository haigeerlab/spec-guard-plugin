# Plan: done-stage-split

依据 [`spec/done-stage-split.md`](../../spec/done-stage-split.md)。三个 task 串行，每个 task 一条提交；先写能在当前
代码上失败的测试并记录失败输出，再修改到通过。全部在临时项目上测试，不访问网络。

每个 task 完成时都运行三条最小验证，并用 `/usr/bin/python3` 再跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

依赖关系：Task 2 复用 Task 1 在 `module_stage.py` 中抽出的项目级判定；Task 3 描述前两者的最终行为。

## Task 1：阶段判定拆成 MODULE_DONE 与 DONE（S1）

- `module_stage.py`：把"项目级阶段是什么"抽成一个可复用的函数（供 Task 2 使用），`describe` 按它输出：
  - 全部模块完成 → `DONE`，沿用现有提示；`activeModule` 指向已完成模块时加一行"可以清除"的说明；
  - `activeModule` 指向已完成模块且仍有未完成模块 → `MODULE_DONE`，下一步点名 Build order 中第一个未完成模块及其阶段；
  - 其余阶段输出不变。
- `test-phase-guard.sh`：新增情况 A（`MODULE_DONE`、点名 `beta`、不含 `**DONE**`）与情况 B（`DONE`、add-module、
  可清除说明）的断言；情况 C 与已有断言保留。
- `CHANGELOG.md` Unreleased：新增阶段说明与兼容性。
- **验收：** 新断言在当前代码上失败、修改后通过；已有 26 个用例全部保留并通过。
- **文件：** `module_stage.py`、`test-phase-guard.sh`、`CHANGELOG.md`。

## Task 2：module-insert 写入后的阶段提示一致（S2）

- `module-insert.py`：`--confirm` 后的 `当前阶段提示` 改用 Task 1 的项目级判定，不在本文件复制算法；检查点校验
  （`_current_module`、`_half_done`）与预览不变。
- `test_module_insert.py`：`activeModule` 指向已完成模块、插入新模块后，提示与 phase-guard 一致；全部完成时仍为 `DONE`。
- **验收：** 新测试在当前代码上失败、修改后通过；已有 module-insert 测试全部通过。
- **验证：** 两种 Python 各跑一次 `test_module_insert.py`。
- **文件：** `module-insert.py`、`test_module_insert.py`。

## Task 3：文档（S3）

- `commands/phase.md`、`docs/workflow.md`：阶段表新增 `MODULE_DONE`，`DONE` 只描述全部完成。
- `README.md` 第 74 行、`spec/phase-and-verification.md` 的阶段列表补上 `MODULE_DONE`。
- **验收：** 全仓 `git grep -w DONE` 中不再有把 DONE 描述成"当前模块已完成"的文字；`check-command-parity.py` 与 `validate.sh` 通过。
- **文件：** 上述四份文档。

## Checkpoint：完成

- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过；CI 两个检查通过；逐条核对 Spec 的成功标准；阶段变为 DONE。
