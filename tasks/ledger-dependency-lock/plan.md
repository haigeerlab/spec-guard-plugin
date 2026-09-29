# Plan: ledger-dependency-lock

依据 [`spec/ledger-dependency-lock.md`](../../spec/ledger-dependency-lock.md)。四个 task 串行，每个 task 一条提交；
先写能在当前代码上失败的测试并记录失败输出，再修改到通过。单元测试沿用 `test_local_ledger_runtime.py` 的
`fake_npm` 脚手架，不访问网络；只有 Task 1 生成 lockfile 和 Task 4 的真实安装验证会访问 npm 注册表。

每个 task 完成时都运行三条最小验证：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Task 1：生成 lockfile 并加防漂移测试（L1）

- 在临时目录运行 `npm install --package-lock-only --ignore-scripts epiq@1.11.0`（只读注册表元数据，不下载安装包、
  不执行代码），把得到的 `package.json`（只声明 `epiq: 1.11.0`）与 `package-lock.json`（lockfileVersion 3）放到
  `plugins/spec-guard/locks/local-ticket-ledger/`。
- 测试：版本常量、`package.json` 与 lockfile 根依赖三者一致；lockfile 中每个包都有 `resolved` 与 `integrity`；
  文件缺失或任何一处漂移时测试失败（用临时副本构造反例）。
- **验收：** 防漂移测试通过，且对三种反例（版本不一致、缺 integrity、文件缺失）各自失败。
- **验证：** `test_local_ledger_runtime.py`；`scripts/check-manifests.py`；`release-package.py` 相关测试。
- **文件：** `locks/local-ticket-ledger/package.json`、`package-lock.json`、`test_local_ledger_runtime.py`。

## Task 2：按 lockfile 安装（L2）

- `install_command` / `install_runtime`：把两个锁定文件复制进临时安装目录，在该目录运行
  `npm ci --ignore-scripts --no-audit --no-fund`；成功后运行时目录中保留与插件一致的 `package-lock.json`。
- 缺插件 lockfile、`npm ci` 失败、或结果不满足现有校验时，不换上目录，报告原因。
- 测试：安装命令与工作目录正确，两个锁定文件被复制进去；缺 lockfile 时拒绝且不创建目录；失败路径清理临时目录。
  现有的安装测试按新命令更新。
- **验收：** 新旧安装测试全部通过；源码中不再出现 `npm install` 加包名的安装方式。
- **验证：** `python3 -B` 与 `/usr/bin/python3 -B` 各跑一次 `test_local_ledger_runtime.py`。
- **文件：** `local_ledger_runtime.py`、`test_local_ledger_runtime.py`、`CHANGELOG.md`。

## Task 3：lock 状态与替换未锁定的运行时（L3）

- `runtime_status` 增加 `lock: locked | unlocked`，`state` 语义不变。
- `install_runtime`：`ready` 加 `locked` 时照旧拒绝；`ready` 加 `unlocked` 时，只有显式替换参数（CLI
  `--replace-unlocked`）才替换：先在临时目录完成锁定安装与校验，再原子换下旧目录，任何一步失败都保留旧运行时。
- `commands/local-ticket-ledger.md` 与 `skills/local-ticket-ledger-ops/SKILL.md`：展示 `lock`；替换前必须经用户明确确认。
- 测试：`lock` 两种取值；无参数时拒绝替换；带参数时成功替换；替换中途失败时旧运行时逐字节不变；替换不触碰运行时目录以外的路径。
- **验收：** 以上测试在修改前失败、修改后通过。
- **验证：** 两种 Python 各跑一次 `test_local_ledger_runtime.py`；`test_ticket_entry.py`；`check-command-parity.py`。
- **文件：** `local_ledger_runtime.py`、`test_local_ledger_runtime.py`、命令与 skill 文档、`CHANGELOG.md`。

## Task 4：文档与真实安装验证（L4）

- `references/local-ticket-ledger-runtime.md`：锁定安装、`lock` 状态、替换方法、维护者重新生成 lockfile 的步骤。
- `spec/collaboration-messaging.md` 与 `references/collaboration-runtime.md`：XATS 两个包未锁定的剩余风险与日落关系。
- 真实安装验证（结果写入交付说明，不进 `validate.sh`）：在 scratchpad 临时目录用真实 npm 调用 `install_runtime`，
  `status` 为 `ready` 加 `locked`；再用篡改了某个 `integrity` 的 lockfile 副本安装，确认失败且没有目录被换上。
  不触碰本机 `~/.spec-guard` 下的运行时。
- **验收：** 真实安装成功、篡改安装失败，两者的输出都记录下来。
- **文件：** 两份参考文档、`spec/collaboration-messaging.md`、`CHANGELOG.md`。

## Checkpoint：完成

- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过；CI 两个检查通过。
- 逐条核对 Spec 的 Success criteria；`todo.md` 全部勾选，阶段变为 DONE；向用户汇报，由用户决定推送与合并。

## 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| lockfile 与注册表上的实际包不符（例如包被撤回） | 中 | `npm ci` 会直接失败并报告，不会装上别的版本；Task 4 的真实安装验证当场确认 |
| 替换运行时时误删数据 | 高 | 运行时目录只含 npm 依赖；原子替换、失败保留旧目录；测试断言只动运行时目录 |
| lockfile 体积大、审阅困难 | 低 | 它是生成物；防漂移测试守住关键不变量，升级流程写进文档 |
