# Plan: doc-chain

<!-- spec-guard: review approved -->

依据 [`spec/doc-chain.md`](../../spec/doc-chain.md)：2026-10-22 批准（事项 C190，Q1 A、Q2 A、Q3 A：影响表留在 Spec、Plan 交审摆出来；
「文档核验」一行给串行与模块会话、不给协调会话；`ready` 不改名、改说明；D15 按 Spec 的写法确认）。同一答复定了与
`ledger-standalone-reminder` 的重叠分工：`docs/design.md` 归本模块独占（对方只改不变量那一句）；`docs/optional-features.md` 归对方独占，
本模块只改其中基线路径的说法；后合入的一方先 `module-crew sync`。

分支 `doc-chain`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/doc-chain`，从集成分支 `crew/fix-batch` 开出。
module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调整批合完后统一改，
本模块把拟写的更新说明记在 todo 末尾。

所需工具：Python 与 bash 回归、本机 `git`。不访问远端，不新增依赖。

## 架构决定

- **核验里的 git 只在 `documentation_verification.py`。** 一个私有函数 `_changes(project, module, path)` 返回 `(check, added, removed, reason)`：
  先 `git log --diff-filter=A --format=%H -- spec/<模块>.md` 取最早一个提交作基点，再 `git diff --numstat <基点> -- <路径>`。
  `subprocess.run` 传列表、`cwd=project`、`timeout=10`、`check=False`，不经 shell；任何失败（`FileNotFoundError`、超时、非零退出、
  输出解析不了）都返回 `unknown` 并带原因。二进制文件 `numstat` 是 `-`，按「改过、行数未知」处理。
- **状态判定按 Spec 假设 6 的顺序**：URL → `unverified`（不跑 git）；`target` → `target-changed`／`target-unchanged`（有删除行加 attention）；
  其余 → `changed`／`unchanged`（没改加 attention）；git 查不了 → `unknown`（加 attention）。只对 `update` 且 `delivered` 的关注点算；
  `create`、`deferred`、`pending` 的 outcome 写 `not-checked`。
- **基线条目从 `parse_impact` 的结果里拿。** 看 `documentation_impact.Impact` 是否已带基线条目；没带就在核验里再调一次 `parse_baseline`
  （同一文件、只读），不改 `documentation_impact.py` 的接口。
- **最终 gate 那一行加在 `describe()` 的 notes 里**，用 `stop_node` 已算出的 `node`，与停点规则块互不依赖；判据 `node == "final-gate"`、
  `role_kind != "coordinator"`、`documentation_baseline_present(root)`。入口文字放进 `COMMANDS`／`COMMANDS_ZH` 的宿主表（新键
  `doc-verify`），沿用现有按宿主取入口的做法。不碰 `phase-guard.sh`。
- **不新建文件**，回归都加在已登记的测试文件里，不用改 `validate.sh`。

## Task List

### Task 0：同步批准标记，按 C190 修订 Spec

1. 开工通知到后单独执行 `module-crew sync`，Spec、Plan、todo 取集成分支带批准标记的版本。
2. 按 C190 的重叠分工改 Spec：「改动 4」里 `docs/optional-features.md` 改为只改基线路径的说法；「并行边界」独占清单去掉
   `docs/optional-features.md`；「与在开模块的重叠」写明分工；Spec 末尾加「变更记录」一行（来源：用户答复 C190，经 sg-coord 转达，消息 #10406）。
   Spec 指纹随之变为修订，最终验收附这段差异，批准最终验收即同时批准修订后的 Spec。

- 验收：sync 退出码 0；validate、phase-guard、verify-artifacts 全过；`module_scope.py validate` 通过。

### Task 1：核验按状态区分（改动 1、改动 5 前半）

1. 先写回归（红），`test_documentation_verification.py` 新增一组用临时 git 仓库的用例：现状类改过（已提交）、改过（只在工作区）、没改过；
   `target` 没改、改过只增、改过有删除；URL 外部文档；`Authority` 带 `#锚点`；Spec 未提交；非 git 目录；git 命令失败（`mock` 掉 `subprocess.run`
   抛 `FileNotFoundError` 与返回非零各一）；`create`／`deferred`／`pending` 为 `not-checked` 且判定不变；JSON 里 `check`、`added`、`removed`。
