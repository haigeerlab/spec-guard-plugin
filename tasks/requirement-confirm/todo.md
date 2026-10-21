# Todo: requirement-confirm

- [x] Task 1：规则一节、模板与 add-module 说明（先红） — `test_workflow_checkpoints.py` 加 `RequirementConfirmTests` 4 例，先红（4 errors）；在「阶段交接」前写「需求确认」一节，两份约定块模板各加一行，`commands/add-module.md` 与 `spec-guard-ops` 的 add-module 一节（Codex 入口，Plan 里写的「一并同步」）各加一步，65 例全绿，已有断言未改。全档校验发现 `docs/convention-block.md` 内嵌的约定块要与模板逐字一致，同步加了同一行（超出 Plan 列出的文件，属于同一行的镜像）。
- [x] Task 2：三处建议下一步（先红） — 新增 5 例（英文 DONE、DONE 领先、IDLE、MAP_ONLY 先确认需求；NEEDS_SPEC 不提确认的反例），先红；原有逐字断言按新措辞改 5 处：zh DONE（普通）、zh DONE（领先）、zh DONE（挂起，补全句）、zh MAP_ONLY、zh IDLE（补一句）。改 `module_stage.py` DONE 六处文案与 `phase-guard.sh` MAP_ONLY、IDLE 中英四处，428 例全过；文档里没有引用旧原文。
- [x] Task 3：CHANGELOG — 新开「[未发布]」段加一条；两份 `plugin.json` 仍为 0.81.0。
- [x] Checkpoint 1（report）：变异核对 — 用 `git archive HEAD` 的完整仓库副本：未改时规则测试 65 例全过；删掉「需求确认」一节后正好 `RequirementConfirmTests` 4 例变红（只取插件目录的副本会因缺仓库层文件多报 23 个无关错误，不计）。删掉 DONE 那句后「DONE 先确认需求再插入模块」「DONE 且领先时也先确认需求」「zh-CN：DONE，含挂起」等变红；删掉 MAP_ONLY 那句后「MAP_ONLY 先确认需求」「zh-CN：MAP_ONLY」变红。
- [x] Checkpoint 2（gate）：模块最终验收；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-21 按交审小项呈现：做了什么、AC1～AC5 逐条证据、变异核对、原有期望改动 5 处、文档改动表（2 个）、其他改动表（超出 Plan 的 `docs/convention-block.md` 已说明）、「新增依赖、锁文件改动：无」、提交表（3044432、0fe8761、9c6cd4e，勾选本 gate 为待提交）、Spec 批准后只补了跳过范围并重新记批准、注意（真实会话未验证；未做独立评审；冻结期间不发版）；用户回复「验收通过，推送并开 PR」。版本号不变。
- [x] Task 4：返工——补两处规则（先红） — `test_workflow_checkpoints.py` 加 `test_summary_comes_first_and_map_row_goes_with_spec`，先红（6 个子断言失败）；「需求确认」一节把「只认明确确认」补上「已确定但没看过总结先给总结」，新增一条「确认后停一轮，再一起交审」；`add-module.md` 与 `spec-guard-ops` 各补半句；Spec 第 2 条按此修订并记变更记录；CHANGELOG 同步。66 例全绿。变异核对：在工作区副本上删掉这两句，正好这个用例变红。
- [x] Checkpoint 3（gate）：返工验收；推送到 #395 在此由用户确认，合并由用户进行 — 2026-10-21 呈现补了什么、补完后的流程、证据（新用例先红后绿、66 例全绿、全档校验、变异核对）、Spec 差异原样、改动文件表、注意（「继续」不算批准）；用户回复「返工验收通过，推送到 #395」，同时批准修订后的 Spec，已用 review-mark 记下。
