# Spec: scope-overlap-interface

<!-- spec-guard: review approved a6698bc9cbb1 -->

## Objective

module-crew 的协调会话批量审 Spec（review batch）前，要知道这几份 Spec 的并行边界和已开模块有没有独占重叠。它现在借用
`/map --json` 的 `startable.conflicts`，可那里只看已落到集成分支的 Spec：还在交审、只存在于模块分支提交里的 Spec 看不到。
2026-10-22 因此漏报了两个在开模块交审 Spec 里相同的独占路径（O10）。

本模块给 spec-guard 加一个只读接口 `module_scope.py overlap`：调用方把几份 Spec 文件按模块传进来（可选再并入项目里已开的模块），
返回两两之间的独占重叠和每一方的来源。并行边界的解析、重叠的判定都复用现有的唯一一份实现，不另写判据。`interface.json` 升 1.10，
新增 `scopeOverlap` 声明，只增不改。

登记：2026-10-22 经 `/spec-guard:add-module` 插入能力图，作为 Build order 最后一组之后单独一步；依赖 `module-scope-boundary`（解析器与
越界检查）、`map-startable`（重叠判定）、`plugin-interface`（接口文件）。来源：用户本人，经模块协调会话 sg-coord（O10）；开会话依据
用户批准事项 C160。假设 1～6 用户已认可。

## Assumptions

1. **放在 `hooks/module_scope.py`，加只读子命令 `overlap`。** 独占清单的解析复用 `module_scope.parse`；重叠判定复用 `map_view._overlap`
   的规则（路径相同，或一方是目录、另一方在它下面；报较具体的那个路径），把它挪进 `module_scope.py` 成为共用函数 `overlap(a, b)`，
   `map_view.py` 改为调用它。只此一份实现，不复制。
2. **输入只接文件。** `--spec <模块 id>=<文件路径>`，可重复。module-crew 自己 `git show` 交审提交里的 Spec，存成临时文件再传；
   spec-guard 不读 git 对象、不接收标准输入。相对路径按当前工作目录解析（不按 `--project`）。
3. **`--project <项目根>` 可选。** 带上时，把项目里状态为进行中（`in_progress`）或就绪（`ready`）、且有 `spec/<id>.md` 的模块一起比；
   状态判定直接用 `/map` 的同一份（`map_view.build`），已完成、挂起、阻塞、未就绪（`done`、`suspended`、`blocked`、`not_ready`）的模块不参与。同一模块也用 `--spec` 传了文件时，以传入的为准，
   项目里那份不再参与。
4. **不受 `moduleConcurrency` 限制。** 开关关着、没设、配置无效时照样比：这是调用方显式要的事实，不是开关控制的提示或表格。
5. **输出只有 JSON**（给插件读，不给人看）：

   ```json
   {
     "conflicts": [
       {"modules": ["a", "b"], "paths": ["apps/shared/"], "sources": {"a": "/tmp/a.md", "b": "project"}}
     ],
     "errors": [
       {"module": "c", "source": "/tmp/c.md", "error": "no-boundary"}
     ]
   }
   ```

   - 所有参与比较的模块两两都比，包括两个 `--spec`、`--spec` 与项目模块、两个项目模块之间。
   - `sources` 的值是 `--spec` 里写的路径原样，或字面 `project`。
   - Spec 缺并行边界、写法有误、读不出时进 `errors`，这个模块不参与比较，其余照常比，不中断。项目层面的问题（没有能力图、能力图读不出）
     也进 `errors`，`module` 为 `null`、`source` 为 `project`，`--spec` 之间照常比。
6. **`interface.json` 从 1.9 升到 1.10，新增 `scopeOverlap`。** 写法照 `gateTick`／`scopeCheck`：`command`、`readOnly`、`exitCodes`、
   `values`、`notes`、`contract`。只增不改，已有内容逐字不动。随 0.84.0 发布（版本号与 CHANGELOG 由模块协调整批改）。
7. **模块的先后。** `conflicts` 每项里 `modules` 的顺序：两个都在能力图的 Build order 里时按 Build order；否则在能力图里的排前，
   都不在时按 `--spec` 出现的顺序。`conflicts` 整体按这个顺序排，`paths` 按路径排序。
8. **错误码是固定词表，不回显 Spec 正文。** 沿用 `ScopeError` 的五个码，另加 `no-boundary`（没有并行边界一节）、`unreadable`（文件读不出
   或不是 UTF-8）、`no-capability-map`、`map-unreadable`。`paths` 只来自解析通过的独占路径，和 `/map` 的 `conflicts` 一样。
9. **不改 phase-guard、verify-artifacts、`/map` 的输出。** `map_view.py` 只是把 `_overlap` 换成调用共用函数，`/map` 的表格与 JSON
   逐字节不变。

## Contract

### C1 `plugins/spec-guard/hooks/module_scope.py`

