# 技术方案: sg-skill-map

<!-- spec-guard: review pending -->

需求文档：`spec/sg-skill-map.md`（用户 2026-11-27「确认需求」）。照已批总体技术方案 7.1 节与第 7 节模块 7 那一行，不重新选型。

## 现状调研

查了下面这些（spec-guard 主干 `d531fd2a` 加本分支）：
- **阶段提示里点名 skill 的地方**：只有需求确认停点（`module_stage._requirement_hint`，「先用 agent-skills 的 interview-me…」）与老流程重要 Spec 的交审步骤；`CODEX_SKILLS`（`module_stage.py:1733` 附近）只给 Codex 宿主映射 `/plan`、`/build` 的写法，不是点名。
- **能判断的位置**：`requirement_wait()`（需求等确认）与 `requirement_review()`（模块 5，有没有审查记录）；`overall_wait()`（总体技术方案关卡）；`design_waits()`（技术方案等审或等批）；`at_final_gate()`（`module_stage.py:1865`，最终 gate）；`stop_node()`（`:1960` 起）按这些给停点。
- **提示里加一行的写法**：`_describe_body` 里 `risk_list_line`、`design_outline_line`（模块 5、6）各返回 `(fact, line)`，line 接在 `counts` 后面，fact 进状态码（`info.update(facts=…)`）。
- **todo 的结构**：`tasks/<id>/todo.md` 是勾选清单加「证据」一节；`regression_view._section_lines(text, names)` 能取某一节的行（带是否在代码块里）。
- **`/map --json`**：`map_view.build()` 每个模块一行字典（`:515` 起），字段由 `interface.json` 的 `mapView.flow.fields` 说明；`test_map_view.MODULE_KEYS` 钉住字段集合。
- **钉接口版本的测试**：`test_map_view.py:176`、`test_sg_review_rules.py:568`、`test_sg_design_outline.py:280` 都写着 `1.27`。
- **下游**：autopilot-hub `origin/main`（`b3aa2ae`）与 module-crew（`14a8221`）没有读 `skillLog`、也不枚举 `/map` 的字段集合（`git grep` 核过）；hub 模块 8 还没写，按本方案读新字段。

没查的：其他已装 spec-guard 的项目里有没有 todo 已经用了「Skill 使用记录」这个标题（不太可能，新写法）。

## 影响面

路径都从仓库根目录写起；越界检查按这里引用的路径判定范围。

| 文件 | 改什么 |
|---|---|
| `plugins/spec-guard/hooks/module_stage.py` | 新函数 `skill_position`、`skill_line`、`skill_log`、`skill_log_problems`、`skill_reminder_line`；`_describe_body` 接上两行与状态码事实 |
| `plugins/spec-guard/hooks/map_view.py` | 每个模块加 `skillLog` |
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

`skill_line(root, module, stage, zh)` 按位置取一张固定表（中英文两份），返回 `"- Skill：…"`。每个位置一句：skill 名（agent-skills 裸名，其他插件写 `delegate:review`、`artifact-diagramming`），括号里的条件照需求原文，句末是记录要求——`review-first`、`confirm`、`overall`、`design` 写「写 todo 时补进 Skill 使用记录」，`build`、`final` 写「记进 todo 的 Skill 使用记录」；`build` 句末再加情境触发的一句（画图、数据迁移、登录权限、浏览器验证、性能、文档先在已装插件里找）。

不进状态码：内容只取决于位置，位置由阶段、停点、档位决定，这些已在状态码里。

### 3. 记录解析（需求规则 7、10）

`skill_log(root, module)`：老流程 `None`；新流程读 `tasks/<id>/todo.md` 的 `## Skill 使用记录`／`## Skill log` 一节（`regression_view._section_lines`），按需求第 10 条的四步解析：只看不在代码块里、以 `- ` 开头的行；用第一个「：」或「:」切 `place`；内容去掉首尾空白与句末标点后等于两种「没有现成的 skill」写法之一（英文不分大小写）→ `none`；否则按「、」「，」「,」「；」「;」拆、去空项与重复。读不了、没有这一节都返回 `[]`。

`map_view.build()` 每个模块加 `"skillLog": skill_log(root, module)`。

### 4. 最终验收提醒（需求规则 12、13、15）

- `skill_reminder_line(root, module, stage, zh)`：`skill_position` 是 `"final"` 且 `skill_log` 为空 → 返回 `(("skill-log", "empty"), "- Skill 使用记录：还没有记录；最终验收前把用过的 skill 记进 todo 的「Skill 使用记录」，找不到的写「没有现成的 skill，按常规做法来」")`，fact 进状态码；有记录 → `(None, "")`。
- `skill_log_problems(root, module)`：新流程模块在最终 gate，或 todo 里的勾选项全部勾上，而 `skill_log` 为空 → `[("warn", …)]`，否则 `[]`；`verify-artifacts.sh` 接在 `design_outline_problems` 后面。

### 5. 规则文字（需求规则 4～6）

- `workflow-checkpoints.md` 新增「skill 对照」一节：阶段提示点名的六个位置（指向阶段提示）；对不上阶段的五处（能力图 planning-and-task-breakdown、质量底线 constraint-driven-development、出事自动修 debugging-and-error-recovery、发版与安装验证 shipping-and-launch、上线之后 observability-and-instrumentation）；情境触发；不进主流程的两个；记录写法与「写 todo 时补进」。「出事处理」一节与发版段落各补一句「skill 见『skill 对照』」。
- `node-rules.md`「能力图审阅」补一句 planning-and-task-breakdown；「最终验收」补一句「Skill 使用记录为空时补上」（守住 3200 字节）。
- `doc-skeletons.md` 的 Plan 一节说明 todo 可以有「Skill 使用记录」一节及写法。

### 6. 接口

`interface.json` 升 `1.28`：`mapView.flow.fields.skillLog`（含义、解析规则、位置、`null`／`[]` 的区别）。三处钉 `1.27` 的测试改成「主版本 1、次版本不低于 27」，原来钉的 1.27 字段断言不动。

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
- 技术方案批准后，把 `skillLog` 的位置、字段与 todo 写法回告 ecosystem-lead（S7）。
