# Spec: doc-chain

<!-- spec-guard: review pending -->

## Objective

用户对文档治理的目的说得很清楚（D14）：「每个模块改了代码，该更新的文档不漏。」现状是三段各自为政：

- 交审 Spec 时的「文档建议」是规则，会触发，但不看文档基线，采纳的建议也不落进影响表；
- 「文档影响」（Spec 的 `Documentation impact` 表、Plan 的 `Documentation delivery` 表）与「文档核验」只在显式调用命令时运行，
  没有任何 hook 或检查点把它们串起来（审查 E-95、整体疑点 3）；
- 核验只要 `delivered` 的证据非空就报 `ready`，名称容易被读成「文档已核验」（F17）；基线状态 `target`（已批准、未完全实现的目标）
  和外部文档与现状类文档一视同仁；
- 设计文档把基线写成 `DOCUMENTATION-BASELINE.md`，实现读的是 `docs/DOCUMENTATION-BASELINE.md`（F17，`docs/design.md:205`）。

用户还提出：顶层架构、需求愿景这类文档不能被小模块的实现覆盖掉（D15）。本模块按 D15 把三段接成一条链：

1. **交审 Spec 时给文档建议**：项目建了基线时按基线的关注点提，采纳的写进本 Spec 的影响表；
2. **Plan 写文档影响**：Plan 交审列出影响表里要改、要建的文档和它的交付计划；
3. **最终 gate 有基线时停点注入要求跑核验**，核验按基线状态区分：现状类文档 `update` 须文件确被改过，`target` 文档不要求改、
   只列出改动差异交用户看，外部文档只要求证据非空并标「未核验」；
4. 基线状态为 `target` 的文档只能补充，不得删改未实现的目标；改目标即改需求，单独交用户批；
5. 设计文档的基线路径统一为 `docs/DOCUMENTATION-BASELINE.md`。

登记：2026-10-22 修复批次的模块之一，经用户批准事项 C184 开模块会话；能力图依赖 `quiet-injection`（已合入，提供一行形式与状态码，
停点进状态码）与 `documentation-verification`（被本模块改语义）。
依据：`docs/reports/2026-10-22-feature-inventory/decisions.md`（D14、D15）；`docs/reports/2026-10-22-multidimension-audit.md`（F17）；
`docs/reports/2026-10-22-feature-inventory/E-proposal-docs.md`（#78～#96 与整体疑点 3）。

## Assumptions

1. **只对建了基线的项目生效。** 没有 `docs/DOCUMENTATION-BASELINE.md` 的项目：阶段注入、停点规则的效果、核验输出都与改前相同
   （停点规则正文里新加的句子都以「项目有文档基线时」开头，没有基线的项目读到也不用做任何事）。「hook 默认不生效」的不变量不变。
2. **影响表留在 Spec，Plan 交审把它摆出来。** D15 写的是「Plan 写文档影响」。现有格式是：Spec 里 `Documentation impact`（每个关注点
   一个决定），Plan 里 `Documentation delivery`（`update`／`create` 的交付物）。按现有格式解释「Plan 写文档影响」为：Plan 交审时把
   影响表里的 `update`／`create` 与 Plan 的交付表一并列出，交付变成 Plan 的普通任务。不挪表、不改解析器的表格式，已建基线的项目
   已写的表不用迁移。（另一种做法见 Q1。）
3. **hook 不跑核验，只注入「要跑」。** 最终 gate 的那一轮（`stop_node` 为 `final-gate`），项目的 `docs/DOCUMENTATION-BASELINE.md`
   存在时，阶段注入在「建议下一步」之前加一行：最终验收前跑文档核验（按宿主写入口），把结果写进验收消息的「验收结果」。
   hook 只看这个文件在不在（与基线解析器判 `absent` 的依据相同），不解析、不跑 git，不写文件。有效与否由核验命令自己报。
4. **这一行在串行与模块会话都出，协调会话不出。** 停点规则块只在串行时附（`rules-at-nodes` 定的，模块与协调会话的停点规则归协作插件）；
   但最终验收【交审】是模块会话发的，文档核验得由做模块的会话跑。所以这一行按 `role_kind` 不是 `coordinator` 出，不跟停点规则块走。
   （另一种做法见 Q2。）
5. **一行形式不变。** 这一行只出现在完整输出里；`stop_node` 已进状态码，进入最终 gate 那一轮必然是完整输出，同一节点后续轮次的一行形式
   不带它（与停点规则相同）。状态码的组成不加「有无基线」。
