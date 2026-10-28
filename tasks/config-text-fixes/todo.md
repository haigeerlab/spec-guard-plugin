# Todo: config-text-fixes

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：三处文字（AC1、AC2） — `commands/config.md` 与 `skills/spec-guard-ops/SKILL.md` 的 moduleConcurrency 一行改为「0.84.0 起遇到不认识的键只忽略那个键」；config.md frontmatter 描述补「自治档位」，与正文 60-63 行四个可配置项一致。
  `git grep 从本版起 -- plugins/spec-guard` 0 个文件；`test_workflow_checkpoints.py` 通过。
- [x] Task 2：版本号与 CHANGELOG（AC3） — 两份 `plugin.json` 改为 0.85.1；README 中英 `--ref v0.85.1`；CHANGELOG 加 `## [0.85.1] - 2026-10-28`（范围一句、变更、文档 #417/#418/#419/#421、维护者工具 #420，无升级须知）。
  `check-readme-sync.py`、`check-manifests.py` 通过。
- [x] Checkpoint 1（report）：发布前完整检查（AC4） — 主机 macOS 15.7.3 arm64，系统 `/bin/bash` 3.2.57，HEAD `64750995`：`validate.sh` 通过；phase-guard 507 例、verify-artifacts 78 例通过；
  `evals/codex-plugin-smoke.sh --selftest` 通过；插件包改动只有 config.md、SKILL.md 与两份 plugin.json（+5 −5）。
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行 — 2026-10-28 呈现做了什么、AC1～AC4 证据（macOS 系统 bash）、改动与提交表、Spec 未改、合并后发版六步；用户回复「config-text-fixes 验收通过」，按 Spec Q1 A 同时授权合并后的发版。
- [ ] 发版（合并后按 Q1 A 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR（AC5）
