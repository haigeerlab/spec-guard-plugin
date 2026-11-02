# Todo: whitespace-only-preview

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-11-03 用户批准能力图新行与 Spec（「批准」）、Plan（「Plan 批准」）。
- [x] Task 1：预览报告只差空白的段（managed-block.py、test-setup-teardown.sh） — `_units` 每段多返回原文（各行去掉行尾换行后用换行拼接）；`replace --dry-run` 统计键在模板里、原文不在模板同键原文里的段，个数大于 0 时在 `will add:` 之后打印 `will adjust whitespace or line wrapping: N paragraph(s)`；判定、写入、teardown 不变。回归：两侧「折开再拼回」与「有续行的旧块」的预览断言这一行且 N 等于折开的行数、不报 unchanged、无 `will remove:`；标准写法再预览断言不报这一行。在 0.86.2 代码上第一处即红（期望 16 段），改后 71 例通过（新断言加在既有用例里，例数不变）。
- [ ] Task 2：文档（命令说明、Codex 技能、docs/commands.md）
- [ ] Task 3：版本号 0.86.3 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查、变异验证与真实块复核
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR
