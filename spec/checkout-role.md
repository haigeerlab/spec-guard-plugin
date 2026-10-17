# Spec: checkout-role

<!-- spec-guard: review approved cd2292bf9cca -->

## Objective

多模块并行时，同一个项目在本机有好几个 checkout：一个协调会话所在的集成 checkout，加上每个模块各一个 worktree。各 worktree 通过提交和同步
拿到同一份能力图与 `.agent/state.json`（不是实时共享），所以阶段提示在每个 checkout 里都按同样的规则算出同一个「当前模块」：在 `shop` 的
worktree 里，提示可能让人去构建 `billing`；在协调会话里，提示会建议它自己去 `/build`，而它的职责是协调、不开发。`/map` 也只看得到当前
checkout 的 todo，看不到其他 worktree 里做到哪了。

本模块在开关 `moduleConcurrency` 为 `on` 时提供三样东西：

1. **角色标记**：每个 checkout 可以有一个角色——「模块：<id>」或「协调」。标记存在这个 checkout 自己的 git 目录里，不进版本库、不在 worktree
   之间共享。由新命令先预览、确认后写。
2. **按角色调整阶段提示的展示**：全局的选模块与算阶段**完全不动**（`project_stage` 的代码和输入都不变）；模块 checkout 另外报告它自己的模块、
   「下一步」只指向它；协调 checkout 的「下一步」改为统筹措辞，不建议 `/build`。
3. **`/map` 看其他 worktree**：有对应 worktree 的模块多一个 `worktree` 字段，给出那里的进度、有没有未提交改动、提交是否已合入当前分支。

开关为 `off`、未设置或配置无效时，角色标记即使存在也**不被读取**，阶段提示与 `/map` 的输出逐字节不变；写标记的命令拒绝运行。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图（同批 7 个模块）。来源：用户本人，经多模块并行需求讨论（2026-10-17～18），需求记录
第 5 节 A6 与 C1。2026-10-18 经 delegate 只读审查后修订：放弃「把角色模块当作 activeModule 传入 `project_stage`」，改为只在展示层报告（见文末
「外部审查意见」），用户决定采纳全部发现。

## Assumptions

### 角色标记

1. **位置。** `git -C <项目根> rev-parse --git-path spec-guard/role` 给出的文件，按项目根解析成绝对路径。普通仓库在 `.git/spec-guard/role`，
   其他 worktree 在 `.git/worktrees/<名>/spec-guard/role`，子模块在它自己的 gitdir 下。所以天然「每个 checkout 一份」，不被提交，也不随同步传到
   别的 worktree。
2. **只认目标项目。** 读写前核对 `git rev-parse --show-toplevel` 就是给定的项目根（防止把父仓库当成项目）；bare 仓库没有 checkout，拒绝写入；
   git 调用失败时读为「没有角色」、写入拒绝，绝不回退到别的路径。
3. **格式与安全。** 内容只有一行：`module <id>` 或 `coordinator`，文件不超过 256 字节。`spec-guard/` 目录或 `role` 文件是符号链接、或不是普通
   文件时，读为「无效」、写入拒绝；读取不跟随链接。其他内容一律视为无效：阶段提示报一行固定措辞（不回显文件内容），按没有角色处理。
4. **命令** `/spec-guard:checkout-role`（Codex：`spec-guard-ops` 的 checkout-role 一节），脚本 `hooks/checkout_role.py`：
   - `show`：只读，报告这个 checkout 的角色（或没有、无效）。
   - `set --module <id>` 或 `set --coordinator`：默认只预览（写明旧值 → 新值），带 `--confirm` 才写；`<id>` 必须是能力图里的模块。
   - `clear`：同样先预览、再确认后删除，只删这一个文件。
   - 开关不是 `on` 时 `set` 与 `clear` 拒绝（退出码 3）；`show` 照常只读。
   - 写入：同目录临时文件加原子替换。`--confirm` 时重新做全部校验（开关、模块、链接、仓库），并重新读取当前值、在输出里写明覆盖了什么；
     两个会话先后确认时以后写入的为准。写后读回，与刚写入的不一致就报 `concurrent-change`（退出码 4），不重试。
   - 通常由运行时（module-crew）开 worktree 后调用；命令本身不开会话、不建 worktree。

### 阶段提示（只改展示，不改选模块）

5. **全局计算不变。** `project_stage(states, active)` 的代码和传入的值都不变，`.agent/state.json` 的 `activeModule` 照旧生效；「当前阶段」
   「Current module」两行仍是全项目的结果。读取角色的入口只有一个：开关为 on 时才调用，off 时一次都不调用。