- 新函数 `overlap(a: Scope, b: Scope) -> list`：就是现在的 `map_view._overlap`，原样挪过来（文档串同）。
- 新常量 `OVERLAP_ERRORS`：第 8 条的九个错误码（`interface.json scopeOverlap.values.error` 由 `check-interface.py` 对照）。
- 新子命令：

  ```bash
  python3 -B hooks/module_scope.py overlap [--project <项目根>] [--spec <模块 id>=<文件路径> ...]
  ```

  - 退出码 0：完成比较，标准输出是第 5 条的 JSON（有冲突、有 errors 也是 0）。
  - 退出码 2：用法错误，什么都不比：既没有 `--spec` 也没有 `--project`；`--spec` 不是 `<id>=<路径>` 形式；模块 id 不合能力图的写法；
    同一模块 id 用 `--spec` 传了两次；`--project` 不是目录。标准输出一行短码（`usage`、`spec-arg-invalid`、`module-id-invalid`、
    `module-repeated`、`project-not-a-directory`）加说明，不输出 JSON。
  - 带 `--project` 时，在函数内部导入 `map_view` 调 `build(root)` 取各模块 `status`（`map_view` 在模块顶层导入 `module_scope`，
    放进函数里避免循环导入）；能力图不存在报 `no-capability-map`，`build` 抛 `MapError`／读不出报 `map-unreadable`。
- 不写任何文件，不调 git。

### C2 `plugins/spec-guard/hooks/map_view.py`

- 删除 `_overlap`，`from module_scope import ... overlap`，`_concurrency` 改调 `overlap`。别的不动。

### C3 `plugins/spec-guard/interface.json`（公共文件，经【公共变更请求】由 sg-coord 落地）

- `"interface": "1.9"` → `"interface": "1.10"`。
- 在 `gateTick` 之后新增（其余内容逐字不动）：

  ```json
  "scopeOverlap": {
    "command": ["python3", "-B", "hooks/module_scope.py", "overlap", "--project", "<project-root>", "--spec", "<module-id>=<spec-file>"],
    "readOnly": true,
    "exitCodes": {
      "0": "ok; stdout is {\"conflicts\": [{\"modules\": [a, b], \"paths\": [...], \"sources\": {a: <spec-file or \"project\">, b: ...}}], \"errors\": [{\"module\": <id or null>, \"source\": <spec-file or \"project\">, \"error\": <code>}]}; a Spec without a usable boundary is listed in errors and left out, the rest are still compared",
      "2": "usage error, nothing compared: neither --spec nor --project, a --spec not in <module-id>=<file> form, an invalid or repeated module id, or --project is not a directory"
    },
    "values": {
      "source": {
        "<spec-file>": "the --spec file path as given; it replaces the project's spec/<id>.md for that module",
        "project": "spec/<id>.md of a module that /map reports in_progress or ready in --project"
      },
      "error": {
        "no-boundary": "the Spec has no concurrency boundary section",
        "missing-exclusive": "the boundary section has no exclusive line",
        "bad-path": "an exclusive path is malformed",
        "bad-category": "an unknown shared-file category",
        "duplicate-section": "two concurrency boundary sections",
        "unknown-line": "a line in the boundary section that is neither exclusive nor shared",
        "unreadable": "the Spec file cannot be read as UTF-8",
        "no-capability-map": "--project has no spec/CAPABILITY-MAP.md; only the --spec files were compared",
        "map-unreadable": "the capability map or a module file under --project cannot be read; only the --spec files were compared"
      }
    },
    "notes": "interface 1.10; --spec is repeatable and --project is optional, at least one is required; relative --spec paths resolve against the working directory; runs whatever moduleConcurrency says; every pair is compared, overlap is the same rule as mapView startable.conflicts (equal paths, or one inside the other's directory; the narrower path is listed); modules are ordered by Build order, modules not in the map follow in --spec order",
    "contract": "spec/scope-overlap-interface.md"
  }
  ```

### C4 `scripts/check-interface.py`

- `ENTRIES` 加 `scopeOverlap`；核对 `scopeOverlap.command` 引用的脚本存在；`scopeOverlap.values.error` 的键与 `module_scope.OVERLAP_ERRORS`
  一致。已有核对不变。

### C5 `docs/design.md`（只追加）

- 「对外接口」一节 1.9 那段之后追加一段：1.10（scope-overlap-interface）起另有 `scopeOverlap`：给几份 Spec 文件（可选并入项目里进行中、
  就绪的模块）返回两两的独占重叠与来源，不受开关限制，判据与 `startable.conflicts` 同一份；`check-interface.py` 核对脚本与错误码。
