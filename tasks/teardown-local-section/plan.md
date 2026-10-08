# Plan: teardown-local-section

依据 [`spec/teardown-local-section.md`](../../spec/teardown-local-section.md)（假设经用户 2026-10-08 确认）。
分支 `claude/teardown-local-section`。本仓库评审节奏为合审：Spec 与本 Plan 一次批准。

## Task List

### Task 1：回归先行（先红）

在 `test-setup-teardown.sh` 加用例：本地段内容留在原位、本地段标记消失、state 停用；`--dry-run` 列出手写行（带
`[needs --accept-removals]`）与本地段保留行数且不改文件；有手写行时不带参数退出 1、指令文件与 state 逐字节不变，带
`--accept-removals` 后移除且本地段仍在；本地段标记两段 / 颠倒 / 不成对时拒绝；无块时 `--accept-removals` 退出 2；
Codex 宿主一例。现有代码上全部为红。

### Task 2：managed-block 与 teardown-convention 实现

`managed-block.py remove` 增加 `--known`、`--accept-removals`、`--dry-run`，复用 `local_section` 与 `_text`；
`teardown-convention.sh` 传入现行模板与派活规则段、打印预览、拒绝时退出 1 且不碰 state。测试转绿，原有往返用例不变。
变异：去掉本地段保留；去掉删除闸门；忽略 `--known`（派活规则段用例变红）。

### Task 3：文档

命令（含 argument-hint）、Codex skill teardown 一节、`docs/workflow.md`；命令与 skill 参数一致性检查通过。

### Checkpoint 1（report）：全部套件通过，ShellCheck 无告警

### Task 4：CHANGELOG + 0.54.2 + macOS 校验

### Checkpoint 2（gate）：模块评审

本 Plan 获批即授权推送本分支并开本模块 PR；合并由用户进行。

### Task 5：发版后证据

按 `docs/release-process.md` 发 0.54.2；两边已安装副本上用临时项目验证：本地段留在原位、手写行触发拒绝且 state 不变、
加参数后移除。
