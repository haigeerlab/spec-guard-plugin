# Spec: module-scope-boundary

<!-- spec-guard: review approved fb632d87ced8 -->

## Objective

几个模块同时开发，前提是它们不改同一批文件。这件事要写下来才能检查：每个模块在 Spec 里声明自己独占哪些目录，做完时对照实际改动，
看有没有越出去。本模块在开关 `moduleConcurrency` 为 `on` 时提供三样东西：

1. 模块 Spec 的「并行边界」一节：固定格式，写独占路径和需要的公共文件类别；
2. 一个只读的越界检查脚本：列出本模块相对集成基线改了哪些文件，标出不在独占路径里的；
3. 两处校验与规则：verify-artifacts 校验这一节的格式；最终验收的改动清单标出「超出并行边界」的文件。

这一节的解析器也是后面 `map-startable`（判断哪些模块能同时开工、有没有冲突）要用的同一份判据。

开关为 `off` 或未设置时，三样都不出现：verify-artifacts 不输出这一项，越界检查脚本拒绝运行，阶段提示不受影响。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图（同批 7 个模块）。来源：用户本人，经多模块并行需求讨论（2026-10-17～18），
需求记录第 5 节 A4。

## Assumptions

1. **「并行边界」一节的格式。** 标题是 `## 并行边界`（英文产物写 `## Concurrency boundary`），下面两行：

   ```markdown
   ## 并行边界

   - 独占：`apps/billing/`、`packages/billing-api/`、`docs/billing.md`
   - 公共：锁文件、迁移
   ```

   - **独占**（英文 `Exclusive:`）：一个或多个路径，每个都放在反引号里，用 `、` 或 `,` 分隔。以 `/` 结尾的是目录，覆盖其下所有子孙；
     不以 `/` 结尾的是单个文件。路径相对项目根目录，不许以 `/` 开头、不许含 `..`、不许含通配符 `* ? [`（需求记录 A4「不用通配符」）。
   - **公共**（英文 `Shared:`）：本模块预计要改的公共文件类别，只能从四类里选：全局配置、锁文件、迁移、测试资源（英文
     `global-config`、`lockfile`、`migration`、`test-resource`）；不需要写 `无`（`none`）。公共文件归协调会话，模块会话要改时提请求，
     这一行只是预告，越界检查不按类别放行。
   - 本模块自己的流程文件 `spec/<id>.md` 与 `tasks/<id>/` 总是算在边界内，不用写。
2. **什么时候必须有这一节。** 开关为 `on` 时，**还没完成**的模块的 Spec 应当有这一节。缺了只警告（「未声明并行边界，无法判断与其他模块
   是否冲突」），不判失败：中途打开开关的项目，已有的 Spec 不该一下子全部变红。格式写错判失败。已完成的模块不检查。
3. **两个模块的独占路径重叠，本模块不报。** 冲突要结合 Build order 和谁正在进行来判断，归 `map-startable` 的 `conflicts`。
4. **越界检查脚本**：`hooks/module_scope.py check --project <root> --module <id> --base <ref> [--format json]`。
   - `--base` 必填，是集成基线的提交或分支。spec-guard 不知道用户的本地集成分支叫什么，由调用方给（module-crew 的协调会话、
     或最终验收时的 agent）。
   - 改动文件 = `git diff --name-only <base>` 的结果（已提交和未提交的已跟踪改动，含删除）加上未跟踪且未被忽略的文件。
   - 输出：每个改动文件归为「独占内」「本模块流程文件」「超出并行边界」三类之一；只报告，不拦截，正常退出码 0。
   - 开关不是 `on` 时退出码 3，只说开关未打开；模块 Spec 没有这一节或格式错误时退出码 4；`--base` 不是有效引用、不在 git 仓库里时
     退出码 2。输出里的路径都来自版本库，不回显 Spec 正文。
5. **最终验收的改动清单。** 共享规则「最终验收列出实际改动的文件」一条后面加一段，开关为 `on` 且本模块 Spec 有并行边界时：
   用越界检查脚本对照集成基线，在清单里单独标出「超出并行边界」的文件并说明原因，没有就写「无」。原有「超出 Plan 预计影响面」
   的标记保留，两者并列。只报告，不卡验收。
6. **Spec 交审要点。** 共享规则里 Spec 交审要点那一行不改；在新的「并行边界」规则一节里写明：开关为 `on` 时，Spec 交审的要点里加上
   并行边界。这样开关为 `off` 的项目读到的交审要求不变。
7. **不进阶段提示。** phase-guard 不读这一节，所以「修改共享判据时同时更新 phase-guard 与 verify-artifacts」这条不变量这里只涉及
   verify-artifacts；解析器放在新文件 `hooks/module_scope.py`，verify-artifacts、越界检查和以后的 `/map` 都只调它。
8. **命名。** 文件、函数、文字都不用 `parallel` 字样；中文「并行边界」不受 `check-no-parallel-surface.py` 限制。

## Contract

### `hooks/module_scope.py`（新增）

