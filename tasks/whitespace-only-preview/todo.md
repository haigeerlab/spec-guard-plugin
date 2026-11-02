# Todo: whitespace-only-preview

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-03 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」）。
- [x] Task 1：预览报告只差空白的段（managed-block.py、test-setup-teardown.sh） — `_units` 每段多返回原文（各行去掉行尾换行后用换行拼接）；`replace --dry-run` 统计键在模板里、原文不在模板同键原文里的段，个数大于 0 时在 `will add:` 之后打印 `will adjust whitespace or line wrapping: N paragraph(s)`；判定、写入、teardown 不变。回归：两侧「折开再拼回」与「有续行的旧块」的预览断言这一行且 N 等于折开的行数、不报 unchanged、无 `will remove:`；标准写法再预览断言不报这一行。在 0.86.2 代码上第一处即红（期望 16 段），改后 71 例通过（新断言加在既有用例里，例数不变）。
- [x] Task 2：文档（命令说明、Codex 技能、docs/commands.md） — 三处讲预览的地方各补一句：只差空白或折行的段不算删减，汇总成 `will adjust whitespace or line wrapping: N paragraph(s)`，不需要 `--accept-removals`。
- [x] Task 3：版本号 0.86.3 与 CHANGELOG — 两份 `plugin.json` 改 0.86.3；README 中英 `--ref v0.86.3`；CHANGELOG 加 `## [0.86.3] - 2026-11-03`（修复、文档）。`check-readme-sync.py`、`check-manifests.py` 通过。
- [x] Checkpoint 1（report）：发布前完整检查、变异验证与真实块复核 — 主机 macOS 15.7.3 arm64，系统 `/bin/bash` 3.2.57，HEAD `c490c9ef`：Task 3 提交时完整档通过（`validate.sh`、phase-guard 512 例、verify-artifacts 88 例、setup/teardown 71 例，ShellCheck 无告警）；`evals/codex-plugin-smoke.sh --selftest` 通过。Task 1 第一次提交时 phase-guard 的「标准输入不关闭」计时用例在并行负载下超时（多等 2.39 s），单独重跑 512 例通过，再提交时通过；与本模块改动无关。变异（新建临时目录里的草稿副本）：去掉这一行的打印 → 「拼成单行后预览应报 16 段空白调整」失败；去掉「原文不同」条件 → 「标准写法再预览应为 block content unchanged，不报空白调整」失败。真实块复核：使用方 oxfmt 格式化后的 CLAUDE.md 块预览报 `will adjust whitespace or line wrapping: 2 paragraph(s)`（正是中文标点后多了空格的两段），AGENTS.md 块仍为 `block content unchanged`。
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR
