# Todo: phase-hint-gaps

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：D6 压缩后那一次不报大小（先红） — `test-phase-guard.sh` 新增第 16 段，6 例：UserPromptSubmit 900k 对照仍报大小；SessionStart 下 Claude BUILDING 900k、DONE 900k，以及 Codex DONE、BUILDING 250k，都不出上下文行与边界行，压缩后的核对提醒照旧。改实现前跑红（SessionStart BUILDING 900k 失败），`phase-guard.sh` 在 SessionStart 时把 `TOKENS` 置 0 后转绿；回归 308→314 例全绿，现有压缩相关用例未改。删掉置 0 那一行即为变异，对应用例变红（即改前的红）。
- [x] Task 2：D5 没开工的当前模块也给边界行（先红） — 第 16 段加两模块夹具（alpha 已完成、beta 无 Spec），9 例：NEEDS_SPEC 600k 与 850k 只出带大小的边界行；100k、读不到大小、无人值守都不出；Codex 达到窗口 50% 出行；NEEDS_PLAN、BUILDING 600k 都不出；BUILDING 850k 照旧只出上下文行。改前 NEEDS_SPEC 600k 一例红；`module_stage.py` 加 `NEEDS_SPEC` 分支（复用 `boundary_note_line`，大小未知不出）后转绿，314→323 例全绿，现有“NEEDS_SPEC 没有模块完成行”等用例不变。把分支删掉即为变异，回到改前的红。
- [x] Task 3：D1 IDLE 与 MAP_ONLY 带配置行（先红） — 第 16 段加 8 例（IDLE、MAP_ONLY 各 4 例：产物语言、combined、无效配置，各多出对应行且位于建议之前，其余逐字不变；separate 逐字不变）。改前 IDLE 产物语言一例红；`module_stage.py` 加 `--config-lines` 入口（复用 `config_lines`），`phase-guard.sh` 在两阶段输出前取一次，取不到不加，之后转绿，323→331 例全绿。变异（入口打印空串）新例变红，已恢复。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 随 Task 1–3 的提交各跑 `verify-and-commit.sh` 全档（暂存了 `.sh`，含 ShellCheck），三次都通过；phase-guard 331 例。另：2026-10-16 发现 Spec 与 Plan 交审时要点没进对话正文，按规则改回 pending、补交要点，用户重新批准（批准前已提交的 Task 0–3 未改）。
- [x] Task 4：文档、能力图文字、CHANGELOG 与版本号 — README 更新表原本已写 Claude Code “然后重开会话”，Spec 说“没写”不准；只补一句不重开的后果（中英各一段），`docs/troubleshooting.md` 加一行“升级后命令仍是旧版本”。能力图 `docs-refresh` 行改为“去掉会过时的命令总数”，「变更记录」追加一行（来源：用户本人）。`docs/design.md` 数据流写明 SessionStart 按 0 处理、两档提醒含 `NEEDS_SPEC`、IDLE／MAP_ONLY 的配置行来源。CHANGELOG `[0.63.2]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.63.2。`check-manifests.py`、`check-readme-sync.py`、本仓库 verify-artifacts（5 通过）通过。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证：两边宿主各手动压缩一次；Claude Code 实测 `/reload-plugins`；回告观测会话
