# Todo: dependency-check

- [x] Task 1：核对模块的单测（先红） — 新增 `hooks/test_dependency_check.py` 13 例（三类清单、只改版本不算、PEP 503、完整词匹配含 `zod-form` 与 `@scope/x`、Plan 一节的标题与行首两种截取、英文标题、代码块不算、锁文件与其他清单分类、读不懂的 pyproject、`node_modules/` 跳过），登记进 `scripts/validate.sh`。没有实现时导入失败。
- [x] Task 2：实现 `dependency_check.py` — 纯函数（`npm_deps`、`requirement_deps`、`pyproject_deps` 行级读法、`normalize_python`、`is_listed`、`external_conditions`、`classify`）加读 git 的 `audit()` 与命令行（每条一行 `WARN`／`UNVERIFIED`）。13 例全绿，系统 `/usr/bin/python3`（3.9.6）同样通过。变异：不做 PEP 503 规范化 → 5 例红；按子串匹配 → `test_whole_word_match` 红；还原后通过。
- [ ] Task 3：接进 verify-artifacts 与端到端用例
- [ ] Checkpoint 1（report）：核对模块与 verify-artifacts 回归全绿
- [ ] Task 4：规则半句、文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行
