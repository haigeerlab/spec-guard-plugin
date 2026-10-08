# Plan: runtime-state-layout

依据 [`spec/runtime-state-layout.md`](../../spec/runtime-state-layout.md)（假设经用户 2026-10-08 确认，根目录按实测修正）。
本仓库 `reviewCadence` 为 `combined`：Spec 与本 Plan 一起评审、一次批准。分支 `claude/runtime-state-layout`，
从 `1a8347f`（`module-suspend` 合并）开出。版本号与发版在本批收尾时另行决定，不在本 Plan 内。

## 依赖与顺序

`state_paths.py` 是唯一来源，使用方、检查器和报告都依赖它，所以先做；检查器在使用方改完后才能对真实代码通过。

## Task List

### Task 1：`state_paths.py` 与单测（先红）

新增 `hooks/test_state_paths.py`（Spec「Testing strategy」第 2 条中与路径计算相关的部分）并确认失败，再实现
`hooks/state_paths.py`。变异：回退条件写反、忽略环境变量。

- 验收：单测全绿，两处变异被抓到。
- 文件：`hooks/state_paths.py`、`hooks/test_state_paths.py`。

### Task 2：五个使用方改用 `state_paths`（先红）

在 `test_state_paths.py` 加"五个默认值在临时 HOME 下与现在逐字节相同、两个迁移项在只有旧目录时取旧目录"的用例，确认失败，
再改 `hosted_ticket.py`、`proposal_closeout.py`、`local_ledger_runtime.py`、`proposal_closeout_local.py`、`local_ticket_journal.py`。

- 验收：新用例与既有 hosted ticket、proposal closeout、local ledger、portability 单测全部通过。
- 文件：上述五个模块与 `test_state_paths.py`。

### Task 3：检查器 `check-state-paths.py`（先红）

`scripts/test-checkers.sh` 加正样例、反样例（带行号）、空目录"没找到"三例并确认失败，再实现检查器并接入 `validate.sh`。
变异：漏扫 `expanduser`。

- 验收：检查器回归全绿；对真实仓库通过。
- 文件：`scripts/check-state-paths.py`、`scripts/test-checkers.sh`、`scripts/validate.sh`。

### Checkpoint 1（report）：全部单测与检查器回归全绿，ShellCheck 无警告

### Task 4：`config show` 报告根目录与回退中的旧位置（先红）

`test_project_config.py` 加用例：输出根目录行；`SPEC_GUARD_STATE_DIR` 时注明来源；有旧位置回退时多一行，没有时不输出。
先红，再改 `project_config.py`；同步 `commands/config.md` 与 `spec-guard-ops` 的 config 一节各一句。

- 验收：单测全绿，command-parity 等检查器通过。
- 文件：`hooks/project_config.py`、`hooks/test_project_config.py`、`commands/config.md`、`skills/spec-guard-ops/SKILL.md`。

### Task 5：文件布局文档与 CHANGELOG

`docs/design.md` 新增 `## File layout`（四类位置）；CHANGELOG `## [未发布]` 记一条。本机实跑 `config show`，确认根目录与
（本机两个旧目录都为空、新目录不存在时）回退行如实显示。

- 验收：`validate.sh` 通过；实跑输出与本机事实一致，且没有任何文件被移动或删除。
- 文件：`docs/design.md`、`CHANGELOG.md`。

### Checkpoint 2（gate）：模块评审

推送前在同一条 `&&` 链里跑 `validate.sh`、两套 hook 断言、相关单测与 ShellCheck；pre-push 钩子兜底。
批准本 Plan 即授权推送本分支并开本模块的 PR；合并由用户进行。

## 风险

| 风险 | 应对 |
|---|---|
| 改默认路径让已连好的账本断开 | 账本运行时与交接日志默认值逐字节不变，有用例守住 |
| 意图或收尾记录分散在两个目录导致重复写入 | 整目录回退：同一类记录只在一个目录；不合并、不搬运 |
| 检查器误报读取宿主配置的正常用法 | 允许清单只放读宿主配置与 epiq 自身目录；反样例证明其余会被拦下 |