6. **核验按基线状态区分**（对每个影响决定为 `update` 且 outcome 为 `delivered` 的关注点，看基线里它那一行的 `Status` 与 `Authority`）：
   - **外部文档**（`Authority` 是 URL，形如 `<scheme>://…`）：只要求证据非空（现有规则），结果标 `unverified`（未核验）；不算 `attention`。
   - **`target`**：不要求文件被改。文件改过时，结果标 `target-changed` 并给出增删行数，提示「把这份文档的改动差异原样附进验收消息，
     由用户看」；有删除行时另加一条 `attention`：「target 文档有删改：删改未实现的目标即改需求，须单独交用户批准」。没改过标 `target-unchanged`。
   - **其余状态（`verified`、`in-progress`、`pending`，现状类）**：文件须确被改过，改过标 `changed`；没改过标 `unchanged` 并加
     `attention`：「声明已交付，但 `<路径>` 自本模块开始以来没有改动」。
   - `create`、`deferred`、`pending` 与没有 outcome 的情况：判定不变。
7. **「被改过」的判据：自本模块 Spec 首次提交以来，工作区里这份文件与那次提交不同。** 基点取 `git log --diff-filter=A` 找到的
   第一个加入 `spec/<模块>.md` 的提交；用 `git diff --numstat <基点> -- <路径>`（比较基点与工作区，包含之后的提交、暂存与未暂存改动）。
   串行与 module-crew 的模块分支都适用，不依赖上游分支或集成分支的配置。`Authority` 带 `#锚点` 时去掉锚点再比。
8. **查不了就说查不了。** 不在 git 仓库、git 不可用、Spec 还没提交过、git 命令失败时，该项结果标 `unknown` 并加 `attention`：
   「无法确认 `<路径>` 是否改过：<原因>」；不当作 `unchanged`，也不当作改过。
9. **`ready` 的名字不改，含义如实写。** `ready` 现在表示：没有未收口的声明；现状类 `update` 的文件确被改过；`target` 的删改已提示。
   它仍不证明文档内容正确、代码与文档一致或已对外发布；外部文档列为 `unverified`。说明文字（命令、参考、Codex 入口）按这个改写，
   不再说「只要证据非空」。（另一种做法见 Q3。）
10. **`target` 只能补充是规则，机械检查只到「有没有删改行」。** 删改行可能只是改错字，所以只提示、交用户看，不判违规。规则写进：
    文档建议一节、停点规则的 Plan 交审与最终验收、文档影响参考说明：`update` 指向 `target` 文档时，只能标注已实现的部分、补充约束，
    不得删改未实现的目标；要改目标就是改需求，停下单独问用户。
11. **核验的 JSON 加字段、不改原有字段。** 每个 outcome 增加 `check`（`changed`／`unchanged`／`target-changed`／`target-unchanged`／
    `unverified`／`unknown`／`not-checked`，后者用于 `create`、`deferred`、`pending`）；`target-changed` 与 `changed` 另带 `added`、`removed`
    行数。`state`、`outcomes`、`attention` 原有含义与字段不变。外部使用方只有本插件的命令与 Codex 入口（2026-10-22 搜过）。
12. **本仓库自己没有基线**，本模块 Spec 不写影响表；构建时用临时项目验证。

## Contract

### 改动 1 核验按状态区分（`hooks/documentation_verification.py`）

- 读基线条目（`parse_impact` 已经解析过基线；需要的话从 `documentation_baseline.parse_baseline` 取 `Authority` 与 `Status`）。
- 按假设 6、7、8 给每个 outcome 算 `check`，补 `attention`；git 调用用 `subprocess.run([...], cwd=project)`、带超时、不经 shell，
  只读命令（`git log`、`git diff --numstat`）。
- `_as_json` 输出加 `check`、`added`、`removed`（假设 11）；命令行参数不变。

### 改动 2 最终 gate 注入核验要求（`hooks/module_stage.py`）

- 新增 `documentation_baseline_present(root) -> bool`：`root / "docs" / "DOCUMENTATION-BASELINE.md"` 存在（含符号链接，交给核验报 invalid）。
- `describe()`：`stop_node(...) == "final-gate"`、`role_kind != "coordinator"`、基线存在时，在 notes 里加一行（按 `zh` 选语言、按宿主选入口）：
  - 中文：`- 文档核验：项目有文档基线，最终验收前跑 <入口> <模块>，把结果写进验收消息的「验收结果」：现状类 update 没改过、target 文档有删改、外部文档未核验的，逐条写明；attention 不卡验收。`
  - 英文：`- Documentation check: this project has a documentation baseline; before the final acceptance run <entry> <module> and put the result under the acceptance results: name each current-state update left unchanged, each target document with deletions, and each external document as unverified; attention does not block the acceptance.`
  - 入口：Claude `/spec-guard:documentation-verification`，Codex `$spec-guard-ops` 的 documentation 一节（沿用 `COMMANDS` 的宿主分法）。
