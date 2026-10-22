# Todo: history-slim

- [x] Task 0：提交已批准的 Spec 标记、Plan 与 todo — Spec（C53）与 Plan（C59）由模块协调带批准标记提交到集成分支 4f91ab2；按同步基线（C57）与开工通知两次 `module-crew sync`（HEAD 63e1f10、b808c20），各取集成分支版本；validate、phase-guard（438 例）、verify-artifacts（74 例）全过。
- [x] Task 1：回归测试先红 — `test-capability-history.sh` 的 audit/correct 正向用例删掉，改为直接写一份带两条补正记录、`at` 为 `imported`／`now` 的旧账本：validate 与 verify 通过（绿）、补正写坏两种（`eventIndex` 越界、`after` 升级为 `completed`）validate 失败（绿）、`audit`／`correct --confirm` 退出码 2 且账本不变（红：audit rc=0、correct rc=1）。`evals/test-codex-skill-teardown-history.sh` 改为对 Codex history 节与 Claude 命令都断言有 verify 与迁移预览、没有 audit／correct／import --confirm（红：Codex 节仍含 audit）。
- [x] Task 2：去掉 audit 与 correct（C1） — 删 `audit()`、`load_json()`、`find_audit_finding()`、`append_correction()`、`correction_identity()` 与只被 audit 用的 `capability_map` 导入，动词集合与用法行去掉两项；`check_correction()` 及 `AUDIT_TIME`、`SHA256`、`MODULE_STATUS` 保留并加注释。三份历史测试全过；本仓库 `verify-history.sh .` 输出「历史证据校验通过」。
- [x] Task 3：两侧入口对齐（C2） — `commands/history-integrity.md` 改为 `verify`（默认）与 `migration-preview`，插件根目录定位引导原样保留；`spec-guard-ops` 的 `## history` 节同样两条。实跑命令代码块：空参数与 verify 报「历史证据校验通过」，migration-preview 输出 JSON，未知参数打印用法退出 2。`check-command-names.py` 把 `) /bin/bash` 读成命令引用，改写为 `bash`（与 teardown 命令一致）。入口回归与 `validate.sh --quick` 通过。
- [x] Task 4：接口 Spec 与文档（C3） — `spec/capability-history.md` 去掉审计与更正的契约、命令与边界，写明已有更正记录照常校验、`at` 不作为时间证据、两侧入口一致；`docs/commands.md` 两行与 `docs/optional-features.md`「能力历史」一节按新入口改写。三份文件中 audit／correct／审计／补正只剩「已去掉」「已有记录照常校验」与归档来源说明。
- [x] Checkpoint 1（report）：变异核对 — 在 scratchpad 里 `mktemp -d` 建的三份副本上各改一处：把 `audit` 加回动词集合 → `test-capability-history.sh` 1 处红（audit rc=0）；Codex history 节加回 `correct --confirm` 命令 → 入口回归报「Codex history section still offers correct --confirm」；`validate_data` 不再调 `check_correction` → 补正写坏两例都红。
- [x] Task 5：公共文件请求（C4） — 发【公共变更请求】（消息 #10296）；模块协调按 C67 在集成分支 3895dbe 改了能力图第 30 行，`module-crew sync` 合入（HEAD ed71366），本分支能力图该行已是新描述。
- [x] Task 6：合入集成分支并跑完整检查 — 实现提交 58d16c0 走 `verify-and-commit.sh` 全套（validate 94s、phase-guard 438 例、verify-artifacts 74 例、repo-artifacts 0 失败、ShellCheck 无告警）；sync 到 3895dbe 后 validate、phase-guard、verify-artifacts、三份历史测试、入口回归与本仓库 `verify-history.sh .` 再跑全过；`module_scope.py check --module history-slim --base crew/fix-batch` 越界 0。
- [x] Checkpoint 2（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **变更**：能力历史只保留 verify 核对与迁移预览（Claude `/spec-guard:history-integrity` 与 Codex `spec-guard-ops` 的 history 节一致）；
> `audit` 与 `correct` 已去掉（决定 D16）。已有账本里的补正记录照常校验，归档快照不变；事件时间 `at` 是迁移时抄下的原值，不作为时间证据。