6. **模块角色 X。** 在全局行之后加一段「本 checkout」块，用同一个 `module_state` 算 X 的状态，「下一步」只指向 X：
   - X 为 NEEDS_SPEC／NEEDS_PLAN／BUILDING：评审状态、`Next gate` 都按 X 计算（复用 `review_hint`、`next_gate`），「下一步」按 X 的阶段与评审约束给出，
     与普通单模块时的措辞一致；全局当前模块的评审行与外部审查提示**不显示**（这个 checkout 不处理别的模块；外部审查由协调会话向用户提议）。
   - X 已完成：只写「`X` 在本 checkout 已完成；交回协调会话做最终验收与合并，不在这里开始别的模块，也不在这里合并或推送」。不出现切换模块、
     设置 activeModule、先 push 再 merge 之类的建议。
   - X 挂起：「`X` 已挂起；恢复它，或请协调会话重新指定或清除本 checkout 的角色；不在这里做别的模块」。
   - X 不在能力图里：「本 checkout 的角色指向 `X`，但能力图里没有它；用 checkout-role 重新指定或清除」。
   - 固定加一行：本 checkout 只做 X，做完交回协调会话。
7. **协调角色。** 全局各行照常显示（协调会话要看全局），另加一行说明身份；「下一步」：
   - 全局当前模块有评审约束（待审、无效、批准后已修订、最终验收复审等，即 `review_step` 不为空）时，**保留**这条约束原文，再接一句「由本协调会话
     在这里呈现给用户并记录」；外部审查提示照常显示，由协调会话负责提议；
   - 没有评审约束时，改为统筹措辞：用 `/spec-guard:map` 查看可开工模块、各 worktree 进度与并行边界重叠，按共享规则「协调会话的批准与合并」处理交审与
     合并。任何情况下都**不建议 `/build`**；`Next gate` 行改为陈述「`M` 的下一个 gate 是……，由它的模块会话推进」，不写「keep going」。
8. **与 PR #345（阶段提示跟随产物语言）的关系。** #345 会把阶段提示的说明文字按 `artifactLanguage` 改成中文，改的正是 `module_stage.py` 里这批字符串。
   本模块新增的提示行先按现有写法用英文；两个分支谁后合入，谁负责解决冲突，并把新增的几行纳入 #345 的语言规则。Plan 的最后一个任务前提写明这一条，
   `crew-interface` 收尾时再核对一次。

### `/map` 的 `worktree` 字段（开关为 on 时）

9. **只枚举一次。** 每次 `/map` 运行 `git worktree list --porcelain -z`（按 NUL 分隔解析）一次，跳过当前 checkout，以及已失效（prunable、路径不存在）
   的 worktree；锁定的照常读；detached HEAD 时 `branch` 为 `null`。读其他 worktree 的角色用底层读取函数，由**当前** checkout 的开关授权，不看对方的配置。
10. **字段形状。** 角色为「模块：X」的 worktree 记到模块 X 上：
    `{"path", "branch", "head", "progress": {"done", "total"} | null, "todo": "ok" | "missing" | "unreadable", "dirty": true | false | null,
    "merged": true | false | null}`；没有对应 worktree 的模块为 `null`。两个 worktree 声明同一模块时按列表顺序取第一个，并加 `"duplicates": [其余路径]`。
    - `progress` 读那个 worktree 的 `tasks/X/todo.md`（勾选计数复用 `module_stage` 的判据）；文件不存在为 `todo: "missing"`，读不了为 `"unreadable"`，两者 `progress` 都为 `null`。
    - `dirty`：那个 worktree 有没有未提交改动（`git status --porcelain`），判断不了为 `null`。
    - `merged`：**只表示提交的祖先关系**——一次取定那个 worktree 的 HEAD 与当前 checkout 的 HEAD，`git merge-base --is-ancestor` 退出 0 为 `true`、1 为
      `false`、其他为 `null`。它不包含未提交改动，也不授权任何合并。
11. **性能与降级。** 每个 worktree 最多 3 次 git 调用，结果缓存；整次扫描超过 10 秒后，剩下的 worktree 只给 `path`、`branch`、`head`，其余为 `null`。
    单个 worktree 出错只影响它自己那一项，不让 `/map` 失败。
12. **表格。** 开关为 on 时，凡是有 worktree 的模块（不论本地状态是就绪、进行中还是已完成），状态格后加「· worktree n/m」，再按情况加「有未提交改动」
    「未合入」「合入未知」；`progress` 为 `null` 时写「进度未知」。主表的状态仍按当前 checkout 计算。

### 不变量

13. hook 只读：阶段提示与 `/map` 只读角色标记、其他 worktree 的 todo 与 git 引用，不写任何文件；写标记只经命令、预览确认后进行；phase-guard 仍只依赖
    `bash`、`git`、`python3`。

## Contract

