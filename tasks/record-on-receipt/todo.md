# Todo: record-on-receipt

- [x] Task 0：提交能力图、两份已批准的 Spec 与两份 Plan — 两份 Plan 经用户批准（2026-10-18），与能力图两行、两份 Spec 一次提交。
- [x] Task 1：规则与模板行（先红） — `test_workflow_checkpoints.py` 新增 1 例，先失败；规则「未了的承诺」在「收到」后补两条（记账不是受理、调用传 `repoRoot`），三处约定块各新增一行，`git diff` 无删除行；规则测试全绿。
- [x] Task 2：读回提醒带 `repoRoot`（先红） — 第 19 段的 fresh 与压缩后期望（中英）改为以传 `repoRoot` 一句结尾，新增路径含引号的两例，先在旧代码上确认失败；`phase-guard.sh` 新增 `ledger_root_note`（路径取当前目录，跟随指向时为目标项目的真实路径；含引号、反斜杠或控制字符时改说项目根目录），两处有账本的提醒末尾接上它；没有账本时输出不变。404 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警 — 随 Task 2 的提交跑 `verify-and-commit.sh` 全档（暂存了 `.sh`，含 ShellCheck）。
- [x] Task 3：更正 0.69.0 证据 — `docs/releases/v0.69.0-claude.json` 只改 `not-verified:` 那一条：去掉「已在维护者会话里观察到」的不实说法，改为如实表述并注明在 0.70.1 更正；其他字段不动。
- [x] Task 4：文档与 CHANGELOG — `docs/workflow.md`「有人在等的事」一段补记账不是受理与传 `repoRoot`；CHANGELOG 新增 `[0.70.1] - 未发布`（两处修复与证据更正），版本号留给 `review-marker-blank-line` 的 PR。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-18 在对话里列出相对 712ed62 的 17 个文件（均在 Plan 范围内；删除行来自第 19 段期望改写、CHANGELOG 与证据各一行）、验证结果与未验证项（真实会话复测放到发版后，未做独立代码评审），拟回告为无；用户验收通过，确认推送与开 PR；不做外部审查。
- [ ] 发版后的验证

## 外部审查意见

<!-- spec-guard: external-review declined -->

用户在最终验收时选择直接验收、不做外部审查（2026-10-18）。