- 不改已有行（`module_scope.py` 那一行文件表也不改）。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_module_scope.py
python3 -B plugins/spec-guard/hooks/test_map_view.py
python3 scripts/check-interface.py
/bin/bash scripts/test-checkers.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- **`test_module_scope.py` 新增 `OverlapTests`，先写、确认变红再实现：**
  - 正例：两份 `--spec` 独占路径相同 → 一项冲突，`sources` 是两份路径原样；一方目录包含另一方文件 → 冲突，`paths` 取较具体的路径；
    同名前缀（`apps/bill/` 与 `apps/billing/x`）不算；
  - `--project`：临时项目里一个进行中模块与传入 Spec 重叠 → 冲突，来源 `project`；传入文件与项目里同名模块 → 用传入的（项目里那份与别人
    重叠、传入的不重叠时不报）；已完成、挂起的模块不参与；两个项目模块之间的重叠也报；
  - errors：缺并行边界 → `no-boundary`；格式错 → 对应码；文件不存在 → `unreadable`；errors 不中断，其余照比；`--project` 没有能力图 →
    `no-capability-map` 且 `--spec` 之间照比；errors 里不含 Spec 正文；
  - 开关：`.agent/config.json` 为 `off`、没有这个文件时结果与 `on` 相同；
  - 用法：没有参数、`--spec` 少 `=`、非法 id、重复 id、`--project` 不是目录 → 退出码 2 且不输出 JSON；
  - 顺序：按 Build order；不在能力图的按 `--spec` 顺序排在后面。
- **`test_map_view.py`：** 原 `_overlap` 两个用例改为测 `module_scope.overlap`；其余用例原样全绿（`/map` 输出不变）。
- **`check-interface.py`：** 接口文件落地后通过；`scripts/test-checkers.sh` 的 check-interface 夹具（`mkifc`）补两例：删掉 `scopeOverlap` → 报缺入口；
  `scopeOverlap.values.error` 少一个码 → 报取值不一致。
- **改坏验证：** 让 `overlap` 用字符串前缀判断，确认「同名前缀不算」在两个测试文件里都变红；让 `--project` 的模块在 `--spec` 同名时不被替换，
  确认「传入为准」变红。两处都复原。
- **未验证：** module-crew 真正接上这个接口后的批量审查，留到 module-crew 那边的改动里验。

## Acceptance criteria

- **AC1** 两份 Spec 独占路径相同时报冲突，`sources` 标出两边来源。
- **AC2** 一方目录包含另一方的路径时也报，`paths` 取较具体的路径；同名前缀不报。
- **AC3** `--project` 能和项目里进行中、就绪的模块比；`--spec` 传入的文件覆盖项目里同名模块。
- **AC4** Spec 缺并行边界或写法有误时进 `errors`，不中断其余比较。
- **AC5** `moduleConcurrency` 为 `off` 或未设置时结果照常。
- **AC6** `interface.json` 为 1.10、有 `scopeOverlap` 且其余逐字不变；`check-interface.py` 通过；`docs/design.md` 追加 1.10 一段。
- **AC7** 正反两类回归全绿，`/map` 回归原样全绿；改坏验证两处各自变红。

## 未决问题

- **Q1：项目里进行中、就绪的模块缺并行边界时，要不要也进 `errors`。** A（推荐）：进，`source` 为 `project`；调用方能看到「这个模块没法比」，
  不会把没报冲突当成没冲突。B：不进，和 `/map` 的 `conflicts` 一样静默跳过；输出更短，但开关关着的项目里大量老模块没有这一节时，
  漏比无从察觉。
- **Q2：要不要给人看的文本输出。** A（推荐）：不要，只出 JSON，人看 `/map`。B：加 `--format text`；多一套输出和回归，暂时没有使用方。

## Boundaries

- **总是做**：只读，不写文件、不调 git；解析只经 `module_scope.parse`，重叠只经共用的 `overlap`；errors 不中断；不回显 Spec 正文；
  `/map` 输出逐字节不变；`interface.json` 只增不改。
- **先问再做**：让 `overlap` 自己从 git 提交里读 Spec；把冲突判为失败（非 0 退出码）；按开关决定跑不跑；在 `/map` 表格或阶段提示里显示这些结果。
- **不做**：改 `parse` 或重叠规则本身；改 phase-guard、verify-artifacts；自己改 `interface.json`（交模块协调落地）；改版本号与 CHANGELOG；
  改 module-crew 仓库。

## 并行边界

- 独占：`spec/scope-overlap-interface.md`、`tasks/scope-overlap-interface/plan.md`、`tasks/scope-overlap-interface/todo.md`、`plugins/spec-guard/hooks/module_scope.py`、`plugins/spec-guard/hooks/test_module_scope.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/test_map_view.py`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`docs/design.md`
- 公共：全局配置

## 与在开模块的重叠

- `quiet-injection` 独占了 `docs/design.md`。按用户原话：本模块只往里追加（C5 一段，不改已有行），后合入的一方先 `module-crew sync`。
  这一处重叠是已知的，不用为它排先后。
- `interface.json` 不在独占里：它是公共文件，C3 的内容经【公共变更请求】由 sg-coord 落地（「公共：全局配置」即指它）。
