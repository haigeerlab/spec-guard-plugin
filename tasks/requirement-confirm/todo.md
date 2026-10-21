# Todo: requirement-confirm

- [x] Task 1：规则一节、模板与 add-module 说明（先红） — `test_workflow_checkpoints.py` 加 `RequirementConfirmTests` 4 例，先红（4 errors）；在「阶段交接」前写「需求确认」一节，两份约定块模板各加一行，`commands/add-module.md` 与 `spec-guard-ops` 的 add-module 一节（Codex 入口，Plan 里写的「一并同步」）各加一步，65 例全绿，已有断言未改。全档校验发现 `docs/convention-block.md` 内嵌的约定块要与模板逐字一致，同步加了同一行（超出 Plan 列出的文件，属于同一行的镜像）。
- [x] Task 2：三处建议下一步（先红） — 新增 5 例（英文 DONE、DONE 领先、IDLE、MAP_ONLY 先确认需求；NEEDS_SPEC 不提确认的反例），先红；原有逐字断言按新措辞改 5 处：zh DONE（普通）、zh DONE（领先）、zh DONE（挂起，补全句）、zh MAP_ONLY、zh IDLE（补一句）。改 `module_stage.py` DONE 六处文案与 `phase-guard.sh` MAP_ONLY、IDLE 中英四处，428 例全过；文档里没有引用旧原文。
- [x] Task 3：CHANGELOG — 新开「[未发布]」段加一条；两份 `plugin.json` 仍为 0.81.0。
- [x] Checkpoint 1（report）：变异核对 — 用 `git archive HEAD` 的完整仓库副本：未改时规则测试 65 例全过；删掉「需求确认」一节后正好 `RequirementConfirmTests` 4 例变红（只取插件目录的副本会因缺仓库层文件多报 23 个无关错误，不计）。删掉 DONE 那句后「DONE 先确认需求再插入模块」「DONE 且领先时也先确认需求」「zh-CN：DONE，含挂起」等变红；删掉 MAP_ONLY 那句后「MAP_ONLY 先确认需求」「zh-CN：MAP_ONLY」变红。
- [ ] Checkpoint 2（gate）：模块最终验收；推送与开 PR 在此由用户确认，合并由用户进行
