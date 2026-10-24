# Plan: review-residual-fixes

<!-- spec-guard: review approved -->

依据 [`spec/review-residual-fixes.md`](../../spec/review-residual-fixes.md)（2026-10-24 用户在本会话批准：「批准 review-residual-fixes 的 Spec，
假设 7～9 也同意」）。评审节奏为分开审，本 Plan 单独交审。分支 `claude/v0.84.2-residual-fixes`，worktree `distracted-morse-46ef70`，
从 `origin/main`（`01420620`）切出。单模块在本会话做，不用 module-crew；本模块自己升版本到 0.84.2 并写 CHANGELOG。

## Overview

十项修复按「改代码的先红后绿，改文字的直接改」排成 8 个 task。每个代码 task 先在对应回归里加用例、在未改代码上跑红，再改到绿，
最后在草稿副本里把修复改回去确认新用例变红（手工变异，不入库）。每个 task 单独提交，走 `scripts/verify-and-commit.sh`。

## Architecture Decisions

1. **C2 create 核验放进 `verify_documentation`，不改 `_check`。** `_check` 是 update 的 git 差异判定；create 只查存在，另写一个小函数
   `_check_created(project, outcome, artifact, attention)`。路径来自 `parse_impact` 已返回的 `impact.delivery[concern].artifact`，
   去掉 `#` 之后部分；外部判据复用 `EXTERNAL`。「在项目内的普通文件」= `resolve()` 后在项目根之下、`is_file()` 且路径本身不是符号链接。
2. **C3 用 `managed-block.py replace --check`，不调整 setup-convention 的步骤顺序。** 给 `replace` 加一个只做拒绝判定的选项：会拒就
   照现在的 `_refuse` 输出并退出 3，否则退出 0、什么都不写也不打印。setup-convention 在 `mkdir` 之前、`HAS_BLOCK && REPLACE && !DRY`
   时调用它。拒绝判定只有一份实现，不在 shell 里复制；输出顺序与成功路径逐字节不变。
3. **C6 共用定义放在 `local_ledger_runtime.py`：** `PROJECT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")`，三处都用 `PROJECT_ID.fullmatch(...)`。
   bind 已导入 runtime；journal 经 inventory 间接依赖 runtime，直接导入不会成环（runtime 只导入 `state_paths`）。
4. **C5 只改 `_visible` 与 `FENCE`。** `FENCE` 改为捕获开围栏的字符与长度（`^ {0,3}(`{3,}|~{3,})`），`_visible` 记住开围栏，
   只有同字符、长度不少于它、后面只有空白的行才闭合。
5. **C4 只在 `info.update(facts=[...])` 末尾追加一个布尔。** `state_key` 是对 facts 求摘要，追加会让所有项目的状态码变一次——发版后每个
   会话第一轮会出一次完整内容。这是可接受的一次性代价（与 0.84.0 引入状态码时相同），交审时说明。
6. **C1 的英文提醒逐字照 Spec C1。** 测试断言关键词，不断言整句。

## Task List

### Task 0：提交已批准的 Spec、Plan 草稿与能力图

- 内容：能力图新行与变更记录、`spec/review-residual-fixes.md`（approved）、本 Plan 与 todo（pending）。
- 验证：`verify-artifacts` 0 失败；快档 `verify-and-commit.sh`。

### Task 1：review-mark 提醒（C1，先红后绿）

- 文件：`hooks/review_mark.py`、`hooks/test_review_marker.py`。
- 先改 `test_review_marker.py:255-261` 的断言为新说法（含 `collaboration plugin`、`current conversation`，不含 `decision hub`、
  `session-protocol`、`item number`），加一条读源码断言三词不在 `review_mark.py` 里 → 红；改提醒与文件头 → 绿。
- 验收：AC1。

### Task 2：create 类文档核验（C2，先红后绿）

- 文件：`hooks/documentation_verification.py`、`hooks/test_documentation_verification.py`。
- 新增三例：存在 → `ready`/`present`；不存在 → `attention`/`missing` 且 attention 含路径；外部 → `unverified`。另加目录与符号链接各一例算 `missing`。
- 变异：去掉 create 分支，「不存在」用例变红。验收：AC2。

### Task 3：setup-convention 先校验（C3，先红后绿）

- 文件：`hooks/managed-block.py`、`hooks/setup-convention.sh`、`hooks/test-setup-teardown.sh`。
- 在 `test-setup-teardown.sh:96` 那一例旁新增：已有声明块含手改行、项目里没有 `spec/` `tasks/` `.agent/`，`--replace` 不带
  `--accept-removals` → 退出 1，三个目录都不存在，目标文件 `cmp` 不变 → 红；加 `--check` 与调用 → 绿。现有 `--accept-removals` 用例照旧。
- `.sh` 改动跑 ShellCheck。验收：AC3。

### Task 4：状态码含文档基线（C4，先红后绿）

- 文件：`hooks/module_stage.py`、`hooks/test-phase-guard.sh`。
- 在 quiet-injection 那段旁新增：同一项目停在最终 gate，先无基线跑一次取状态码，建 `docs/DOCUMENTATION-BASELINE.md` 再跑，两次状态码不同、
  第二次输出含「文档核验」行（带 `--last-state` 为第一次的码）→ 红；追加 facts → 绿。现有状态码用例不改。
- 同一提交改 C10 的注释（`module_stage.py:351-353`）。验收：AC4。

### Task 5：围栏配对（C5，先红后绿）

- 文件：`hooks/module_scope.py`、`hooks/test_module_scope.py`。
- 新增两例（`~~~` 包 ```` ``` ````；四个反引号包三个），各自后面的真「并行边界」能读到、示例里的假一节不读 → 红；改 `FENCE` 与 `_visible` → 绿。
- 验收：AC5。

