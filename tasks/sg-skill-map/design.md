# 技术方案: sg-skill-map

<!-- spec-guard: review approved c776355a23fb -->

需求文档：`spec/sg-skill-map.md`（用户 2026-11-27「确认需求」）。照已批总体技术方案 7.1 节与第 7 节模块 7 那一行，不重新选型。

## 现状调研

查了下面这些（spec-guard 主干 `d531fd2a` 加本分支）：
- **阶段提示里点名 skill 的地方**：只有需求确认停点（`module_stage._requirement_hint`，「先用 agent-skills 的 interview-me…」）与老流程重要 Spec 的交审步骤；`COMMANDS["codex"]`（`module_stage.py:1725` 起）只给 Codex 宿主映射 `/plan`、`/build` 等命令的写法，不是点名。
- **能判断的位置**：`requirement_wait()`（需求等确认）与 `requirement_review()`（模块 5，有没有审查记录）；`overall_wait()`（总体技术方案关卡）；`design_waits()`（技术方案等审或等批）；`at_final_gate()`（`module_stage.py:1865`，最终 gate）；`stop_node()`（`:1960` 起）按这些给停点。
- **提示里加一行的写法**：`_describe_body` 里 `risk_list_line`、`design_outline_line`（模块 5、6）各返回 `(fact, line)`，line 接在 `counts` 后面，fact 进状态码（`info.update(facts=…)`）。
- **todo 的结构**：`tasks/<id>/todo.md` 是勾选清单加「证据」一节；`regression_view._section_lines(text, names)` 能取某一节的行（带是否在代码块里）。
- **`/map --json`**：`map_view.build()` 每个模块一行字典（`:515` 起），字段由 `interface.json` 的 `mapView.flow.fields` 说明；`test_map_view.MODULE_KEYS` 钉住字段集合。`map_view.py` 文件头写着 JSON 契约在 `spec/map-view.md`，但那是已完成模块的需求文档，1.15 以后加的字段（`important`、`designApproval`、`requirementReview` 等）都只写进了 `interface.json`，`spec/map-view.md` 里一个都没有。
- **并行时的模块视角**：`role_view()`（`:2562`）给标了「模块」角色的 checkout 出它自己模块的提示，`_role_facts()`（`:2660`）给它的状态码；项目视角的行接在 `_describe_body` 里。
- **完成态**：`module_state()` 的 `DONE` 不只看 todo 全部勾选——合并是自动的新流程模块有有效的合并前验证时，没勾的最终 gate 也算完成（`:1543` 附近）。
- **钉接口版本的测试**：`test_map_view.py:176`、`test_sg_review_rules.py:568`、`test_sg_design_outline.py:280` 都写着 `1.27`。
- **下游**：autopilot-hub `origin/main`（`b3aa2ae`）与 module-crew（`14a8221`）上 `git grep -e skillLog -e 'Skill 使用记录' -e MODULE_KEYS -e 'set(module)'`（先只查 `*.py`），第 2 轮审查后对全部受版本控制的文件再查 `skillLog`、`Skill 使用记录`，都没有命中：不读 `skillLog`、也不枚举 `/map` 的字段集合；hub 模块 8 还没写，按本方案读新字段。最终验收前按这两个提交再核一次。

没查的：其他已装 spec-guard 的项目里有没有 todo 已经用了「Skill 使用记录」这个标题（不太可能，新写法）。

## 影响面

路径都从仓库根目录写起；越界检查按这里引用的路径判定范围。

