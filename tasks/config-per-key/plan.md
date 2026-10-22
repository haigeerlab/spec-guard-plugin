# Plan: config-per-key

依据 [`spec/config-per-key.md`](../../spec/config-per-key.md)（2026-10-22 用户批准，事项 C4）。评审节奏为分开审，本 Plan 单独交审。
分支 `config-per-key`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/config-per-key`，从集成分支 `crew/fix-batch` 切出。

按用户 2026-10-22 的答复：CHANGELOG 与版本号由模块协调在整批合完后统一改，本模块不碰，只把更新说明写在 todo 末尾的「更新说明」一节。
不推送、不开 PR；合入集成分支由模块协调做，本模块需要同步时运行 `module-crew sync`。

所需工具：没有 UI 改动，不需要浏览器或电脑操作。

## Overview

先在 `project_config.py` 把问题代码分成结构类与逐键类，`load` 遇到逐键问题时保留合法值（单元测试先红后绿）；再让阶段提示、
verify-artifacts 与 `set`／`unset` 按两类分别处理；最后同步说明文字。每一步都用「无配置、合法配置、结构损坏三种情况输出逐字节不变」
的既有回归兜底。

## Architecture Decisions

- **`STRUCTURAL` 常量放在 `project_config.py`。** 值为 `unreadable`、`not-json`、`not-an-object`、`version-invalid` 四个代码。
  `module_stage.py` 与 `check` 用它判断是整体失效还是逐键问题，不自己写死代码列表。
- **`load` 的返回形状不变，只改逐键问题时的 `values`。** `module_concurrency`、`summary`、`hint_language`、`config_lines`、
  combined 下的下一步提示里那几处 `not problems and …` 的条件去掉，改为只看自己的键在不在 `values` 里。这样
  `module_scope`、`checkout_role`、`map_view` 都不用改代码。
- **`set`／`unset` 要保留未知键与非法值的原文，所以写入不能再只用 `values`。** 新增一个内部读取，返回解析后的整个对象；`render`
  改为接收「已知合法键 + 其余原有键」两部分：已知键按 `VALIDATORS` 顺序在前，其余键按原文件顺序在后。没有其余键时，
  输出与现在的 `render(values)` 逐字节相同（既有用例锁住）。
- **读回核对改为比对目标键与其余原有键。** 不再要求 `load` 读回 `(updated, [])`：文件里本来就有未知键时，读回的 `problems`
  依然不为空，这是预期结果。
- **`check` 只有一种新输出 `ok (ignored: unknown-key)`。** verify-artifacts 按「退出码 0 且输出含 `ignored`」判为警告，其余映射不变。
- **两份文档补进并行边界。** `docs/design.md`（第 173～178 行）与 `docs/commands.md`（第 80 行）也写着「文件无效时所有项按默认」，
  属于 Spec「说明文字」的范围，但 Spec 的并行边界没有列出这两个文件。按范围内修正处理：Task 4 在 Spec 并行边界的「独占」里补上这两个路径，
  在 Spec 末尾写变更记录，最终验收时附上这段差异，一并批准。
- **Python 3.9 兼容。** 不用 `match` 和 3.10 才有的类型写法，`test_python_compat` 要通过。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `/spec-guard:review-mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：`load` 逐键判定与读取方（先红后绿）

先在 `test_project_config.py` 写失败用例，确认是红的：
- 未知键加合法 `artifactLanguage`：语言在 `values` 里，`problems == ["unknown-key"]`；
- `reviewCadence: "both"` 加合法 `artifactLanguage`：只有 `reviewCadence` 缺席，问题为 `reviewCadence-invalid`；
- 两个未知键加两个已知键非法：代码顺序为 `unknown-key` 在前，其余按 `VALIDATORS` 顺序，`unknown-key` 只出现一次；
- 四种结构问题仍是 `({}, [代码])`，`version-invalid` 时其他键合法也不生效；
- `module_concurrency`：别的键非法时 `on` 仍是 True；它自己非法时是 False；
- `summary`：逐键问题时非法的那个键来源为 `default (config invalid)`，其余键为实际来源；
- 既有的 `test_invalid_documents_return_no_values` 拆开：结构类保留原断言，逐键类改为新断言（属于 Spec 改变的行为，不是放宽测试）。

再改 `load`、`STRUCTURAL`、`module_concurrency`、`summary`。

- 验收：`test_project_config.py` 全绿，`test_python_compat` 通过。

### Task 2：`check`、`set`／`unset` 与 `show` 文本（先红后绿）

先写失败用例：
- `check` 三档：合法 → 0 `ok`；只有未知键 → 0 `ok (ignored: unknown-key)`；已知键非法或结构问题 → 1，输出格式同现在；
- 有未知键时 `set --key artifactLanguage --value en --confirm`：只改目标键，未知键与它的值按原顺序原样保留，读回通过；
- 有一个非法 `reviewCadence` 时 `set --key reviewCadence --value combined --confirm`：修好它，其余不变；`unset` 一个非法键也能删掉它；
- 有未知键时 `set` 不带 `--confirm`：只打印差异、文件不变；
- 结构问题时 `set` 仍退出 2；
- 没有其余键时写出的文本与现在逐字节相同（既有 `set`／`unset` 用例不改）；
- `show` 文本：逐键问题写「<代码> 已忽略，其余设置照常生效」的英文说法，结构问题仍是原句；
- 问题输出不回显文件内容：未知键名与值都不出现在 `show`、`check`、`set` 的输出里。

