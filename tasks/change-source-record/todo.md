# Todo: change-source-record

- [x] Task 0：提交已批准的产物 — 能力图新行与第一条「变更记录」、评审节奏改为分开审、已批准的 Spec（6393945b4b68）、已批准的 Plan 与本 todo 一次提交。
- [x] Task 1：规则「需求来源与回告」与模板行（先红） — `test_workflow_checkpoints.py` 新增 1 例（新一节三段的关键词；两份模板与 `docs/convention-block.md` 含新增两行），先失败。共享检查点规则在「返工与小模块」后新增「需求来源与回告」（变更记录、回告、接收回告）；两份模板与约定块文档各新增两行，`git diff` 无删除行。23 例全绿，`validate.sh --quick` 通过。
- [x] Task 2：带「变更记录」的能力图照常通过校验 — `test-verify-artifacts.sh` 新增 1 例（能力图末尾带「变更记录」时 0 警告 0 失败），不需要改代码，61 例全绿。另核对成功标准：临时项目先用安装的 0.63.0 装约定块，再用工作区版本 `setup-convention local --replace`（Claude 与 `--host=codex` 各一次），退出码都是 0，新增两行已写入，不需要 `--accept-removals`。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 随 Task 2 的提交跑 `verify-and-commit.sh` 全档（暂存了 `.sh`，含 ShellCheck）。
- [x] Task 3：文档、CHANGELOG 与版本号 — `docs/workflow.md` 两段（需求在开发中途被别人改了时、做完后回告提需求的人）；CHANGELOG `[0.63.1] - 2026-10-16`；两份 `plugin.json` 改为 0.63.1，中英 README 的 `--ref` 改为 v0.63.1；`validate.sh` 通过。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证：两边宿主各一次真实会话，观察转来的变更要求是否被记录并交复审、最终 gate 是否列出拟回告
