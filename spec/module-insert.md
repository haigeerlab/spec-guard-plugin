# Spec: module-insert

## Objective

项目做到一半冒出新需求时，最常见的做法是在一个模块做完的检查点，把理顺的需求上下文交给 agent，问它插在哪、
让它改能力图。这很灵活，但全靠 agent 手改，可能把新模块排在依赖之前、改坏 Build order、顺手改动 `## 目标` 或
已有模块行，或者在当前模块做到一半时插入。

本模块把这种做法变成一条带校验的命令：agent 根据上下文提出新模块的 id、职责、依赖和插入位置并说明理由，命令
复用现有解析器校验，展示能力图改动前后的对比，用户明确确认后才写入能力图。之后照常先写并评审新模块的 Spec。它是新增模块的默认方式；Proposal 九步保留，
只在需要留下经过评审的决定记录时选用。

登记：2026-09-28 按用户决定直接插入能力图，未经 Proposal 流程
（`docs/decisions/2026-09-28-quick-insert.md`）。

## Contract

- **入口**：`module-insert.py --project <dir> --id <module-id> --responsibility <text> --depends-on <a,b|—>
  --anchor <after:<module-id>|end> [--confirm]`。Claude 命令 `/spec-guard:add-module`，Codex 经 `spec-guard-ops`
  skill。
- **检查点**：取 `module_stage.py` 选出的当前模块。它的 `todo.md` 里**既有已勾选项、又有未勾选项**（做到一半）时
  拒绝，并说明先完成当前模块；计划好但一项都没勾、或已全部完成时允许。能力图无效（`MAP_INVALID`）或不存在时拒绝。
- **校验**（全部通过才算有效）：
  - 把新行加进模块表、把新模块按锚点加进 Build order 后，新能力图通过 `capability_map.parse_map` 严格校验，
    即 id 为 kebab-case 且不重复、依赖存在、依赖排在新模块之前、无环、Build order 恰好包含每个模块一次；
  - 职责非空且为单行；
  - 用 `spec-digest.py` 比对：`## 目标` 摘要不变，所有已有模块的行摘要不变，已有模块在 Build order 中的相对顺序
    不变；
  - `spec/<id>.md` 已存在时拒绝，不覆盖。
- **插入位置**：模块表中新行放在锚点模块那一行之后（`end` 时放在表末）；Build order 中新模块作为单独一步，放在
  锚点所在那一步之后（`end` 时放在最后）。
- **预览**（默认）：只读，输出新行、新 Build order、能力图的统一 diff，以及插入后当前模块会不会变；失败时说明
  是哪一条校验、非零退出。
- **写入**（`--confirm`）：重新执行全部检查后，只写 `spec/CAPABILITY-MAP.md`，用同目录临时文件加原子替换。
  不创建 Spec 骨架：阶段判定只看 `spec/<id>.md` 是否存在，空骨架会让阶段直接跳到 `NEEDS_PLAN`，绕过「先写并评审
  Spec」。写入后新模块若成为当前模块，阶段为 `NEEDS_SPEC`。不改 `.agent/state.json`、`tasks/`、Proposal 文件，不做
  任何 Git 或远端操作。
- **agent 行为**（命令与 skill 文本）：先根据用户给的上下文提出字段和插入位置并说明理由，运行预览，原样展示，
  等用户明确确认后才加 `--confirm`；用户改了任一字段就重新预览。
- **阶段提示**：全部模块完成（`DONE`）时，建议下一步改为指向 `/spec-guard:add-module`，并说明需要留痕时用 Proposal。
- **与 Proposal 的关系**：互不依赖。本命令不修改 `spec/proposals/`。插入会改变 Build order，但不改变目标、已有行
  和已有模块的相对顺序，因此已发布 Proposal 的新鲜度判定不变（`proposal_review.py` 只比对这些，以及依赖和锚点的先后）。
  唯一例外：新模块 id 与某份 Proposal 要新增的模块 id 相同，那份 Proposal 会被判为 `proposal-module-already-present`。
  预览时若本地 `spec/proposals/` 里有同 id 的 Proposal，给出提醒。

## Commands

```text
python3 plugins/spec-guard/hooks/module-insert.py --project <dir> --id <id> --responsibility <text> \
  --depends-on <a,b|—> --anchor <after:<id>|end>            # 预览
python3 plugins/spec-guard/hooks/module-insert.py ... --confirm   # 确认后写入
python3 -B plugins/spec-guard/hooks/test_module_insert.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
```

## Project structure

```text
plugins/spec-guard/hooks/module-insert.py        -> 预览、校验与确认后写入
plugins/spec-guard/hooks/test_module_insert.py   -> 回归
plugins/spec-guard/hooks/module_stage.py         -> DONE 提示指向本命令
plugins/spec-guard/commands/add-module.md        -> Claude 入口
plugins/spec-guard/skills/spec-guard-ops/SKILL.md -> Codex 入口（add-module 一节）
README.md, docs/workflow.md                      -> 用户文档
```

## Testing strategy

`test_module_insert.py` 在临时项目上运行，每条校验都有反例：

- 正例：`after:` 与 `end` 两种锚点；预览不写任何文件；`--confirm` 只改能力图、不建任何新文件，写入后能力图
  通过严格解析，阶段变为新模块的 `NEEDS_SPEC`（新模块排在当前模块之前时）；
- 检查点：当前模块有 Plan 但一项都没勾时放行；
- 反例：当前模块做到一半（既有已勾选、又有未勾选项）；能力图无效或缺失；id 重复或不合法；未知依赖；依赖排在锚点之后；锚点不存在；职责为空
  或多行；`spec/<id>.md` 已存在；每个反例都断言没有写任何文件；
- 已有内容不变：写入前后目标摘要、已有行摘要、已有模块相对顺序一致；
- `test-phase-guard.sh` 断言 DONE 提示指向 `/spec-guard:add-module`。

## Boundaries

- Always：先预览再确认；复用 `capability_map.parse_map`、`spec-digest.py` 与 `module_stage.py`，不复制它们的算法；
  失败时不留下半写的文件。
- Ask first：修改或删除已有模块、调整已有模块顺序、改写 `## 目标`——这些不属于本命令，需人工改能力图并评审。
- Never：在无确认时写文件；创建或覆盖 Spec；改 `.agent/state.json`、`tasks/`、Proposal 文件；执行 Git 或远端操作。

## Success criteria

- 在一个已完成若干模块的项目里，用户给出需求上下文，一次预览、一次确认就能把新模块插进能力图，阶段提示随即指向
  这个新模块的下一步（写并评审 Spec）。
- 所有反例都被拒绝且不改任何文件；现有回归和 `validate.sh` 保持通过。