| 文件 | 改什么 |
|---|---|
| `plugins/spec-guard/hooks/module_stage.py` | 新函数 `skill_position`、`skill_line`、`skill_log`、`skill_log_problems`、`skill_reminder_line`；`_describe_body` 接上两行与状态码事实 |
| `plugins/spec-guard/hooks/map_view.py` | 每个模块加 `skillLog`；文件头注明 1.15 以后的字段以 `interface.json` 为准 |
| `plugins/spec-guard/hooks/verify-artifacts.sh` | 多调一个 `skill_log_problems` |
| `plugins/spec-guard/interface.json` | 升 `1.28`：`mapView.flow.fields.skillLog`；顺带把 #530 已改的 `takeover.notes` 一起发出去（不再改） |
| `plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md` | 新增「skill 对照」一节；「出事处理」、发版段落、能力图审阅各补一句指向 |
| `plugins/spec-guard/references/doc-skeletons.md` | Plan 一节说明 todo 里「Skill 使用记录」的写法 |
| `plugins/spec-guard/hooks/test_sg_skill_map.py`（新）、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test_sg_review_rules.py`、`plugins/spec-guard/hooks/test_sg_design_outline.py`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh` | 正反例；三处钉 `1.27` 的断言改成「不低于 1.27」，`MODULE_KEYS` 加 `skillLog`，不删断言 |
| `scripts/validate.sh` | 登记新测试文件 |
| `docs/workflow.md` | 使用者说明一句 |
| `CHANGELOG.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、`README.md`、`README.en.md`（**条件**） | 单独发 0.101.0 时升版本号与 `--ref`、CHANGELOG 写 `[0.101.0]`（含 #530 的接口说明修正）；不单独发时只把 CHANGELOG 写进 `[未发布]` |

## 实现方案

### 1. 位置判断（需求规则 2、3）

`skill_position(root, module, stage)` 返回下面之一或 `None`，按顺序先中先定，所以任一时刻只有一个：
1. 不是新流程模块 → `None`；
2. `requirement_wait()` 为真：`requirement_review()` 的 `status` 是 `missing` → `"review-first"`，否则 → `"confirm"`；
3. `overall_wait()` 为真 → `"overall"`；
4. `stage == "NEEDS_DESIGN"`，或 `stage == "NEEDS_REGRESSION"` 且 `design_waits()` 不是 `None` → `"design"`；
5. `stage == "BUILDING"`：`at_final_gate()` → `"final"`，否则 → `"build"`；
6. 其他 → `None`。

### 2. 点名那一行（需求规则 2、3、3a、7a、15）

`skill_line(root, module, stage, zh)` 按位置取一张固定表（项目视角接在 `_describe_body`；模块角色的 checkout 由 `role_view()` 按它自己的模块与阶段同样接上一行）（中英文两份），返回 `"- Skill：…"`。每个位置一句：skill 名（agent-skills 裸名，其他插件写 `delegate:review`、`artifact-diagramming`），括号里的条件照需求原文，句末是记录要求——`review-first`、`confirm`、`overall`、`design` 写「写 todo 时补进 Skill 使用记录」，`build`、`final` 写「记进 todo 的 Skill 使用记录」；`build` 句末再加情境触发的一句（画图、数据迁移、登录权限、浏览器验证、性能、文档先在已装插件里找）。

项目视角不另进状态码（`requirement_review_fact`、`design_fact` 等已覆盖位置的变化）；模块角色的 `_role_facts()` 只记阶段、Spec／Plan 状态与停点，从「先审一轮」切到「确认停点」时这些可能都不变，所以把 `skill_position` 加进 `_role_facts()`。

### 3. 记录解析（需求规则 7、10）

`skill_log(root, module)`：老流程 `None`；新流程读 `tasks/<id>/todo.md` 的 `## Skill 使用记录`／`## Skill log` 一节（`regression_view._section_lines`），按需求第 10 条的四步解析：只看不在代码块里、以 `- ` 开头的行；用第一个「：」或「:」切 `place`；内容去掉首尾空白与句末标点后等于两种「没有现成的 skill」写法之一（英文不分大小写）→ `none`；否则按「、」「，」「,」「；」「;」拆、去空项与重复。读不了、没有这一节都返回 `[]`。

`map_view.build()` 每个模块加 `"skillLog": skill_log(root, module)`。

### 4. 最终验收提醒（需求规则 12、13、15）

- `skill_reminder_line(root, module, stage, zh)`（项目视角在 `_describe_body`，模块角色在 `role_view()`，fact 同时进 `_role_facts()`）：`skill_position` 是 `"final"` 且 `skill_log` 为空 → 返回 `(("skill-log", "empty"), "- Skill 使用记录：还没有记录；最终验收前把用过的 skill 记进 todo 的「Skill 使用记录」，找不到的写「没有现成的 skill，按常规做法来」")`，fact 进状态码；有记录 → `(None, "")`。
- `skill_log_problems(root, module)`：新流程模块在最终 gate，或 `module_state(root, module)["stage"] == "DONE"`（不自己数勾选框），而 `skill_log` 为空 → `[("warn", …)]`，否则 `[]`；`verify-artifacts.sh` 接在 `design_outline_problems` 后面。

### 5. 规则文字（需求规则 4～6）

- `workflow-checkpoints.md` 新增「skill 对照」一节：阶段提示点名的六个位置（指向阶段提示）；对不上阶段的五处（能力图 planning-and-task-breakdown、质量底线 constraint-driven-development、出事自动修 debugging-and-error-recovery、发版与安装验证 shipping-and-launch、上线之后 observability-and-instrumentation）；情境触发；不进主流程的两个；记录写法与「写 todo 时补进」。「出事处理」一节与发版段落各补一句「skill 见『skill 对照』」。
- `node-rules.md`「能力图审阅」补一句 planning-and-task-breakdown。「最终验收」一节不加：节点规则是整节附在提示里的静态文字，没法按记录空不空来决定出不出；提醒只由 `skill_reminder_line()` 动态给。
- `doc-skeletons.md` 的 Plan 一节说明 todo 可以有「Skill 使用记录」一节及写法。

### 6. 接口

