# Todo: feature-guidance-examples

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：改写两行（AC1～AC3） — 出处：Proposal「审查与接受的记录、多人确认」取自 `docs/workflow.md` 181 行（加新需求两种方式表），「谁接受」落在 Issue 标签取自 `docs/concepts.md` 设计原则「人工接受，只改标签」，
  「个人或小团队、需求已理顺、一次预览一次确认」取自 workflow.md 快速插入一行，「新项目不写 Proposal」取自 workflow.md 第 8 行；文档治理「需求文档、架构文档、使用手册」取自 `docs/optional-features.md` 46 行，
  「文档本身也要交付、要审查」取自同文件第 9 行，「哪些文档是项目的依据」（需求文档是验收依据）取自 48 行起的基线说明。判断方法两句（「事后有人会问谁批准的吗」「改功能时是否必须同步改并让人审」）是把上述用途改写成问句，没有新定标准。链接检查 0 处问题。
- [x] Checkpoint 1（report）：整体检查（AC4） — 见本次提交的 validate 结果；`git diff --stat origin/main -- plugins/spec-guard` 为空。
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行 — 2026-10-28 呈现两行改前改后、AC1～AC4 证据与出处、改动与提交表、Spec 未改；用户回复「feature-guidance-examples 验收通过」。
