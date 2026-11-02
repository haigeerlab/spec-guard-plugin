# Todo: replace-only-existing

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-02 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」），能力图经预览确认后写入。
- [x] Task 1：拒绝分支（setup-convention.sh、test-setup-teardown.sh） — 在「═══ Spec Guard local convention ═══」之后、C3 检查与 `mkdir -p` 之前加拒绝：`--replace` 而目标文件没有块时退出 1、不写任何东西，按另一侧（`OTHER`／`OTHER_BEGIN`／`OTHER_END`）有没有独占一行的标记给三种提示之一。回归加 9 例（只有 AGENTS.md、只有 AGENTS.md 且没目录、只有 CLAUDE.md、两侧都没有，含 `--dry-run` 与 Codex 侧；两侧都有时各自替换），在 Task 0 代码副本上第一例即红；第一版断言里 `grep -F '--replace …'` 把文字当成选项，补 `--` 后重测。改后 62 例通过，ShellCheck 无告警。其他回归与 evals 没有在没块的项目上用 `--replace` 并期望成功的用例（grep 结果为空）。
- [x] Task 2：文档（命令说明、Codex 技能、commands、workflow、README 中英） — 命令说明与 `spec-guard-ops` 写明没有块时退出 1、提示哪一侧、原样转述；`docs/commands.md` 加一条；README 中英与 `docs/workflow.md` 的升级说法补「在块所在的一侧运行，两侧都有就各跑一次」。`validate.sh --quick` 通过。
- [x] Task 3：版本号 0.86.1 与 CHANGELOG（含改正 0.86.0 升级须知） — 两份 `plugin.json` 改 0.86.1；README 中英 `--ref v0.86.1`；CHANGELOG 加 `## [0.86.1] - 2026-11-02`（修复、文档），0.86.0 升级须知「约定块多了一行」改为在块所在的一侧运行并注明 0.86.1 更正。`check-readme-sync.py`、`check-manifests.py` 通过。
- [ ] Checkpoint 1（report）：发布前完整检查与变异验证
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、告诉总负责人
