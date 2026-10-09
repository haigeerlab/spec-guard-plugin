# Spec: verify-and-commit-untracked-warning

## Objective

`scripts/verify-and-commit.sh` 只提交已暂存的内容，但它跑的检查读的是工作区。新文件写好了却忘了 `git add` 时，本地检查
看得到它、照常通过，提交里却没有它，推上去 CI 才变红。本模块让脚本在跑检查**之前**就把这种文件列出来并警告，
仍照常检查与提交，不拒绝。来源：verify-and-commit（#269）审查时列出的候选，用户 2026-10-09 选定。

读者：本仓库维护者。

## 现状（2026-10-09 读代码）

- 跑检查前只拒绝两种情况：已跟踪文件有未暂存改动、没有暂存内容。未跟踪文件不看。
- 提交成功后，`scripts/verified_trees.py record` 发现未跟踪文件时打印"未写入检查记录：工作区有未跟踪文件……"并列出
  最多 10 个（local-check-dedup 加的，`test_untracked_files_skip_the_record_but_not_the_commit` 覆盖）。这条提示说的是
  检查记录，出现在提交之后、夹在 `git commit` 的输出里，没有提醒"可能漏了 `git add`"。
- pre-push 跑的也是工作区，同样看不到这个问题，所以只能在本地提交时提醒。

## Assumptions

用户 2026-10-09 批准：

1. **时机与位置**：在两项拒绝检查之后、打印 `── verify-and-commit: …` 并启动检查之前，用
   `git ls-files --others --exclude-standard` 取未被忽略的未跟踪文件；有的话打印一段警告，写到标准输出（与脚本其他
   提示一致）。被 `.gitignore` 或 `.git/info/exclude` 忽略的文件不算（例如 `.agent/state.json`）。
2. **措辞**：首行
   `⚠️  工作区有 N 个未跟踪文件：检查会读到它们，提交里却没有；如果是漏了 git add，CI 会失败：`，
   下面每行一个路径，最多 10 个，超出时加一行 `     … 另有 M 个`。
3. **不改变结果**：警告不影响检查、提交与退出码；检查失败时警告照样已经打印在前面。
4. **提交后的那条提示改为指向上方警告**（用户 2026-10-09 选 B）：`verified_trees.py record` 遇到未跟踪文件时仍不写
   记录，提示改为 `ℹ  未写入检查记录：工作区有未跟踪文件（见上方警告）；推送时会照常全跑`，不再逐个列出。`record`
   只有 verify-and-commit 一处调用（2026-10-09 grep 核对），记录判据不变。
5. **回归**：在 `scripts/test_verify_and_commit.py` 里新增用例：
   - 有未跟踪文件：退出 0、提交成功、警告首行与文件名出现在 `── verify-and-commit:` 之前；
   - 没有未跟踪文件、或只有被忽略的文件：不出现警告；
   - 有未跟踪文件且某套检查失败：退出 1、不提交、警告照样出现；
   - 12 个未跟踪文件：只列 10 个，并有"另有 2 个"；
   - 提交后的"未写入检查记录"提示指向上方警告、不再逐个列出（改现有用例
     `test_untracked_files_skip_the_record_but_not_the_commit`），文件名只出现一次。

   每条判据手工改坏一次，确认会变红。
6. **文档**：`docs/maintainer-workflow.md` 讲 verify-and-commit 的那段补一句。
7. **范围**：只改 `scripts/verify-and-commit.sh`、`scripts/verified_trees.py` 的这条提示、两者的回归与上面那句文档；插件发布包不变，不发版，下次发版时写进
   CHANGELOG 的"维护者工具"。

## Requirements

1. `verify-and-commit.sh` 按假设 1–3 在检查前警告未被忽略的未跟踪文件；`verified_trees.py record` 的提示按假设 4 改。
2. 回归按假设 5 覆盖并有变异证明；系统 Python 3.9（`/usr/bin/python3`）通过。
3. ShellCheck（CI 同版本）无告警。

## Commands

```bash
python3 -B scripts/test_verify_and_commit.py
/usr/bin/python3 -B scripts/test_verify_and_commit.py
/bin/bash scripts/validate.sh
```

## Boundaries

- Always：警告只增加输出，不改检查、提交与退出码。
- Ask first：推送、PR；把警告升级为拒绝；改 `verified_trees.py` 的记录判据（本模块只改提示文字）。
- Never：替用户 `git add`；为消掉警告而忽略 `.gitignore` 规则以外的文件。
- 不保证：检查过程中才新出现的未跟踪文件（例如测试残留）不在开头的警告里，提交后的"（见上方警告）"指不到它们；
  这时照样不写检查记录、推送时照常全跑，只是提示不完整（2026-10-09 审查补记，按已知边界处理，未改代码）。

## Success criteria

1. 留一个没 `git add` 的新文件时，跑检查前就能看到它的路径和"CI 会失败"的提醒。
2. 没有未跟踪文件、或只有被忽略的文件时，输出与改前相同。
3. 退出码与提交行为与改前一致，现有回归全部通过。

## Open questions

无。