### Task 6：projectId 共用判据（C6，先红后绿）

- 文件：`hooks/local_ledger_runtime.py`、`hooks/local_ticket_bind.py`、`hooks/local_ticket_journal.py`、`hooks/test_local_ledger_runtime.py`。
- 新增：`journal_path` 接受 `my-ledger_1`，拒 `a/b`、65 位、`é1`；`PROJECT_ID` 存在且 bind、journal 源码不再含 `isalnum` → 红；改 → 绿。
  bind 的判定在函数中段，不单独构造预览文件，用源码断言加 `PROJECT_ID` 行为断言覆盖。
- 验收：AC6。

### Task 7：history-migration 清理（C7，先红后绿）

- 文件：`hooks/history-migration.py`、`hooks/test-history-migration.sh`。
- 新增：在 `$TMP` 下复制一份 hooks 目录，把副本里的 `capability-history.py` 换成退出 1 的替身，用副本的 `history-migration.py import --confirm`
  → 退出 1、项目根无 `.history-migration-*` → 红；在 except 里删除临时文件（`event_path` 先置 `None`，删除失败忽略）→ 绿。
- 验收：AC7。

### Task 8：规则文字（C8、C9）

- 文件：`skills/spec-guard-ops/SKILL.md`、`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`。
- SKILL.md:357 按 C8 改；workflow-checkpoints「批量插入之后」末尾加 C9 那句，`test_workflow_checkpoints.py:683` 的短语表加「靠本会话记得」。
- 验收：AC8。

### Checkpoint 1（report）：三套核心回归

- 全档 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿，ShellCheck 无告警。

### Task 9：版本号与 CHANGELOG 0.84.2

- 两份 `plugin.json`、README 中英里的 0.84.1 改 0.84.2（`git grep` 已查：只有这四个文件；marketplace 不带版本）；CHANGELOG 新开 0.84.2 一节（修复逐条、来源写 QV6KWMJ、HT9AJX2）。
- `interface.json` 不动。验收：AC9。

### Checkpoint 2（gate）：最终验收

- 呈现每项以前／现在、先红后绿与变异核对、全档结果、改动文件与提交表。用户通过后：发版前先告诉 ecosystem-lead 判断影响面；
  推送与开 PR 由用户确认，合并由用户进行。

## 风险

- **C4 让所有项目的状态码变一次**（见决定 5）：升级后每个会话第一轮出一次完整注入，之后照常。
- **C6 收紧了非 ASCII 字母数字**：本机已有账本的 projectId 都是 runtime 认可的格式（runtime 早就只认 ASCII），bind/journal 之前也走不到这类 id，
  不会有现存数据因此失效。
- **C3 的 `--check` 是 managed-block 的新选项**：只给 setup-convention 内部用，不写进命令说明。
