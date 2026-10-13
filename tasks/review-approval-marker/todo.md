# Todo: review-approval-marker

- [x] Task 1：文本指纹入口（先红） — `spec-digest.py` 新增 `text_digest` 与 `text <file>` 子命令，复用 `_h`；自测先加 3 组断言（稳定／定长／随内容变、子命令输出、读不了退出 1），在旧代码上因 `text_digest` 未定义失败，实现后通过；`test-checkers.sh` 的 digest-single-source 5 例仍通过。
- [ ] Task 2：标记解析与评审状态（先红）
- [ ] Task 3：阶段提示的 Review 行与建议语（先红）
- [ ] Task 4：下一个 gate（先红）
- [ ] Checkpoint 1（report）：判定与阶段提示回归全绿，ShellCheck 无警告
- [ ] Task 5：`review_mark.py`（先红）
- [ ] Task 6：`verify-artifacts`（先红）
- [ ] Checkpoint 2（report）：三套核心回归与新单测全绿，ShellCheck 无警告
- [ ] Task 7：命令文件与 Codex 路由
- [ ] Task 8：规则文本、模板与文档（先红）
- [ ] Task 9：版本号与自用
- [ ] Checkpoint 3（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
