# Todo: change-source-record

- [x] Task 0：提交已批准的产物 — 能力图新行与第一条「变更记录」、评审节奏改为分开审、已批准的 Spec（6393945b4b68）、已批准的 Plan 与本 todo 一次提交。
- [x] Task 1：规则「需求来源与回告」与模板行（先红） — `test_workflow_checkpoints.py` 新增 1 例（新一节三段的关键词；两份模板与 `docs/convention-block.md` 含新增两行），先失败。共享检查点规则在「返工与小模块」后新增「需求来源与回告」（变更记录、回告、接收回告）；两份模板与约定块文档各新增两行，`git diff` 无删除行。23 例全绿，`validate.sh --quick` 通过。
- [ ] Task 2：带「变更记录」的能力图照常通过校验
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告
- [ ] Task 3：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证：两边宿主各一次真实会话，观察转来的变更要求是否被记录并交复审、最终 gate 是否列出拟回告
