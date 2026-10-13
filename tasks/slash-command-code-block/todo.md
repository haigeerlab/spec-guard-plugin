# Todo: slash-command-code-block

- [x] Task 1：三句提示加斜杠命令说明（先红） — `test-phase-guard.sh`：三处硬编码的 Claude 行期望（模块完成行、带大小的模块完成行、上下文行）加上说明；Codex 的模块完成行与上下文行各加三条要点断言，模块完成行另断言说明恰好一处；判断不了宿主时断言不出现说明。先在四条模块完成行用例变红。`module_stage.py` 新增常量 `SLASH_BLOCK`，接进 `free-next`、`free-current` 与 `CODEX_COMPACT`，放在 `do not paste handoff text` 之前。实现后第 9、10 段仍红，查明是测试自己的问题：带大小的那一行期望写在双引号字符串里，新文字的反引号被 bash 当成命令替换，转义后 258 例全绿，实现未动。
- [ ] Task 2：规则与文档（先红）
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告
- [ ] Task 3：版本号
- [ ] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
