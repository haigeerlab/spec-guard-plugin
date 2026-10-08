# Spec: project-config

## Objective

插件的可调项散落在四处：`setup-convention --dispatch` 写进约定块的一行标记、`tracker-default` 管的 `.agent/tracker.json`、
写死在规则文本里的评审节奏，以及根本不存在的产物语言。后果有两个：

- 产物语言没人决定。本仓库 `spec/*.md` 中文 39 份、英文 18 份，`plan.md` 中文 30、英文 17、混合 9；写哪种语言取决于
  当时模型受模板（中文）、上游 skill（英文）和会话长度的哪股力量更大。
- 单个模块的 Spec 评审与 Plan 评审几乎总被连着批（2026-10-08 一个会话里两次批准的间隔多在 2 分钟内），
  但规则只有"分别评审"一种节奏，项目无法选择合审。

本模块给项目一个入库的配置文件和一个查看／设置入口，首批两项可配置，并把已有的两项汇总显示在同一处。

登记：2026-10-08 经 `/spec-guard:add-module` 插入能力图。同批后续模块：`module-suspend`、`runtime-state-layout`。

## Assumptions

用户已于 2026-10-08 确认：

1. **语言分层。** 结构关键字（能力图表头、`## 目标`／`## Goal`、勾选框、`gate`／`report`、各类标记行）由插件固定，
   不随配置变；产物正文语言由使用插件的项目决定；对话语言属于个人或宿主设置，不归插件管。
2. **配置文件** 为 `.agent/config.json`，入库、团队共享，Claude 与 Codex 读同一份。与 `.agent/tracker.json` 同目录。
3. **首批配置项**：`artifactLanguage`、`reviewCadence`。`dispatch`（约定块标记）与默认事项后端（`tracker.json`）
   只在总览里显示当前值和来源，不搬家、不改它们的设置入口。`contextHint`、`defaultCheckpoint` 本次不做。
4. **`artifactLanguage`** 只管新写的产物，已有产物不回头翻译。未设置时不注入任何内容，现有项目行为不变。
5. **`reviewCadence`** 默认 `separate`（保持现状）。`combined` 表示：写入能力图后一次给出 Spec 与 Plan、一次批准；
   出现预览时未确认过的新决策、范围不清或高风险不可逆改动时，仍退回分两次评审。合并永远由用户进行。
6. **hook 只读配置**，只注入已设置且会影响模型行为的项（这两项），各一行；不写文件。
7. **本仓库** 交付时设 `artifactLanguage = zh-CN`、`reviewCadence = combined`。
8. **范围收窄说明**：讨论中提过"setup 时按已有产物预填语言"。本模块不做自动探测，只在 `setup-convention` 的输出里
   提示可以用 `/spec-guard:config` 设置产物语言；预填留待有需求时再加。

## Contract

### 配置文件 `.agent/config.json`

```json
{
  "version": 1,
  "artifactLanguage": "zh-CN",
  "reviewCadence": "combined"
}
```

- `version` 必须为 `1`；其余键都可省略。
- `artifactLanguage`：语言标签，形如 `zh-CN`、`en`、`ja`、`pt-BR`（`^[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?$`）。
- `reviewCadence`：`separate` 或 `combined`。
- 出现未知键、类型或取值不合法、JSON 解析失败，都算**配置无效**。无效时不按默认值静默处理（见下方注入与校验）。

### `hooks/project_config.py`（唯一的读取与校验实现）

- `load(root)` 返回 `(values, problems)`。文件不存在时返回空值且无问题；
  phase-guard、verify-artifacts、config 命令都调用它，不各自解析。
- `show`：逐项列出生效值和来源。`artifactLanguage`、`reviewCadence` 的来源是配置文件或"未设置（默认）"；
  `dispatch` 读约定块里的标记行；默认事项后端读 `tracker.json`，并写明各自去哪里改（`setup-convention --dispatch`、
  `tracker-default`）。配置文件被 `.gitignore` 忽略时（`git check-ignore`）加一条警告：团队看不到这份配置。
