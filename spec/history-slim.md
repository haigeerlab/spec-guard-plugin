# Spec: history-slim

<!-- spec-guard: review approved 219b43092696 -->

## Objective

决定 D16：每个项目只有一张能力图，能力历史不再产生新归档。能力历史只为还没迁完的旧布局项目保留两件事——
**迁移导入**与 **verify 核对**；**audit（语义审计）与 correct（追加补正）去掉**。Claude 与 Codex 两侧给出同样的入口；
已归档的快照（`spec/history/`、`tasks/history/`、`.agent/history/`）与已有账本原样保留。

同时处理审查报告 F18 的后半（模块协调转来的用户指派）：

| 编号 | 位置 | 现在的问题 | 本模块的处理 |
| --- | --- | --- | --- |
| F18（后半·1） | `hooks/capability-history.py` `check_initiative` | 不校验事件的 `at` 字段 | **不做格式校验**，改为在契约里写明 `at` 不是证据（理由见假设 3） |
| F18（后半·2） | `hooks/history-migration.py` 写 `"at": "imported"`，`correct` 只许把时间补正为 `unknown` | 迁移写入 `imported` 后没有合法的补正路径 | 随 `correct` 去掉，这条问题不再存在 |

现状（入口不对齐）：

| 能力 | Claude `/spec-guard:history-integrity` | Codex `spec-guard-ops` 的 history 节 |
| --- | --- | --- |
| verify 核对 | 没有 | 有 |
| audit 审计 | 有 | 有 |
| correct 补正 | 有 | 有 |
| 迁移预览 | 没有 | 有 |

改完后两侧都是：verify 核对 + 迁移预览；迁移导入（`import --confirm`）仍是维护者内部工具，两侧都不给用户入口（与现行
`spec/capability-history.md` 一致）。

## Assumptions

1. **【待用户确认】去掉 audit 与 correct。** D16 里「`audit`、`correct` 去掉」标着「未逐字确认，最终复述时再核」。本 Spec 按去掉写；
   用户若改为保留其一，本 Spec 要重写，不在这一版里留开关。
2. **已有账本里的补正记录照常读、照常校验，只是不能再追加。** 本机 6 份能力历史账本（只统计，不列项目）中有 3 份带补正记录
   （本仓库的两份副本各 102 条，一个使用者项目 1 条）。`validate_data` 继续按现有规则校验 `corrections` 数组，verify 对带补正记录的账本照常通过；
   去掉的只是写入口（`correct`）和产生补正依据的 `audit`。
3. **`event.at` 不做格式校验。** 同一批账本里，5 份含 `"at": "now"`，4 份含 `"imported"`，只有 3 份里出现过真实时间戳。加格式校验会让
   这些旧布局项目的 verify 直接失败——而 D16 保留 verify 正是为了它们。audit 去掉后，再没有命令对事件时间作主张；verify 只证明
   归档文件逐字未改（sha256），契约里写明 `at` 是迁移时抄下的原值、不作为时间证据。
4. **命令名 `/spec-guard:history-integrity` 不改名**，只改它做的事（verify 核对 + 迁移预览）。改名会让已有用户的习惯失效，
   收益只是名字更贴切。
5. **`history-migration.py import --confirm` 与 `capability-history.py create` 不动**：它们就是 D16 保留的「迁移导入」。
   `status`、`validate`、`artifact-dirs` 这几个只读动词也不动（`verify-history.sh` 用 `artifact-dirs`）。
6. **本模块改 `spec/capability-history.md`（接口 Spec）。** 它是 capability-history 模块的契约，本模块的 Contract 就是改它；
   依赖 capability-history 的模块（audit-remediation、retired-module-separation）都已完成，契约里它们用到的只有 verify 与归档布局，
   不受影响。

## Contract

### C1 去掉 audit 与 correct（`hooks/capability-history.py`）

- `audit`、`correct` 两个动词从可接受动词集合里删掉；调用它们与调用其他未知动词同样处理（退出码 2、打印用法），**不读写账本**。
- 删除只为它们服务的代码：`audit()`、`find_audit_finding()`、`append_correction()`，以及删完后没人用的辅助函数与常量。
  `check_correction()` 与它依赖的常量（如 `AUDIT_TIME`、`SHA256`）**保留**，用于校验已有补正记录（假设 2）。
- 账本格式（`schemaVersion` 1、事件类型、模块状态、`corrections` 结构）不变；不迁移、不改写任何已有账本。
- 不给 `check_initiative` 加 `event.at` 校验（假设 3）。

### C2 两侧入口对齐

- **Claude** `commands/history-integrity.md`：description 与 argument-hint 改为 verify 与迁移预览；
  - `verify`（默认，不带参数时也走它）：运行 `hooks/verify-history.sh "$PROJECT"`；没有账本时照原样报「未验证」并退出 0。
  - `migration-preview`：运行 `hooks/history-migration.py preview "$PROJECT"`，只读。
  - 删去 audit 与 correct 两段及其说明；插件根目录定位那段引导保持原样（`codex-skill-root` 的共用写法）。
- **Codex** `skills/spec-guard-ops/SKILL.md` 的 `## history` 节：只留 verify 与迁移预览两条命令，删去 audit、correct 及补正说明；
  保留「历史快照与旧 state 是证据，不是恢复旧 tracker 工作流的授权」一句。
- 两侧都写一句：`at` 是迁移时抄下的原值，不作为时间证据；verify 通过只说明归档文件未被改动。
- 两侧都不出现 `import --confirm` 的用户入口。

