# Spec: takeover-narrow

<!-- spec-guard: review approved 5e3507b39a2a -->

## Objective

出事时自动降档：给 autopilot（发现自动合并被撤回、主干变红、发布后回滚）和 module-crew（发现它的四类出事）一个只许往严里改的写入口，
不需要用户原话，一次收回一格，并记下原因与来源。放宽（恢复）仍走 config、要用户原话；收窄过的地方恢复时一次只升一格。

给谁用：autopilot 与 module-crew 的自动降档；恢复档位的用户。

对外接口与用法草案一致吗：一致。对应 `spec/usage/auto-takeover.md` 入口「`project_config.py narrow`」，典型用法 U3。

登记：S101 合并方案 r2 Q6、Q7（用户「按推荐批准」）与 r3 Q13（降档先撤发布）；总账 `bfce091`、`1d5fd45`。账本 T1T36MR。

## Assumptions

1. **命令**：`project_config.py narrow --project <路径> [--module <id>] --source <调用方> --reason <原因> [--confirm]`。
   - 不带 `--confirm` 只预览：写明收窄前后四项、收回的是哪一格，什么都不写。
   - 带 `--confirm` 才写入并读回。不需要用户原话（Q6：收窄是安全方向）。
   - `--source` 取固定词表 `autopilot`／`module-crew`／`user`；`--reason` 单行、可打印字符、最长 200 字。不合格退出 2。
2. **收回一格的顺序**（Q7、r3 Q13）：
   - 值是预设时：`merge` → `plan` → `none`。
   - 值是自定义对象时：按 发布 → 合并 → Plan → Spec 的顺序，把第一个不是 `human` 的项改成 `human`。发布不管现在是 `prepare`、
     `auto-confirm` 还是 `auto`，都一步收回到 `human`（「撤发布」就是交还给人，不在发布内部逐级降）。
   - 收窄后如果四项都是 `human`，写成预设 `none`。
   - 已经是 `none`（或四项全 `human`）时：不写，退出 0，输出「已是最严」。
3. **收窄谁**：
   - 带 `--module`：收窄这个模块的生效值。模块原来没有自己的条目时，以项目生效值为起点收窄，结果写成该模块的条目（只影响这个模块）。
   - 不带 `--module`：收窄项目的 `takeover`；模块自己的条目不动（它们比项目宽时照旧只提醒）。
4. **存在哪：只存一处**（Q6）。收窄结果写回 `.agent/config.json` 的 `takeover`／`moduleTakeover`；同一文件新增键 `takeoverNarrowed`：
   范围（`project` 或模块 id）→ `{"from", "to", "source", "reason", "at"}`，记这个范围第一次收窄之前的值（`from`）与当前值（`to`）。
   同一范围再次收窄时只更新 `to`、`source`、`reason`、`at`，`from` 不变。见未决问题 Q3。
5. **恢复一次一格**：某个范围在 `takeoverNarrowed` 里有记录时，`config set` 对这个范围的放宽只允许比现值宽一格（按假设 2 的逆序）；
   宽出不止一格时退出 2，说明一次只能升一格。恢复到 `from` 或比 `from` 更宽时，删除这条记录。没有收窄记录的范围照旧不限（首次设置可以一步到位）。
   放宽照旧要用户原话（规则文字）。`config set` 往严里改不受限，也不需要记录。
6. **原因不进阶段提示**：`reason` 是调用方写的文字，阶段提示不输出它；`show` 与 `/map --json` 只给固定字段，`reason` 原样给（已限长、单行）。
   `/map --json` 每个模块的 `takeover` 增加 `narrowed`：没有收窄记录为 `null`，有则为 `{"from", "source", "at"}`（不含 `reason`）。
7. **接口**：同在 1.15（0.91.0 一起发）：`interface.json` 新增 `takeoverNarrow` 条目（命令、参数、退出码、顺序、写到哪），`mapView.takeover`
   增加 `narrowed` 字段，`takeoverNarrowed` 键写进 `takeover` 条目的说明。module-crew 现有的 `tier degrade` 改调本命令，参数不变（合并方案 Q6，
   由 module-crew 改）。
8. **阶段提示**：本模块不改阶段提示（同 takeover-config）。

## Contract

### C1 `hooks/project_config.py`

- 新函数 `narrow_step(value) -> value | None`：按假设 2 返回收回一格后的值，已是最严时 `None`；与 `PRESETS`、`ITEMS` 同处定义，唯一判据。
- 子命令 `narrow`（假设 1、3）；`VALIDATORS` 加 `takeoverNarrowed`（范围为 `project` 或合法模块 id，字段与取值合法，`reason` 单行≤200）。
- `set` 对有收窄记录的范围按假设 5 检查并维护记录。

### C2 `/map --json`

- `takeover.narrowed`（假设 6）；`TAKEOVER_FIELDS` 同步，`check-interface.py` 核对。

### C3 接口与说明

- `interface.json`：`takeoverNarrow` 条目，`mapView.takeover.fields.narrowed`，`takeover` 条目说明 `takeoverNarrowed`。
- `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`：收窄入口给调用方用、恢复一次一格；用户想恢复时怎么说。

## Acceptance criteria

- **AC1** `narrow` 顺序：`merge`→`plan`→`none`→已是最严；自定义 `{"spec":"codex","plan":"codex","merge":"auto","release":"auto"}` 依次收回发布、合并、Plan、Spec，
  最后写成 `none`；预览不写文件；`--source`／`--reason` 不合格退出 2 不写。
- **AC2** 范围：带 `--module` 且模块无条目时以项目值为起点并只写该模块；不带时只改项目值、不动模块条目。
- **AC3** 记录：第一次收窄写 `from`；再次收窄 `from` 不变、`to` 更新；文件里 `takeoverNarrowed` 不合法时只这个键失效、`check` 失败。
- **AC4** 恢复：有记录时 `set` 放宽两格退出 2、放宽一格成功；回到 `from` 或更宽后记录删除；无记录的范围放宽不限；往严里 `set` 不受限。
- **AC5** `/map --json`：`narrowed` 为 `null` 或 `{from, source, at}`，不含 `reason`；阶段提示有无收窄记录逐字相同。
- **AC6** `interface.json` 与 `check-interface.py` 一致，改坏时变红；`validate.sh`、phase-guard、verify-artifacts 全绿。

## Boundaries

- **会做**：C1～C3 及回归。
- **先问再做**：让收窄改阶段提示；在发布内部逐级降；自动恢复。
- **不做**：发现出事（autopilot、module-crew 的事）；改 module-crew 的 `tier degrade`；版本号与发版（0.91.0 在 `codex-final-acceptance`）。

## 未决问题

- **Q3 收窄记录放哪**（2026-11-21 用户选 A）：
  - **A（推荐）**：和档位放在同一个 `.agent/config.json`（键 `takeoverNarrowed`）。档位只存一处，`/map`、恢复检查都只读这一个文件。
    代价：调用方收窄后这个入库文件会多出一处未提交的改动，需要有人提交（autopilot 可以在降级 issue 里提醒）。
  - **B**：本机状态目录里另存一份收窄覆盖（不入库、不弄脏工作区）。代价：档位变成两处、两台机器看到的不一样，`/map` 要合并两处。

## 并行边界

- 独占：`spec/takeover-narrow.md`、`tasks/takeover-narrow/`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`plugins/spec-guard/commands/config.md`
- 公共：无

## 文档建议

改 `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`；CHANGELOG 与 README 在最后一个模块统一写。项目没有文档基线。