再改 `check`、`_change`、`render`、`_show`。

- 验收：`test_project_config.py` 全绿。

### Task 3：阶段提示与 verify-artifacts（先红后绿）

先写失败用例：
- `test-phase-guard.sh` project-config 段：
  - 未知键加 `pt-BR`：语言行在，后面一行 `- Project config: ignored (unknown-key)`，去掉这两行后与无配置时逐字节相同；
  - 节奏非法加 `pt-BR`：语言行在、节奏行不在、出现 ignored 行；
  - 未知键加 `zh-CN`：提示是中文，出现「项目配置: 已忽略 (unknown-key)」；
  - 结构问题（`version: 2`、非 JSON）：只有原 invalid 行，逐字节同现在。
- 既有三处用例的期望要改，因为它们用的是逐键问题而不是结构问题：第 1049 行（`zh-CN` + 节奏非法 + 未知键，原期望只有 invalid 行）、
  第 1828 行早期阶段的同类用例（期望定义在第 1729 行）、第 1245 行 Codex 的 `{"x": 1}`。改为：前两处出现中文提示与「已忽略」行；Codex 一处改测 ignored 行里
  的 `$spec-guard-ops` 命令写法，并另加一个结构问题用例保住原来 invalid 行的 Codex 写法。
- `test-verify-artifacts.sh`：只有未知键 → 警告、不失败；第 214 行的 `both` 加未知键 → 仍失败；结构问题 → 失败。
- `test_map_view.py`：别的键有问题时 `reviewCadence` 的值和来源只按它自己判定。

再改 `module_stage.py` 的 `config_lines`、`hint_language` 与两处 combined 条件，以及 `verify-artifacts.sh` 的配置一项。

- 验收：phase-guard、verify-artifacts、map-view 三套全绿；ShellCheck 无警告。

### Checkpoint 1（report）：三套核心回归、ShellCheck 与改坏验证

- `verify-and-commit.sh` 全档通过（含 ShellCheck）；
- 在草稿副本上手工改坏三处，确认测试变红，然后复原：
  - 逐键问题时把 `values` 改回清空；
  - `check` 把只有 `unknown-key` 判为退出 1；
  - `set` 写出时丢掉未知键。
- 结果记进 todo。

### Task 4：说明文字

- `commands/config.md`：「配置无效时」一节改为两段（结构问题整份按默认、拒写；逐键问题只忽略那个键、其余生效、`set` 只改目标键）；
  `moduleConcurrency` 一行的旧版本提醒补一句「从本版起，新版本遇到不认识的键只忽略那个键」。
- `skills/spec-guard-ops/SKILL.md` 的 config 一节同步。
- `README.md` 第 140 行并行开关那一步：保留旧版本提醒，补同一句。
- `docs/design.md` 第 173～178 行、`docs/commands.md` 第 80 行：改为逐键判定的写法。
- `spec/project-config.md`：Contract 里「出现未知键……都算配置无效」与「配置无效：追加一行……其余配置项一律不注入」后面各加一句
  「（已由 config-per-key 改为逐键判定，见 spec/config-per-key.md）」，原文不删。
- `spec/config-per-key.md`：并行边界「独占」补上 `docs/design.md`、`docs/commands.md`，末尾加「变更记录」一节写明原因。

- 验收：`validate.sh` 全档通过（含 README 同步检查与 command-parity）。

### Checkpoint 2（gate）：模块验收

在正文列出：
- 实际改动的文件（取自版本库），标出超出 Plan 影响面的文件；
- Spec 改动差异（Task 4 补的并行边界与变更记录）原文；
- 四种配置（无配置、合法、只有未知键、结构损坏）下 `/spec-guard:config` 的 `show` 与阶段提示的实跑原文；
- 验收标准逐条的证据、验证结果与未验证项（已安装副本要等发版）；
- 文档建议。

最终验收【交审】发给模块协调；获批后由模块协调合并并勾选末项，本模块不再提交。

- 验收：用户验收通过。

## 影响面

- 修改：`hooks/project_config.py`、`hooks/test_project_config.py`、`hooks/module_stage.py`、`hooks/test-phase-guard.sh`、
  `hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`、`hooks/test_map_view.py`、`commands/config.md`、
  `skills/spec-guard-ops/SKILL.md`、`README.md`、`docs/design.md`、`docs/commands.md`、`spec/project-config.md`、`spec/config-per-key.md`；
- 本模块的 Plan 与 todo。
- 不改：`interface.json`、`module_scope.py`、`checkout_role.py`、`map_view.py`、CHANGELOG、版本号。

## Risks and Mitigations

- **`set` 写回时改了原文件里其余键的格式。** 写出统一用 `json.dumps(indent=2)`，其余键的值原样保留但缩进会被规范化；差异在预览里如实显示，
  用户确认后才写。用例锁住「其余键的键名、值和顺序不变」。
- **改了三处既有阶段提示用例的期望，可能掩盖回归。** 每处在 todo 里写明原期望、新期望与原因；结构问题另有用例保住原 invalid 行逐字节不变。
- **后面波次的 sibling-rules-out、rules-at-nodes、quiet-injection 也改 `commands/config.md`、`module_stage.py`、`test-phase-guard.sh`。**
  本模块改动集中在配置相关的几段；它们开工前会同步集成分支，冲突由它们按 `module-crew sync` 处理。

## Open Questions

- 无。
