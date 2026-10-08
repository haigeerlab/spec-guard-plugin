# Plan: convention-block-local-lines

依据 [`spec/convention-block-local-lines.md`](../../spec/convention-block-local-lines.md)（假设经用户 2026-10-08
确认）。分支 `claude/convention-block-local-lines`。本仓库评审节奏为合审：Spec 与本 Plan 一次批准。

## Task List

### Task 1：回归先行（先红）

在 `test-setup-teardown.sh` 加用例：本地段保留并移到新块末尾；`--replace --dry-run` 列出 will remove / will add；
块内有手写行时不带 `--accept-removals` 退出 1 且文件逐字节不变；带上后替换；`--no-dispatch` 只删规则段不需要接受；
本地段标记不成对、颠倒或重复时拒绝；`--accept-removals` 单独给出是用法错误。现有代码上全部为红。

### Task 2：managed-block 与 setup-convention 实现

`managed-block.py` 增加本地段读取与差异计算（`diff` 动作或等价接口），`replace` 保留本地段；`setup-convention.sh`
打印预览清单、执行删除闸门、解析 `--accept-removals`。测试转绿；首次安装与 teardown 往返用例不变。变异：去掉本地段
保留；去掉删除闸门；把规则段的行也算作需接受的删除。

### Task 3：文档

命令、Codex skill setup 一节、`docs/workflow.md` 写明本地段与 `--accept-removals`；命令与 skill 的参数一致性检查通过。

### Checkpoint 1（report）：全部套件通过，ShellCheck 无告警

### Task 4：本仓库 AGENTS.md 迁移

把 5 行手写规则移进本地段，运行新的 `--replace --dry-run` 并把预览给用户看（这一步是 gate：用户确认后才执行真正替换）；
替换后块内模板部分与现行 Codex 模板一致，阶段提示与 verify-artifacts 照常。

### Task 5：CHANGELOG + 0.54.1 + macOS 校验

### Checkpoint 2（gate）：模块评审

本 Plan 获批即授权推送本分支并开本模块 PR；合并由用户进行。

### Task 6：发版后证据

按 `docs/release-process.md` 发 0.54.1；两边已安装副本上用临时项目验证：本地段保留、手写行触发拒绝、加参数后替换。
