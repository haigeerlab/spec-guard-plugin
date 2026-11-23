# Plan: project-sections

<!-- spec-guard: review codex-approved 6c358d1af516 -->

Spec：[spec/project-sections.md](../../spec/project-sections.md)（2026-11-24 批准）。

## 架构决定

- **配置键照现有写法加**：`project_config.VALIDATORS` 加 `projectSections`（校验函数 `valid_sections`），`DEFAULTS` 加 `{}`；`summary`、`show`、`render` 都按 `VALIDATORS` 遍历，自动带上。
  `set` 对 `projectSections` 单独处理：`--value` 整串按 JSON 解析（前导、尾随空白都允许），解析失败或不是对象就退出 2；`takeover`、`moduleTakeover` 原来的「以 `{` 开头才解析」规则不动。`config_lines` 不加分支，所以阶段提示不为它单独出一行；不合法时走现有的「已忽略 (projectSections-invalid)」一行。
- **骨架章节名只有一处**：`valid_sections` 判「与骨架同名」时读 `module_stage.DOC_SECTIONS`（`requirement` 含 `small`、`bug` 两组的名字，中英都比）。`project_config` 不能在模块顶层导入 `module_stage`（后者导入前者），在函数里延迟导入。
- **一个取值函数**：`module_stage.project_sections(root) -> {"requirement": (...), "design": (...), "regression": (...)}`，读不到或不合法时各为空元组；`flow_doc_problems` 与下一步提示都只用它。
  `flow_doc_problems`：每份已存在的文档在骨架章节之外加查该文档种类的追加章节；`bug`、`small` 只查 `requirement`（只有一份文件）。
- **提示**：`doc_step` 不改；`describe` 与模块会话提示在新流程模块的 `NEEDS_SPEC`（写需求文档）、`NEEDS_DESIGN`、`NEEDS_REGRESSION` 下一步后面加一句「另加本项目要求的章节：A、B。」（中英），没有声明时不加，输出与现在逐字相同。
  `NEEDS_SPEC` 时还没有需求文档、也就没有流程标记，分不出新旧流程：这一句只在项目声明了 `requirement` 追加章节时出现，措辞是「按新流程写需求文档时，另加本项目要求的章节：…」。
  这一点与 Spec AC4「老模块提示不变」在 `NEEDS_SPEC` 上冲突，已修订 Spec：AC4 的「老模块」指已有需求文档但没有流程标记的模块，随本 Plan 交用户批。
- **状态码**：quiet-injection 的状态事实（`describe` 里的 `facts`，普通视图与 `DONE` 两处）加上 `project_sections(root)`，章节设置增删时下一轮给完整提示，不只给简版一行；模块角色视图共用同一份 facts。

## 任务

编码由我在本会话完成，每个任务先写回归、确认失败再实现。

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**：C1。`valid_sections`、`VALIDATORS`／`DEFAULTS`、`set` 的 JSON 解析。回归（`test_project_config.py` 新类）：合法值预览后写入并读回；每类不合法值（不是对象、键不是三种文档、章节名为空、超长、含 `|`／`#`／换行、重复、与骨架同名、超过 10 个）退出 2 且文件不变（AC1）；
  文件里的值不合法时只有这个键失效、`artifactLanguage` 照常生效，`show` 标它无效（AC2）；`--value` 带前导空白的合法对象照样写入、不是 JSON 的值退出 2。现有 `Summary.test_sources_for_every_item` 的键集合加 `projectSections`（新增配置键必须改这一处）。验证：`test_project_config`。
- **Task 2**：C2。`project_sections`、`flow_doc_problems` 加查追加章节、提示加一句。回归：`test_flow_v2.py` 新类——声明 `design: ["浏览器兼容"]` 时 normal 档技术方案缺章节报失败、写了标题通过；bug、small 两档同时声明 `requirement`、`design`、`regression` 三类追加章节，
  前两类之外只有 `requirement` 的缺失会报失败、补上后通过；老模块不受影响（AC3、AC4）；`NEEDS_SPEC` 时声明了 `requirement` 才出现「按新流程写需求文档时」一句，没声明时逐字不变；带 `last_state` 调 `describe`，增删章节设置后返回完整提示而不是简版（状态码变化）；
  `NEEDS_DESIGN` 提示列出追加章节（中英），没有声明时与现在逐字相同（AC5）；`test-verify-artifacts.sh` 加两个端到端用例：声明了追加章节时缺章节失败、补上通过；`projectSections` 不合法而 `artifactLanguage` 合法时，verify-artifacts 报 `projectSections-invalid`、追加章节不生效（AC2）。验证：`test_flow_v2`、`test-verify-artifacts.sh`。
- **Task 3**：C3、C4。`references/doc-skeletons.md` 加「项目追加章节」一节；`commands/config.md` 配置表加一行（写法、作用范围、不需要原话、不注入阶段提示）；`docs/commands.md` 的配置说明（如有）同步；
  两份 `plugin.json` 0.94.0、CHANGELOG（M1：flow-doc-skeletons 与 project-sections）、README 中英 `--ref v0.94.0`。验证：`validate.sh`（版本一致性）。

## 会改哪些文件

- 新增：`tasks/project-sections/{plan,todo}.md`。
- 修改：`plugins/spec-guard/hooks/{project_config,module_stage}.py`、`plugins/spec-guard/hooks/{test_project_config,test_flow_v2}.py`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/references/doc-skeletons.md`、
  `plugins/spec-guard/commands/config.md`、`docs/commands.md`、两份 `plugin.json`、`CHANGELOG.md`、`README.md`、`README.en.md`。
- 新增依赖、锁文件：无。

## 风险

- **循环导入**：`project_config` 校验要读 `module_stage.DOC_SECTIONS`，而 `module_stage` 导入 `project_config`。缓解：函数内延迟导入；回归直接 `import project_config` 跑校验。
- **改变没有声明的项目的输出**：缓解：AC5 的逐字比对；Checkpoint 1 用本仓库新旧输出比对（本仓库不声明这个键）。
- **老版本 spec-guard 读到这个键**：0.84.0 起只忽略不认识的键（已有回归覆盖）；`commands/config.md` 写明。

## 检查点

- Checkpoint 1（report）：逐项给出 AC7 的证据（`/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 的退出码与末行，两份 `plugin.json` 版本）；变异（不读追加章节、校验不拦重复章节名）各让哪条回归变红；
  临时项目：用 `/spec-guard:config` 的脚本预览并写入 `projectSections`，新流程模块走到 `NEEDS_DESIGN` 看提示、缺章节时 verify-artifacts 失败、补上后通过；本仓库阶段提示、`/map --json`、verify-artifacts 与改动前逐字比对。证据记在 todo 的「证据」一节。
- Checkpoint 2（gate）：最终验收（M1 的版本 0.94.0 在本模块）；通过后在 PR #483 合并之后推送并开 PR，合并由用户进行；合并后用 `scripts/release.py` 发 0.94.0（发版、安装各要用户授权），通知 ecosystem-lead 与 S110 各方。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 未决问题

- 无。

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=5 sha256=0dd984ea2456 -->
<!-- spec-guard: codex-review round=2 blocking=0 sha256=126ffead4c23 -->
