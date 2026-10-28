# Todo: user-docs-onboarding

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A；Q2 A；Q3 A；Q5 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：实跑例子项目并存下输出（AC2、AC4 的证据） — scratchpad 里 `mktemp -d note-app.XXXX`、`git init`，用 `hooks/setup-convention.sh local` 装约定、`project_config.py set artifactLanguage zh-CN --confirm`，
  每步提交后用 `CLAUDE_PROJECT_DIR=<例子> bash hooks/phase-guard.sh </dev/null` 取 `additionalContext` 存成 `onboarding-out/01～10-*.txt`；能力图写完与结束时各跑一次 `verify-artifacts.sh`（4 通过／5 通过，均 0 警告 0 失败）；`map_view.py` 存 `09-map.txt`。
  阶段依次为 MAP_ONLY（装好即是，模板里有示例模块）→ NEEDS_PLAN（Spec 待批准）→ NEEDS_PLAN → BUILDING（Plan 待批准）→ BUILDING（下一个 gate）→ BUILDING（最终验收）→ MODULE_DONE → NEEDS_SPEC。
- [x] Task 2：写 `docs/getting-started.md`（AC1 文档部分、AC2～AC6） — 用脚本把实跑输出嵌入模板，避免手抄；Spec、Plan、todo 取自例子项目「待批准」那次提交（`git show`）。
  偏离 Plan 决定 2：除路径换成 `<项目目录>` 外，另删「外部审查（delegate）」一行（只在装了 delegate 时出现）、停点规则原文用一句代替，页首写明这三处处理。
  一行摘要的写法用 `module_stage.brief_line` 对例子项目实际生成后贴入（我起初手拼的少了反引号和「未勾选」）。/spec 与能力图关系核对 `docs/upstream-analysis.md` 3.3 节与 `templates/CAPABILITY-MAP.md`；链接检查 0 处问题。
  发现（先问，未改）：user-docs-align 写进 `docs/troubleshooting.md`「只看到一行 spec-guard 提示」的例子格式不对，同样少了反引号和「未勾选」。
- [ ] Task 3：`docs/concepts.md` 术语（AC7）
- [ ] Task 4：`docs/commands.md` 的 Codex 话术（AC8）
- [ ] Task 5：README 中英（AC1、AC9）
- [ ] Checkpoint 1（report）：整体检查（validate、两套回归、链接、插件包无改动）
- [ ] Task 6：新手测试复跑（AC10）
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
