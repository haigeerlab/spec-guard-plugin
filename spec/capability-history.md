# Spec: capability-history

## Objective

为已归档的能力图与模块产物保存可核验的历史证据：`spec/CAPABILITY-HISTORY.json` 记录每个归档 initiative 的事件与
checkpoint，checkpoint 中每个文件都有 sha256。用户可以只读核验证据完整，并在导入旧证据前只读预览迁移。

2026-10-22 起（决定 D16，模块 history-slim）：每个项目只有一张能力图，能力历史只为还没迁完的旧布局项目保留迁移导入与
verify 核对；审计（`audit`）与追加更正（`correct`）已去掉，Claude 与 Codex 两侧入口一致。

登记：本模块是既有能力，由 2026-09-28 的一次性人工登记纳入能力图，未经 Proposal 流程
（`docs/decisions/2026-09-28-single-capability-map.md`）。它整合了已归档的 history-ledger、history-verification、
history-migration 与 audit-history-integrity 规格中仍在交付的部分；initiative 生命周期命令（pause、resume、
complete 等）已退役，不在本模块范围。改为全插件一张能力图后，历史账本只保存旧 initiative 的归档。

## Contract

- **账本格式**：`schemaVersion` 1；事件类型 `created`、`paused`、`resumed`、`completed`、`abandoned`、
  `superseded`；模块状态 `not-started`、`in-progress`、`completed`、`abandoned`、`unknown`。checkpoint 的能力图、
  Spec、Plan 与 state 快照分别位于 `spec/history/<id>/<checkpoint>/`、`tasks/history/<id>/<checkpoint>/<module>/`、
  `.agent/history/<id>/<checkpoint>/`。`capability-history.py` 是唯一的读写实现。整个插件只用一张能力图，账本
  只保存已归档的旧 initiative，不再追加生命周期事件；写入只有迁移导入用的 `create`。
- **已有更正记录**：账本里已有的 `corrections` 照常按原规则校验（不合法则账本无效），但不再能追加；verify 对带更正记录的
  账本照常通过。
- **事件时间**：`at` 是迁移时抄下的原值（旧账本里常见 `now`、`imported`），不做格式校验，也不作为时间证据；
  verify 只证明归档文件逐字未改。
- **核验**（`verify-history.sh`）：没有账本时报“未验证”并以 0 退出；有账本时核对每个文件的 sha256，并拒绝未登记的
  历史目录。
- **迁移预览**（`history-migration.py preview`）：只读列出旧项目可导入的证据与冲突。
- 入口：Claude `/spec-guard:history-integrity`（`verify` 默认、`migration-preview`）与 Codex `spec-guard-ops` 的 history 节
  提供同样两件事；`audit`、`correct` 调用即退出码 2、不读写账本。Claude Desktop MCPB 已于 2026-09-28 退役。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/verify-history.sh <project>
python3 plugins/spec-guard/hooks/capability-history.py verify spec/CAPABILITY-HISTORY.json <project>
python3 plugins/spec-guard/hooks/history-migration.py preview <project>
/bin/bash plugins/spec-guard/hooks/test-capability-history.sh
/bin/bash plugins/spec-guard/hooks/test-history-verification.sh
/bin/bash plugins/spec-guard/hooks/test-history-migration.sh
```

## Project structure

```text
plugins/spec-guard/hooks/capability-history.py  -> 账本校验（含已有更正记录）、核验，以及供迁移导入的 create
plugins/spec-guard/hooks/verify-history.sh      -> 只读核验入口
plugins/spec-guard/hooks/history-migration.py   -> 旧证据迁移预览与导入
plugins/spec-guard/commands/history-integrity.md, skills/spec-guard-ops/SKILL.md
```

## Testing strategy

- `test-capability-history.sh` 覆盖账本校验与篡改检测、带更正记录与 `now`／`imported` 时间的旧账本仍可校验与核验、
  更正记录写坏时账本无效，以及 `audit`、`correct` 被拒绝且不改动账本；`evals/test-codex-skill-teardown-history.sh`
  断言两侧入口都只给 verify 与迁移预览；`test-history-verification.sh` 与 `test-history-migration.sh`
  任一断言失败即退出。
- `ensure`、`append`、`checkpoint`、`active`、`verify-checkpoint` 与 `artifact_history.py` 只服务于已退役的
  initiative 轮换，已于 2026-09-28 移除；测试断言这些动词被拒绝且不改动账本。
- `history-migration.py import --confirm` 是维护者处理已退役 initiative 证据的内部工具，
  不提供 Claude 命令或 Codex skill 用户入口；日常用户入口只提供只读迁移预览。
  需要实际导入时，维护者先核对预览、目标与冲突，再单独取得本次写入确认。

## Boundaries

- Always：核验与迁移预览只读；归档是逐字复制并记录 sha256；已有更正记录照常校验。
- Ask first：导入旧证据；为 import 增加用户入口；恢复审计或更正。
- Never：改写已有事件、更正记录或 checkpoint 文件；给 `at` 加会让旧账本核验失败的校验。

## Success criteria

- `verify-history.sh` 对完整证据（含带更正记录的旧账本）通过、对篡改或未登记目录失败；`audit`、`correct` 被拒绝且账本不变；
  两侧入口一致。
