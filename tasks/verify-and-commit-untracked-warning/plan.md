# Plan: verify-and-commit-untracked-warning

依据 [`spec/verify-and-commit-untracked-warning.md`](../../spec/verify-and-commit-untracked-warning.md)（用户 2026-10-09 批准
Spec，选 B）。分开审：本 Plan 单独批准。分支 `claude/verify-and-commit-untracked-warning`；提交一律走
`scripts/verify-and-commit.sh`。

## Task List

### Task 1：检查前警告未跟踪文件

回归先行，在 `scripts/test_verify_and_commit.py` 新增用例，改代码前先跑一遍确认变红：
- 有未跟踪文件：退出 0、提交成功，警告首行与文件名出现在 `── verify-and-commit:` 之前；
- 没有未跟踪文件、或只有被忽略的文件（`.agent/state.json`）：不出现警告；
- 有未跟踪文件且某套检查失败：退出 1、不提交，警告照样出现；
- 12 个未跟踪文件：只列 10 个，并有"另有 2 个"。

再改 `scripts/verify-and-commit.sh`：两项拒绝检查之后、打印套件标题之前，取 `git ls-files --others --exclude-standard`
并打印警告。

变异：
- 去掉警告；
- 不排除被忽略的文件（不带 `--exclude-standard`）；
- 列表不截断；
- 警告挪到检查之后。

### Task 2：提交后的提示指向上方警告

先改现有用例 `test_untracked_files_skip_the_record_but_not_the_commit`：提示含"见上方警告"，文件名在输出里只出现一次；
确认变红。再改 `scripts/verified_trees.py record` 的那条提示，记录判据不动。

变异：恢复逐个列出。

### Task 3：文档与全量验证

`docs/maintainer-workflow.md` 讲 verify-and-commit 的那段补一句。跑：
- `python3 -B` 与 `/usr/bin/python3 -B scripts/test_verify_and_commit.py`；
- CI 同版本 ShellCheck；
- 经 `verify-and-commit.sh` 全档提交（即完整 `validate.sh` 与两套 hook 回归）。

### Checkpoint 1（gate）：模块评审

全部回归通过，ShellCheck 无告警。本 Plan 获批即授权推送本分支并开本模块 PR，合并由用户进行。

### Task 4：下次发版时写进 CHANGELOG

插件发布包不变，不另补证据。下次发版时在 CHANGELOG 的"维护者工具"里写一条。