- 其他输出逐字不变；没有基线时这一行不出。

### 改动 3 规则文字（`references/node-rules.md`、`references/workflow-checkpoints.md`）

- `node-rules.md`：
  - 「Spec 交审」的文档建议句后加：项目有文档基线时，按基线的关注点提，采纳的写进本 Spec 的 `Documentation impact` 表。
  - 「Plan 交审」加附加项：文档影响（项目有文档基线时，列影响表里的 `update`／`create` 与 Plan 的 `Documentation delivery`；
    `update` 指向 `target` 文档时只补充，不删改未实现的目标）。
  - 「最终验收」加一条：项目有文档基线时，验收前跑文档核验，按状态写结果（假设 6），`target` 文档改过的把差异原样附上。
- `workflow-checkpoints.md` 的「文档建议」一节：加一段写明三段链（建议 → 影响 → 核验）在有基线时怎么接，以及 `target` 只补充的规则（假设 10）。
- 体积：`node-rules.md` 每节只加一两句；`test_workflow_checkpoints.py`／`test_stop_rules.py` 里对体积或短语的断言如需跟着改，一并改。

### 改动 4 说明（`references/documentation-verification.md`、`references/documentation-impact.md`、`commands/documentation-verification.md`、`skills/spec-guard-ops/SKILL.md`、`docs/design.md`、`docs/optional-features.md`）

- 核验参考与命令：按假设 6～9、11 改写结果说明与 `ready` 的含义；去掉「只要证据非空」的说法。
- 影响参考：「模块 Plan」一节加 `target` 只补充（假设 10）。
- Codex 入口：documentation 一节同步结果说明（一两句）。
- `docs/design.md:205`：`DOCUMENTATION-BASELINE.md` → `docs/DOCUMENTATION-BASELINE.md`；并在讲文档治理的地方（如有）补一句三段链与最终 gate 注入。
- `docs/optional-features.md` 的文档治理一节：写明有基线时最终 gate 会提示跑核验，核验按状态区分。

### 改动 5 回归

- `hooks/test_documentation_verification.py`：假设 6 的每种情况各一条（外部、target 改过有删、target 改过只增、target 没改、现状类改过、
  现状类没改、`#锚点`、Spec 未提交、非 git 目录、git 失败）；`create`／`deferred`／`pending` 判定不变各一条；原有用例照过。用临时 git 仓库，
  不依赖本仓库状态。
- `hooks/test_stop_rules.py`：最终 gate 有基线出这一行（中英各一，Claude／Codex 入口各一）；没基线不出；协调会话不出；模块会话出；
  非最终 gate 节点不出。
- 现有 `test-phase-guard.sh`、`test-verify-artifacts.sh` 不改、照过。

## 对使用者的影响

- 没建文档基线的项目：没有变化。
- 建了基线的项目：
  - 最终验收那一轮的阶段提示多一行「文档核验」，提醒跑核验并写进验收消息；
  - 核验更严：声明 `delivered` 的现状类文档，自本模块 Spec 提交以来没有改动时报 `attention`（之前是 `ready`）；
    `target` 文档有删改行时报 `attention`，提示删改未实现目标须单独批；外部文档标 `unverified`；
  - 核验 JSON 每项多了 `check`（和行数），原字段不变。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_documentation_verification.py
python3 -B plugins/spec-guard/hooks/test_stop_rules.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Acceptance criteria

- **AC1**：现状类文档（`verified`／`in-progress`／`pending`）`update` 声明 `delivered`：文件自本模块 Spec 首次提交以来改过时 `check` 为
  `changed`、状态可为 `ready`；没改过时 `check` 为 `unchanged`、状态为 `attention` 并写明路径。已提交与未提交的改动都算改过。各有回归。
- **AC2**：`target` 文档：没改过不报 `attention`（`target-unchanged`）；改过给 `target-changed` 与增删行数；有删除行时加一条 `attention`
  说明删改未实现目标须单独批准。各有回归。