### C3 接口 Spec 与文档

- `spec/capability-history.md`：Objective、Contract、Commands、Project structure、Testing strategy、Boundaries、Success criteria
  去掉审计与更正，写明已有补正记录只读校验、`event.at` 不作为证据、入口两侧一致（verify + 迁移预览）。
- `docs/commands.md`（两处表格行）、`docs/optional-features.md`「能力历史」一节：按 C2 改写。
- 已归档的旧 Spec 与快照（如 `spec/history/138/.../audit-history-integrity.md`）**不改**，它们是逐字归档、受 sha256 约束。

### C4 公共文件（发【公共变更请求】，不自己改）

- `spec/CAPABILITY-MAP.md` 中 capability-history 行的职责描述（现为「read-only verify and audit, append-only corrections, and migration preview」）
  改为只写 verify 与迁移预览/导入。构建时按模块协调答复处理。
- CHANGELOG 与版本号由模块协调整批统一改；更新说明记在 todo 末尾（「`/spec-guard:history-integrity` 不再提供 audit 与 correct，改为 verify 与迁移预览」）。

## Commands

```bash
/bin/bash plugins/spec-guard/hooks/test-capability-history.sh
/bin/bash plugins/spec-guard/hooks/test-history-verification.sh
/bin/bash plugins/spec-guard/hooks/test-history-migration.sh
/bin/bash evals/test-codex-skill-teardown-history.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash plugins/spec-guard/hooks/verify-history.sh .
```

## Project structure

```text
plugins/spec-guard/hooks/capability-history.py        -> 删 audit/correct 动词与专用代码，保留补正记录校验
plugins/spec-guard/hooks/test-capability-history.sh   -> audit/correct 用例改为「被拒绝且账本不变」，保留补正记录校验用例
plugins/spec-guard/commands/history-integrity.md      -> verify + migration-preview
plugins/spec-guard/skills/spec-guard-ops/SKILL.md     -> ## history 节同上
evals/test-codex-skill-teardown-history.sh            -> history 部分改断言：有 verify 与迁移预览，没有 audit/correct
spec/capability-history.md, docs/commands.md, docs/optional-features.md
```

## Testing strategy

- **动词去除**（`test-capability-history.sh`）：对一份带补正记录的账本分别调用 `audit`、`correct --confirm …`，断言退出码 2、账本字节不变；
  现有的 audit/correct 正向用例删掉。先改测试跑出红（现代码接受这两个动词），再改代码。
- **旧账本兼容**：带 `corrections` 的账本、`at` 为 `now`／`imported` 的账本，`validate` 与 `verify` 照常通过；补正记录字段写坏时
  `validate` 照常失败（证明 `check_correction` 仍在起作用）。
- **入口对齐**（`evals/test-codex-skill-teardown-history.sh` 扩展，并对 Claude 命令做同样检查）：两侧都含 `verify-history.sh` 与
  `history-migration.py" preview`，都不含 `capability-history.py" audit`、`correct --confirm`、`import --confirm`。
- **本仓库实测**：`verify-history.sh .` 对本仓库账本（12 个 initiative、102 条补正）通过。
- 变异验证：手工把 `audit` 加回动词集合、把 Codex 节的 correct 命令加回，确认对应断言变红。

## Boundaries

- Always：verify 与迁移预览只读；已有账本、补正记录与归档快照一个字节不改。
- Ask first：给 `import --confirm` 加用户入口；改账本格式或 `schemaVersion`；改命令名。
- Never：改写或删除已归档的快照、`spec/CAPABILITY-HISTORY.json`；给 `event.at` 加会让旧账本 verify 失败的校验；自己改公共文件。
- `spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/optional-features.md` 只改与能力历史相关的段落（`## history` 节、两行表格、
  「能力历史」一节）；`spec/CAPABILITY-MAP.md` 的 capability-history 一行走【公共变更请求】（C4）。
- 不改 `history-migration.py`、`verify-history.sh`、`test-history-verification.sh`、`test-history-migration.sh`（行为不变，测试应原样通过）。

## 并行边界

- 独占：`plugins/spec-guard/hooks/capability-history.py`、`plugins/spec-guard/hooks/test-capability-history.sh`、`plugins/spec-guard/commands/history-integrity.md`、`evals/test-codex-skill-teardown-history.sh`、`spec/capability-history.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/optional-features.md`
- 公共：无

## Success criteria

- AC1：`capability-history.py audit …` 与 `correct --confirm …` 退出码 2，账本字节不变；改前为接受。
- AC2：带补正记录、`at` 为 `now`／`imported` 的账本，`validate` 与 `verify` 通过；补正记录写坏时 `validate` 失败。
- AC3：Claude 命令与 Codex history 节都只提供 verify 与迁移预览，都不出现 audit、correct、`import --confirm`；回归测试覆盖两侧。
- AC4：`spec/capability-history.md`、`docs/commands.md`、`docs/optional-features.md` 不再描述 audit 与 correct，写明 `event.at` 不作为证据。
- AC5：本仓库 `verify-history.sh .` 通过；最小验证三条与上面的历史测试全绿。
- AC6：capability-history 在能力图里的职责描述经【公共变更请求】按答复更新（或协调答复不改）。

## Open questions

- 假设 1：D16「audit、correct 去掉」请用户逐字确认。
- 假设 3：`event.at` 按「不校验、写明不作为证据」处理，请用户确认（另一种做法是只校验为非空字符串，`now`／`imported` 都能通过，但不增加任何证明力）。