### `hooks/checkout_role.py`（新增）

- `role_path(root) -> Path | None`：按假设 1、2 求绝对路径；不满足时为 `None`。
- `read_role(root) -> tuple`：`("none", None)`、`("invalid", None)`、`("coordinator", None)` 或 `("module", id)`；按假设 3 处理链接、大小与内容。
- `role(root)`：开关不是 on 时直接返回 `("none", None)`，**不调用** `read_role`；阶段提示只调它。
- CLI：`show`、`set --module <id> | --coordinator [--confirm]`、`clear [--confirm]`，`--project` 指定项目根。退出码：0 成功；2 用法错误、不在 git
  仓库、项目根不符、bare 仓库、链接或非普通文件、模块不在能力图；3 开关不是 on（只对 `set`、`clear`）；4 `concurrent-change`。

### `hooks/module_stage.py`

- `describe()` 末尾组装输出前：开关为 on 时调 `checkout_role.role(root)`，按假设 6、7 调整展示；不改 `project_stage`、`module_state` 与它们的调用参数。
- 开关不是 on 时，`describe()` 的代码路径与输出都与现在相同。

### `hooks/map_view.py`

- `_concurrency()` 里调用一次 worktree 扫描，为每个模块加 `worktree`（假设 9～11）；`render` 按假设 12 改状态格。开关不是 on 时不扫描、不变。

### 命令与文档

- 新增 `commands/checkout-role.md`；`skills/spec-guard-ops/SKILL.md` 加 checkout-role 一节；`docs/design.md` 文件表加 `checkout_role.py`；`docs/commands.md`
  命令总表加一行；CHANGELOG 未发布小节加一条「新增」。
- 共享规则「协调会话的批准与合并」一节里「协调会话」的说明补一句：由角色标记 `coordinator` 标出，外部审查由协调会话向用户提议。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_checkout_role.py
python3 -B plugins/spec-guard/hooks/test_map_view.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- **`test_checkout_role.py`（新增，先红后绿）：**
  - 在临时仓库与它的一个 worktree 里：标记写在各自的 git 目录、互不影响、不出现在 `git status`；`--project` 与进程当前目录不同时仍写对位置；
  - `show`／`set`（预览写明旧值 → 新值且不写；确认后写并读回）／`clear`；模块不在能力图、项目根是父仓库的子目录、bare 仓库、`spec-guard` 目录或 `role` 是
    符号链接、超过 256 字节时都拒绝或读为无效，且不回显内容；开关 off 时 `set`、`clear` 退出 3；
  - 读回不一致（测试里在写后替换文件）报退出码 4；
  - **off 时零读取**：开关 off 时调用 `role()`，用计数替身确认 `read_role` 一次都没被调用。
- **阶段提示（`test-phase-guard.sh` 与单元测试）：**
  - 开关 off、未设置、配置无效时，放了角色标记，注入与没有标记时逐字节相同；
  - on + 模块角色 X（X 不是全局当前模块），X 分别处于 NEEDS_SPEC、NEEDS_PLAN（Spec 待审）、BUILDING、已完成、挂起、不在能力图：「本 checkout」块与「下一步」
    都只指向 X；X 已完成时不出现切换模块、activeModule、push 或 merge 的建议；全局当前模块的评审行与外部审查提示不出现；
  - on + 模块角色时，另有一个模块半完成、state.json 的 activeModule 无效或指向别的模块：全局两行照旧，「下一步」仍只指向 X；
  - on + 协调角色：全局当前模块分别为待审、批准后已修订、在构建中：前两种保留评审约束原文并加呈现说明，第三种为统筹措辞；都不含 `/build`；
  - on + 标记无效：一行固定措辞，其余与没有角色时相同；
  - `project_stage` 与 `module_state` 的代码不变（检查点用 `git diff` 核对）。
- **`/map`（`test_map_view.py`）：** 一个主仓库加三个 worktree（两个声明不同模块且进度不同、其中一个已合入、一个有未提交改动；第三个与第一个声明同一模块）：
  `worktree` 各字段、`duplicates`、todo 缺失与不可读、detached HEAD、已删除目录的 worktree 被跳过；本地为就绪或已完成的模块也带后缀；开关 off 时不扫描（计数替身确认
  一次 git worktree 调用都没有）、字段与后缀都不出现。
- **改坏验证：** 让 off 时也调用 `read_role`，确认零读取断言变红；让模块角色 X 已完成时保留原「下一步」，确认对应断言变红；让协调角色丢掉评审约束，确认对应断言
  变红；让 `merged` 在退出码非 0／1 时为 `true`，确认对应断言变红。
