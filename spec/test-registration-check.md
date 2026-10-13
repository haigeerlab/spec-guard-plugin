# Spec: test-registration-check

<!-- spec-guard: review approved 833de266b61e -->

## Objective

`scripts/validate.sh` 用一张显式列表逐条写出要跑的测试文件，没有通配，也没有按文件名发现。新增一个测试文件而忘了往
列表里加一行时，什么都不会报错：这个文件不在 CI、pre-push 和 verify-and-commit 的任何一处运行，它断言的行为等于没有
回归保护。

2026-10-13 核对时发现三个这样的文件：`test_module_suspend.py`、`test_project_config.py`、`test_state_paths.py`。它们都在
2026-10-08 随各自模块加入，从第一天起就没被任何检查运行过，五天里没人发现。三个文件已另行补登记；本模块加一个检查器，
让同样的遗漏在提交时就报错，不再靠人记得。

读者：本仓库维护者。

## 现状（2026-10-13 实测）

- 运行测试的入口只有三处：`scripts/validate.sh`、`scripts/verify-and-commit.sh`、`.github/workflows/ci.yml`。三处都按
  完整路径点名测试文件；`scripts/run_tests_parallel.py` 只在一个文件内部按测试类分进程，不发现文件。
- `plugins/spec-guard/hooks/`、`scripts/`、`evals/` 顶层共有 61 个 `test_*.py` 与 `test-*.sh`。补登记之后，没被上述入口
  点名的只剩三个 `*_acceptance.py`。
- 这三个验收测试需要外部运行时（`SPEC_GUARD_EPIQ_RUNTIME`），故意不进常规校验；`scripts/check-acceptance-wired.py` 已经
  要求它们在运行器或维护者文档里有运行指引。
- `evals/dispatch-cost/` 下另有 15 个 `test_*.py`，是一道评测题目的素材（种子项目、参考答案与隐藏测试），由评测脚本在
  临时目录里使用，不是本仓库的回归。

## Assumptions

以下已由用户 2026-10-13 确认：

1. **做法**：新建 `scripts/check-tests-registered.py`（只依赖标准库，Python 3.9 可用），写法与
   `check-acceptance-wired.py` 一致：可传入另一个仓库根供测试夹具使用，默认检查本仓库。
2. **查哪些文件**：`plugins/`、`scripts/`、`evals/` 下（含子目录）文件名形如 `test_*` 或 `test-*`、扩展名为 `.py` 或
   `.sh` 的文件，按文件系统查找。所以还没 `git add` 的新测试文件也会被查到，这正是最容易漏登记的时刻。
3. **两类不查**，都写在检查器里并各带一句原因：
   - 文件名含 `acceptance` 的测试：归 `check-acceptance-wired.py` 管，这里不重复要求。
   - `evals/dispatch-cost/` 目录：评测题目的素材。
4. **什么算已登记**：文件相对仓库根的完整路径出现在某个运行器的非注释行里，并且路径前后不是文件名字符。
   - 只写文件名不算，必须是完整路径。
   - 整行以 `#` 开头的注释行不算，所以被注释掉的那一步等于没登记。
   - `test_foo_bar.py` 已登记不能让 `test_foo.py` 蒙混过关，反过来也一样。
5. **运行器范围**：只认 `scripts/validate.sh` 与 `.github/workflows/*.yml`、`*.yaml`。`scripts/verify-and-commit.sh` 不算：
   它只在本机提交时运行，只改文档的提交还会跳过它的全套，一个只在那里被点名的测试 CI 永远不会跑（用户 2026-10-13
   决定收窄）。它现在点名的四个文件都同时在 `validate.sh` 或 CI 里，收窄不影响现状。
6. **没找到不算通过**（docs/lenses.md A5）：一个测试文件都没查到，或一个运行器都读不到，判失败并说明原因。
7. **失败时的输出**：列出每个没登记的文件的完整路径，并写明怎么改（往 `scripts/validate.sh` 的回归段加一步；若它
   需要外部运行时，按验收测试命名并在 `docs/maintainer-workflow.md` 写运行指引）。通过时输出一行，写明查了多少个文件。
8. **接入位置**：`validate.sh` 的结构检查段，紧跟 `check-acceptance-wired.py`。这一段 `--quick` 也跑，所以只改文档的
   提交也会查到；检查器本身应在 1 秒以内。
9. **回归**：在 `scripts/test-checkers.sh` 加一组用例，正反都有：
   - 全部已登记时通过；
   - 有一个没登记时失败，输出里有那个文件的路径；
   - 只在注释行里出现时失败；
   - 只登记了名字更长的同前缀文件时失败；
   - 只在 CI 工作流里登记时通过；
   - 没登记的验收测试不报错；
   - 豁免目录里的测试不报错；
   - 一个测试文件都没有时失败；
   - 读不到任何运行器时失败。

   每条判据手工改坏一次，确认对应用例变红，结果记进 todo。
10. **文档**：`docs/maintainer-workflow.md` 加一两句，说明新增测试文件必须登记、由哪个检查器看守。CHANGELOG 不单独
    发版，留到下次发版时写进“维护者工具”。
11. **范围**：只新增检查器、它的回归、`validate.sh` 里的一行调用和一处文档说明。不改任何测试与被测代码，不改插件
    发布包（`scripts/` 不进包），不发版。

## Requirements

1. 新建 `scripts/check-tests-registered.py`，按假设 2–7 查找、判定并输出；退出码 0 表示全部已登记，非零表示有遗漏或
   没找到可查的东西。
2. `scripts/validate.sh` 在结构检查段调用它（假设 8），`--quick` 同样运行。
3. `scripts/test-checkers.sh` 加入假设 9 的用例。
4. `docs/maintainer-workflow.md` 补充说明（假设 10）。
5. 在本仓库当前状态下检查器通过；临时去掉 `validate.sh` 里任意一个已登记的测试步骤后检查器失败并指出该文件，恢复后
   再次通过。这次实测与 Python 3.9（`/usr/bin/python3`）的结果记进 todo。

## Commands

```bash
python3 scripts/check-tests-registered.py
/usr/bin/python3 scripts/check-tests-registered.py
/bin/bash scripts/test-checkers.sh
/bin/bash scripts/validate.sh --quick
/bin/bash scripts/validate.sh
```

## Boundaries

- Always：没登记的文件逐个列出完整路径；没找到可查的东西时判失败。
- Ask first：推送、PR；扩大或缩小豁免范围；因检查器报错而需要改某个测试或运行器的时候。
- Never：为了让检查器通过而把文件加进豁免；把一次历史运行记录（`docs/reports/`、CHANGELOG）当作已登记。
- 不保证：
  - 被点名的那一步真的会执行，例如写在永远不成立的条件分支里；
  - 测试文件内部的每个用例都会跑（`run_tests_parallel.py` 自己核对用例数）；
  - 不按 `test_*`／`test-*` 命名的自检，例如各脚本的 `--selftest`。

## Success criteria

1. 本仓库当前状态下检查器与完整 `validate.sh` 通过，CI 绿。
2. 去掉任意一个已登记测试的步骤，`validate.sh --quick` 就失败并报出那个文件。
3. `test-checkers.sh` 里假设 9 的用例全过，且每条判据都被手工改坏验证过一次。

## Open questions

无。
