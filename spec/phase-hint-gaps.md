# Spec: phase-hint-gaps

<!-- spec-guard: review approved 4204fb21d654 -->

## Objective

一份真实使用报告（全新项目，从 setup-convention 做到 9/14 个模块，宿主 Claude Code，插件 0.61.0）指出阶段提示有四处
该说而没说、或说错的地方。前三处已在当前源码（0.63.1）核对属实：

1. **D6 压缩后报的是压缩前的大小（已造成误导）。** 用户手动 `/compact` 后，SessionStart 注入写“上下文约 814k，建议压缩”，
   实际压缩后只有约 19k。会话把这句当真，后来又劝用户压缩。原因：`session_context.py` 认得 `compact_boundary`，但 SessionStart
   钩子运行时这条记录还没写进记录文件，读到的是压缩前最后一轮的用量。
2. **D5 模块边界的释放上下文提示从不出现（多耗成本）。** 边界提示只在 `MODULE_DONE` 输出（`module_stage.py` 的
   `stage == "MODULE_DONE"` 分支）。按 0.60.4 的规则，最终验收的提交同时勾上 gate、把 `activeModule` 切到下一个模块，于是下一轮
   阶段已是 `NEEDS_SPEC`，而 `NEEDS_SPEC` 只在“模块中途”的 80% 档才提醒。报告里上下文从 500k 涨到 811k，跨了 5 个模块边界，
   边界提示一次都没出现。
3. **D1 IDLE 与 MAP_ONLY 不注入项目配置。** `phase-guard.sh` 在这两个阶段输出后直接 `exit 0`，不调用 `module_stage.py`，
   产物语言、`combined` 评审节奏、配置无效这几行都不会出现。MAP_ONLY 恰好是写第一个模块 Spec 的时候。
4. **D4 升级后旧版本仍在用。** Claude Code 会话启动时就定下了插件根目录；会话中途升级插件，命令仍调旧版本的脚本。README
   只写了 Codex 升级后要重启（#316），没写 Claude Code。

另顺带修一处能力图文字：`docs-refresh` 一行写“命令数改为实际的 24 条”，实际做法是去掉命令总数。

登记：2026-10-16 经 `/spec-guard:add-module` 插入能力图。需求来自会话「Spec/Guard 插件使用观测」（`local_3b05d344-963e-4750-8edb-83b08ad9d0ca`）
的使用报告，经用户审阅后转来；用户 2026-10-16 决定做 D6、D5、D1、D4，D2、D3 不做。发版后按「需求来源与回告」回告该会话。

**有意偏离「返工与小模块」。** 规则要求修已完成模块的问题时在原模块追加任务；这里三处分属 `compact-phase-injection`、
`context-hint-thresholds`、`project-config`，用户选择开一个 bug 模块一次发 0.63.2，免得三个模块各自重审 Plan。

## Assumptions

用户已于 2026-10-16 确认：

1. **D6：压缩后那一次按“刚压缩”处理。** `phase-guard.sh` 以 SessionStart 事件运行时（两边宿主都只在压缩后注册它），不读记录
   文件里的用量，把上下文大小当作 0：不出上下文行，也不出边界行。之后普通的 UserPromptSubmit 轮次照旧读记录文件（那时
   `compact_boundary` 已写入）。不尝试等待记录写入。
2. **D5：没开工的当前模块也算模块边界。** 当前模块阶段为 `NEEDS_SPEC`（`spec/<id>.md` 还不存在）时，上下文达到边界档
   （Claude 500k，Codex 窗口的 50%）就输出与 `MODULE_DONE` 相同的 Module boundary 行（带大小）；不再另出 80% 档的上下文行。
   读不到大小时 `NEEDS_SPEC` 不出边界行（与现在一样），只有 `MODULE_DONE`／`DONE` 保留不带大小的那一行。`NEEDS_PLAN`、
   `BUILDING` 不变，仍只在 80% 档提醒。0.60.4 的“验收提交同时切换状态”规则不改。
3. **代价：** 写 Spec 期间（`NEEDS_SPEC` 持续多轮）上下文超过边界档时，边界行每轮都会出现，与现在 `MODULE_DONE` 停留多轮时的
   行为一样。“提示每轮重复”是另一个尚未决定的问题，不在本模块处理。
4. **D1：IDLE 与 MAP_ONLY 也带配置行。** 取自 `module_stage.py` 现有的 `config_lines`（同一实现，不在 shell 里复制），放在
   阶段计数之后、建议之前；未设置任何项时输出与现在逐字相同。只加配置行，不给这两个阶段加上下文行或边界行。
