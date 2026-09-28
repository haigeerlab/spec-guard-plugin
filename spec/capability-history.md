# Spec: capability-history

## Objective

为已归档的能力图与模块产物保存可核验的历史证据：`spec/CAPABILITY-HISTORY.json` 记录每个归档 initiative 的事件与
checkpoint，checkpoint 中每个文件都有 sha256。用户可以只读核验证据完整、审计账本字段是否有证据支持，并在明确确认后
追加更正记录。

登记：本模块是既有能力，由 2026-09-28 的一次性人工登记纳入能力图，未经 Proposal 流程
（`docs/decisions/2026-09-28-single-capability-map.md`）。它整合了已归档的 history-ledger、history-verification、
history-migration 与 audit-history-integrity 规格中仍在交付的部分；initiative 生命周期命令（pause、resume、
complete 等）已退役，不在本模块范围。改为全插件一张能力图后，历史账本只保存旧 initiative 的归档。

## Contract

- **账本格式**：`schemaVersion` 1；事件类型 `created`、`paused`、`resumed`、`completed`、`abandoned`、
  `superseded`；模块状态 `not-started`、`in-progress`、`completed`、`abandoned`、`unknown`。checkpoint 的能力图、
  Spec、Plan 与 state 快照分别位于 `spec/history/<id>/<checkpoint>/`、`tasks/history/<id>/<checkpoint>/<module>/`、
  `.agent/history/<id>/<checkpoint>/`。`capability-history.py` 是唯一的读写实现。整个插件只用一张能力图，账本
  只保存已归档的旧 initiative，不再追加生命周期事件；写入只有迁移导入用的 `create` 与更正用的 `correct`。
- **核验**（`verify-history.sh`）：没有账本时报“未验证”并以 0 退出；有账本时核对每个文件的 sha256，并拒绝未登记的
  历史目录。
- **审计**（`capability-history.py audit`）：独立于核验，报告无法由证据确立的字段，例如模块状态不是 `unknown`、事件
  时间没有来源证据、职责或依赖与 checkpoint 能力图不符；已有更正记录的发现标为已解决。
- **更正**（`correct --confirm`）：只追加更正记录，不改写原事件；需要用户明确确认。
- **迁移预览**（`history-migration.py preview`）：只读列出旧项目可导入的证据与冲突。
- 入口：Claude `/spec-guard:history-integrity`（audit、correct）；Codex `spec-guard-ops` 的 history 节（verify、
  audit、迁移 preview）。Claude Desktop MCPB 已于 2026-09-28 退役。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/verify-history.sh <project>
python3 plugins/spec-guard/hooks/capability-history.py verify|audit spec/CAPABILITY-HISTORY.json <project>
python3 plugins/spec-guard/hooks/capability-history.py correct --confirm <ledger> <audit-report> <correction>
python3 plugins/spec-guard/hooks/history-migration.py preview <project>
/bin/bash plugins/spec-guard/hooks/test-capability-history.sh
/bin/bash plugins/spec-guard/hooks/test-history-verification.sh
/bin/bash plugins/spec-guard/hooks/test-history-migration.sh
```

## Project structure

```text
plugins/spec-guard/hooks/capability-history.py  -> 账本校验、核验、审计、更正，以及供迁移导入的 create
plugins/spec-guard/hooks/verify-history.sh      -> 只读核验入口
plugins/spec-guard/hooks/history-migration.py   -> 旧证据迁移预览与导入
plugins/spec-guard/commands/history-integrity.md, skills/spec-guard-ops/SKILL.md
```

## Testing strategy

- `test-capability-history.sh` 覆盖账本校验与篡改检测；`test-history-verification.sh` 与 `test-history-migration.sh`
  任一断言失败即退出。
- `ensure`、`append`、`checkpoint`、`active`、`verify-checkpoint` 与 `artifact_history.py` 只服务于已退役的
  initiative 轮换，已于 2026-09-28 移除；测试断言这些动词被拒绝且不改动账本。
- 已知缺口：`history-migration.py import --confirm` 没有命令或 skill 入口。

## Boundaries

- Always：核验与审计只读；更正只追加；归档是逐字复制并记录 sha256。
- Ask first：导入旧证据；追加更正；为写入动词或 import 增加用户入口。
- Never：改写已有事件或 checkpoint 文件；把审计发现当作已修复而不留更正记录。

## Success criteria

- `verify-history.sh` 对完整证据通过、对篡改或未登记目录失败；`audit` 的未解决发现只在追加更正后减少。