2. 原有用例里断言 `ready` 的 `update`+`delivered` 用例在非 git 临时目录跑，按 Spec 假设 8 会变成 `unknown`／`attention`：把它们的夹具改为
   临时 git 仓库并在加 Spec 后提交、再改文档，断言本身不改（见风险一）。
3. 实现 `_changes()` 与状态判定，`_as_json` 加字段。

- 验收：AC1～AC5；新断言先红后绿，原有断言不改照过。
- 验证：`python3 -B plugins/spec-guard/hooks/test_documentation_verification.py`；`python3 -B plugins/spec-guard/hooks/test_documentation_impact.py`；
  `python3 -B plugins/spec-guard/hooks/test_python_compat.py`。

### Task 2：最终 gate 注入核验要求（改动 2、改动 5 后半）

1. 先写回归（红），`test_stop_rules.py`：最终 gate、有基线、串行 → 有「文档核验」一行（中文、英文；Claude、Codex 入口各一）；模块会话（checkout 角色
   为模块）→ 有；协调会话 → 无；没有基线 → 无且整段输出与改前逐字相同；Spec 待审、Plan 待审、中途 gate 节点 → 无。
2. 实现 `documentation_baseline_present()`、`COMMANDS` 的 `doc-verify` 键与 `describe()` 的 notes 追加。

- 验收：AC6；新断言先红后绿。
- 验证：`python3 -B plugins/spec-guard/hooks/test_stop_rules.py`；`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`；
  `python3 -B plugins/spec-guard/hooks/test_checkout_role.py`、`test_module_stage_sanitization.py`。

### Task 3：规则文字（改动 3）

`references/node-rules.md` 的「Spec 交审」「Plan 交审」「最终验收」三节各加一两句；`references/workflow-checkpoints.md`「文档建议」一节加一段
三段链与 `target` 只补充。都以「项目有文档基线时」开头。`test_workflow_checkpoints.py` 加短语断言（先红），体积或短语断言要跟着改的一并改。

- 验收：AC7。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`python3 -B plugins/spec-guard/hooks/test_stop_rules.py`。

### Task 4：说明文字（改动 4）

`references/documentation-verification.md`、`commands/documentation-verification.md`、`skills/spec-guard-ops/SKILL.md` 的 documentation 一节按
Spec 假设 6～9、11 改写结果说明与 `ready` 的含义；`references/documentation-impact.md`「模块 Plan」一节加 `target` 只补充；
`docs/design.md:205` 改 `docs/DOCUMENTATION-BASELINE.md`，并在讲文档治理处补一句三段链与最终 gate 注入；`docs/optional-features.md` 只改基线路径的
说法（现已是 `docs/DOCUMENTATION-BASELINE.md` 的话不改）。

- 验收：AC8；`grep -rn 'DOCUMENTATION-BASELINE' --exclude-dir=.git . | grep -v 'docs/DOCUMENTATION-BASELINE'` 除 `docs/reports/`（历史报告原文）
  与测试代码的临时路径外为空；`grep` 不再有「证据非空即 ready」的说法。
- 验证：`/bin/bash scripts/validate.sh --quick`；`python3 scripts/check-readme-sync.py`。

### Checkpoint 1（report）：变异核对

在 scratchpad 里 `mktemp -d` 建的副本（`git archive HEAD`）上分别：让 `target` 有删除行也不加 attention；让 git 失败按 `unchanged` 处理；
把基点改成 `HEAD`（只看工作区）；去掉 `role_kind != "coordinator"`。每种都应让对应断言变红，结果记进 todo。

