# Todo: codex-hook-reapproval-docs

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「能力图 批准。Spec 批准；Q1 A；Q2 A」）与 Plan（「Plan 批准」），能力图新行经预览确认后写入。
- [x] Task 1：README 中英（AC1） — 安装表 Codex 一栏、「更新与卸载」写 0.164 起的批准三步（桌面版可能不提示、其他插件也会待批准、0.164 之前的说法保留并标版本）、排查小表补一问；`check-readme-sync.py` 通过。
- [x] Task 2：故障排查（AC2） — 原因列表加第 6 条、「解决」加 Codex 0.164 一条、压缩后一节改正原有 `UserPromptSubmit` 不受影响的说法、升级排查表补重新批准；旧说法 grep 0 处；三个文档回归通过。
- [x] Task 3：发布流程、维护者流程与 smoke 提示（AC3、AC4） — 发布第 5 步改为先在命令行版 `codex` 的 `/hooks` 批准 3 个 hook 再跑 smoke；维护者流程写明返回 2 时先查批准（`[hooks.state]`、启动 `codex` 看提示），信任说明改为 3 个 hook 并补 0.164 起任何内容改动都会失效；smoke 返回 2 时多打印一行提示，判决与退出码不变；`--selftest` 通过，ShellCheck 无告警。
- [x] Checkpoint 1（report）：完整检查（AC4） — 主机 macOS 15.7.3 arm64，系统 `/bin/bash` 3.2.57，HEAD `36564f84`（verify-and-commit 完整档）：`validate.sh` 通过；phase-guard 507 例、verify-artifacts 78 例通过；ShellCheck 通过；
  `git diff --stat origin/main -- plugins/spec-guard` 为空。仓库产物校验 0 失败，5 条警告：4 条是已有模块批准后修订，1 条是本模块 Spec 无并行边界一节（并行开关关闭，不影响）。
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行 — 2026-10-28 呈现做了什么、AC1～AC4 证据（macOS 系统 bash）、文档表、提交表、Spec 未改；用户回复「codex-hook-reapproval-docs 验收通过」。