- `set <key> <value>`／`unset <key>`：默认只预览，显示改前改后；带 `--confirm` 时原子写入并读回。只接受首批两项，
  对 `dispatch` 和事项后端给出对应命令的指引，不代为修改。

### 命令

- Claude：新增 `commands/config.md`（`/spec-guard:config`），使用规范引导段。
- Codex：`skills/spec-guard-ops/SKILL.md` 新增 `config` 一节，参数与命令一致（command-parity 检查器覆盖）。

### 阶段注入

- `module_stage.py` 通过 `project_config.load` 读取配置，在阶段摘要中追加：
  - 设了 `artifactLanguage`：`Artifact language: <tag> — write new spec, plan and todo prose in it; structural keywords stay as defined.`
  - 设了 `reviewCadence = combined`：`Review cadence: combined — after the capability map is written, present the Spec and the Plan together for one approval; split them when a new decision, unclear scope or a high-risk change appears.`
  - `separate` 或未设置：不追加。
  - 配置无效：追加一行 `Project config: invalid (<原因>) — run /spec-guard:config.`，其余配置项一律不注入。
- 没有配置文件时，所有现有用例的输出逐字节不变。

### 规则文本

- `references/workflow-checkpoints.md` 新增 `## 评审节奏` 一节，写明 `separate`／`combined` 的含义与退回条件。
  `## 按需求批量前置审` 不变。
- 两份约定块模板各加一行：产物语言与评审节奏以 `.agent/config.json` 为准，用 `/spec-guard:config` 查看。

### 校验

- `verify-artifacts.sh`：配置文件存在时用 `project_config.load` 校验；无效即失败并列出原因；不存在时不输出这一项。
- 同一判据在 phase-guard（注入"invalid"行）与 verify-artifacts（失败）两边都有正反回归。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_project_config.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash scripts/test-checkers.sh
/bin/bash scripts/validate.sh
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh evals/*/*.sh
```

## Testing strategy

- 先写测试并确认在当前代码上失败，再实现。
- `test_project_config.py`：缺文件、合法的完整配置与部分配置、未知键、错误 `version`、非法语言标签、非法节奏、
  非 JSON、非对象顶层；`show` 的来源标注；`set`／`unset` 只预览不写、`--confirm` 才写且读回一致；
  对 `dispatch` 和事项后端的 `set` 只给指引；`.gitignore` 忽略时的警告。
- `test-phase-guard.sh`：设语言→出现语言行；`combined`→出现节奏行；`separate`→不出现；配置无效→只出现 invalid 行；
  无配置文件→与现有输出逐字节一致。
- `test-verify-artifacts.sh`：合法配置通过、无效配置失败、无配置不输出该项。
- `test_workflow_checkpoints.py`：新一节标题与 `separate`、`combined`、退回条件、"合并永远由用户"；两份模板含指向配置的那一行。
- 变异：去掉未知键检查、把无效配置当成未设置、`separate` 也注入，三处都必须让测试变红。

## Boundaries

- Always：先红后绿；只有 `project_config.py` 一处解析配置；hook 只读；无配置时行为不变。
- Ask first：增加首批以外的配置项；改动 `dispatch` 或事项后端的存放位置；让 setup 自动写配置文件。
- Never：按配置翻译结构关键字；把无效配置静默当成默认值；hook 写文件；在 Spec、代码、测试、提交信息或 PR 中写入
  消费者项目的名称、模块或编号。

## Success criteria

- `/spec-guard:config` 与 Codex 的 `config` 能列出四项的生效值和来源，并能预览、确认、设置和取消首批两项。
- 设置后阶段提示每轮出现对应的一行，无效配置被报告而不是被忽略。
- `verify-artifacts` 能拦下无效配置。
- 本仓库设好 `zh-CN` 与 `combined` 后，阶段注入出现两行，其余输出不变。
- 无配置文件的项目所有既有回归逐字节通过。

## Open questions

- 无。