`interface.json` 升 `1.28`：`mapView.flow.fields.skillLog`（含义、解析规则、位置、`null`／`[]` 的区别）。契约以 `interface.json` 为准，不改 `spec/map-view.md`（已完成模块的需求文档，1.15 起的字段都没写进去）。`test_map_view.py` 的接口版本断言改成 `1.28`；`test_sg_review_rules.py`、`test_sg_design_outline.py` 里钉 `1.27` 的版本断言改成「主版本 1、次版本不低于 27」（它们钉的是各自那一版加的字段还在），本模块新测试另断言等于 `1.28`。

## 接口和数据改动

| 位置 | 改动 | 旧调用方 |
|---|---|---|
| `/map --json` 每个模块 `skillLog` | 新字段 | 不读；hub 模块 8 将读它 |
| 阶段提示 | 新流程模块多一行「- Skill：…」，最终 gate 记录为空时再多一行 | 不读 |
| verify-artifacts | 新流程模块在最终 gate 或已完成而记录为空时多一条警告 | 不判失败，退出码不变 |
| todo | 新的可选一节「Skill 使用记录」 | 勾选清单解析不读这一节的列表项（不是 `- [ ]` 写法） |

## 风险与回滚

- **todo 的勾选解析误读记录行**：记录行是 `- 关卡：…`，不是 `- [ ]`／`- [x]`，现有勾选解析只认方括号写法；用例钉住「加了这一节后进度不变」。
- **提示变长**：每个新流程阶段最多多两行。
- **记录不属实**：不核对（需求规则 9），只提醒有没有记。
- **回滚**：一个 PR，revert 即可；todo 里写下的记录留着无害。

## 方案取舍

- **位置用一个函数按顺序判定**：选这样，保证任一时刻只有一行；没选在各个提示函数里各加一句，那样容易重叠、也难测。
- **点名行不进状态码、提醒行进**：点名行的内容由已在状态码里的事实决定，再进一次没有意义；提醒行取决于 todo 内容，必须进。
- **记录解析在 spec-guard、不在 hub**：hub 只读 `/map --json`（总体技术方案 A11），解析规则只有一份。
- **不为写 todo 之前的关卡另设存放处**：写 todo 时补记，少一个文件、少一种格式。

## 待定问题

- **发版方式**（交用户定）：模块 7 单独发 0.101.0（本模块 PR 里改版本号与 CHANGELOG，连同 #530 的接口说明修正一起发出），还是先不发。
- 技术方案批准后，把 `skillLog` 的位置、字段与 todo 写法回告 ecosystem-lead（S7）：这一步写成 Plan 里的一个任务——经 agent-relay 发到线程 `autopilot-m5-7`，读回投递结果，把消息编号写进本模块 todo 的「证据」；发送失败时这一项不勾。

## 外部审查意见

<!-- spec-guard: design-review round=1 blocking=3 sha256=71c5ba5558e4 vendor=openai same-vendor=false criteria=design-v1 report=ce2f9829712f52c3937dd8072af834996c8888d459b067c39091f9109d2e3be6 -->

第 1 轮（Codex，gpt-5.6-sol high，3 条阻断、3 条建议），逐条对照代码核实：
1. （阻断）漏了 `spec/map-view.md` 这份 `/map --json` 契约 → 部分采纳：那是已完成模块的需求文档，1.15 以后加的字段都只写在 `interface.json`，改它要动已批准的需求文档；契约以 `interface.json` 为准，并在 `map_view.py` 文件头写明。
2. （阻断）模块角色 checkout 的提示路径没接 → 采纳：`role_view()` 与 `_role_facts()` 同样接上点名行与提醒。
3. （阻断）「todo 全部勾选」不等于完成 → 采纳：用 `module_state()` 的 `DONE`。
4. （建议）放宽版本断言后测不出升到 1.28 → 采纳：`test_map_view` 钉 `1.28`，新测试也断言 `1.28`。
5. （建议）下游结论核不了 → 采纳：写明 `git grep` 的范围与提交，最终验收前再核一次。
6. （建议）S7 没落成步骤 → 采纳：写成 Plan 任务，消息编号进 todo，发送失败不勾。
<!-- spec-guard: design-review round=2 blocking=1 sha256=a7f449d9cf59 vendor=openai same-vendor=false criteria=design-v1 report=88ecd5b2fc5f136c41dbd8cf7e84080965b8174cd4821bd1551c5317b08a8c3c -->

第 2 轮（Codex，带第 1 轮报告复审）：第 1 轮阻断 2 条已解决（模块角色、完成态），1 条仍判未解决（`spec/map-view.md`），新建议 3 条：
1. （阻断，未解决）仍不改 `spec/map-view.md` → **交用户定**：我仍建议不改（理由见第 1 轮第 1 条），请你在批准时选。
2. （建议）模块角色的状态码缺审查记录状态 → 采纳：`skill_position` 进 `_role_facts()`，加「先审一轮切到确认停点」的用例。
3. （建议）节点规则「最终验收」加静态提醒会在有记录时也出现 → 采纳：不加，只由 `skill_reminder_line()` 动态给。
4. （建议）下游只查了 `*.py` → 采纳：对全部受版本控制的文件再查，没有命中。