### Task 5：临时消费者项目实跑（AC10）

在 scratchpad 里 `mktemp -d` 建临时项目：落约定、写基线（一行 URL、一行 `target`、两行现状类），造一个模块走到最终 gate（Spec 已提交，
影响表与 Plan 的交付、outcome 表齐全），改一份现状类文档、给 `target` 文档删一行；用本 worktree 的 `phase-guard.sh`（`CLAUDE_PROJECT_DIR` 指向
临时项目）看到「文档核验」一行，再跑本 worktree 的 `documentation_verification.py` 得到 `changed`、`unchanged`、`target-changed`、`unverified`
各一项，两段原文记进 todo。

- 验收：AC10。

### Task 6：合入集成分支并跑完整检查

实现各提交走 `verify-and-commit.sh` 全套；单独执行 `module-crew sync`，再跑 validate、phase-guard、verify-artifacts、`test_stop_rules.py`、
`test_documentation_verification.py`；`module_scope.py check --module doc-chain --base crew/fix-batch` 核对越界，应为空。todo 末尾写拟写的更新说明
与对使用者的影响。

### 最终验收（gate）

按停点规则「最终验收」一节交审：做了什么、AC1～AC10 逐条证据、改动文件／提交／依赖表、Spec 中途改过吗（Task 0 的修订差异原样附上）；
「拟回告：无」（需求来自用户本人）。不含推送与开 PR；合并由模块协调按用户原话做。

## 会改哪些文件

- 代码：`hooks/documentation_verification.py`、`hooks/module_stage.py`。
- 回归：`hooks/test_documentation_verification.py`、`hooks/test_stop_rules.py`、`hooks/test_workflow_checkpoints.py`。
- 规则与说明：`references/node-rules.md`、`references/workflow-checkpoints.md`、`references/documentation-verification.md`、
  `references/documentation-impact.md`、`commands/documentation-verification.md`、`skills/spec-guard-ops/SKILL.md`、`docs/design.md`、
  `docs/optional-features.md`（仅基线路径说法，按 C190）。
- 本模块：`spec/doc-chain.md`（Task 0 修订）、`tasks/doc-chain/plan.md`、`tasks/doc-chain/todo.md`。
- 不新增依赖，不碰公共文件。

## 风险

- **原有核验回归在非 git 目录跑。** 按 Spec 假设 8，`update`+`delivered` 在非 git 目录会变成 `unknown`／`attention`，与原断言 `ready` 冲突。
  处理：只改这些用例的夹具（建临时 git 仓库、先提交 Spec 再改文档），断言不改；改了哪几条记进 todo。若有原断言在 git 夹具下仍过不了，
  说明行为与 Spec 假设冲突，停下问。
- **使用者的老模块被新判据翻成 `attention`。** 老模块的 Spec 早已提交，基点在很久以前，只要之后改过文档就是 `changed`，误报少；
  真没改过的本来就该提醒。写进「对使用者的影响」。
- **`git log --diff-filter=A` 遇到改名或删除后重建的 Spec。** 取最早一个加入提交，基点更早只会多算「改过」，不会把改过判成没改；回归覆盖一次删除重建。
- **`module_stage.py` 与 `ledger-standalone-reminder` 同碰。** 本模块只加一个函数、一个宿主表键和 `describe()` 一处追加；按 C190 后合入的一方先 sync。
- **停点规则体积断言。** `rules-at-nodes` 对 `node-rules.md` 有体积约束时，每节只加一两句；超了先压字，不放宽断言。

## 中途会停下来问你的地方

没有中途 `gate`，做完直接交最终验收（不含推送与开 PR）。只在 Spec「先问再做」的情况停：要让 hook 自己跑核验或 git、要改表格式或状态集合、
要检查 `create` 的交付物、要把核验计入 `verify-artifacts` 或阻断验收、发现别的插件解析核验 JSON；以及风险一里原断言在 git 夹具下仍过不了时。