5. **D4：只写文档。** README 中英与 `docs/troubleshooting.md` 写明 Claude Code 升级插件后要新开会话。`/reload-plugins` 能否
   让已开的会话改用新版本，先在真实宿主上实测，按实测结果写；测不出来就只写“新开会话”。
6. **能力图那一处文字**：改 `docs-refresh` 行的说法，并按「需求来源与回告」在能力图「变更记录」追加一行（来源：用户本人）。
7. 版本 0.63.2，一个 PR；CHANGELOG、两份 `plugin.json`、README 中英的 `--ref` 同步。

## Contract

### D6 压缩后的注入

- 输入：钩子事件为 SessionStart。
- 行为：传给 `module_stage.py` 的上下文大小为 0；窗口照旧（Codex 有则传）。
- 输出：没有 `Session context:` 行，也没有 `Module boundary:` 行；压缩提醒 `Context was just compacted: …` 照旧。
- UserPromptSubmit 的行为逐字不变。

### D5 NEEDS_SPEC 的边界行

| 当前模块阶段 | 上下文 | 输出 |
|---|---|---|
| `NEEDS_SPEC` | ≥ 边界档 | `- Module boundary: this session's context is about N k tokens (…); a good point to free context. …`（与 `MODULE_DONE` 同一函数） |
| `NEEDS_SPEC` | < 边界档，或读不到 | 不出边界行、不出上下文行 |
| `NEEDS_PLAN`、`BUILDING` | ≥ 中途档 | 照旧出 `Session context:` 行 |
| `MODULE_DONE`、`DONE` | 照旧 | 照旧 |

无人值守（`--unattended`）时照旧不出这两类行。

### D1 IDLE／MAP_ONLY 的配置行

- `.agent/config.json` 设了 `artifactLanguage`：多一行 `- Artifact language: …`，文字与其他阶段相同。
- `reviewCadence` 为 `combined`：多一行 `- Review cadence: combined — …`。
- 文件无效：多一行 `- Project config: invalid (…) — run …`。
- 都没有：输出与现在逐字相同。
- 取配置行失败（例如 python3 跑不起来）时不报错、不出这几行，阶段输出照旧（降级，不误报）。

## Commands

```bash
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
python3 plugins/spec-guard/hooks/test_session_context.py
/bin/bash scripts/validate.sh
/bin/bash scripts/verify-and-commit.sh -- -m "<信息>"
```

## Testing strategy

- 每处先写失败的回归，再改实现：
  - D6：SessionStart 输入 + 记录文件末尾是一条 900k 的用量 → 没有上下文行与边界行；同样输入走 UserPromptSubmit → 照旧有。
  - D5：`NEEDS_SPEC` + 600k → 有边界行；+ 100k → 都没有；+ 读不到 → 都没有；`BUILDING` + 600k → 没有（< 800k）；
    `BUILDING` + 850k → 上下文行照旧；Codex 窗口折算各一例。
  - D1：IDLE、MAP_ONLY 各一例带 `artifactLanguage`，一例 `combined`，一例无效配置，一例无配置（逐字不变）。
- 现有 phase-guard 回归除上述有意改变的用例外逐字不变。
- 变异：把 D5 的条件改回只认 `MODULE_DONE`、把 D6 的 0 去掉，各应有断言变红。
- 发版后：两边宿主各在真实会话里手动压缩一次，看注入是否不再报旧大小；Claude Code 测一次 `/reload-plugins`（假设 5）。

## Boundaries

- Always：配置行只有一处实现；钩子只读；所有输出仍是合法 JSON；`phase-guard.sh` 只依赖 bash、git、python3。
- Ask first：改 0.60.4 的“验收提交同时切换状态”规则；让边界行只出现一次（需要记状态）；改阈值。
- Never：钩子写文件；在仓库、提交或 PR 里写消费者项目的名称或路径。

## Success criteria

1. 压缩后那一次注入不出现上下文大小与压缩建议。
2. 验收提交同时切换 `activeModule` 时，下一轮（`NEEDS_SPEC`）在上下文超过边界档时出现边界行。
3. IDLE、MAP_ONLY 阶段在设了产物语言时带产物语言行；未设置时输出不变。
4. README 中英与故障排查写明 Claude Code 升级后要新开会话（以及实测得到的 `/reload-plugins` 结论）。
5. 三套核心回归与 `validate.sh` 全绿；ShellCheck 无警告；变异各有断言变红。
6. 发版后两边真实宿主的观察如实记录，并回告观测会话。

## Open questions

- 无。
