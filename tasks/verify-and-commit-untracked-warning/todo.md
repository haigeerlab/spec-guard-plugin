# Todo: verify-and-commit-untracked-warning

- [x] Task 1：检查前警告未跟踪文件（回归先行、四项变异）— `scripts/test_verify_and_commit.py` 新增 4 例：
  - 改代码前 3 例红；"无未跟踪或只有被忽略文件时不警告"一例天然绿，靠变异"不带 `--exclude-standard`"证明它管用；
  - 变异全部变红并已还原：去掉警告（3 例红）、不排除被忽略文件、列表不截断、警告挪到检查之后（各 1 例红）。
- [x] Task 2：提交后的"未写入检查记录"提示指向上方警告、不再逐个列出（改现有用例、一项变异）— 现有用例改为要求"（见上方警告）"且文件名只出现一次，改代码前红；变异"恢复逐个列出"变红并已还原；记录判据未动。
- [x] Task 3：`docs/maintainer-workflow.md` 补一句；两个 Python 版本、ShellCheck、全档提交通过 — 回归 20 例在 python3 与系统 Python 3.9.6 下通过；ShellCheck 4.1.0（CI 同版本）无告警；全档提交见下一条记录。
- [ ] Checkpoint 1（gate）：模块评审；全部回归通过、ShellCheck 无告警，Plan 获批即授权推送与开 PR，合并由用户进行
- [ ] Task 4：下次发版时写进 CHANGELOG 的"维护者工具"
