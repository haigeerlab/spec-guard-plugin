# Plan: history-slim

<!-- spec-guard: review approved -->

依据 [`spec/history-slim.md`](../../spec/history-slim.md)（2026-10-22 批准，事项 C53）。Spec 的两个待确认项按用户答复定为：
**D7 A**——audit 与 correct 都去掉（逐字确认）；**D8 A**——`event.at` 不做格式校验，契约写明不作为时间证据。

分支 `history-slim`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/history-slim`，从集成分支 `crew/fix-batch` 开出。
module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调整批合完后统一改，
本模块把拟写的更新说明记在 todo 末尾。

所需工具：无 UI 改动，不需要浏览器或电脑操作；不访问远端，不新增依赖。

## 实现要点

- **动词集合**：`main()` 的可接受集合去掉 `audit`、`correct`，删掉两个分支；用法行同步去掉。未知动词已有的处理是打印用法、退出码 2，
  不读账本（参数检查在 `load()` 之前），所以这两个动词被拒时账本字节不变。
- **删除的代码**：`audit()`、`find_audit_finding()`、`append_correction()`、`correction_identity()`（只被 audit 用）、`load_json()`（只被
  `append_correction` 用），以及删完后没人引用的 `import`／常量。`check_correction()` 与 `AUDIT_TIME`、`SHA256`、`MODULE_STATUS` 保留
  （校验已有补正记录）。`write_atomic()` 仍被 `create` 用，保留。删前逐个 `grep` 确认引用，删后靠三份历史测试与
  `python3 -m py_compile` 兜底。
- **测试改造**（`test-capability-history.sh`）：现有 audit/correct 正向用例（约第 127～231 行）删掉；补正记录的校验用例（第 233 行起的
  「补正指向不存在的事件即无效」）改为直接写一份带补正记录的账本 JSON，不再依赖 `correct` 生成。新增：
  1. `audit`、`correct --confirm` 都退出码 2，账本 `shasum` 前后一致；
  2. 带合法补正记录、`at` 为 `now`／`imported` 的账本，`validate` 与 `verify` 通过；
  3. 补正记录写坏（如 `after` 不是 `unknown`）时 `validate` 失败。
- **入口回归**：`evals/test-codex-skill-teardown-history.sh` 的 history 部分改断言——Codex `## history` 节含 `verify-history.sh` 与
  `history-migration.py" preview`，不含 `capability-history.py" audit`、`correct --confirm`、`import --confirm`；对
  `commands/history-integrity.md` 做同样的检查（同一脚本里加一段，脚本头注释同步改）。脚本名不改（`validate.sh` 按名字调用）。
- **Claude 命令**：`history-integrity.md` 保留插件根目录定位那段引导原样；`verify`（默认）调 `verify-history.sh`，`migration-preview`
  调 `history-migration.py preview`，没有账本时 verify 照原样报「未验证」退出 0。说明里写一句 `at` 不作为时间证据。

## Task List

### Task 0：提交已批准的 Spec 标记、Plan 与 todo

Plan 获批后由模块协调带批准标记提交到集成分支，`module-crew sync` 合入。

- 验收：sync 退出码 0；`verify-and-commit.sh` 快档通过。

### Task 1：回归测试先红

按实现要点改 `test-capability-history.sh` 与 `evals/test-codex-skill-teardown-history.sh`。

- 验收：在现有代码上「audit/correct 被拒」与两侧入口断言为红，红的原因恰是动词仍被接受、入口仍含 audit/correct（Claude 侧还缺 verify）；
  旧账本兼容与补正记录校验两例为绿（行为本来就对）。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-capability-history.sh`、`/bin/bash evals/test-codex-skill-teardown-history.sh`（预期失败）。

### Task 2：去掉 audit 与 correct（C1）

按实现要点改 `capability-history.py`。

- 验收：`test-capability-history.sh`、`test-history-verification.sh`、`test-history-migration.sh` 全过（AC1、AC2）；
  本仓库 `verify-history.sh .` 输出「历史证据校验通过」（AC5 前半）。

### Task 3：两侧入口对齐（C2）

改 `commands/history-integrity.md` 与 `skills/spec-guard-ops/SKILL.md` 的 `## history` 节。

- 验收：`evals/test-codex-skill-teardown-history.sh` 通过（AC3）；`validate.sh --quick` 通过（命令与 skill 的结构检查）。

### Task 4：接口 Spec 与文档（C3）

改 `spec/capability-history.md`、`docs/commands.md` 两行、`docs/optional-features.md`「能力历史」一节。

- 验收：三份文件里 `grep -n "audit\|correct\|补正\|审计"` 只剩「已有补正记录只读校验」与「不再提供」这类说明（AC4）。

### Checkpoint 1（report）：变异核对

在 scratchpad 里 `mktemp -d` 建的副本上分别：把 `audit` 加回动词集合；把 Codex 节的 correct 命令加回；把 `check_correction` 的调用去掉。
每种都应让对应断言变红，结果记进 todo。

### Task 5：公共文件请求（C4）

发【公共变更请求】：`spec/CAPABILITY-MAP.md` capability-history 一行的职责描述改为
「Keep verifiable history of archived capability maps and artifacts: read-only verify, migration preview and maintainer-only import; existing corrections stay validated.」
按模块协调答复处理（它改或交回我改；不改也照实记进 todo）。

- 验收：答复已记进 todo（AC6）。

### Task 6：合入集成分支并跑完整检查

先提交实现，再单独执行 `module-crew sync`，然后走 `verify-and-commit.sh` 全套（validate、phase-guard、verify-artifacts）。

- 验收：sync 退出码 0（冲突按 sync 规则处理）；全套通过（AC5）。

### Checkpoint 2（gate）：模块最终验收

发最终验收【交审】：按 AC1～AC6 逐条给证据、变异核对结果、改动统计与越界检查
（`module_scope.py check --module history-slim --base crew/fix-batch`）、新增依赖（无）、提交表、拟写的更新说明。
不推送、不开 PR，合并由模块协调按用户原话做。

## 风险

| 风险 | 影响 | 处理 |
| --- | --- | --- |
| 有其他脚本或文档仍调用 `capability-history.py audit`／`correct` | 调用方报退出码 2 | Task 2 前全仓 `grep`（排除 `docs/reports/`、`spec/history/`、`tasks/history/` 等归档）；Spec 写作时已查过，只有命令、Codex 节、测试与 docs 两处 |
| 删函数时误删 `create`／`verify` 仍要用的辅助函数 | 迁移导入或 verify 坏掉 | `test-history-migration.sh`（走 `create`）与 `test-history-verification.sh` 必须原样通过；本仓库 `verify-history.sh .` 实跑 |
| 集成分支上别的模块同时改了 `SKILL.md` 或 `docs/commands.md` 的其他段落 | sync 冲突 | 只改能力历史相关段落；冲突按 sync 规则用编辑工具解决 |
