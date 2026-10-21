# Plan: gate-tick

<!-- spec-guard: review approved -->

依据 [`spec/gate-tick.md`](../../spec/gate-tick.md)。能力图新行和 Spec 已一起批准，本 Plan 单独审。
分支 `claude/gate-tick`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `cbf3f45`（0.82.0 证据 #398 合并）开出。
本模块一个 PR，含版本号 0.83.0。批准本 Plan 即授权推送分支并开本模块的 PR；合并由用户进行，发版在合并后另问。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：gate_tick.py 与测试（先红）

先写 `hooks/test_gate_tick.py`，覆盖 Spec「Testing strategy」各条（正、已勾过、反、判据一致），确认失败（脚本还不存在）。
再写 `hooks/gate_tick.py`：参数与能力图校验照 `review_mark.py`；判据只调 `module_stage` 的 `gate_checkpoints`／`at_final_gate`；
预览打印要勾的行和勾完剩余未勾项数；`--confirm` 用 `_write_atomic` 只改那一格并保留行尾。在 `scripts/validate.sh` 登记新测试。

- 验收：新测试先红后绿（AC1～AC3）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_gate_tick.py`、`/bin/bash scripts/validate.sh --quick`。
- 文件：`hooks/gate_tick.py`、`hooks/test_gate_tick.py`、`scripts/validate.sh`。

### Task 2：接口 1.7（先红）

`scripts/test-checkers.sh`（或检查器自己的回归）先加：`gateTick` 一节缺失或脚本路径不存在时报错。然后在 `interface.json` 加 `gateTick`、
`interface` 改为 1.7，`scripts/check-interface.py` 的 `ENTRIES` 加上它并核对脚本路径。

- 验收：检查器新断言先红后绿；`check-interface.py` 通过（AC4）。
- 文件：`interface.json`、`scripts/check-interface.py`、检查器回归文件。

### Task 3：文档、CHANGELOG 与版本号

列出接口或脚本清单的文档（如有）补一行；CHANGELOG 新开「[0.83.0]」段；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.83.0。

- 验收：`verify-and-commit.sh` 全档通过（AC5）。
- 文件：`CHANGELOG.md`、两份 `plugin.json`、`README.md`、`README.en.md`，以及受影响的文档。

### Checkpoint 1（report）：变异核对

在完整仓库副本上把判据换成「唯一未勾项」，确认「最终验收后还有发版后核对」用例变红；把预览改成也写文件，确认「预览不改文件」用例变红。
结果记入 todo。

### Checkpoint 2（gate）：模块最终验收

按交审小项呈现验证结果、AC 逐条证据、改动文件与提交表。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 中：写文件的命令，一旦判错会勾错行。测试覆盖「只改那一格、其余逐字不变」与各拒绝情形；判据不另写，只调 `module_stage`。
- 低：接口升到 1.7，下游 module-crew 要等发版后才用；发版后通知对方。

## 返工 1（2026-10-22）

0.83.0 发版后实测发现：预览模式打印的那一行已经是勾完后的样子（`[x]`），文件其实没改，但读输出的人容易误以为已经勾了。
用户选了修这一处（原话「1」，对应「gateTick 预览的显示」）。属于已批准范围内的修正：只改预览的打印，退出码、判据与写入不变。

- Task 4：`test_gate_tick.py` 先加断言（预览打印原样的 `[ ]` 行，并另起一句写出将改成的样子），确认失败；再改 `gate_tick.py`。
  验证：`test_gate_tick.py` 与全档校验。
- Checkpoint 3（gate）：返工验收；推送与开 PR 在此由用户确认。