- `parse(text) -> Scope | None`：从 Spec 全文取出「并行边界」一节（跳过 ``` 围起来的代码块，示例里的标题不算）；没有这一节返回 None；
  格式错误抛 `ScopeError(code)`，code 是固定词表
  （`missing-exclusive`、`bad-path`、`bad-category`、`duplicate-section`、`unknown-line`），不回显文件内容。
- `Scope`：`exclusive`（路径元组，目录以 `/` 结尾）、`shared`（类别元组，英文代码）。
- `covers(scope, module_id, path) -> str`：返回 `exclusive`、`own` 或 `outside`。
- CLI 子命令 `check`（见假设 4）和 `validate --project <root>`（供 verify-artifacts 调用：开关不是 `on` 时什么都不输出；否则逐个检查
  未完成模块的 Spec，按固定格式输出 ok／warn／bad 行）。「未完成」的判据复用 `module_stage.py`，与阶段提示同一份。
- 读开关只用 `project_config.module_concurrency()`。

### `hooks/verify-artifacts.sh`

新增一段，和项目配置、评审标记各段同样的写法：调用 `module_scope.py validate`；没有输出时这一项不出现；python3 不可用或脚本没有正常
运行时报「未验证」，不当成通过。

### `references/workflow-checkpoints.md`

- 新增一节 `## 并行边界（moduleConcurrency 为 on 时）`，放在「并行评估」之后：节首写明不是 `on` 时不适用；格式（假设 1）、何时必须有
  （假设 2）、Spec 交审要点加上并行边界（假设 6）、越界检查脚本的用法。
- 「最终验收列出实际改动的文件」一条末尾加一句指向新一节；新一节里写明假设 5 的做法。

### 文档

`docs/design.md` 的文件表加 `module_scope.py` 一行；CHANGELOG 未发布小节加一条「新增」。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_module_scope.py
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- **`test_module_scope.py`（新增，先红后绿）：**
  - 解析：中英两种标题与行名；`、` 和 `,` 两种分隔；目录与文件；`公共：无`；没有这一节返回 None；只出现在代码块里的标题不算；
  - 格式错误各一例：没有独占行、路径不在反引号里、以 `/` 开头、含 `..`、含 `*`、未知类别、两个「并行边界」标题、节内有无法识别的行；
    报错只含固定代码，不含文件里的文字；
  - `covers`：目录覆盖子孙、不覆盖同名前缀（`apps/bill/` 不覆盖 `apps/billing/x`）、单文件精确匹配、`spec/<id>.md` 与 `tasks/<id>/` 归 own；
  - `check`：在临时 git 仓库里基线之后改独占内、流程文件、外部文件，再加一个未跟踪文件和一个删除，分类正确；`--format json` 结构稳定；
    开关 off 退出 3；没有这一节退出 4；`--base` 无效退出 2；
  - `validate`：开关 off 时没有输出；on 时未完成模块缺这一节出 warn、格式错出 bad、正确出 ok，已完成模块不检查。
- **verify-artifacts 正反回归：** off 时输出与改动前逐字相同（不出现这一项）；on 时正确、缺失、格式错各一例。
- **phase-guard：** 不改代码；在 project-config 段加一例「开关 on 且 Spec 有并行边界时，阶段提示与无配置时逐字节相同」。
- **共享规则断言：** 新一节存在、节首写明不适用条件、写到格式和越界检查命令；「最终验收列出实际改动的文件」一条指向它；约定块模板仍不出现
  `moduleConcurrency`。
- **改坏验证：** 让 `covers` 用字符串前缀判断（不按目录边界），确认「不覆盖同名前缀」变红；让 `validate` 在开关 off 时也检查，确认 verify-artifacts
  「off 逐字相同」变红。两处都复原。

## Boundaries

- Always：开关不是 `on` 时三样都不出现；只报告不拦截；路径只取自版本库，不回显 Spec 正文；解析只有 `module_scope.py` 一份。
- Ask first：按公共文件类别放行越界文件；让越界检查自己推断集成基线；在阶段提示里报告越界；把重叠的独占路径判为失败。
- Never：越界时阻止提交或验收；改动 phase-guard 的阶段计算；用 `parallel` 命名新文件或函数。

## Success criteria

1. 开关为 `on` 时，未完成模块 Spec 的「并行边界」一节由 verify-artifacts 校验：正确通过、缺失警告、格式错失败。
2. `module_scope.py check` 能对照给定基线，把本模块的改动文件分成独占内、流程文件、超出边界三类，有文本和 JSON 两种输出。
3. 共享规则要求开关为 `on` 时，在最终验收的改动清单里标出超出并行边界的文件。
4. 开关为 `off` 或未设置时，verify-artifacts 与阶段提示的输出逐字不变，越界检查以退出码 3 拒绝运行。

## 文档建议

无。面向用户的说明等 `crew-interface` 统一写；`docs/design.md` 的文件表在本模块里同步。

<!-- spec-guard: external-review declined -->