- **AC3**：`Authority` 为 URL 时结果为 `unverified`，证据非空即可，不跑 git；证据为空照旧 `invalid`。
- **AC4**：git 查不了（非仓库、Spec 未提交、命令失败）时 `check` 为 `unknown` 并有 `attention` 写明原因，不出现 `changed`／`unchanged`。
- **AC5**：`create`、`deferred`、`pending`、无 outcome、无基线（`absent`）、结构无效（`invalid`）的判定与改前相同；原有回归全部通过。
- **AC6**：最终 gate 那一轮、项目有基线时，串行与模块会话的完整阶段提示含「文档核验」一行（中英、Claude／Codex 入口正确）；
  协调会话、没有基线、非最终 gate 节点时不出，其余输出与改前逐字相同。
- **AC7**：停点规则的 Spec 交审、Plan 交审、最终验收三节与共享检查点规则的「文档建议」一节写明三段链与 `target` 只补充；
  只在「项目有文档基线时」生效的写法。
- **AC8**：仓库里所有说明文字的基线路径都是 `docs/DOCUMENTATION-BASELINE.md`（`grep` 不再有不带 `docs/` 的写法，测试代码的临时路径除外）；
  核验的命令说明、参考、Codex 入口不再说「证据非空即 ready」。
- **AC9**：`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全部通过；hook 输出仍是宿主接受的 JSON；不新增 `jq` 依赖。
- **AC10**：在一个临时消费者项目（有基线、一个模块走到最终 gate）里，用本 worktree 的插件跑 `phase-guard.sh` 看到「文档核验」一行，
  再跑核验命令得到 `changed`／`unchanged`／`target-changed`／`unverified` 各一项的真实输出，原文附进最终验收。

## 未决问题

- **Q1：「Plan 写文档影响」怎么落。** A（推荐，假设 2）：影响表留在 Spec，Plan 交审把 `update`／`create` 与交付表摆出来；格式不变，
  已建基线的 6 个项目不用迁移。B：把 `Documentation impact` 表挪进 Plan，Spec 只留文档建议；要改两个解析器、迁移已有项目的表，
  Spec 交审时就看不到影响决定。
- **Q2：最终 gate 的「文档核验」一行给谁。** A（推荐，假设 4）：串行与模块会话都给，协调会话不给（最终验收【交审】由模块会话写）。
  B：跟停点规则块一样只给串行，模块会话的提醒交给 module-crew（要另向 module-crew 提需求）。
- **Q3：`ready` 改不改名。** A（推荐，假设 9）：不改名，改说明；现状类 `update` 有了真实的「改过」检查，名实已接近，外部文档单列 `unverified`。
  B：改名为 `declared`（更诚实，但改 JSON 取值，用过它的说明与脚本要跟着改）。

## Boundaries

- **会做**：改动 1～5；todo 末尾记更新说明与「对使用者的影响」。
- **先问再做**：要让 hook 自己跑核验或跑 git；要改基线、影响表的表格式或状态集合；要检查 `create` 的交付物是否存在（D15 没要求）；
  要把核验结果计入 `verify-artifacts` 的判定或阻断验收；发现别的插件解析核验 JSON。
- **不做**：自动生成或修改业务文档；判断文档内容是否正确、代码是否符合文档；给提示加开关或配置项；改 `stop_node`、状态码组成、
  指纹算法；改账本读回提醒（归 `ledger-standalone-reminder`）；改其他插件仓库；改版本号与 CHANGELOG；重装或更新本机 spec-guard；
  改已完成模块（`documentation-verification` 等）的 Spec 与能力图那一行（现行行为以本模块为准）。

## 并行边界

- 独占：`spec/doc-chain.md`、`tasks/doc-chain/plan.md`、`tasks/doc-chain/todo.md`、`plugins/spec-guard/hooks/documentation_verification.py`、`plugins/spec-guard/hooks/test_documentation_verification.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/test_stop_rules.py`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/references/node-rules.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/documentation-verification.md`、`plugins/spec-guard/references/documentation-impact.md`、`plugins/spec-guard/commands/documentation-verification.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、`docs/design.md`、`docs/optional-features.md`
- 公共：无

## 与在开模块的重叠

- `ledger-standalone-reminder`（同一波）改阶段注入的账本读回提醒，主要在 `phase-guard.sh`；本模块不碰 `phase-guard.sh`、`test-phase-guard.sh`。
  可能重叠的是 `module_stage.py`、`docs/design.md`，以及它若改共享检查点规则时的 `workflow-checkpoints.md`／`test_workflow_checkpoints.py`；
  本模块对 `module_stage.py` 只加一个函数和 `describe()` 里一处 notes 追加，对 `docs/design.md` 只改第 205 行与一两句。重叠由模块协调核对后交用户定。
- `quiet-injection`、`rules-at-nodes` 已合入，本模块只调用 `stop_node` 与状态码现有行为，不改它们。