- **一次性整份比对：** 与前两个模块一样，用改动前提交的 hooks 在同一组夹具（开关不是 on，含放了角色标记的 checkout）上对比阶段提示与 `/map` 输出，去掉
  `generatedAt` 与分钟戳后逐字节相同。

## Boundaries

- Always：开关不是 on 时不读角色标记、不扫描 worktree、输出不变；hook 只读；写标记先预览后确认；`project_stage` 与 `module_state` 的代码和输入不改；
  `merged` 判断不了不当作已合入；模块 checkout 的「下一步」只指向它自己的模块。
- Ask first：让角色标记改变全局当前模块或阶段；让角色标记影响 `verify-artifacts`；在 `/map` 里 fetch 或读远端；让命令自动建 worktree 或开会话；把角色标记放进
  版本库或 `.agent/`。
- Never：hook 写任何文件；在协调 checkout 的提示里建议 `/build`；在模块 checkout 的提示里建议切换到别的模块、合并或推送；跟随符号链接写入；用 `parallel` 命名新文件或函数。

## Success criteria

1. 开关为 on 时，`/spec-guard:checkout-role` 能在每个 checkout 各自预览、确认后写入或清除角色；标记不进版本库、互不影响；链接、bare、父仓库、并发写都有明确拒绝或报错。
2. 模块 checkout 的阶段提示保留全局两行，另给出它自己模块的状态与只指向它的「下一步」；做完时只提示交回协调会话。协调 checkout 的「下一步」保留评审约束或给出统筹措辞，
   从不建议 `/build`。全局选模块与算阶段的代码和输入不变。
3. `/map --json` 中有对应 worktree 的模块多一个 `worktree` 字段，给出进度、未提交改动与提交祖先关系；表格对应加后缀。
4. 开关为 off、未设置或配置无效时，不读角色、不扫描 worktree，阶段提示与 `/map` 的输出与改动前逐字节相同，写标记的命令以退出码 3 拒绝。

## 文档建议

无新增文档；本模块自身要更新的命令说明与设计文档已列在 Contract。

## 外部审查意见

2026-10-18，delegate 只读审查（Codex 后端），范围：本 Spec 的修订前版本、`hooks/module_stage.py`、`hooks/map_view.py`。结论只作参考，不算批准。
共 6 条 P1、7 条 P2，用户决定全部采纳，已按下列方式修订：

- **P1 函数代码不变不能证明没改阶段判断核心**（换掉 `active` 会改变 current、stage、paused、审查对象与完成后建议）→ 放弃「角色当作 activeModule」，改为只在展示层报告
  （假设 5、6），`project_stage` 的代码和输入都不变。
- **P1 X 完成后会建议切到别的模块、先 push 再 merge** → 假设 6：X 已完成时只提示交回协调会话，不出现这些建议；加对应用例。
- **P1 X 挂起或被移出能力图时回落 Build order，与「只做 X」矛盾** → 假设 6：这两种情况停下，提示恢复、重新指定或清除角色。
- **P2 只换传入值会让诊断与来源对不上** → 随展示层方案消失：全局两行与 state.json 诊断照旧，「本 checkout」块单独呈现；加 state.json 无效与半完成模块的用例。
- **P1 协调角色整体替换「下一步」会丢掉审查约束** → 假设 7：有 `review_step` 时保留原文并写明由协调会话呈现与记录，外部审查由协调会话提议；加三种用例。
- **P2 git-path 相对路径与仓库类型** → 假设 1、2：按项目根解析为绝对路径，核对顶层，bare 拒绝写，git 失败不回退。
- **P1 符号链接越界** → 假设 3：不跟随链接、只接受普通文件、256 字节上限；`clear` 只删这一个文件。
- **P2 并发更新** → 假设 4：确认时重新校验并写明覆盖了什么，后写入为准，读回不一致报退出码 4。
- **P2 跨 worktree 扫描的开关与异常路径** → 假设 9、10：由当前 checkout 的开关授权、用底层读取；区分 todo 缺失与不可读；处理失效、锁定、detached；NUL 分隔解析。
- **P2 `merged` 不代表工作已合入** → 假设 10：加 `dirty`，写明 `merged` 只是提交祖先关系、一次取定两边 HEAD、退出码三态映射。
- **P2 表格只给本地进行中模块加后缀** → 假设 12：凡有 worktree 的模块都显示，`progress` 为空时写「进度未知」。
- **P2 性能** → 假设 11：只枚举一次、缓存、每个 worktree 最多 3 次调用、10 秒总预算后降级。
- **P2 测试证明不了 off 时不读** → 测试策略：计数替身证明 off 时零读取、零扫描；整份比对去掉动态字段。
- 另指出 Objective 里「共用同一份能力图与 state.json」的说法不准确（worktree 之间靠提交与同步，不是实时共享）→ 已改写。
